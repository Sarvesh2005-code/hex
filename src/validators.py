import re
import os
from typing import Tuple, Optional
from src.logger import get_logger

class Validator:
    """Input validation utilities."""
    
    YOUTUBE_URL_PATTERNS = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]
    
    @staticmethod
    def validate_youtube_url(url: str) -> Tuple[bool, Optional[str]]:
        """Validate YouTube URL and extract video ID."""
        if not url or not isinstance(url, str):
            return False, "URL must be a non-empty string"
        
        for pattern in Validator.YOUTUBE_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return True, video_id
        
        return False, "Invalid YouTube URL format"
    
    @staticmethod
    def validate_file_path(file_path: str, must_exist: bool = True) -> Tuple[bool, Optional[str]]:
        """Validate file path."""
        if not file_path or not isinstance(file_path, str):
            return False, "File path must be a non-empty string"
        
        if must_exist and not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}"
        
        # Check if directory is writable (for output files)
        if not must_exist:
            dir_path = os.path.dirname(file_path) or '.'
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    return False, f"Cannot create directory: {e}"
            elif not os.access(dir_path, os.W_OK):
                return False, f"Directory is not writable: {dir_path}"
        
        return True, None
    
    @staticmethod
    def validate_api_key(api_key: str, service: str = "gemini") -> Tuple[bool, Optional[str]]:
        """Validate API key format (basic checks)."""
        if not api_key or not isinstance(api_key, str):
            return False, f"{service} API key must be a non-empty string"
        
        if len(api_key) < 10:
            return False, f"{service} API key appears to be too short"
        
        return True, None
    
    @staticmethod
    def validate_video_duration(duration: float, min_duration: float = 10, max_duration: float = 3600) -> Tuple[bool, Optional[str]]:
        """Validate video duration."""
        if duration < min_duration:
            return False, f"Video duration ({duration}s) is too short (minimum: {min_duration}s)"
        
        if duration > max_duration:
            return False, f"Video duration ({duration}s) is too long (maximum: {max_duration}s)"
        
        return True, None


