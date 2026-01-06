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
        """Create subtitle clips based on configuration."""
        subtitle_config = self.config.get('video.subtitle') or self.config.get('editing.subtitle', {})
        
        if not subtitle_config.get('enabled', True):
            return []
        
        style = subtitle_config.get('style', 'sentence')
        font = subtitle_config.get('font') or subtitle_config.get('font', 'Arial-Bold')
        fontsize = subtitle_config.get('font_size') or subtitle_config.get('fontsize', 70)
        color = subtitle_config.get('color', 'yellow')
        stroke_color = subtitle_config.get('stroke_color', 'black')
        stroke_width = subtitle_config.get('stroke_width', 2)
        position = subtitle_config.get('position', 'bottom')
        relative_pos = subtitle_config.get('relative_position', 0.8)
        
        subtitle_clips = []
        
        try:
            if style == 'sentence':
                # Group words into sentences
                sentences = self._group_words_into_sentences(clip_words, start_time)
                
                for sentence in sentences:
                    duration = sentence['end'] - sentence['start']
                    if duration < 0.1:
                        duration = 0.1
                    
                    # Determine position
                    if position == 'top':
                        pos = ('center', 0.1)
                    elif position == 'center':
                        pos = ('center', 'center')
                    else:  # bottom
                        pos = ('center', relative_pos)
                    
                    txt = TextClip(
                        sentence['text'],
                        fontsize=fontsize,
                        color=color,
                        stroke_color=stroke_color,
                        stroke_width=stroke_width,
                        font=font,
                        method='caption',
                        size=(None, None),
                        align='center'
                    )
                    txt = txt.set_position(pos, relative=True).set_start(sentence['start']).set_duration(duration)
                    subtitle_clips.append(txt)
            else:
                # Word-by-word (original behavior)
                for word in clip_words:
                    w_start = word['start'] - start_time
                    w_end = word['end'] - start_time
                    duration = w_end - w_start
                    if duration < 0.1:
                        duration = 0.1
                    
                    if position == 'top':
                        pos = ('center', 0.1)
                    elif position == 'center':
                        pos = ('center', 'center')
                    else:
                        pos = ('center', relative_pos)
                    
                    txt = TextClip(
                        word['word'],
                        fontsize=fontsize,
                        color=color,
                        stroke_color=stroke_color,
                        stroke_width=stroke_width,
                        font=font
                    )
                    txt = txt.set_position(pos, relative=True).set_start(w_start).set_duration(duration)
                    subtitle_clips.append(txt)
        
        except Exception as e:
            self.logger.warning(f"TextClip error (ImageMagick might be missing): {e}")
            self.logger.warning("Skipping subtitles.")
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
        
        # Crop to target aspect ratio
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
        
        # Resize to target resolution
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
