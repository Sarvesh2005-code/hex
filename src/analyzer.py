import os
import google.generativeai as genai
import json
import time
from dotenv import load_dotenv
from src.config import get_config
from src.logger import get_logger
from src.validators import Validator
from src.retry import retry_on_network_error

load_dotenv()

class ContentAnalyzer:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        # Validate API key
        is_valid, message = Validator.validate_api_key(api_key, "gemini")
        if not is_valid:
            raise ValueError(f"Invalid Gemini API key: {message}")
        
        self.logger = get_logger()
        config = get_config()
        model_name = config.get('models.analyzer.model_name') or config.get('analysis.model', 'gemini-2.0-flash')
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self.logger.info(f"Initialized Gemini model: {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini model: {e}")
            raise

    @retry_on_network_error(max_retries=5, base_delay=10.0)
    def analyze(self, transcript_data):
        """
        Analyzes transcript to find viral clips.
        transcript_data: List of dicts {word, start, end}
        Returns: List of dicts {start, end, title, description, virality_score}
        """
        if not transcript_data:
            self.logger.warning("Empty transcript data provided")
            return []
        
        self.logger.info("Analyzing transcript for viral moments...")
        config = get_config()
        
        # Use legacy config keys (they're synced from new structure)
        min_length = config.get('analysis.min_clip_length', 30)
        max_length = config.get('analysis.max_clip_length', 60)
        max_clips = config.get('analysis.max_clips', 3)
        min_score = config.get('analysis.min_virality_score', 7)
        content_type = config.get('analysis.content_type', 'auto')
        
        # Prepare transcript with timestamps for the LLM
        formatted_transcript = ""
        current_sentence = ""
        sentence_start = transcript_data[0]['start']
        
        for i, word in enumerate(transcript_data):
            current_sentence += word['word'] + " "
            # Break every ~10 seconds or on punctuation (simplified)
            if word['end'] - sentence_start > 10 or (word['word'].strip() and word['word'].strip()[-1] in ".!?"):
                formatted_transcript += f"[{sentence_start:.2f}] {current_sentence.strip()}\n"
                current_sentence = ""
                if i + 1 < len(transcript_data):
                    sentence_start = transcript_data[i+1]['start']
        
        # Add remainder
        if current_sentence:
             formatted_transcript += f"[{sentence_start:.2f}] {current_sentence.strip()}\n"

        content_type_prompt = ""
        if content_type != 'auto':
            content_type_prompt = f"Focus on {content_type} content. "

        prompt = f"""
        You are an expert video editor and social media strategist. 
        Analyze the following transcript (with timestamps in seconds) of a video and identify the top {max_clips} most engaging, funny, or insightful segments suitable for YouTube Shorts / TikTok ({min_length}-{max_length} seconds long).
        {content_type_prompt}
        
        Transcript:
        {formatted_transcript}
        
        Output strictly in valid JSON format with this structure:
        [
          {{
            "start": 12.5,
            "end": 45.2,
            "title": "Catchy Viral Title",
            "description": "Short description of why it is viral",
            "virality_score": 9
          }}
        ]
        
        Ensure the 'start' and 'end' times are accurate based on the transcript provided.
        Only return clips with virality_score >= {min_score}.
        """
        
        try:
            response = self.model.generate_content(prompt)
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                self.logger.warning("Gemini 2.0 Flash quota exceeded. Switching to Gemini 1.5 Flash...")
                try:
                    # Fallback to gemini-flash-latest
                    fallback_model = genai.GenerativeModel('gemini-flash-latest')
                    response = fallback_model.generate_content(prompt)
                    self.logger.info("Successfully received response from Gemini 1.5 Flash")
                except Exception as fallback_e:
                    self.logger.error(f"Fallback model also failed: {fallback_e}")
                    raise
            else:
                self.logger.error(f"Error calling Gemini API: {e}")
                raise
        
        try:
            # Clean up response
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
            
            # Remove any potential leading/trailing whitespace or non-json chars
            text = text.strip()
            
            clips = json.loads(text)
            
            # Filter by min score and validate
            filtered_clips = []
            for clip in clips:
                if clip.get('virality_score', 0) >= min_score:
                    # Validate clip times
                    if 'start' in clip and 'end' in clip:
                        duration = clip['end'] - clip['start']
                        if min_length <= duration <= max_length:
                            filtered_clips.append(clip)
                        else:
                            self.logger.warning(f"Clip duration {duration}s outside range [{min_length}, {max_length}]")
                    else:
                        self.logger.warning("Clip missing start/end times, skipping")
            
            self.logger.info(f"Found {len(filtered_clips)} clips after filtering")
            return filtered_clips[:max_clips]

        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing Gemini response as JSON: {e}")
            self.logger.debug(f"Raw response: {response.text}")
            return []
        except Exception as e:
            self.logger.error(f"Error processing Gemini response: {e}")
            return []

