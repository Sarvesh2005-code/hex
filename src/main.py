import argparse
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from src.downloader import VideoDownloader
from src.transcriber import Transcriber
from src.analyzer import ContentAnalyzer
from src.editor import VideoEditor
from src.uploader import YouTubeUploader
from src.logger import get_logger
from src.config import get_config
from src.cache import Cache
from src.validators import Validator
from src.reporter import Reporter

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_stage(stage_num, stage_name, color=Colors.OKBLUE):
    """Print formatted stage header."""
    print(f"\n{color}{Colors.BOLD}--- Stage {stage_num}: {stage_name} ---{Colors.ENDC}")

def process_single_video(url, args, config, cache):
    """Process a single video URL."""
    logger = get_logger()
    start_time = time.time()
    results = {
        'url': url,
        'success': False,
        'clips_found': 0,
        'clips_processed': 0,
        'errors': []
    }
    
    try:
        # 1. Download
        print_stage(1, "Acquisition", Colors.OKBLUE)
        downloader = VideoDownloader()
        
        # Check cache for metadata
        cached_metadata = cache.get_metadata(url)
        if cached_metadata:
            logger.info("Using cached metadata")
            video_path = cached_metadata.get('video_path')
            audio_path = cached_metadata.get('audio_path')
            if video_path and os.path.exists(video_path) and audio_path and os.path.exists(audio_path):
                logger.info("Using cached video/audio files")
            else:
                video_path, audio_path, video_info = downloader.download(url)
                cache.save_metadata(url, {'video_path': video_path, 'audio_path': audio_path, 'video_info': video_info})
        else:
            video_path, audio_path, video_info = downloader.download(url)
            cache.save_metadata(url, {'video_path': video_path, 'audio_path': audio_path, 'video_info': video_info})

        # 2. Transcribe
        print_stage(2, "Transcription", Colors.OKCYAN)
        
        # Check cache for transcript
        transcript = cache.get_transcript(url)
        if transcript:
            logger.info("Using cached transcript")
        else:
            model_size = args.model_size or config.get('models.transcriber.size') or 'small'
            transcriber = Transcriber(model_size=model_size)
            
            # Use canonical video ID from downloader if available
            video_id = None
            if 'video_info' in locals() and video_info and 'id' in video_info:
                video_id = video_info['id']
            # Fallback: Extract from filename (downloads/ID.ext) - reliable for existing cache
            elif 'video_path' in locals() and video_path:
                filename = os.path.basename(video_path)
                video_id = os.path.splitext(filename)[0]
            # Fallback to URL parsing (least reliable due to case sensitivity)
            elif "v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]
            
            with tqdm(desc="Transcribing", unit="words") as pbar:
                transcript = transcriber.transcribe(audio_path, video_id=video_id)
                pbar.update(len(transcript))
            cache.save_transcript(url, transcript)

        # 3. Analyze
        print_stage(3, "Analysis", Colors.OKGREEN)
        analyzer = ContentAnalyzer()
        clips_metadata = analyzer.analyze(transcript)
        
        if not clips_metadata:
            logger.warning("No viral clips found.")
            results['errors'].append("No viral clips found")
            return results
        
        results['clips_found'] = len(clips_metadata)
        logger.info(f"Found {len(clips_metadata)} potential viral clips.")
        for clip in clips_metadata:
            logger.info(f"- {clip.get('title', 'Untitled')} ({clip['start']}s - {clip['end']}s)")

        # Preview mode
        if args.preview:
            print_stage("Preview", "Review Clips", Colors.WARNING)
            print("\nClips to be processed:")
            for i, clip in enumerate(clips_metadata, 1):
                print(f"{i}. {clip.get('title', 'Untitled')} "
                      f"({clip['start']:.1f}s - {clip['end']:.1f}s) "
                      f"Score: {clip.get('virality_score', 'N/A')}")
            
            response = input("\nProcess all clips? (y/n): ").strip().lower()
            if response != 'y':
                logger.info("User cancelled processing")
                return results
            
            # Allow selection
            if args.select_clips:
                selected = input("Enter clip numbers to process (comma-separated, or 'all'): ").strip()
                if selected.lower() != 'all':
                    indices = [int(x.strip()) - 1 for x in selected.split(',')]
                    clips_metadata = [clips_metadata[i] for i in indices if 0 <= i < len(clips_metadata)]

        # 4. Edit
        print_stage(4, "Editing", Colors.OKGREEN)
        editor = VideoEditor()
        generated_clips = []
        
        workers = args.workers or config.get('processing.workers', 1)
        parallel = args.parallel or config.get('processing.parallel_clips', False)
        
        if parallel and workers > 1 and len(clips_metadata) > 1:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(editor.process_clip, video_path, clip_meta, transcript): clip_meta
                    for clip_meta in clips_metadata
                }
                
                with tqdm(total=len(clips_metadata), desc="Processing clips") as pbar:
                    for future in as_completed(futures):
                        clip_meta = futures[future]
                        try:
                            output_path = future.result()
                            if output_path:
                                logger.info(f"Created: {output_path}")
                                generated_clips.append((output_path, clip_meta))
                                results['clips_processed'] += 1
                        except Exception as e:
                            logger.error(f"Editing failed for clip {clip_meta.get('title')}: {e}")
                            results['errors'].append(f"Editing failed: {e}")
                        pbar.update(1)
        else:
            # Sequential processing
            for clip_meta in tqdm(clips_metadata, desc="Processing clips"):
                try:
                    output_path = editor.process_clip(video_path, clip_meta, transcript)
                    if output_path:
                        logger.info(f"Created: {output_path}")
                        generated_clips.append((output_path, clip_meta))
                        results['clips_processed'] += 1
                except Exception as e:
                    logger.error(f"Editing failed for clip {clip_meta.get('title')}: {e}")
                    results['errors'].append(f"Editing failed: {e}")

        # 5. Upload (Optional)
        if args.upload and generated_clips:
            print_stage(5, "Distribution", Colors.WARNING)
            profile_path = args.profile or config.get('upload.browser_profile')
            uploader = YouTubeUploader(profile_path)
            
            for path, meta in tqdm(generated_clips, desc="Uploading clips"):
                try:
                    success = uploader.upload_video(path, meta['title'], meta.get('description', ''))
                    if success:
                        logger.info(f"Successfully uploaded: {meta['title']}")
                    else:
                        logger.warning(f"Failed to upload: {meta['title']}")
                        results['errors'].append(f"Upload failed: {meta['title']}")
                except Exception as e:
                    logger.error(f"Upload error: {e}")
                    results['errors'].append(f"Upload error: {e}")
        
        results['success'] = True
        results['processing_time'] = time.time() - start_time
        
    except Exception as e:
        logger.exception(f"Error processing video {url}: {e}")
        results['errors'].append(str(e))
        results['success'] = False
    
    return results

