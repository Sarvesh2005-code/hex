import os
import yt_dlp
from src.config import get_config
from src.logger import get_logger
from src.validators import Validator
from src.retry import retry_on_network_error

class VideoDownloader:
    def __init__(self, download_dir=None):
        config = get_config()
        self.download_dir = download_dir or config.get('system.download_dir') or config.get('downloader.download_dir', 'downloads')
        self.logger = get_logger()
        
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            self.logger.debug(f"Created download directory: {self.download_dir}")

    def validate_url(self, url: str) -> tuple:
        """Validate YouTube URL before downloading."""
        is_valid, message = Validator.validate_youtube_url(url)
        if not is_valid:
            self.logger.error(f"URL validation failed: {message}")
            raise ValueError(f"Invalid URL: {message}")
        return is_valid, message

    @retry_on_network_error(max_retries=3, base_delay=5.0)
    def download(self, url):
        """
        Downloads video and audio from YouTube URL.
        Returns tuple: (video_path, audio_path)
        """
        # Validate URL first
        self.validate_url(url)
        
        self.logger.info(f"Downloading from {url}...")
        config = get_config()
        format_str = config.get('downloader.format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best')
        
        # Options for downloading the video
        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': False,
            'no_warnings': False,
        }

        try:
            # Extract info first to get filename/ID
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info['id']
                video_title = info['title'] # Keep this for potential future use or debugging
                
                # Determine the actual downloaded video path
                # yt_dlp might rename files or use different extensions based on format
                # We need to find the actual file that was downloaded.
                # A common pattern is id.ext or title-id.ext
                # For simplicity, we'll assume the outtmpl pattern for now.
                # A more robust solution would iterate through info['requested_downloads']
                # or check for files matching the ID in the download_dir.
                video_ext = info.get('ext', 'mp4') # Default to mp4 if ext not found
                video_path = os.path.join(self.download_dir, f"{video_id}.{video_ext}")
                
                # Validate downloaded file exists
                if not os.path.exists(video_path):
                    # Fallback for cases where ext might be different or file name is not exactly id.ext
                    # This is a basic attempt; a more robust solution would be needed for all cases.
                    potential_video_path_mp4 = os.path.join(self.download_dir, f"{video_id}.mp4")
                    if os.path.exists(potential_video_path_mp4):
                        video_path = potential_video_path_mp4
                    else:
                        raise FileNotFoundError(f"Downloaded video file not found: {video_path} or {potential_video_path_mp4}")
                
                self.logger.info(f"Video downloaded: {video_path}")

            # Extract audio as WAV for Whisper
            audio_path = os.path.join(self.download_dir, f"{video_id}_audio.wav")
            
            audio_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.download_dir, f"{video_id}_audio.%(ext)s"),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                }],
                'noplaylist': True,
                'quiet': False,
                'no_warnings': False,
            }
            
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                ydl.download([url])
             
            audio_path = os.path.join(self.download_dir, f"{video_id}_audio.wav")
            
            # Validate audio file exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Downloaded audio file not found: {audio_path}")
            
            self.logger.info(f"Audio extracted: {audio_path}")

            return video_path, audio_path
            
        except yt_dlp.DownloadError as e:
            self.logger.error(f"Download error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during download: {e}")
            raise

if __name__ == "__main__":
    # Test
    dl = VideoDownloader()
    v, a = dl.download("https://www.youtube.com/watch?v=jNQXAC9IVRw") # First YouTube video
    print(f"Video: {v}, Audio: {a}")
