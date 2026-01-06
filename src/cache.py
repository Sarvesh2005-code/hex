import os
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from src.config import get_config
from src.logger import get_logger

class Cache:
    """Caching system for transcripts and metadata."""
    
    def __init__(self):
        config = get_config()
        self.enabled = config.get('cache.enabled', True)
        self.cache_dir = Path(config.get('cache.cache_dir', '.cache'))
        self.ttl_days = config.get('cache.ttl_days', 30)
        self.logger = get_logger()
        
        if self.enabled:
            self.cache_dir.mkdir(exist_ok=True)
            self.metadata_dir = self.cache_dir / 'metadata'
            self.transcript_dir = self.cache_dir / 'transcripts'
            self.metadata_dir.mkdir(exist_ok=True)
            self.transcript_dir.mkdir(exist_ok=True)
    
    def _get_video_id(self, url: str) -> str:
        """Extract or hash video ID from URL."""
        # Try to extract YouTube video ID
        if 'youtube.com' in url or 'youtu.be' in url:
            if 'v=' in url:
                return url.split('v=')[1].split('&')[0]
            elif 'youtu.be' in url:
                return url.split('/')[-1].split('?')[0]
        
        # Fallback to hash
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_path(self, video_id: str, cache_type: str) -> Path:
        """Get cache file path for video ID and type."""
        if cache_type == 'metadata':
            return self.metadata_dir / f"{video_id}.json"
        elif cache_type == 'transcript':
            return self.transcript_dir / f"{video_id}.json"
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")
    
    def _is_expired(self, cache_path: Path) -> bool:
        """Check if cache file is expired."""
        if not cache_path.exists():
            return True
        
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_time = file_time + timedelta(days=self.ttl_days)
        return datetime.now() > expiry_time
    
    def get_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached metadata for a video URL."""
        if not self.enabled:
            return None
        
        video_id = self._get_video_id(url)
        cache_path = self._get_cache_path(video_id, 'metadata')
        
        if self._is_expired(cache_path):
            if cache_path.exists():
                cache_path.unlink()
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                self.logger.debug(f"Cache hit for metadata: {video_id}")
                return data
        except Exception as e:
            self.logger.warning(f"Error reading cache: {e}")
            return None
    
    def save_metadata(self, url: str, metadata: Dict[str, Any]):
        """Save metadata to cache."""
        if not self.enabled:
            return
        
        video_id = self._get_video_id(url)
        cache_path = self._get_cache_path(video_id, 'metadata')
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            self.logger.debug(f"Cached metadata: {video_id}")
        except Exception as e:
            self.logger.warning(f"Error saving cache: {e}")
    
    def get_transcript(self, url: str) -> Optional[list]:
        """Get cached transcript for a video URL."""
        if not self.enabled:
            return None
        
        video_id = self._get_video_id(url)
        cache_path = self._get_cache_path(video_id, 'transcript')
        
        if self._is_expired(cache_path):
            if cache_path.exists():
                cache_path.unlink()
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                self.logger.debug(f"Cache hit for transcript: {video_id}")
                return data
        except Exception as e:
            self.logger.warning(f"Error reading cache: {e}")
            return None
    
    def save_transcript(self, url: str, transcript: list):
        """Save transcript to cache."""
        if not self.enabled:
            return
        
        video_id = self._get_video_id(url)
        cache_path = self._get_cache_path(video_id, 'transcript')
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(transcript, f, indent=2)
            self.logger.debug(f"Cached transcript: {video_id}")
        except Exception as e:
            self.logger.warning(f"Error saving cache: {e}")
    
    def clear_cache(self, video_id: Optional[str] = None):
        """Clear cache for specific video or all videos."""
        if not self.enabled:
            return
        
        if video_id:
            for cache_type in ['metadata', 'transcript']:
                cache_path = self._get_cache_path(video_id, cache_type)
                if cache_path.exists():
                    cache_path.unlink()
            self.logger.info(f"Cleared cache for: {video_id}")
        else:
            # Clear all
            for cache_path in list(self.metadata_dir.glob('*.json')) + list(self.transcript_dir.glob('*.json')):
                cache_path.unlink()
            self.logger.info("Cleared all cache")


