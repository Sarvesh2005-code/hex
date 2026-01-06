from faster_whisper import WhisperModel
import torch
from src.config import get_config
from src.logger import get_logger

def detect_device():
    """Auto-detect best available device."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"

def get_compute_type(device):
    """Get optimal compute type for device."""
    if device == "cuda":
        return "float16"
    elif device == "mps":
        return "float16"
    else:
        return "int8"

class Transcriber:
    def __init__(self, model_size=None, device=None, compute_type=None):
        config = get_config()
        logger = get_logger()
        
        # Support both new and legacy config paths
        self.model_size = model_size or config.get('models.transcriber.size') or config.get('transcription.model_size', 'small')
        device_config = device or config.get('models.transcriber.device') or config.get('transcription.device', 'auto')
        compute_type_config = compute_type or config.get('models.transcriber.compute_type') or config.get('transcription.compute_type', 'auto')
        
        # Auto-detect device if needed
        if device_config == 'auto':
            self.device = detect_device()
            logger.info(f"Auto-detected device: {self.device}")
        else:
            self.device = device_config
        
        # Auto-select compute type if needed
        if compute_type_config == 'auto':
            self.compute_type = get_compute_type(self.device)
            logger.info(f"Using compute type: {self.compute_type}")
        else:
            self.compute_type = compute_type_config
        
        logger.info(f"Initializing Whisper model: size={self.model_size}, device={self.device}, compute_type={self.compute_type}")
        
        try:
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load model with {self.device}/{self.compute_type}, falling back to CPU/int8: {e}")
            self.device = "cpu"
            self.compute_type = "int8"
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

    def fetch_youtube_transcript(self, video_id):
        """Fetch existing transcript from YouTube."""
        from youtube_transcript_api import YouTubeTranscriptApi
        
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            # Convert to our format
            result = []
            for item in transcript:
                # Basic splitting of text into words for compatibility
                words = item['text'].split()
                duration_per_word = item['duration'] / len(words) if words else 0
                
                for i, word in enumerate(words):
                    start = item['start'] + (i * duration_per_word)
                    end = start + duration_per_word
                    result.append({
                        "word": word,
                        "start": start,
                        "end": end,
                        "probability": 1.0
                    })
            return result
        except Exception as e:
            return None

    def transcribe(self, audio_path, video_id=None):
        """
        Transcribes audio file.
        Returns a list of segments with word-level timestamps.
        """
        logger = get_logger()
        
        # Try YouTube captions first if video_id is provided
        if video_id:
            logger.info(f"Attempting to fetch existing captions for {video_id}...")
            transcript = self.fetch_youtube_transcript(video_id)
            if transcript:
                logger.info("Successfully fetched YouTube captions (Instant)")
                return transcript
            logger.info("No captions found, falling back to local Whisper...")

        logger.info(f"Transcribing {audio_path}...")
        
        try:
            segments, info = self.model.transcribe(audio_path, word_timestamps=True)
            logger.debug(f"Transcription info: language={info.language}, probability={info.language_probability}")
            
            # Convert generator to list and structure data
            result = []
            for segment in segments:
                for word in segment.words:
                    result.append({
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability
                    })
            
            logger.info(f"Transcription complete: {len(result)} words transcribed")
            return result
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

if __name__ == "__main__":
    # Test
    # You need a sample audio file to run this
    pass
