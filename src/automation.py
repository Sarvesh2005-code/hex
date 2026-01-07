"""
Main automation script for 24/7 autonomous operation.
"""
import os
import time
import sys
from datetime import datetime
from src.logger import get_logger
from src.config import get_config
from src.database import Database
from src.queue import JobQueue
from src.scheduler import Scheduler
from src.discovery import ContentDiscovery
from src.notifier import Notifier
from src.health import HealthMonitor
from src.ratelimit import RateLimiter
from src.main import process_single_video, Colors, print_stage

class Automation:
    """Main automation orchestrator."""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.db = Database()
        self.queue = JobQueue(self.db)
        self.scheduler = Scheduler()
        self.discovery = ContentDiscovery()
        self.notifier = Notifier()
        self.health_monitor = HealthMonitor(self.db)
        self.rate_limiter = RateLimiter(self.db)
        self.running = False
        
        # Load configuration
        self.schedule_interval = float(os.getenv('SCHEDULE_INTERVAL_HOURS', '6'))
        self.max_uploads_per_day = int(os.getenv('MAX_UPLOADS_PER_DAY', '5'))
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))
        
        # Setup scheduled tasks
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Setup scheduled tasks."""
        # Schedule content discovery
        self.scheduler.schedule_interval(
            self.schedule_interval,
            self.discover_and_queue_content
        )
        
        # Schedule health checks
        self.scheduler.schedule_interval(
            self.health_check_interval / 3600,  # Convert seconds to hours
            self.perform_health_check
        )
        
        # Schedule daily summary
        self.scheduler.schedule_daily('23:00', self.send_daily_summary)
    
    def discover_and_queue_content(self):
        """Discover new content and add to queue."""
        self.logger.info("Starting content discovery...")
        
        # Get discovery sources from config/env
        channel_ids = os.getenv('YOUTUBE_CHANNEL_IDS', '').split(',')
        channel_ids = [c.strip() for c in channel_ids if c.strip()]
        
        keywords = os.getenv('DISCOVERY_KEYWORDS', '').split(',')
        keywords = [k.strip() for k in keywords if k.strip()]
        
        playlist_urls = os.getenv('PLAYLIST_URLS', '').split(',')
        playlist_urls = [p.strip() for p in playlist_urls if p.strip()]
        
        urls = []
        
        # Discover from channels
        if channel_ids:
            for channel_id in channel_ids:
                try:
                    channel_urls = self.discovery.discover_from_channels(
                        [channel_id], max_videos=10, hours_back=24
                    )
                    urls.extend(channel_urls)
                except Exception as e:
                    self.logger.error(f"Error discovering from channel {channel_id}: {e}")
        
        # Discover from keywords
        if keywords:
            try:
                keyword_urls = self.discovery.discover_from_keywords(keywords, max_results_per_keyword=5)
                urls.extend(keyword_urls)
            except Exception as e:
                self.logger.error(f"Error discovering from keywords: {e}")
        
        # Discover from playlists
        if playlist_urls:
            for playlist_url in playlist_urls:
                try:
                    playlist_urls_found = self.discovery.discover_from_playlist(playlist_url, max_videos=20)
                    urls.extend(playlist_urls_found)
                except Exception as e:
                    self.logger.error(f"Error discovering from playlist {playlist_url}: {e}")
        
        # Filter and add to queue
        filtered_urls = self.discovery.filter_urls(urls, exclude_processed=True)
        
        added_count = 0
        for url in filtered_urls:
            try:
                job_id = self.queue.add(url, priority=5)
                if job_id:
                    added_count += 1
                    self.discovery.mark_processed(url)
            except Exception as e:
                self.logger.error(f"Error adding URL to queue: {e}")
        
        self.logger.info(f"Discovered and queued {added_count} new videos")
        
        if added_count > 0:
            self.notifier.notify_health_alert(
                "info",
                f"Discovered {added_count} new videos and added to queue"
            )
    
    def process_queue(self):
        """Process jobs from the queue."""
        self.logger.info("Processing queue...")
        
        processed_count = 0
        max_jobs = self.max_uploads_per_day
        
        while processed_count < max_jobs:
            # Check rate limits
            can_upload, reason = self.rate_limiter.can_upload()
            if not can_upload:
                self.logger.info(f"Rate limit reached: {reason}")
                break
            
            # Get next job
            job = self.queue.get_next()
            if not job:
                self.logger.info("No pending jobs in queue")
                break
            
            job_id = job['id']
            url = job['url']
            
            self.logger.info(f"Processing job {job_id}: {url}")
            self.queue.mark_processing(job_id)
            
            try:
                # Process video (using main.py function)
                # Create a minimal args object
                class Args:
                    def __init__(self):
                        self.model_size = None
                        self.workers = 1
                        self.parallel = False
                        self.preview = False
                        self.select_clips = False
                        self.no_cache = False
                        self.upload = True
                        self.profile = None
                
                args = Args()
                from src.cache import Cache
                cache = Cache()
                
                result = process_single_video(url, args, self.config, cache)
                
                if result and result.get('success'):
                    self.queue.mark_completed(job_id)
                    self.rate_limiter.record_upload(success=True)
                    
                    # Record in database
                    self.db.add_video_record(
                        url=url,
                        clips_found=result.get('clips_found', 0),
                        clips_processed=result.get('clips_processed', 0),
                        processing_time=result.get('processing_time'),
                        status='completed',
                        metadata=result
                    )
                    
                    # Update statistics
                    today = datetime.now().date().isoformat()
                    self.db.update_statistics(
                        today,
                        videos_processed=1,
                        clips_created=result.get('clips_processed', 0),
                        uploads_successful=1
                    )
                    
                    # Send notification
                    if result.get('clips_processed', 0) > 0:
                        self.notifier.notify_upload_success(
                            f"Processed {result.get('clips_processed', 0)} clips",
                            url,
                            processing_time=result.get('processing_time')
                        )
                    
                    processed_count += 1
                else:
                    # Check if should retry
                    if self.queue.should_retry(job_id):
                        self.queue.retry_job(job_id)
                        self.logger.info(f"Job {job_id} will be retried")
                    else:
                        self.queue.mark_failed(job_id, str(result.get('errors', ['Unknown error'])))
                        self.rate_limiter.record_upload(success=False)
                        
                        # Send error notification
                        self.notifier.notify_processing_error(url, str(result.get('errors', ['Unknown error'])))
                        
                        # Update statistics
                        today = datetime.now().date().isoformat()
                        self.db.update_statistics(today, uploads_failed=1, errors_count=1)
            
            except Exception as e:
                self.logger.exception(f"Error processing job {job_id}: {e}")
                self.db.log_error(job_id, type(e).__name__, str(e))
                
                if self.queue.should_retry(job_id):
                    self.queue.retry_job(job_id)
                else:
                    self.queue.mark_failed(job_id, str(e))
                    self.notifier.notify_processing_error(url, str(e))
        
        self.logger.info(f"Processed {processed_count} jobs from queue")
    
    def perform_health_check(self):
        """Perform health check and send alerts if needed."""
        self.logger.info("Performing health check...")
        health = self.health_monitor.check_health()
        
        if health['status'] == 'unhealthy':
            self.notifier.notify_health_alert(
                "critical",
                f"System health check failed: {', '.join(health['errors'])}"
            )
        elif health['warnings']:
            self.notifier.notify_health_alert(
                "warning",
                f"Health warnings: {', '.join(health['warnings'])}"
            )
        
        return health
    
    def send_daily_summary(self):
        """Send daily summary notification."""
        stats = self.db.get_statistics(days=1)
        if stats:
            today_stats = stats[0]
            self.notifier.notify_daily_summary({
                'videos_processed': today_stats.get('videos_processed', 0),
                'clips_created': today_stats.get('clips_created', 0),
                'uploads_successful': today_stats.get('uploads_successful', 0),
                'uploads_failed': today_stats.get('uploads_failed', 0),
                'errors_count': today_stats.get('errors_count', 0),
                'total_time': today_stats.get('total_processing_time', 0)
            })
    
    def run(self):
        """Run the automation loop."""
        self.running = True
        self.logger.info("Starting automation system...")
        
        # Initial content discovery
        self.discover_and_queue_content()
        
        # Start scheduler in background
        import threading
        scheduler_thread = threading.Thread(target=self.scheduler.run_continuously, daemon=True)
        scheduler_thread.start()
        
        # Main processing loop
        while self.running:
            try:
                # Process queue
                self.process_queue()
                
                # Check quota and wait if needed
                wait_time = self.rate_limiter.wait_if_needed()
                if wait_time > 0:
                    self.logger.info(f"Rate limit reached, waiting {wait_time/3600:.2f} hours")
                    # Sleep in smaller chunks to allow interruption
                    sleep_interval = min(3600, wait_time)  # Sleep max 1 hour at a time
                    for _ in range(int(wait_time / sleep_interval)):
                        if not self.running:
                            break
                        time.sleep(sleep_interval)
                else:
                    # Normal sleep interval
                    time.sleep(300)  # Check every 5 minutes
                
            except KeyboardInterrupt:
                self.logger.info("Shutting down...")
                self.running = False
                break
            except Exception as e:
                self.logger.exception(f"Error in automation loop: {e}")
                time.sleep(60)  # Wait before retrying
        
        self.scheduler.stop()
        self.logger.info("Automation stopped")

def main():
    """Main entry point."""
    automation = Automation()
    automation.run()

if __name__ == "__main__":
    main()

