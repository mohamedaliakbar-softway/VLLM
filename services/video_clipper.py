"""Video clipping service for creating shorts from highlights."""
from moviepy.editor import VideoFileClip
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import subprocess
import concurrent.futures
from config import settings, PLATFORM_DIMENSIONS
from services.smart_cropper import SmartCropper

logger = logging.getLogger(__name__)


class VideoClipper:
    """Creates short video clips from highlight segments."""
    
    def __init__(self):
        self.output_dir = Path(settings.output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.smart_cropper = SmartCropper()
    
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
    
    def cleanup(self, file_path: str):
        """Remove output video file."""
        try:
            if Path(file_path).exists():
                Path(file_path).unlink()
                logger.info(f"Cleaned up output file: {file_path}")
        except Exception as e:
            logger.warning(f"Error cleaning up file {file_path}: {str(e)}")

