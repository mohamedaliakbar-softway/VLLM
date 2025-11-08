"""Smart cropping service with intelligent subject tracking."""
import cv2
import numpy as np
from moviepy import VideoFileClip
from typing import Dict, List, Tuple, Optional
import logging
from scipy.interpolate import interp1d
import os

logger = logging.getLogger(__name__)


class SmartCropper:
    """Intelligent cropping with subject tracking for podcasts and product demos."""
    
    def __init__(self):
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
        """Track person/face position for podcast videos."""
        logger.info("Tracking person/face in video...")
        
        positions = []
        fps = clip.fps
        frame_interval = 0.5  # Analyze every 0.5 seconds
        num_frames = int(duration / frame_interval)
        
        # Get video dimensions
        video_width = clip.w
        video_height = clip.h
        
        for i in range(num_frames):
            t = i * frame_interval
            if t >= duration:
                break
            
            try:
                # Get frame at time t
                frame = clip.get_frame(t)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                
                # Detect faces using Haar Cascade
                faces = []
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(
                        frame_gray,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(30, 30)
                    )
                
                if len(faces) > 0:
                    # Get the largest face (most prominent)
                    largest_face = max(faces, key=lambda f: f[2] * f[3])  # width * height
                    x, y, w, h = largest_face
                    
                    # Get face center
                    face_center_x = x + w // 2
                    face_center_y = y + h // 2
                    
                    # Calculate crop position to center face
                    crop_x = max(0, min(face_center_x - crop_width // 2, video_width - crop_width))
                    crop_y = max(0, min(face_center_y - crop_height // 2, video_height - crop_height))
                    
                    positions.append((t, crop_x, crop_y))
                else:
                    # No face detected - use center
                    crop_x = (video_width - crop_width) // 2
                    crop_y = (video_height - crop_height) // 2
                    positions.append((t, crop_x, crop_y))
            
            except Exception as e:
                logger.warning(f"Error tracking face at {t}s: {str(e)}")
                # Fallback to center
                crop_x = (video_width - crop_width) // 2
                crop_y = (video_height - crop_height) // 2
                positions.append((t, crop_x, crop_y))
        
        # Smooth the positions
        return self._smooth_positions(positions, duration)
    
    def _track_mouse_or_feature(
        self,
        clip: VideoFileClip,
        crop_width: int,
        crop_height: int,
        duration: float,
        tracking_focus: str
    ) -> List[Tuple[float, int, int]]:
        """Track mouse cursor or product feature for demo videos."""
        logger.info(f"Tracking mouse/feature in video: {tracking_focus}")
        
        positions = []
        fps = clip.fps
        frame_interval = 0.3  # Analyze more frequently for mouse tracking
        num_frames = int(duration / frame_interval)
        
        video_width = clip.w
        video_height = clip.h
        
        # Try to detect mouse cursor (white/light colored small object)
        for i in range(num_frames):
            t = i * frame_interval
            if t >= duration:
                break
            
            try:
                frame = clip.get_frame(t)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Convert to HSV for better color detection
                hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
                
                # Detect white/light objects (typical mouse cursor)
                lower_white = np.array([0, 0, 200])
                upper_white = np.array([180, 30, 255])
                mask = cv2.inRange(hsv, lower_white, upper_white)
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if contours:
                    # Find the smallest contour (likely mouse cursor)
                    smallest_contour = min(contours, key=cv2.contourArea)
                    if cv2.contourArea(smallest_contour) < 500:  # Small object
                        M = cv2.moments(smallest_contour)
                        if M["m00"] != 0:
                            cursor_x = int(M["m10"] / M["m00"])
                            cursor_y = int(M["m01"] / M["m00"])
                            
                            # Center crop on cursor with some offset for context
                            offset_x = crop_width // 4
                            offset_y = crop_height // 4
                            
                            crop_x = max(0, min(cursor_x - crop_width // 2 + offset_x, video_width - crop_width))
                            crop_y = max(0, min(cursor_y - crop_height // 2 + offset_y, video_height - crop_height))
                            
                            positions.append((t, crop_x, crop_y))
                            continue
                
                # Fallback: detect center of screen activity (motion detection)
                if i > 0:
                    prev_frame = clip.get_frame(max(0, t - frame_interval))
                    diff = cv2.absdiff(frame, prev_frame)
                    gray_diff = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
                    
                    # Find region with most activity
                    _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    if contours:
                        largest_contour = max(contours, key=cv2.contourArea)
                        M = cv2.moments(largest_contour)
                        if M["m00"] != 0:
                            center_x = int(M["m10"] / M["m00"])
                            center_y = int(M["m01"] / M["m00"])
                            
                            crop_x = max(0, min(center_x - crop_width // 2, video_width - crop_width))
                            crop_y = max(0, min(center_y - crop_height // 2, video_height - crop_height))
                            
                            positions.append((t, crop_x, crop_y))
                            continue
                
                # Final fallback: center
                crop_x = (video_width - crop_width) // 2
                crop_y = (video_height - crop_height) // 2
                positions.append((t, crop_x, crop_y))
            
            except Exception as e:
                logger.warning(f"Error tracking mouse/feature at {t}s: {str(e)}")
                crop_x = (video_width - crop_width) // 2
                crop_y = (video_height - crop_height) // 2
                positions.append((t, crop_x, crop_y))
        
        return self._smooth_positions(positions, duration)
    
    def _center_crop_positions(
        self,
        crop_width: int,
        crop_height: int,
        duration: float
    ) -> List[Tuple[float, int, int]]:
        """Generate center crop positions (fallback)."""
        return [(0.0, 0, 0), (duration, 0, 0)]
    
    def _smooth_positions(
        self,
        positions: List[Tuple[float, int, int]],
        duration: float
    ) -> List[Tuple[float, int, int]]:
        """Smooth crop positions using interpolation and filtering to prevent shaking."""
        if len(positions) < 2:
            return positions
        
        times = np.array([p[0] for p in positions])
        x_positions = np.array([p[1] for p in positions], dtype=float)
        y_positions = np.array([p[2] for p in positions], dtype=float)
        
        # Apply moving average filter to reduce jitter
        if len(positions) > 3:
            try:
                from scipy.ndimage import uniform_filter1d
                window_size = min(3, len(positions) // 2)
                if window_size > 1:
                    x_positions = uniform_filter1d(x_positions, size=window_size, mode='nearest')
                    y_positions = uniform_filter1d(y_positions, size=window_size, mode='nearest')
            except ImportError:
                # Fallback if scipy.ndimage not available
                logger.warning("scipy.ndimage not available, skipping filter")
        
        # Use cubic interpolation for smoother motion (if enough points)
        if len(positions) >= 4:
            interp_kind = 'cubic'
        else:
            interp_kind = 'linear'
        
        # Create interpolation functions
        fx = interp1d(times, x_positions, kind=interp_kind, fill_value='extrapolate', bounds_error=False)
        fy = interp1d(times, y_positions, kind=interp_kind, fill_value='extrapolate', bounds_error=False)
        
        # Generate smooth positions at video frame rate (more frequent = smoother)
        smooth_positions = []
        fps = 30  # Assume 30fps for smooth interpolation
        interval = 1.0 / fps  # ~0.033s intervals
        
        t = 0.0
        while t <= duration:
            x = float(fx(t))
            y = float(fy(t))
            smooth_positions.append((t, int(x), int(y)))
            t += interval
        
        return smooth_positions
    
    def _apply_dynamic_crop(
        self,
        clip: VideoFileClip,
        crop_positions: List[Tuple[float, int, int]],
        crop_width: int,
        crop_height: int,
        target_size: Tuple[int, int]
    ) -> VideoFileClip:
        """Apply dynamic cropping based on position data."""
        target_width, target_height = target_size
        
        # If we have very few positions, use average position
        if len(crop_positions) <= 2:
            avg_x = sum(p[1] for p in crop_positions) // len(crop_positions)
            avg_y = sum(p[2] for p in crop_positions) // len(crop_positions)
            # Use simple crop
            cropped = clip.cropped(x1=avg_x, y1=avg_y, x2=avg_x + crop_width, y2=avg_y + crop_height)
            return cropped.resized(new_size=(target_width, target_height))
        
        # Create interpolation functions for smooth position lookup
        times = np.array([p[0] for p in crop_positions])
        x_positions = np.array([p[1] for p in crop_positions], dtype=float)
        y_positions = np.array([p[2] for p in crop_positions], dtype=float)
        
        # Use interpolation for smooth position lookup (no abrupt jumps)
        if len(crop_positions) >= 4:
            interp_kind = 'cubic'
        elif len(crop_positions) >= 2:
            interp_kind = 'linear'
        else:
            interp_kind = 'linear'
        
        fx = interp1d(times, x_positions, kind=interp_kind, fill_value='extrapolate', bounds_error=False)
        fy = interp1d(times, y_positions, kind=interp_kind, fill_value='extrapolate', bounds_error=False)
        
        # Store previous position for velocity limiting (prevents sudden jumps)
        prev_crop_x = None
        prev_crop_y = None
        max_velocity = 50  # Maximum pixels per frame to move (prevents shaking)
        
        # For dynamic cropping, create a function that adjusts crop position over time
        def make_frame(t):
            nonlocal prev_crop_x, prev_crop_y
            
            # Use interpolation to get smooth position (not closest)
            crop_x = float(fx(t))
            crop_y = float(fy(t))
            
            # Apply velocity limiting to prevent sudden jumps
            if prev_crop_x is not None and prev_crop_y is not None:
                dx = crop_x - prev_crop_x
                dy = crop_y - prev_crop_y
                distance = np.sqrt(dx**2 + dy**2)
                
                if distance > max_velocity:
                    # Limit velocity
                    scale = max_velocity / distance
                    crop_x = prev_crop_x + dx * scale
                    crop_y = prev_crop_y + dy * scale
                
                prev_crop_x = crop_x
                prev_crop_y = crop_y
            else:
                prev_crop_x = crop_x
                prev_crop_y = crop_y
            
            # Ensure crop coordinates are within bounds
            crop_x = max(0, min(int(crop_x), clip.w - crop_width))
            crop_y = max(0, min(int(crop_y), clip.h - crop_height))
            
            # Get frame at time t
            frame = clip.get_frame(t)
            
            # Crop the frame
            cropped = frame[int(crop_y):int(crop_y + crop_height), int(crop_x):int(crop_x + crop_width)]
            
            # Handle edge cases where crop might be out of bounds
            if cropped.shape[0] != crop_height or cropped.shape[1] != crop_width:
                # Fallback: use center crop
                center_x = (clip.w - crop_width) // 2
                center_y = (clip.h - crop_height) // 2
                cropped = frame[int(center_y):int(center_y + crop_height), int(center_x):int(center_x + crop_width)]
            
            # Resize to target size using high-quality resampling
            from PIL import Image
            img = Image.fromarray(cropped)
            img_resized = img.resize((target_width, target_height), Image.LANCZOS)
            
            return np.array(img_resized)
        
        # Create new clip with dynamic cropping
        from moviepy import VideoClip
        new_clip = VideoClip(make_frame, duration=clip.duration)
        new_clip = new_clip.with_fps(clip.fps)
        
        # Copy audio if available
        if clip.audio is not None:
            new_clip = new_clip.with_audio(clip.audio)
        
        return new_clip

