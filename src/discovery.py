import os
import re
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import yt_dlp
from src.logger import get_logger
from src.config import get_config
from src.validators import Validator

class ContentDiscovery:
    """Automated content discovery from various sources."""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.processed_urls = set()  # In-memory cache of processed URLs
    
    def discover_from_channels(self, channel_ids: List[str], 
                               max_videos: int = 10,
                               hours_back: int = 24) -> List[str]:
        """Discover new videos from YouTube channels."""
        urls = []
        
        for channel_id in channel_ids:
            try:
                channel_urls = self._get_channel_videos(channel_id, max_videos, hours_back)
                urls.extend(channel_urls)
                self.logger.info(f"Found {len(channel_urls)} videos from channel {channel_id}")
            except Exception as e:
                self.logger.error(f"Error discovering from channel {channel_id}: {e}")
        
        return urls
    
    def _get_channel_videos(self, channel_id: str, max_videos: int, hours_back: int) -> List[str]:
        """Get recent videos from a channel."""
        channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlistend': max_videos,
        }
        
        urls = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                            upload_date = entry.get('upload_date')
                            
                            if upload_date:
                                try:
                                    upload_dt = datetime.strptime(upload_date, '%Y%m%d')
                                    if upload_dt >= cutoff_time:
                                        urls.append(video_url)
                                except:
                                    # If date parsing fails, include it anyway
                                    urls.append(video_url)
                            else:
                                urls.append(video_url)
        except Exception as e:
            self.logger.error(f"Error fetching channel videos: {e}")
        
        return urls
    
    def discover_from_keywords(self, keywords: List[str], 
                              max_results_per_keyword: int = 5) -> List[str]:
        """Discover videos by searching keywords."""
        urls = []
        
        for keyword in keywords:
            try:
                keyword_urls = self._search_videos(keyword, max_results_per_keyword)
                urls.extend(keyword_urls)
                self.logger.info(f"Found {len(keyword_urls)} videos for keyword: {keyword}")
            except Exception as e:
                self.logger.error(f"Error searching keyword {keyword}: {e}")
        
        return urls
    
    def _search_videos(self, query: str, max_results: int) -> List[str]:
        """Search YouTube for videos."""
        search_url = f"ytsearch{max_results}:{query}"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        urls = []
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            video_id = entry.get('id')
                            if video_id:
                                urls.append(f"https://www.youtube.com/watch?v={video_id}")
        except Exception as e:
            self.logger.error(f"Error searching videos: {e}")
        
        return urls
    
    def discover_from_playlist(self, playlist_url: str, max_videos: int = 20) -> List[str]:
        """Discover videos from a playlist."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlistend': max_videos,
        }
        
        urls = []
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            video_id = entry.get('id')
                            if video_id:
                                urls.append(f"https://www.youtube.com/watch?v={video_id}")
            
            self.logger.info(f"Found {len(urls)} videos from playlist")
        except Exception as e:
            self.logger.error(f"Error fetching playlist videos: {e}")
        
        return urls
    
    def discover_from_file(self, file_path: str) -> List[str]:
        """Load URLs from a file (one per line)."""
        urls = []
        
        if not os.path.exists(file_path):
            self.logger.warning(f"File not found: {file_path}")
            return urls
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):
                        # Validate URL
                        is_valid, _ = Validator.validate_youtube_url(url)
                        if is_valid:
                            urls.append(url)
                        else:
                            self.logger.warning(f"Invalid URL in file: {url}")
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
        
        return urls
    
    def filter_urls(self, urls: List[str], 
                   min_duration: Optional[int] = None,
                   max_duration: Optional[int] = None,
                   exclude_processed: bool = True) -> List[str]:
        """Filter URLs based on criteria."""
        filtered = []
        
        for url in urls:
            # Skip if already processed
            if exclude_processed and url in self.processed_urls:
                continue
            
            # Basic validation
            is_valid, _ = Validator.validate_youtube_url(url)
            if not is_valid:
                continue
            
            # Duration filtering would require fetching video info
            # For now, just validate URL
            filtered.append(url)
        
        return filtered
    
    def mark_processed(self, url: str):
        """Mark a URL as processed."""
        self.processed_urls.add(url)

