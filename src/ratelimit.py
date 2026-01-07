import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.logger import get_logger
from src.database import Database

class RateLimiter:
    """Rate limiting and quota management for YouTube uploads."""
    
    def __init__(self, db: Optional[Database] = None):
        self.logger = get_logger()
        self.db = db or Database()
        self.daily_limit = 6  # YouTube's default daily upload limit
        self.hourly_limit = 3  # Conservative hourly limit
        self.quota_reset_hour = 0  # Midnight UTC
    
    def can_upload(self) -> tuple[bool, Optional[str]]:
        """Check if upload is allowed based on rate limits."""
        today = datetime.now().date().isoformat()
        hour = datetime.now().hour
        
        # Check daily quota
        daily_count = self._get_daily_upload_count(today)
        if daily_count >= self.daily_limit:
            reset_time = datetime.now().replace(hour=self.quota_reset_hour, minute=0, second=0)
            if reset_time < datetime.now():
                reset_time += timedelta(days=1)
            return False, f"Daily quota reached ({daily_count}/{self.daily_limit}). Resets at {reset_time}"
        
        # Check hourly quota
        hourly_count = self._get_hourly_upload_count(today, hour)
        if hourly_count >= self.hourly_limit:
            next_hour = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            return False, f"Hourly quota reached ({hourly_count}/{self.hourly_limit}). Resets at {next_hour}"
        
        return True, None
    
    def record_upload(self, success: bool = True):
        """Record an upload attempt."""
        today = datetime.now().date().isoformat()
        hour = datetime.now().hour
        
        # Store in database
        setting_key = f"uploads_{today}"
        uploads = self.db.get_setting(setting_key, [])
        
        uploads.append({
            'hour': hour,
            'success': success,
            'timestamp': datetime.now().isoformat()
        })
        
        self.db.set_setting(setting_key, uploads)
        self.logger.debug(f"Recorded upload: success={success}, daily_count={len(uploads)}")
    
    def _get_daily_upload_count(self, date: str) -> int:
        """Get upload count for a specific date."""
        uploads = self.db.get_setting(f"uploads_{date}", [])
        return len([u for u in uploads if u.get('success', True)])
    
    def _get_hourly_upload_count(self, date: str, hour: int) -> int:
        """Get upload count for current hour."""
        uploads = self.db.get_setting(f"uploads_{date}", [])
        return len([u for u in uploads if u.get('hour') == hour and u.get('success', True)])
    
    def get_quota_status(self) -> Dict:
        """Get current quota status."""
        today = datetime.now().date().isoformat()
        daily_count = self._get_daily_upload_count(today)
        hour = datetime.now().hour
        hourly_count = self._get_hourly_upload_count(today, hour)
        
        return {
            'daily': {
                'used': daily_count,
                'limit': self.daily_limit,
                'remaining': max(0, self.daily_limit - daily_count),
                'percentage': (daily_count / self.daily_limit) * 100
            },
            'hourly': {
                'used': hourly_count,
                'limit': self.hourly_limit,
                'remaining': max(0, self.hourly_limit - hourly_count),
                'percentage': (hourly_count / self.hourly_limit) * 100
            }
        }
    
    def wait_if_needed(self):
        """Wait if rate limit is reached."""
        can_upload, reason = self.can_upload()
        if not can_upload:
            self.logger.info(f"Rate limit reached: {reason}")
            # Calculate wait time
            if "Daily quota" in reason:
                # Wait until next day
                reset_time = datetime.now().replace(hour=self.quota_reset_hour, minute=0, second=0)
                if reset_time < datetime.now():
                    reset_time += timedelta(days=1)
                wait_seconds = (reset_time - datetime.now()).total_seconds()
            else:
                # Wait until next hour
                next_hour = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                wait_seconds = (next_hour - datetime.now()).total_seconds()
            
            self.logger.info(f"Waiting {wait_seconds/3600:.2f} hours before next upload")
            return wait_seconds
        return 0

