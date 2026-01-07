"""
Simple keep-alive script to prevent Render free tier from spinning down.
Run this as a separate cron job or scheduled task.
"""
import requests
import time
import os
from src.logger import get_logger

def ping_service(url: str):
    """Ping the service to keep it alive."""
    try:
        response = requests.get(f"{url}/health", timeout=10)
        if response.status_code == 200:
            logger.info("Service is alive")
            return True
        else:
            logger.warning(f"Service returned status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to ping service: {e}")
        return False

if __name__ == "__main__":
    logger = get_logger()
    service_url = os.getenv("SERVICE_URL", "http://localhost:5000")
    
    logger.info(f"Starting keep-alive for {service_url}")
    
    while True:
        ping_service(service_url)
        # Ping every 10 minutes (600 seconds)
        time.sleep(600)

