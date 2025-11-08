"""Video clipping service for creating shorts from highlights."""
from moviepy import VideoFileClip
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
        Create short video clips using FFmpeg directly (10x faster than MoviePy).
        
        Args:
            segment_files: List of downloaded segment file paths
            video_id: Video ID for naming output files
            highlights: Highlight metadata for each segment
            platform: Platform name for resizing
            
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
        target_width, target_height = target_size
        
        def process_segment(idx, segment_file, highlight):
            """Process a single segment with FFmpeg."""
            try:
                input_path = segment_file['file_path']
                
                # Generate output filename
                platform_suffix = platform_key if platform_key != "default" else ""
                if platform_suffix:
                    output_filename = f"{video_id}_short_{idx}_{platform_suffix}.mp4"
                else:
                    output_filename = f"{video_id}_short_{idx}.mp4"
                output_path = self.output_dir / output_filename
                
                # Build FFmpeg command for fast processing
                # Use veryfast preset and crop/scale in one pass
                cmd = [
                    'ffmpeg',
                    '-i', input_path,
                    '-vf', f'scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2',
                    '-c:v', 'libx264',
                    '-preset', 'veryfast',  # 10x faster than 'slow'
                    '-crf', '23',  # Good quality, faster encoding
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',  # Overwrite output
                    str(output_path)
                ]
                
                # Run FFmpeg
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg error for segment {idx}: {result.stderr}")
                    return None
                
                logger.info(f"Created short {idx}: {output_filename}")
                
                return {
                    "short_id": idx,
                    "file_path": str(output_path),
                    "filename": output_filename,
                    "start_time": highlight.get("start_time", "00:00"),
                    "end_time": highlight.get("end_time", "00:30"),
                    "duration_seconds": highlight.get("duration_seconds", 30),
                    "engagement_score": highlight.get("engagement_score", 0),
                    "marketing_effectiveness": highlight.get("marketing_effectiveness", ""),
                    "suggested_cta": highlight.get("suggested_cta", ""),
                }
            
            except Exception as e:
                logger.error(f"Error processing segment {idx}: {str(e)}")
                return None
        
        # Process all segments in parallel for maximum speed
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for idx, (segment_file, highlight) in enumerate(zip(segment_files, highlights), 1):
                future = executor.submit(process_segment, idx, segment_file, highlight)
                futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    created_shorts.append(result)
        
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
                    start_time = highlight["start_seconds"]
                    end_time = highlight["end_seconds"]
                    
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

