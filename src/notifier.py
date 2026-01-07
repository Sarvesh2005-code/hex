import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List
from datetime import datetime
from src.logger import get_logger
from src.config import get_config

class Notifier:
    """Multi-channel notification system."""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.email_to = os.getenv('EMAIL_TO', self.email_user)
    
    def notify_upload_success(self, video_title: str, video_url: str, 
                              youtube_url: Optional[str] = None,
                              processing_time: Optional[float] = None):
        """Send notification for successful upload."""
        message = f"✅ Video Uploaded Successfully!\n\n"
        message += f"Title: {video_title}\n"
        if youtube_url:
            message += f"YouTube URL: {youtube_url}\n"
        if processing_time:
            message += f"Processing Time: {processing_time:.2f}s\n"
        message += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_all(message, title="Video Upload Success", 
                      color=0x00ff00, video_url=youtube_url)
    
    def notify_upload_error(self, video_title: str, error_message: str):
        """Send notification for upload error."""
        message = f"❌ Upload Failed!\n\n"
        message += f"Title: {video_title}\n"
        message += f"Error: {error_message}\n"
        message += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_all(message, title="Upload Error", color=0xff0000)
    
    def notify_processing_error(self, url: str, error_message: str):
        """Send notification for processing error."""
        message = f"⚠️ Processing Error\n\n"
        message += f"URL: {url}\n"
        message += f"Error: {error_message}\n"
        message += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_all(message, title="Processing Error", color=0xffaa00)
    
    def notify_health_alert(self, alert_type: str, message: str):
        """Send health alert notification."""
        emoji = "🔴" if alert_type == "critical" else "🟡"
        title = f"{emoji} Health Alert: {alert_type.upper()}"
        
        full_message = f"{title}\n\n{message}\n"
        full_message += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        color = 0xff0000 if alert_type == "critical" else 0xffaa00
        self._send_all(full_message, title=title, color=color)
    
    def notify_daily_summary(self, stats: Dict):
        """Send daily summary notification."""
        message = "📊 Daily Summary\n\n"
        message += f"Videos Processed: {stats.get('videos_processed', 0)}\n"
        message += f"Clips Created: {stats.get('clips_created', 0)}\n"
        message += f"Uploads Successful: {stats.get('uploads_successful', 0)}\n"
        message += f"Uploads Failed: {stats.get('uploads_failed', 0)}\n"
        message += f"Errors: {stats.get('errors_count', 0)}\n"
        if stats.get('total_time'):
            message += f"Total Processing Time: {stats.get('total_time', 0):.2f}s\n"
        message += f"Date: {datetime.now().strftime('%Y-%m-%d')}"
        
        self._send_all(message, title="Daily Summary", color=0x0099ff)
    
    def notify_quota_warning(self, quota_used: int, quota_limit: int):
        """Send quota warning notification."""
        percentage = (quota_used / quota_limit) * 100
        message = f"⚠️ Quota Warning\n\n"
        message += f"Quota Used: {quota_used}/{quota_limit} ({percentage:.1f}%)\n"
        if percentage >= 90:
            message += "⚠️ Approaching daily limit!\n"
        message += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_all(message, title="Quota Warning", color=0xffaa00)
    
    def _send_all(self, message: str, title: str = "", color: int = 0x0099ff, 
                  video_url: Optional[str] = None):
        """Send notification to all configured channels."""
        if self.discord_webhook:
            self._send_discord(message, title, color, video_url)
        
        if self.telegram_token and self.telegram_chat_id:
            self._send_telegram(message)
        
        if self.email_user and self.email_password:
            self._send_email(title or "OpenClip Notification", message)
    
    def _send_discord(self, message: str, title: str, color: int, 
                     video_url: Optional[str] = None):
        """Send Discord webhook notification."""
        try:
            embed = {
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if video_url:
                embed["url"] = video_url
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            self.logger.debug("Discord notification sent")
        except Exception as e:
            self.logger.error(f"Failed to send Discord notification: {e}")
    
    def _send_telegram(self, message: str):
        """Send Telegram notification."""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            self.logger.debug("Telegram notification sent")
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {e}")
    
    def _send_email(self, subject: str, body: str):
        """Send email notification."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = self.email_to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()
            
            self.logger.debug("Email notification sent")
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")

