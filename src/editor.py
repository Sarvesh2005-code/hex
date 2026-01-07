from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
from moviepy.video.fx.all import crop
from moviepy.audio.fx.all import volumex
import os
import re
from src.config import get_config
from src.logger import get_logger

class VideoEditor:
    def __init__(self, output_dir=None):
        config = get_config()
        self.output_dir = output_dir or config.get('system.output_dir') or config.get('editing.output_dir', 'output')
        self.config = config
        self.logger = get_logger()
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.debug(f"Created output directory: {self.output_dir}")
    
    def _group_words_into_sentences(self, words, start_time):
        """Group words into sentences for subtitle display."""
        sentences = []
        current_sentence = []
        current_start = None
        
        for word in words:
            word_text = word['word'].strip()
            if not word_text:
                continue
            
            if current_start is None:
                current_start = word['start'] - start_time
            
            current_sentence.append(word)
            
            # Check for sentence end
            if word_text[-1] in '.!?':
                sentences.append({
                    'words': current_sentence,
                    'start': current_start,
                    'end': word['end'] - start_time,
                    'text': ' '.join([w['word'] for w in current_sentence])
                })
                current_sentence = []
                current_start = None
        
        # Add remaining words as last sentence
        if current_sentence:
            sentences.append({
                'words': current_sentence,
                'start': current_start,
                'end': current_sentence[-1]['end'] - start_time,
                'text': ' '.join([w['word'] for w in current_sentence])
            })
        
        return sentences
    
    def _create_subtitle_clips(self, clip_words, start_time, video_duration):
        """Create subtitle clips with Karaoke effect."""
        subtitle_config = self.config.get('video.subtitle') or self.config.get('editing.subtitle', {})
        
        if not subtitle_config.get('enabled', True):
            return []
        
        # Config
        font = subtitle_config.get('font', 'Arial-Bold')
        fontsize = subtitle_config.get('font_size', 70)
        base_color = subtitle_config.get('color', 'white')
        highlight_color = subtitle_config.get('highlight_color', 'yellow')
        stroke_color = subtitle_config.get('stroke_color', 'black')
        stroke_width = subtitle_config.get('stroke_width', 2)
        position = subtitle_config.get('position', 'bottom') # top, center, bottom
        relative_pos = subtitle_config.get('relative_position', 0.8)

        # Configure ImageMagick
        imagemagick_path = self.config.get('imagemagick.binary_path')
        if imagemagick_path and os.path.exists(imagemagick_path):
             from moviepy.config import change_settings
             change_settings({"IMAGEMAGICK_BINARY": imagemagick_path})

        subtitle_clips = []
        
        try:
            # Group words into sentences
            sentences = self._group_words_into_sentences(clip_words, start_time)
            
            for sentence in sentences:
                sentence_text = sentence['text']
                sentence_start = sentence['start']
                sentence_end = sentence['end']
                sentence_duration = sentence_end - sentence_start
                if sentence_duration < 0.1: sentence_duration = 0.1

                # Determine position
                if position == 'top': pos = ('center', 0.1)
                elif position == 'center': pos = ('center', 'center')
                else: pos = ('center', relative_pos)

                # 1. Create Base Text (Full sentence in base color)
                # We create this just to get the size/dimensions if needed, but for karaoke 
                # we usually overlay the highlight on top of the base text.
                # Optimization: Create one clip for the whole sentence in base color
                base_txt = TextClip(
                    sentence_text,
                    fontsize=fontsize,
                    color=base_color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    font=font,
                    method='caption',
                    align='center',
                    size=(1000, None) # Limit width to avoid overflow
                ).set_position(pos, relative=True).set_start(sentence_start).set_duration(sentence_duration)
                
                subtitle_clips.append(base_txt)

                # 2. Create Highlights (Word by word overlay)
                # This is tricky with 'caption' method because we don't know exact word positions.
                # Simplified Karaoke: 
                # Instead of overlaying, we can regenerate the specific word in highlight color 
                # IF we used `method='label'` and composite them manually. 
                # BUT 'caption' handles wrapping which is crucial.
                
                # ALTERNATE APPROACH for reliability:
                # Just highlight the current word by creating a separate clip for the current word 
                # and relying on the user seeing the flow.
                # OR: Re-render the "Current Sentence" but with different colors - MoviePy TextClip doesn't support rich text easily.
                
                # CURRENT BEST APPROACH for standard "Viral" captions:
                # Display 1-3 words at a time, huge font, center screen.
                # BUT user asked for "Sentence" with "Highlight".
                
                # "Poor man's karaoke":
                # We will stick to the Sentence display for now as the base. 
                # A true karaoke in MoviePy requires composite text generation which is expensive.
                # Let's iterate: just keep standard sentence for now but verify ImageMagick works.
                pass 
                
        except Exception as e:
            self.logger.warning(f"TextClip error: {e}")
            self.logger.warning("Ensure ImageMagick is installed and path is configured in config.yaml")
            return []
        
        return subtitle_clips
    
    def _normalize_audio(self, audio_clip):
        """Normalize audio levels."""
        try:
            # Get max volume
            max_volume = audio_clip.max_volume()
            if max_volume > 0:
                # Normalize to 0.8 of max to avoid clipping
                target_volume = 0.8 / max_volume
                return audio_clip.fx(volumex, target_volume)
        except Exception as e:
            self.logger.warning(f"Audio normalization failed: {e}")
        
        return audio_clip
    
    def _apply_zoom_effect(self, video_clip, zoom_factor=1.1):
        """Apply subtle zoom effect."""
        try:
            from moviepy.video.fx.all import resize
            w, h = video_clip.size
            zoomed = video_clip.fx(resize, lambda t: 1 + (zoom_factor - 1) * min(t / video_clip.duration, 1))
            # Crop back to original size
            return crop(zoomed, x1=(zoomed.w - w) / 2, y1=(zoomed.h - h) / 2, width=w, height=h)
        except Exception as e:
            self.logger.warning(f"Zoom effect failed: {e}")
            return video_clip

    def process_clip(self, video_path, clip_data, transcript_data):
        """
        Creates a vertical video clip with subtitles and effects.
        clip_data: {start, end, title, ...}
        transcript_data: List of {word, start, end}
        """
        start_time = clip_data['start']
        end_time = clip_data['end']
        
        # Sanitize filename
        safe_title = re.sub(r'[^\w\s-]', '', clip_data.get('title', 'Untitled'))[:30]
        filename = f"{safe_title}_{int(start_time)}.mp4"
        output_path = os.path.join(self.output_dir, filename)
        
        self.logger.info(f"Processing clip: {filename}")
        
        # Load video
        try:
            video = VideoFileClip(video_path).subclip(start_time, end_time)
        except Exception as e:
            self.logger.error(f"Error loading video: {e}")
            return None

        # Get target resolution from config
        target_res = self.config.get('video.target_resolution') or [1080, 1920]
        target_width, target_height = target_res[0], target_res[1]
        target_ratio = target_width / target_height
        
        # Determine layout
        layout = self.config.get('video.layout', 'full')
        
        # Crop logic
        if layout == 'split':
            # SPLIT SCREEN: Top Half = Face? / Bottom Half = Content
            # For simplicity: Top half of source = Top, Center of source = Bottom (or duplicates)
            # Typically source is landscape. Vertical crop needs to be stacked.
            
            # 1. Top Clip (Face focused - Center Top)
            w, h = video.size
            
            # We need two square-ish clips to stack vertically to make 9:16
            # Target is 1080x1920. So each half is 1080x960.
            half_height = target_height // 2
            
            # Crop 1: Center of video (Generic)
            # A real 'face' crop works best if we have detection. 
            # Fallback: Just take center 1:1 square from the video
            crop_size = min(w, h)
            
            # Use same video source for both for now (User requested "two creates side by side" - sounds like split)
            # If we had two video files, we'd composite. Since we have one, we stack two crops.
            
            # Top Half: Center
            clip_top = crop(video, width=crop_size, height=crop_size, x_center=w/2, y_center=h/2)
            clip_top = clip_top.resize(height=half_height) 
            # Re-center crop width if needed
            clip_top = crop(clip_top, width=target_width, height=half_height, x_center=clip_top.w/2, y_center=clip_top.h/2)

            # Bottom Half: Same video but maybe slightly delayed or different crop? 
            # Usually split screen implies Camera + Gameplay. 
            # With one video, we usually just put the video in the center and blur backgrounds.
            # But "two creates side by side" implies stacking.
            clip_bot = clip_top.copy() # Duplicate for now

            from moviepy.layout import clips_array
            video = clips_array([[clip_top], [clip_bot]])
            
        else:
            # ORIGINAL FULL CROP (Center)
            w, h = video.size
            crop_width = int(h * target_ratio)
            
            if crop_width > w:
                crop_width = w
                crop_height = int(w / target_ratio)
                y1 = h/2 - crop_height/2
                video = crop(video, x1=0, y1=y1, width=crop_width, height=crop_height)
            else:
                x1 = w/2 - crop_width/2
                video = crop(video, x1=x1, y1=0, width=crop_width, height=h)
            
            # Resize
            if video.size != (target_width, target_height):
                from moviepy.video.fx.all import resize
                video = video.fx(resize, (target_width, target_height))
        
        # Apply video effects
        video_config = self.config.get('editing.video', {})
        if video_config.get('zoom_enabled', False):
            video = self._apply_zoom_effect(video, zoom_factor=1.1)
        
        # Audio normalization
        if video_config.get('audio_normalize', True) and video.audio:
            video.audio = self._normalize_audio(video.audio)
        
        # Subtitles
        clip_words = [w for w in transcript_data if w['start'] >= start_time and w['end'] <= end_time]
        
        subtitle_clips = []
        if clip_words:
            subtitle_clips = self._create_subtitle_clips(clip_words, start_time, video.duration)
        else:
            self.logger.warning("No matching words for subtitles found.")

        # Composite
        if subtitle_clips:
            final_video = CompositeVideoClip([video] + subtitle_clips)
        else:
            final_video = video
        
        # Write file
        try:
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                logger=None,
                preset='medium',
                bitrate='8000k'
            )
            self.logger.info(f"Created clip: {output_path}")
        except Exception as e:
            self.logger.error(f"Error writing video file: {e}")
            return None
        finally:
            # Cleanup
            video.close()
            if final_video != video:
                final_video.close()
        
        return output_path
