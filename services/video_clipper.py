"""Video clipping service for creating shorts from highlights."""
from moviepy import VideoFileClip
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import subprocess
import concurrent.futures
from config import settings, PLATFORM_DIMENSIONS
from services.smart_cropper import SmartCropper
from services.logo_overlay import LogoOverlay

logger = logging.getLogger(__name__)


class VideoClipper:
    """Creates short video clips from highlight segments."""
    
    def __init__(self):
        self.output_dir = Path(settings.output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.smart_cropper = SmartCropper()
        self.logo_overlay = LogoOverlay()
    
    def create_shorts_fast(
        self, 
        segment_files: List[Dict],
        video_id: str,
        highlights: List[Dict],
        platform: str = "default"
    ) -> List[Dict]:
        """
        Create short video clips from pre-downloaded segments using MoviePy with smart cropping.
        This uses smart cropping for proper landscape-to-portrait conversion with subject tracking.
        
        Args:
            segment_files: List of dictionaries with 'file_path', 'start_seconds', 'end_seconds' for each segment
            video_id: Video ID for naming output files
            highlights: List of highlight dictionaries with timestamps and metadata
            platform: Platform name for resizing (default: "default")
            
        Returns:
            List of created short video info
        """
        created_shorts = []
        
        # Get platform dimensions
        platform_key = platform.lower() if platform else "default"
        target_size = PLATFORM_DIMENSIONS.get(
            platform_key, 
            PLATFORM_DIMENSIONS["default"]
        )
        
        # Helper function to convert timestamp to seconds
        def timestamp_to_seconds(timestamp_str):
            """Convert MM:SS or HH:MM:SS timestamp to seconds."""
            if isinstance(timestamp_str, (int, float)):
                return int(timestamp_str)
            if not timestamp_str:
                return 0
            try:
                parts = str(timestamp_str).split(":")
                if len(parts) == 2:  # MM:SS
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:  # HH:MM:SS
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    return int(timestamp_str)
            except:
                return 0
        
        # Map segment files to their corresponding highlight data
        # Safely extract start_seconds and end_seconds from highlights
        highlight_map = {}
        for h in highlights:
            start_sec = h.get("start_seconds")
            end_sec = h.get("end_seconds")
            
            # Convert from timestamps if seconds not available
            if start_sec is None and "start_time" in h:
                start_sec = timestamp_to_seconds(h["start_time"])
            if end_sec is None and "end_time" in h:
                end_sec = timestamp_to_seconds(h["end_time"])
            
            # Only add to map if we have valid timestamps
            if start_sec is not None and end_sec is not None:
                highlight_map[(start_sec, end_sec)] = h
            else:
                logger.warning(f"Skipping highlight without valid timestamps: {h}")
        
        def process_segment(idx, segment_file_info, highlight):
            """Process a single segment with MoviePy and smart cropping."""
            try:
                segment_path = segment_file_info['file_path']
                
                # Load the segment
                video = VideoFileClip(segment_path)
                
                # Get category and tracking info from highlight
                category = highlight.get("category", "product_demo")
                tracking_focus = highlight.get("tracking_focus", "")
                
                # Apply smart cropping with subject tracking
                try:
                    clip = self.smart_cropper.apply_smart_crop(
                        video, category, tracking_focus, target_size
                    )
                    logger.info(f"Applied smart crop for {category} (tracking: {tracking_focus}) on segment {idx}")
                except Exception as e:
                    logger.warning(f"Smart cropping failed for segment {idx}, using fallback: {str(e)}")
                    # Fallback to simple resize
                    clip = video.resized(new_size=target_size)
                
                # Generate output filename with platform suffix
                platform_suffix = platform_key if platform_key != "default" else ""
                if platform_suffix:
                    output_filename = f"{video_id}_h_{idx}_{platform_suffix}.mp4"
                else:
                    output_filename = f"{video_id}_h_{idx}.mp4"
                output_path = self.output_dir / output_filename
                
                # Export clip with high quality settings - balanced for quality and performance
                clip.write_videofile(
                    str(output_path),
                    codec='libx264',
                    audio_codec='aac',
                    preset='medium',  # Balanced: good quality and reasonable speed
                    bitrate='6000k',  # High quality for social media (1080p shorts)
                    fps=clip.fps if clip.fps else 30,
                    audio_bitrate='192k',  # High quality audio
                    threads=8,  # Use multiple threads for faster encoding
                    ffmpeg_params=[
                        '-crf', '20',  # High quality (18=near lossless, 23=good, 20=excellent)
                        '-pix_fmt', 'yuv420p',  # Compatible format
                        '-movflags', '+faststart',  # Enable streaming
                        '-profile:v', 'high',  # High profile for better quality
                        '-level', '4.2',  # H.264 level 4.2 (supports 1080p60)
                    ],
                    logger=None  # Suppress moviepy logs
                )
                
                # Close clip and video to free memory
                clip.close()
                video.close()
                
                # Helper function to format seconds as timestamp
                def seconds_to_timestamp(seconds):
                    """Convert seconds to MM:SS format"""
                    mins = int(seconds // 60)
                    secs = int(seconds % 60)
                    return f"{mins:02d}:{secs:02d}"
                
                # Safely get start_seconds and end_seconds
                start_sec = highlight.get("start_seconds")
                end_sec = highlight.get("end_seconds")
                
                # Convert from timestamps if seconds not available
                if start_sec is None:
                    if "start_time" in highlight:
                        start_sec = timestamp_to_seconds(highlight["start_time"])
                    else:
                        start_sec = 0
                
                if end_sec is None:
                    if "end_time" in highlight:
                        end_sec = timestamp_to_seconds(highlight["end_time"])
                    else:
                        # Fallback to duration_seconds + start_sec
                        duration = highlight.get("duration_seconds", 30)
                        end_sec = start_sec + duration
                
                # Get duration_seconds safely
                duration_sec = highlight.get("duration_seconds")
                if duration_sec is None:
                    duration_sec = end_sec - start_sec
                
                created_shorts.append({
                    "short_id": idx,
                    "file_path": str(output_path),
                    "filename": output_filename,
                    "start_time": highlight.get("start_time", seconds_to_timestamp(start_sec)),
                    "end_time": highlight.get("end_time", seconds_to_timestamp(end_sec)),
                    "start_seconds": start_sec,
                    "end_seconds": end_sec,
                    "duration_seconds": duration_sec,
                    "engagement_score": highlight.get("engagement_score", 0),
                    "marketing_effectiveness": highlight.get("marketing_effectiveness", ""),
                    "suggested_cta": highlight.get("suggested_cta", ""),
                    "category": highlight.get("category", "product_demo"),
                    "tracking_focus": highlight.get("tracking_focus", ""),
                })
                
                logger.info(f"Created short {idx}: {output_filename}")
                return True
            
            except Exception as e:
                logger.error(f"Error creating short {idx} from segment {segment_file_info.get('file_path', 'unknown')}: {str(e)}", exc_info=True)
                return False
        
        # Process all segments in parallel for maximum speed
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for idx, segment_file_info in enumerate(segment_files, 1):
                # Get start_seconds and end_seconds from segment_file_info
                # segment_file_info has 'start_time' and 'duration', not 'start_seconds' and 'end_seconds'
                seg_start = segment_file_info.get('start_seconds') or segment_file_info.get('start_time', 0)
                seg_duration = segment_file_info.get('duration_seconds') or segment_file_info.get('duration', 30)
                seg_end = seg_start + seg_duration
                
                # Convert to int if needed
                if isinstance(seg_start, str):
                    seg_start = timestamp_to_seconds(seg_start)
                if isinstance(seg_end, str):
                    seg_end = timestamp_to_seconds(seg_end)
                if isinstance(seg_duration, str):
                    seg_duration = timestamp_to_seconds(seg_duration)
                    seg_end = seg_start + seg_duration
                
                # Find the corresponding highlight data
                highlight = highlight_map.get((seg_start, seg_end))
                if not highlight:
                    # Try to find by start time only (within 5 seconds tolerance)
                    for (h_start, h_end), h in highlight_map.items():
                        if abs(h_start - seg_start) < 5:
                            highlight = h
                            break
                
                if not highlight:
                    logger.warning(f"No matching highlight found for segment {segment_file_info.get('file_path', 'unknown')} (start: {seg_start}s, end: {seg_end}s), skipping.")
                    continue
                
                future = executor.submit(process_segment, idx, segment_file_info, highlight)
                futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                future.result()  # Wait for completion
        
        # Sort by short_id to maintain order
        created_shorts.sort(key=lambda x: x["short_id"])
        
        return created_shorts
    
    def _resize_for_platform(
        self, 
        clip: VideoFileClip, 
        target_size: Tuple[int, int]
    ) -> VideoFileClip:
        """
        Resize video clip to target dimensions while maintaining aspect ratio.
        Uses letterboxing/pillarboxing to avoid pixel distortion.
        
        Args:
            clip: Video clip to resize
            target_size: Target (width, height) tuple
            
        Returns:
            Resized video clip
        """
        target_width, target_height = target_size
        target_aspect = target_width / target_height
        
        # Get current dimensions
        current_width = clip.w
        current_height = clip.h
        current_aspect = current_width / current_height
        
        # Calculate new dimensions maintaining aspect ratio
        if current_aspect > target_aspect:
            # Video is wider than target - fit to width
            new_width = target_width
            new_height = int(target_width / current_aspect)
        else:
            # Video is taller than target - fit to height
            new_height = target_height
            new_width = int(target_height * current_aspect)
        
        # Resize the clip (MoviePy 2.x uses new_size instead of newsize)
        resized_clip = clip.resized(new_size=(new_width, new_height))
        
        # If dimensions don't match target, add letterboxing/pillarboxing
        if new_width != target_width or new_height != target_height:
            # Create a black background clip
            from moviepy import ColorClip, CompositeVideoClip
            background = ColorClip(
                size=(target_width, target_height),
                color=(0, 0, 0),
                duration=clip.duration
            )
            
            # Center the resized clip on the background
            resized_clip = resized_clip.with_position(('center', 'center'))
            # Composite the resized clip on top of the background
            resized_clip = CompositeVideoClip([background, resized_clip])
        
        return resized_clip
    
    def create_shorts(
        self, 
        video_path: str, 
        highlights: List[Dict],
        video_id: str,
        platform: str = "default"
    ) -> List[Dict]:
        """
        Create short video clips from highlight segments.
        
        Args:
            video_path: Path to source video file
            highlights: List of highlight dictionaries with timestamps
            video_id: Video ID for naming output files
            platform: Platform name for resizing (default: "default")
            
        Returns:
            List of created short video info
        """
        created_shorts = []
        
        try:
            # Load the video once
            video = VideoFileClip(video_path)
            
            for idx, highlight in enumerate(highlights, 1):
                try:
                    # Safely get start_seconds and end_seconds
                    start_time = highlight.get("start_seconds")
                    end_time = highlight.get("end_seconds")
                    
                    # Convert from timestamps if needed
                    if start_time is None and "start_time" in highlight:
                        parts = highlight["start_time"].split(":")
                        if len(parts) == 2:
                            start_time = int(parts[0]) * 60 + int(parts[1])
                        elif len(parts) == 3:
                            start_time = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        else:
                            start_time = 0
                    
                    if end_time is None and "end_time" in highlight:
                        parts = highlight["end_time"].split(":")
                        if len(parts) == 2:
                            end_time = int(parts[0]) * 60 + int(parts[1])
                        elif len(parts) == 3:
                            end_time = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        else:
                            end_time = start_time + highlight.get("duration_seconds", 30)
                    
                    if start_time is None:
                        start_time = 0
                    if end_time is None:
                        end_time = start_time + highlight.get("duration_seconds", 30)
                    
                    # Validate timestamps
                    if start_time < 0 or end_time > video.duration:
                        logger.warning(
                            f"Highlight {idx} has invalid timestamps, skipping"
                        )
                        continue
                    
                    # Create clip (MoviePy 2.x uses subclipped instead of subclip)
                    clip = video.subclipped(start_time, end_time)
                    
                    # Get platform dimensions
                    platform_key = platform.lower() if platform else "default"
                    target_size = PLATFORM_DIMENSIONS.get(
                        platform_key, 
                        PLATFORM_DIMENSIONS["default"]
                    )
                    
                    # Get category and tracking info from highlight
                    category = highlight.get("category", "product_demo")
                    tracking_focus = highlight.get("tracking_focus", "")
                    
                    # Apply smart cropping with subject tracking
                    try:
                        clip = self.smart_cropper.apply_smart_crop(
                            clip, category, tracking_focus, target_size
                        )
                        logger.info(f"Applied smart crop for {category} (tracking: {tracking_focus})")
                    except Exception as e:
                        logger.warning(f"Smart cropping failed, using fallback: {str(e)}")
                        # Fallback to simple resize
                        clip = self._resize_for_platform(clip, target_size)
                    
                    # Generate output filename with platform suffix
                    platform_suffix = platform_key if platform_key != "default" else ""
                    if platform_suffix:
                        output_filename = f"{video_id}_short_{idx}_{platform_suffix}.mp4"
                    else:
                        output_filename = f"{video_id}_short_{idx}.mp4"
                    output_path = self.output_dir / output_filename
                    
                    # Export clip with high quality settings for direct upload
                    clip.write_videofile(
                        str(output_path),
                        codec='libx264',
                        audio_codec='aac',
                        preset='slow',  # Better quality, slower encoding
                        bitrate='8000k',  # Higher bitrate for better quality
                        fps=clip.fps if clip.fps else 30,
                        audio_bitrate='192k',  # High quality audio
                        threads=4,  # Use multiple threads for faster encoding
                        ffmpeg_params=[
                            '-crf', '18',  # High quality (lower = better, 18 is visually lossless)
                            '-pix_fmt', 'yuv420p',  # Compatible format
                            '-movflags', '+faststart',  # Enable streaming
                            '-profile:v', 'high',  # H.264 high profile
                            '-level', '4.0',  # H.264 level
                        ],
                        logger=None  # Suppress moviepy logs
                    )
                    
                    # Close clip to free memory
                    clip.close()
                    
                    created_shorts.append({
                        "short_id": idx,
                        "file_path": str(output_path),
                        "filename": output_filename,
                        "start_time": highlight["start_time"],
                        "end_time": highlight["end_time"],
                        "duration_seconds": highlight["duration_seconds"],
                        "engagement_score": highlight["engagement_score"],
                        "marketing_effectiveness": highlight["marketing_effectiveness"],
                        "suggested_cta": highlight["suggested_cta"],
                    })
                    
                    logger.info(f"Created short {idx}: {output_filename}")
                
                except Exception as e:
                    logger.error(f"Error creating short {idx}: {str(e)}")
                    continue
            
            # Close main video
            video.close()
            
            return created_shorts
        
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            raise
    
    def trim_clip(
        self, 
        input_path: str, 
        new_start: Optional[float] = None,
        new_end: Optional[float] = None,
        output_suffix: str = "_trimmed"
    ) -> str:
        """
        Trim a video clip to new start/end times using FFmpeg.
        
        Args:
            input_path: Path to input video file
            new_start: New start time in seconds (None = keep original start)
            new_end: New end time in seconds (None = keep original end)
            output_suffix: Suffix to add to output filename
            
        Returns:
            Path to trimmed video file
        """
        try:
            input_file = Path(input_path)
            output_path = input_file.parent / f"{input_file.stem}{output_suffix}{input_file.suffix}"
            
            # Build FFmpeg command
            cmd = ["ffmpeg", "-y", "-i", str(input_path)]
            
            if new_start is not None:
                cmd.extend(["-ss", str(new_start)])
            
            if new_end is not None:
                if new_start is not None:
                    duration = new_end - new_start
                else:
                    duration = new_end
                cmd.extend(["-t", str(duration)])
            
            cmd.extend([
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                str(output_path)
            ])
            
            logger.info(f"Trimming video: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info(f"Trimmed video saved to: {output_path}")
            return str(output_path)
        
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg trim error: {e.stderr}")
            raise ValueError(f"Failed to trim video: {e.stderr}")
        except Exception as e:
            logger.error(f"Error trimming clip: {str(e)}")
            raise
    
    def change_speed(
        self, 
        input_path: str, 
        speed_factor: float,
        output_suffix: str = "_speed"
    ) -> str:
        """
        Change playback speed of a video using FFmpeg.
        
        Args:
            input_path: Path to input video file
            speed_factor: Speed multiplier (2.0 = 2x speed, 0.5 = half speed)
            output_suffix: Suffix to add to output filename
            
        Returns:
            Path to speed-adjusted video file
        """
        try:
            input_file = Path(input_path)
            output_path = input_file.parent / f"{input_file.stem}{output_suffix}{input_file.suffix}"
            
            # Calculate PTS (presentation timestamp) multiplier
            # For 2x speed, we need pts=0.5 (half the timestamps)
            pts_multiplier = 1.0 / speed_factor
            
            # Calculate audio tempo
            # For 2x speed, we need atempo=2.0
            audio_tempo = speed_factor
            
            # Build complex filter for video and audio
            video_filter = f"setpts={pts_multiplier}*PTS"
            
            # atempo only supports 0.5 to 2.0, so we may need to chain
            audio_filters = []
            remaining_tempo = audio_tempo
            while remaining_tempo > 2.0:
                audio_filters.append("atempo=2.0")
                remaining_tempo /= 2.0
            while remaining_tempo < 0.5:
                audio_filters.append("atempo=0.5")
                remaining_tempo /= 0.5
            if remaining_tempo != 1.0:
                audio_filters.append(f"atempo={remaining_tempo}")
            
            audio_filter = ",".join(audio_filters) if audio_filters else "anull"
            
            cmd = [
                "ffmpeg", "-y", "-i", str(input_path),
                "-filter:v", video_filter,
                "-filter:a", audio_filter,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                str(output_path)
            ]
            
            logger.info(f"Changing speed: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info(f"Speed-adjusted video saved to: {output_path}")
            return str(output_path)
        
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg speed change error: {e.stderr}")
            raise ValueError(f"Failed to change speed: {e.stderr}")
        except Exception as e:
            logger.error(f"Error changing speed: {str(e)}")
            raise
    
    def adjust_duration(
        self,
        input_path: str,
        target_duration: Optional[float] = None,
        reduce_by: Optional[float] = None,
        extend_by: Optional[float] = None,
        output_suffix: str = "_adjusted"
    ) -> str:
        """
        Adjust video duration by trimming or speeding up.
        
        Args:
            input_path: Path to input video file
            target_duration: Target duration in seconds
            reduce_by: Amount to reduce duration by (in seconds)
            extend_by: Amount to extend duration by (in seconds)
            output_suffix: Suffix to add to output filename
            
        Returns:
            Path to duration-adjusted video file
        """
        try:
            # Get current duration
            video = VideoFileClip(input_path)
            current_duration = video.duration
            video.close()
            
            # Calculate new duration
            if target_duration is not None:
                new_duration = target_duration
            elif reduce_by is not None:
                new_duration = max(1, current_duration - reduce_by)  # Minimum 1 second
            elif extend_by is not None:
                # For extending, we'll slow down the video
                new_duration = current_duration + extend_by
            else:
                raise ValueError("Must specify target_duration, reduce_by, or extend_by")
            
            # Decide strategy
            if new_duration < current_duration:
                # Need to shorten - trim from the end
                logger.info(f"Shortening video from {current_duration}s to {new_duration}s by trimming")
                return self.trim_clip(input_path, new_start=0, new_end=new_duration, output_suffix=output_suffix)
            elif new_duration > current_duration:
                # Need to extend - slow down playback
                speed_factor = current_duration / new_duration
                logger.info(f"Extending video from {current_duration}s to {new_duration}s by slowing to {speed_factor}x")
                return self.change_speed(input_path, speed_factor, output_suffix=output_suffix)
            else:
                # No change needed
                logger.info("Duration already matches target, no adjustment needed")
                return input_path
        
        except Exception as e:
            logger.error(f"Error adjusting duration: {str(e)}")
            raise
    
    def split_clip(
        self,
        input_path: str,
        split_at: float,
        output_suffix_1: str = "_part1",
        output_suffix_2: str = "_part2"
    ) -> Tuple[str, str]:
        """
        Split a video clip at a specific timestamp.
        
        Args:
            input_path: Path to input video file
            split_at: Time in seconds to split at
            output_suffix_1: Suffix for first part
            output_suffix_2: Suffix for second part
            
        Returns:
            Tuple of (part1_path, part2_path)
        """
        try:
            # Create first part (0 to split_at)
            part1_path = self.trim_clip(input_path, new_start=0, new_end=split_at, output_suffix=output_suffix_1)
            
            # Create second part (split_at to end)
            part2_path = self.trim_clip(input_path, new_start=split_at, output_suffix=output_suffix_2)
            
            logger.info(f"Split video at {split_at}s into: {part1_path} and {part2_path}")
            return (part1_path, part2_path)
        
        except Exception as e:
            logger.error(f"Error splitting clip: {str(e)}")
            raise
    
    def add_captions(
        self,
        input_path: str,
        style: str = "bold_modern",
        output_suffix: str = "_captioned"
    ) -> str:
        """
        Add live captions to a video using Vosk (offline) or Gemini (online).
        
        Args:
            input_path: Path to input video file
            style: Caption style (bold_modern, elegant_serif, fun_playful)
            output_suffix: Suffix for output filename
            
        Returns:
            Path to captioned video file
        """
        try:
            # Import caption services
            from services.caption_generator import CaptionGenerator
            from services.caption_burner import CaptionBurner
            
            # Generate output path
            input_file = Path(input_path)
            output_path = str(input_file.parent / f"{input_file.stem}{output_suffix}{input_file.suffix}")
            
            logger.info(f"Adding captions to video: {input_path}")
            
            # Step 1: Generate captions
            caption_gen = CaptionGenerator()
            logger.info("Extracting audio and generating captions...")
            
            # Extract audio
            audio_path = caption_gen.extract_audio(input_path)
            
            # Transcribe (tries Vosk first, falls back to Gemini)
            captions = []
            try:
                if caption_gen.use_vosk:
                    try:
                        logger.info("Using Vosk for accurate offline transcription...")
                        result = caption_gen.transcribe_with_vosk(audio_path)
                        captions = result.get("words", [])
                        logger.info(f"Generated {len(captions)} caption words using Vosk")
                    except Exception as vosk_error:
                        logger.warning(f"Vosk transcription failed: {vosk_error}, falling back to Gemini")
                        logger.info("Using Gemini for online transcription...")
                        result = caption_gen.transcribe_with_gemini(audio_path)
                        captions = result.get("words", [])
                        logger.info(f"Generated {len(captions)} caption words using Gemini")
                else:
                    logger.info("Using Gemini for online transcription...")
                    result = caption_gen.transcribe_with_gemini(audio_path)
                    captions = result.get("words", [])
                    logger.info(f"Generated {len(captions)} caption words using Gemini")
                
            finally:
                # Clean up audio file
                if Path(audio_path).exists():
                    Path(audio_path).unlink()
            
            # Step 2: Burn captions into video
            if captions:
                caption_burner = CaptionBurner()
                logger.info(f"Burning captions with style: {style}")
                caption_burner.burn_captions(
                    video_path=input_path,
                    captions=captions,
                    style_name=style,
                    output_path=output_path
                )
                logger.info(f"Captions added successfully: {output_path}")
            else:
                logger.warning("No captions generated, copying original file")
                # Just copy the file if no captions
                import shutil
                shutil.copy2(input_path, output_path)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding captions: {str(e)}")
            raise
    
    def cleanup(self, file_path: str):
        """Remove output video file."""
        try:
            if Path(file_path).exists():
                Path(file_path).unlink()
                logger.info(f"Cleaned up output file: {file_path}")
        except Exception as e:
            logger.warning(f"Error cleaning up file {file_path}: {str(e)}")
    
    def add_logo(
        self,
        input_path: str,
        logo_path: str,
        output_path: str,
        position: str = "bottom-right",
        size_percent: float = 10.0,
        opacity: float = 0.8,
        padding: int = 20
    ) -> str:
        """
        Add brand logo overlay to a video.
        
        Args:
            input_path: Path to input video
            logo_path: Path to logo image (PNG recommended for transparency)
            output_path: Path for output video with logo
            position: Logo position ("top-left", "top-right", "bottom-left", "bottom-right",
                     "center", "top-center", "bottom-center")
            size_percent: Logo size as percentage of video width (1-50, default 10)
            opacity: Logo opacity 0.0-1.0 (default 0.8)
            padding: Padding from edges in pixels (default 20)
            
        Returns:
            Path to output video with logo overlay
            
        Raises:
            Exception: If logo overlay fails
        """
        try:
            logger.info(f"Adding logo overlay to video: {input_path}")
            
            result = self.logo_overlay.add_logo(
                video_path=input_path,
                logo_path=logo_path,
                output_path=output_path,
                position=position,
                size_percent=size_percent,
                opacity=opacity,
                padding=padding
            )
            
            logger.info(f"Logo overlay completed: {output_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error adding logo overlay: {str(e)}")
            raise


