import time
import schedule
from datetime import datetime, timedelta
from typing import Callable, Optional
from src.logger import get_logger
from src.config import get_config

class Scheduler:
    """Cron-like scheduling system for automated processing."""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.jobs = []
        self.running = False
    
    def schedule_interval(self, interval_hours: float, func: Callable, *args, **kwargs):
        """Schedule a function to run at regular intervals."""
        def wrapper():
            try:
                self.logger.info(f"Running scheduled task: {func.__name__}")
                func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in scheduled task: {e}")
        
        schedule.every(interval_hours).hours.do(wrapper)
        self.logger.info(f"Scheduled {func.__name__} to run every {interval_hours} hours")
    
    def schedule_daily(self, time_str: str, func: Callable, *args, **kwargs):
        """Schedule a function to run daily at a specific time."""
        def wrapper():
            try:
                self.logger.info(f"Running daily scheduled task: {func.__name__}")
                func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in scheduled task: {e}")
        
        schedule.every().day.at(time_str).do(wrapper)
        self.logger.info(f"Scheduled {func.__name__} to run daily at {time_str}")
    
    def schedule_hourly(self, func: Callable, *args, **kwargs):
        """Schedule a function to run every hour."""
        self.schedule_interval(1, func, *args, **kwargs)
    
    def run_pending(self):
        """Run all pending scheduled jobs."""
        schedule.run_pending()
    
    def run_continuously(self, interval: int = 60):
        """Run scheduler continuously, checking every interval seconds."""
        self.running = True
        self.logger.info(f"Scheduler started, checking every {interval} seconds")
        
        while self.running:
            try:
                self.run_pending()
                time.sleep(interval)
            except KeyboardInterrupt:
                self.logger.info("Scheduler stopped by user")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(interval)
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        schedule.clear()
        self.logger.info("Scheduler stopped")