def main():
    parser = argparse.ArgumentParser(
        description="OpenClip - Autonomous YouTube Clipper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main https://youtube.com/watch?v=VIDEO_ID
  python -m src.main https://youtube.com/watch?v=VIDEO_ID --upload --preview
  python -m src.main --batch urls.txt --workers 4
  python -m src.main https://youtube.com/watch?v=VIDEO_ID --model-size medium --verbose
        """
    )
    
    parser.add_argument("url", nargs='?', help="YouTube Video URL")
    parser.add_argument("--batch", help="Process multiple URLs from file (one per line) or comma-separated")
    parser.add_argument("--upload", action="store_true", help="Upload to YouTube automatically")
    parser.add_argument("--profile", help="Path to Chrome User Data for uploading")
    parser.add_argument("--model-size", choices=['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3'],
                        help="Whisper model size (default: from config)")
    parser.add_argument("--workers", type=int, help="Number of parallel workers for clip processing")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel clip processing")
    parser.add_argument("--preview", action="store_true", help="Preview clips before processing")
    parser.add_argument("--select-clips", action="store_true", help="Allow selecting which clips to process")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (only errors)")
    
    args = parser.parse_args()
    
    # Initialize logger and config
    logger = get_logger()
    config = get_config()
    
    # Configure logger based on flags
    if args.verbose:
        logger.set_verbose(True)
    if args.quiet:
        logger.set_quiet(True)
    
    # Initialize cache
    cache = Cache()
    if args.no_cache:
        cache.enabled = False
    
    # Validate inputs
    if not args.url and not args.batch:
        parser.error("Either URL or --batch must be provided")
    
    # Process URLs
    urls = []
    if args.batch:
        if os.path.exists(args.batch):
            # Read from file
            with open(args.batch, 'r') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        else:
            # Comma-separated list
            urls = [u.strip() for u in args.batch.split(',') if u.strip()]
    else:
        urls = [args.url]
    
    if not urls:
        logger.error("No URLs to process")
        return
    
    # Validate all URLs
    for url in urls:
        is_valid, message = Validator.validate_youtube_url(url)
        if not is_valid:
            logger.error(f"Invalid URL: {url} - {message}")
            return
    
    # Process videos
    all_results = []
    for url in urls:
        print(f"\n{Colors.BOLD}Processing: {url}{Colors.ENDC}")
        result = process_single_video(url, args, config, cache)
        all_results.append(result)
    
    # Summary
    reporter = Reporter(output_dir=config.get('system.output_dir', 'output'))
    reporter.print_summary(all_results)
    
    # Generate report if multiple videos processed
    if len(all_results) > 1:
        report_path = reporter.generate_report(all_results, format='json')
        print(f"\nDetailed report saved to: {report_path}")
    
    # Print errors
    for result in all_results:
        if result['errors']:
            print(f"\n{Colors.FAIL}Errors for {result['url']}:{Colors.ENDC}")
            for error in result['errors']:
                print(f"  - {error}")

if __name__ == "__main__":
    main()


