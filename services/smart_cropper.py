"""Smart cropping service with intelligent subject tracking."""
import cv2
import numpy as np
from moviepy import VideoFileClip
from typing import Dict, List, Tuple, Optional
import logging
from scipy.interpolate import interp1d, CubicSpline
import os

logger = logging.getLogger(__name__)


class SmartCropper:
    """Intelligent cropping with subject tracking for podcasts and product demos."""
    
    def __init__(self, enable_smooth_transitions: bool = False):
        # Initialize OpenCV face detector (Haar Cascade - more compatible)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if os.path.exists(cascade_path):
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
        else:
            # Try DNN face detector as fallback
            try:
                self.face_cascade = None
                self.face_net = cv2.dnn.readNetFromTensorflow(
                    'opencv_face_detector_uint8.pb',
                    'opencv_face_detector.pbtxt'
                )
            except:
                self.face_cascade = None
                self.face_net = None
                logger.warning("Face detection not available, will use fallback methods")
        
        # Smooth transition settings (DISABLED BY DEFAULT for performance)
        # Enable only for high-quality professional videos where smoothness matters more than speed
        self.enable_smooth_transitions = enable_smooth_transitions
        self.max_velocity = 100  # Max pixels per second movement (increased for less restriction)
        self.min_movement_threshold = 50  # Only apply smoothing if movement > this many pixels
    
    def apply_smart_crop(
        self,
        clip: VideoFileClip,
        category: str,
        tracking_focus: str,
        target_size: Tuple[int, int]
    ) -> VideoFileClip:
        """
        Apply intelligent cropping based on video category.
        
        Args:
            clip: Video clip to crop
            category: "podcast" or "product_demo"
            tracking_focus: Description of what to track
            target_size: Target (width, height) tuple
            
        Returns:
            Cropped and resized video clip
        """
        target_width, target_height = target_size
        target_aspect = target_width / target_height
        
        # Get video properties
        original_width = clip.w
        original_height = clip.h
        original_aspect = original_width / original_height
        duration = clip.duration
        
        # If aspect ratios match, just resize
        if abs(original_aspect - target_aspect) < 0.01:
            return clip.resized(new_size=(target_width, target_height))
        
        # Determine crop dimensions
        if original_aspect > target_aspect:
            # Video is wider - need to crop width
            crop_width = int(original_height * target_aspect)
            crop_height = original_height
        else:
            # Video is taller - need to crop height
            crop_width = original_width
            crop_height = int(original_width / target_aspect)
        
        # Track subject and get crop positions
        if category == "podcast":
            crop_positions = self._track_person(clip, crop_width, crop_height, duration)
        elif category == "product_demo":
            crop_positions = self._track_mouse_or_feature(
                clip, crop_width, crop_height, duration, tracking_focus
            )
        else:
            # Fallback to center crop
            crop_positions = self._center_crop_positions(crop_width, crop_height, duration)
        
        # Apply dynamic cropping
        return self._apply_dynamic_crop(clip, crop_positions, crop_width, crop_height, target_size)
    
    def _track_person(
        self,
        clip: VideoFileClip,
        crop_width: int,
        crop_height: int,
        duration: float
    ) -> List[Tuple[float, int, int]]:
        """Track person/face position for podcast videos (OPTIMIZED - Strategic Sampling)."""
        logger.info("Fast tracking person/face in video...")
        
        # Get video dimensions
        video_width = clip.w
        video_height = clip.h
        
        # OPTIMIZATION: Sample strategically at beginning, middle, and end
        # This catches face position changes while being 12x faster than every-0.5s sampling
        sample_times = []
        if duration <= 10:
            # Short video: sample at 25%, 50%, 75%
            sample_times = [duration * 0.25, duration * 0.5, duration * 0.75]
        elif duration <= 30:
            # Medium video: sample at 20%, 40%, 60%, 80%
            sample_times = [duration * 0.2, duration * 0.4, duration * 0.6, duration * 0.8]
        else:
            # Long video: sample every 10 seconds
            num_samples = min(5, max(3, int(duration / 10)))
            sample_times = [duration * i / (num_samples - 1) if num_samples > 1 else duration / 2 
                           for i in range(num_samples)]
        
        positions = []
        best_face = None
        best_face_size = 0
        
        # Find the best (largest) face across all samples
        for t in sample_times:
            if t >= duration:
                t = duration - 0.1
            
            try:
                # Get frame at time t
                frame = clip.get_frame(t)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                
                # Detect faces using Haar Cascade (optimized parameters)
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(
                        frame_gray,
                        scaleFactor=1.15,  # Balanced: not too slow, not too imprecise
                        minNeighbors=4,    # Balanced: reduce false positives while staying fast
                        minSize=(60, 60),  # Larger minimum for better detection
                        maxSize=(int(video_width * 0.8), int(video_height * 0.8))  # Ignore unrealistic sizes
                    )
                    
                    if len(faces) > 0:
                        # Find the largest face in this frame
                        largest_face = max(faces, key=lambda f: f[2] * f[3])
                        face_size = largest_face[2] * largest_face[3]
                        
                        # Keep track of the best face found across all samples
                        if face_size > best_face_size:
                            best_face = largest_face
                            best_face_size = face_size
            
            except Exception as e:
                logger.warning(f"Error tracking face at {t}s: {str(e)}")
        
        # Calculate crop position based on best face found (or center if no face)
        if best_face is not None:
            x, y, w, h = best_face
            
            # Position face in upper-third of frame (rule of thirds for portraits)
            # This looks more natural than dead center
            face_center_x = x + w // 2
            face_top_third = y + h // 3  # Focus on eyes/upper face
            
            # Calculate crop position
            crop_x = max(0, min(face_center_x - crop_width // 2, video_width - crop_width))
            crop_y = max(0, min(face_top_third - crop_height // 3, video_height - crop_height))
            
            logger.info(f"Face detected: {w}x{h}px at ({x}, {y}), using crop position ({crop_x}, {crop_y})")
        else:
            # No face detected - use center crop
            crop_x = (video_width - crop_width) // 2
            crop_y = (video_height - crop_height) // 2
            logger.info(f"No face detected, using center crop at ({crop_x}, {crop_y})")
        
        # Return static crop positions (smooth transitions disabled for performance)
        positions = [(0.0, crop_x, crop_y), (duration, crop_x, crop_y)]
        
        return positions
    
    def _track_mouse_or_feature(
        self,
        clip: VideoFileClip,
        crop_width: int,
        crop_height: int,
        duration: float,
        tracking_focus: str
    ) -> List[Tuple[float, int, int]]:
        """Track mouse cursor or product feature for demo videos (OPTIMIZED - Smart Activity Analysis)."""
        logger.info(f"Analyzing screen recording for optimal crop: {tracking_focus}")
        
        video_width = clip.w
        video_height = clip.h
        
        # OPTIMIZATION: Analyze activity zones to find optimal crop position
        # Sample 3 strategic frames to detect where the action is
        sample_times = [duration * 0.25, duration * 0.5, duration * 0.75]
        activity_zones = []
        
        for t in sample_times:
            if t >= duration:
                t = duration - 0.1
            
            try:
                frame = clip.get_frame(t)
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                
                # Detect high-contrast regions (likely UI elements, text, or active areas)
                # Use edge detection to find areas of interest
                edges = cv2.Canny(frame_gray, 50, 150)
                
                # Divide frame into grid and find which regions have most edges (activity)
                grid_size = 4  # 4x4 grid
                cell_width = video_width // grid_size
                cell_height = video_height // grid_size
                
                max_activity = 0
                best_cell_x = grid_size // 2
                best_cell_y = grid_size // 2
                
                for grid_y in range(grid_size):
                    for grid_x in range(grid_size):
                        # Extract cell
                        y1 = grid_y * cell_height
                        y2 = min((grid_y + 1) * cell_height, video_height)
                        x1 = grid_x * cell_width
                        x2 = min((grid_x + 1) * cell_width, video_width)
                        
                        cell = edges[y1:y2, x1:x2]
                        activity = np.sum(cell) / 255  # Count edge pixels
                        
                        if activity > max_activity:
                            max_activity = activity
                            best_cell_x = grid_x
                            best_cell_y = grid_y
                
                # Store the center of the most active cell
                center_x = (best_cell_x + 0.5) * cell_width
                center_y = (best_cell_y + 0.5) * cell_height
                activity_zones.append((center_x, center_y, max_activity))
                
            except Exception as e:
                logger.warning(f"Error analyzing activity at {t}s: {str(e)}")
        
        # Calculate weighted average of activity zones
        if activity_zones:
            total_weight = sum(zone[2] for zone in activity_zones)
            if total_weight > 0:
                weighted_x = sum(zone[0] * zone[2] for zone in activity_zones) / total_weight
                weighted_y = sum(zone[1] * zone[2] for zone in activity_zones) / total_weight
                
                # Calculate crop position centered on activity zone
                crop_x = int(max(0, min(weighted_x - crop_width // 2, video_width - crop_width)))
                crop_y = int(max(0, min(weighted_y - crop_height // 2, video_height - crop_height)))
                
                logger.info(f"Activity detected at ({int(weighted_x)}, {int(weighted_y)}), using crop position ({crop_x}, {crop_y})")
            else:
                # No significant activity - use center
                crop_x = (video_width - crop_width) // 2
                crop_y = (video_height - crop_height) // 2
                logger.info(f"Low activity detected, using center crop at ({crop_x}, {crop_y})")
        else:
            # Fallback to center crop
            crop_x = (video_width - crop_width) // 2
            crop_y = (video_height - crop_height) // 2
            logger.info(f"Analysis failed, using center crop at ({crop_x}, {crop_y})")
        
        # Return static crop positions (smooth transitions disabled for performance)
        positions = [(0.0, crop_x, crop_y), (duration, crop_x, crop_y)]
        
        return positions
    
    def _create_simple_smooth_path(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        duration: float,
        fps: int = 30
    ) -> List[Tuple[float, int, int]]:
        """Create simple linear smooth path between two points (SIMPLIFIED for performance)."""
        if duration <= 0:
            return [(0.0, start_pos[0], start_pos[1])]
        
        # Check if movement is significant enough to warrant smoothing
        movement = np.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
        if movement < self.min_movement_threshold:
            # Not enough movement, use static
            return [(0.0, start_pos[0], start_pos[1]), (duration, start_pos[0], start_pos[1])]
        
        # Create simple linear interpolation
        num_frames = int(duration * fps)
        path = []
        
        for i in range(num_frames):
            t = i / fps
            progress = i / (num_frames - 1) if num_frames > 1 else 0
            
            # Simple linear interpolation (fast and smooth enough)
            x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * progress)
            y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * progress)
            
            path.append((t, x, y))
        
        return path
    
    def _center_crop_positions(
        self,
        crop_width: int,
        crop_height: int,
        duration: float
    ) -> List[Tuple[float, int, int]]:
        """Generate center crop positions (fallback)."""
        return [(0.0, 0, 0), (duration, 0, 0)]
    
    def _smooth_positions_simple(
        self,
        positions: List[Tuple[float, int, int]],
        duration: float
    ) -> List[Tuple[float, int, int]]:
        """Simple position smoothing (DEPRECATED - use static crop for performance)."""
        # This method is kept for backward compatibility but not used
        # Static cropping is faster and good enough for most use cases
        logger.warning("Smooth positions called but static crop is recommended for performance")
        return positions
    
    def _apply_dynamic_crop(
        self,
        clip: VideoFileClip,
        crop_positions: List[Tuple[float, int, int]],
        crop_width: int,
        crop_height: int,
        target_size: Tuple[int, int]
    ) -> VideoFileClip:
        """Apply static cropping (OPTIMIZED - removed slow dynamic cropping)."""
        target_width, target_height = target_size
        
        try:
            # ALWAYS use static crop for best performance
            # Dynamic frame-by-frame cropping is 10-20x slower with minimal visual benefit
            
            # Calculate average position from all samples
            avg_x = sum(p[1] for p in crop_positions) // len(crop_positions)
            avg_y = sum(p[2] for p in crop_positions) // len(crop_positions)
            
            # Ensure crop position is within bounds
            avg_x = max(0, min(avg_x, clip.w - crop_width))
            avg_y = max(0, min(avg_y, clip.h - crop_height))
            
            # Use MoviePy's built-in crop and resize (fast and reliable)
            logger.info(f"Applying static crop at ({avg_x}, {avg_y}) size {crop_width}x{crop_height}")
            cropped = clip.cropped(x1=avg_x, y1=avg_y, x2=avg_x + crop_width, y2=avg_y + crop_height)
            resized = cropped.resized(new_size=(target_width, target_height))
            
            logger.info(f"✅ Crop applied successfully, resized to {target_width}x{target_height}")
            return resized
            
        except Exception as e:
            logger.error(f"Error applying crop: {e}")
            logger.warning(f"Falling back to simple resize without cropping")
            # Fallback: just resize without cropping
            try:
                return clip.resized(new_size=(target_width, target_height))
            except Exception as e2:
                logger.error(f"Resize fallback also failed: {e2}")
                raise Exception(f"Crop and resize both failed: {e}, {e2}")
