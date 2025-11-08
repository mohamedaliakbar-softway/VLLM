"""Mouse cursor tracker for screen recordings."""
import cv2
import numpy as np
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


class CursorTracker:
    """Track mouse cursor position in screen recordings."""
    
    def __init__(self):
        self.cursor_templates = self._load_cursor_templates()
    
    def _load_cursor_templates(self) -> List[np.ndarray]:
        """Load cursor templates for template matching."""
        # Create simple cursor templates (white arrow, black arrow, hand pointer)
        templates = []
        
        # White arrow cursor (most common)
        white_arrow = np.zeros((20, 15, 3), dtype=np.uint8)
        pts = np.array([[0, 0], [0, 18], [5, 13], [8, 19], [11, 17], [8, 11], [14, 11]], np.int32)
        cv2.fillPoly(white_arrow, [pts], (255, 255, 255))
        templates.append(white_arrow)
        
        # Black arrow cursor
        black_arrow = np.zeros((20, 15, 3), dtype=np.uint8)
        cv2.fillPoly(black_arrow, [pts], (0, 0, 0))
        templates.append(black_arrow)
        
        return templates
    
    def detect_cursor(
        self,
        frame: np.ndarray,
        method: str = 'bright_spot'
    ) -> Optional[Tuple[int, int]]:
        """
        Detect cursor position using multiple methods.
        
        Args:
            frame: Video frame (RGB numpy array)
            method: Detection method ('bright_spot', 'template', 'motion')
            
        Returns:
            (x, y) cursor position, or None if not found
        """
        if method == 'bright_spot':
            return self._detect_cursor_bright_spot(frame)
        elif method == 'template':
            return self._detect_cursor_template(frame)
        elif method == 'motion':
            return self._detect_cursor_motion(frame)
        else:
            # Try all methods in order
            for m in ['bright_spot', 'template', 'motion']:
                pos = self.detect_cursor(frame, method=m)
                if pos:
                    return pos
            return None
    
    def _detect_cursor_bright_spot(
        self,
        frame: np.ndarray
    ) -> Optional[Tuple[int, int]]:
        """
        Detect cursor as a bright white spot (common in screen recordings).
        
        Args:
            frame: Video frame (RGB numpy array)
            
        Returns:
            (x, y) cursor position, or None
        """
        try:
            # Convert to HSV for better white detection
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            
            # Detect bright white spots (typical cursor)
            lower_white = np.array([0, 0, 200])
            upper_white = np.array([180, 30, 255])
            mask = cv2.inRange(hsv, lower_white, upper_white)
            
            # Find contours of white regions
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for cursor-sized regions (small, bright spots)
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Cursor is typically 10-500 pixels
                if 10 < area < 500:
                    # Get bounding box
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Check aspect ratio (cursor is roughly square or triangular)
                    aspect_ratio = w / h if h > 0 else 0
                    if 0.3 < aspect_ratio < 3.0:
                        # Return center of region
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            return (cx, cy)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error in bright spot cursor detection: {e}")
            return None
    
    def _detect_cursor_template(
        self,
        frame: np.ndarray
    ) -> Optional[Tuple[int, int]]:
        """
        Detect cursor using template matching.
        
        Args:
            frame: Video frame (RGB numpy array)
            
        Returns:
            (x, y) cursor position, or None
        """
        try:
            best_match = None
            best_score = 0.6  # Minimum confidence threshold
            
            for template in self.cursor_templates:
                # Resize template to multiple scales
                for scale in [0.5, 0.75, 1.0, 1.25, 1.5]:
                    h, w = template.shape[:2]
                    new_h, new_w = int(h * scale), int(w * scale)
                    
                    if new_h > frame.shape[0] or new_w > frame.shape[1]:
                        continue
                    
                    scaled_template = cv2.resize(template, (new_w, new_h))
                    
                    # Template matching
                    result = cv2.matchTemplate(frame, scaled_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    if max_val > best_score:
                        best_score = max_val
                        # Return center of matched region
                        best_match = (max_loc[0] + new_w // 2, max_loc[1] + new_h // 2)
            
            return best_match
            
        except Exception as e:
            logger.debug(f"Error in template cursor detection: {e}")
            return None
    
    def _detect_cursor_motion(
        self,
        frame: np.ndarray,
        prev_frame: Optional[np.ndarray] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Detect cursor based on motion (requires previous frame).
        
        Args:
            frame: Current video frame (RGB numpy array)
            prev_frame: Previous video frame (RGB numpy array)
            
        Returns:
            (x, y) cursor position, or None
        """
        if prev_frame is None:
            return None
        
        try:
            # Convert to grayscale
            gray1 = cv2.cvtColor(prev_frame, cv2.COLOR_RGB2GRAY)
            gray2 = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # Calculate frame difference
            diff = cv2.absdiff(gray1, gray2)
            
            # Threshold to get motion regions
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            
            # Find contours of motion
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for small motion regions (likely cursor)
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if 10 < area < 500:
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        return (cx, cy)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error in motion cursor detection: {e}")
            return None
    
    def track_cursor_path(
        self,
        frames: List[np.ndarray],
        sample_rate: int = 5
    ) -> List[Tuple[float, int, int]]:
        """
        Track cursor path across multiple frames.
        
        Args:
            frames: List of video frames
            sample_rate: Sample every Nth frame
            
        Returns:
            List of (time, x, y) tuples representing cursor path
        """
        cursor_path = []
        prev_frame = None
        
        for i in range(0, len(frames), sample_rate):
            frame = frames[i]
            
            # Try to detect cursor
            pos = self.detect_cursor(frame)
            
            if pos:
                # Calculate time based on frame index (assuming 30fps)
                time = i / 30.0
                cursor_path.append((time, pos[0], pos[1]))
            
            prev_frame = frame
        
        logger.info(f"Tracked cursor across {len(cursor_path)} points")
        return cursor_path
    
    def detect_cursor_clicks(
        self,
        frames: List[np.ndarray],
        cursor_path: List[Tuple[float, int, int]]
    ) -> List[Tuple[float, int, int]]:
        """
        Detect potential cursor clicks (cursor stops moving).
        
        Args:
            frames: List of video frames
            cursor_path: Cursor path from track_cursor_path
            
        Returns:
            List of (time, x, y) tuples where clicks likely occurred
        """
        if len(cursor_path) < 3:
            return []
        
        clicks = []
        
        for i in range(1, len(cursor_path) - 1):
            t1, x1, y1 = cursor_path[i - 1]
            t2, x2, y2 = cursor_path[i]
            t3, x3, y3 = cursor_path[i + 1]
            
            # Calculate movement
            dist_before = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            dist_after = np.sqrt((x3 - x2)**2 + (y3 - y2)**2)
            
            # If cursor was moving, then stopped, then moved again -> likely a click
            if dist_before > 10 and dist_after > 10:
                # Check if cursor stayed relatively still
                if np.sqrt((x3 - x1)**2 + (y3 - y1)**2) < 20:
                    clicks.append((t2, x2, y2))
        
        logger.info(f"Detected {len(clicks)} potential cursor clicks")
        return clicks
