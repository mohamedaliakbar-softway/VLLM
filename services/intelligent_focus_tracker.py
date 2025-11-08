"""Intelligent focus tracker combining audio, OCR, and cursor tracking."""
import cv2
import numpy as np
import logging
from typing import Optional, Tuple, List, Dict
from services.audio_focus_analyzer import AudioFocusAnalyzer
from services.ocr_focus_detector import OCRFocusDetector
from services.cursor_tracker import CursorTracker

logger = logging.getLogger(__name__)


class IntelligentFocusTracker:
    """
    Combine all focus detection methods with priority system.
    
    Priority Hierarchy:
    1. Mouse cursor (highest) → Follows pointer
    2. Text from audio → Focuses on mentioned UI elements
    3. Activity zones → Focuses on motion/edges
    4. High-contrast regions → Focuses on important content
    5. Center (fallback) → Safe default
    """
    
    def __init__(self, enable_audio_focus: bool = False, enable_ocr: bool = False, enable_cursor: bool = False):
        """Initialize Intelligent Focus Tracker (ALL DISABLED BY DEFAULT for performance)."""
        self.enable_audio_focus = enable_audio_focus
        self.enable_ocr = enable_ocr
        self.enable_cursor = enable_cursor
        
        # Initialize components only if enabled
        self.audio_analyzer = None
        self.ocr_detector = None
        self.cursor_tracker = None
        
        try:
            if enable_audio_focus:
                self.audio_analyzer = AudioFocusAnalyzer()
                logger.info("✅ Audio focus analysis enabled")
        except Exception as e:
            logger.warning(f"⚠️ Audio focus initialization failed: {e}")
            self.enable_audio_focus = False
        
        try:
            if enable_ocr:
                self.ocr_detector = OCRFocusDetector(enable_ocr=True)
                if not self.ocr_detector.ocr_available:
                    logger.info("⚠️ OCR not available, disabled")
                    self.enable_ocr = False
                else:
                    logger.info("✅ OCR text detection enabled")
        except Exception as e:
            logger.warning(f"⚠️ OCR initialization failed: {e}")
            self.enable_ocr = False
        
        try:
            if enable_cursor:
                self.cursor_tracker = CursorTracker()
                logger.info("✅ Cursor tracking enabled")
        except Exception as e:
            logger.warning(f"⚠️ Cursor tracking initialization failed: {e}")
            self.enable_cursor = False
        
        # Log final status
        enabled_features = []
        if self.enable_audio_focus: enabled_features.append("audio")
        if self.enable_ocr: enabled_features.append("ocr")
        if self.enable_cursor: enabled_features.append("cursor")
        
        if enabled_features:
            logger.info(f"Intelligent Focus Tracker initialized: {', '.join(enabled_features)}")
        else:
            logger.info("Intelligent Focus Tracker initialized (all features disabled - using fallback only)")
    
    def get_focus_point(
        self,
        frame: np.ndarray,
        timestamp: float,
        audio_focus: Optional[Dict] = None,
        video_width: int = None,
        video_height: int = None,
        prev_frame: Optional[np.ndarray] = None
    ) -> Tuple[int, int]:
        """
        Determine optimal focus point using priority system (with error handling).
        
        Args:
            frame: Current video frame (RGB numpy array)
            timestamp: Current timestamp in seconds
            audio_focus: Optional audio focus data from AudioFocusAnalyzer
            video_width: Video width in pixels
            video_height: Video height in pixels
            prev_frame: Previous frame for motion detection
            
        Returns:
            (focus_x, focus_y) tuple - Always returns a valid point (fallback to center)
        """
        try:
            if video_width is None:
                video_width = frame.shape[1]
            if video_height is None:
                video_height = frame.shape[0]
        except Exception as e:
            logger.error(f"Error getting frame dimensions: {e}")
            return (960, 540)  # Default center for 1920x1080
        
        # Priority 1: Mouse cursor (if detected)
        if self.enable_cursor and self.cursor_tracker:
            try:
                cursor_pos = self.cursor_tracker.detect_cursor(frame)
                if cursor_pos:
                    logger.debug(f"Focus: Cursor at {cursor_pos}")
                    return cursor_pos
            except Exception as e:
                logger.debug(f"Cursor detection failed (non-critical): {e}")
        
        # Priority 2: Text mentioned in audio
        if self.enable_audio_focus and audio_focus:
            try:
                # Check if current timestamp falls within audio focus range
                if 'start_time' in audio_focus and 'end_time' in audio_focus:
                    if audio_focus['start_time'] <= timestamp <= audio_focus['end_time']:
                        # Try to find the mentioned UI element using OCR
                        if self.enable_ocr and self.ocr_detector and 'focus_element' in audio_focus:
                            try:
                                text_pos = self.ocr_detector.get_text_center(frame, audio_focus['focus_element'])
                                if text_pos:
                                    logger.debug(f"Focus: Text '{audio_focus['focus_element']}' at {text_pos}")
                                    return text_pos
                            except Exception as e:
                                logger.debug(f"OCR text search failed (non-critical): {e}")
                        
                        # Fall back to screen region from audio
                        if 'screen_region' in audio_focus and self.audio_analyzer:
                            region_pos = self.audio_analyzer.map_region_to_coordinates(
                                audio_focus['screen_region'],
                                video_width,
                                video_height
                            )
                            logger.debug(f"Focus: Audio region '{audio_focus['screen_region']}' at {region_pos}")
                            return region_pos
            except Exception as e:
                logger.debug(f"Audio focus failed (non-critical): {e}")
        
        # Priority 3: Any text on screen (OCR)
        if self.enable_ocr and self.ocr_detector:
            try:
                text_center = self.ocr_detector.get_text_center(frame)
                if text_center:
                    logger.debug(f"Focus: OCR text at {text_center}")
                    return text_center
            except Exception as e:
                logger.debug(f"OCR detection failed (non-critical): {e}")
        
        # Priority 4: Activity detection (high-contrast regions)
        try:
            activity_pos = self._detect_activity_zone(frame)
            if activity_pos:
                logger.debug(f"Focus: Activity zone at {activity_pos}")
                return activity_pos
        except Exception as e:
            logger.debug(f"Activity detection failed (non-critical): {e}")
        
        # Priority 5: Center (fallback) - ALWAYS works
        center = (video_width // 2, video_height // 2)
        logger.debug(f"Focus: Center fallback at {center}")
        return center
    
    def get_focus_path(
        self,
        clip,
        transcript: str = "",
        duration: float = 0,
        sample_rate: int = 30
    ) -> List[Tuple[float, int, int]]:
        """
        Get focus path across entire video (SIMPLIFIED - samples fewer frames).
        
        NOTE: This is DISABLED by default since static crop is faster.
        Only use if intelligent focus tracking is truly needed.
        
        Args:
            clip: VideoFileClip object
            transcript: Video transcript for audio analysis
            duration: Video duration in seconds
            sample_rate: Sample every Nth frame (higher = faster)
            
        Returns:
            List of (time, x, y) tuples representing focus path
        """
        # If no features enabled, just return center
        if not (self.enable_audio_focus or self.enable_ocr or self.enable_cursor):
            logger.info("No focus tracking features enabled, using center")
            video_width = clip.w
            video_height = clip.h
            center = (video_width // 2, video_height // 2)
            return [(0.0, center[0], center[1]), (duration or clip.duration, center[0], center[1])]
        
        try:
            video_width = clip.w
            video_height = clip.h
            duration = duration or clip.duration
            
            # Get audio focus points if available (reuse existing Gemini analysis if possible)
            audio_focus_points = []
            if self.enable_audio_focus and self.audio_analyzer and transcript and len(transcript) > 100:
                try:
                    # Sample fewer timestamps to reduce Gemini API calls
                    timestamps = list(np.arange(0, duration, max(duration / 5, 10)))  # Max 5 samples
                    audio_focus_points = self.audio_analyzer.analyze_audio_for_focus(
                        transcript, timestamps, duration
                    )
                    logger.info(f"Got {len(audio_focus_points)} audio focus points")
                except Exception as e:
                    logger.warning(f"Audio focus analysis failed: {e}")
            
            # Sample VERY SPARSELY to avoid slowdown
            focus_path = []
            fps = clip.fps or 30
            total_frames = int(duration * fps)
            
            # Sample at most 10 points regardless of video length
            actual_sample_rate = max(sample_rate, total_frames // 10)
            
            for frame_idx in range(0, total_frames, actual_sample_rate):
                t = frame_idx / fps
                
                try:
                    frame = clip.get_frame(t)
                    
                    # Find relevant audio focus for this timestamp
                    current_audio_focus = None
                    if audio_focus_points:
                        for af in audio_focus_points:
                            if af.get('start_time', 0) <= t <= af.get('end_time', duration):
                                current_audio_focus = af
                                break
                    
                    # Get focus point
                    focus_x, focus_y = self.get_focus_point(
                        frame, t, current_audio_focus, video_width, video_height
                    )
                    
                    focus_path.append((t, focus_x, focus_y))
                    
                except Exception as e:
                    logger.debug(f"Error getting focus at {t}s: {e}")
                    # Add center as fallback
                    focus_path.append((t, video_width // 2, video_height // 2))
            
            # Ensure we have at least start and end points
            if not focus_path:
                center = (video_width // 2, video_height // 2)
                focus_path = [(0.0, center[0], center[1]), (duration, center[0], center[1])]
            
            logger.info(f"Generated focus path with {len(focus_path)} points (sampled every {actual_sample_rate} frames)")
            return focus_path
            
        except Exception as e:
            logger.error(f"Focus path generation failed: {e}, using center fallback")
            # Return center as ultimate fallback
            center = (clip.w // 2, clip.h // 2)
            return [(0.0, center[0], center[1]), (clip.duration, center[0], center[1])]
    
    def _detect_activity_zone(
        self,
        frame: np.ndarray
    ) -> Optional[Tuple[int, int]]:
        """
        Detect high-activity zone using edge detection.
        
        Args:
            frame: Video frame (RGB numpy array)
            
        Returns:
            (x, y) center of activity zone, or None
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # Detect edges
            edges = cv2.Canny(gray, 50, 150)
            
            # Divide into grid and find most active region
            h, w = frame.shape[:2]
            grid_size = 4
            cell_w = w // grid_size
            cell_h = h // grid_size
            
            max_activity = 0
            best_cell_x = grid_size // 2
            best_cell_y = grid_size // 2
            
            for gy in range(grid_size):
                for gx in range(grid_size):
                    y1 = gy * cell_h
                    y2 = min((gy + 1) * cell_h, h)
                    x1 = gx * cell_w
                    x2 = min((gx + 1) * cell_w, w)
                    
                    cell = edges[y1:y2, x1:x2]
                    activity = np.sum(cell) / 255
                    
                    if activity > max_activity:
                        max_activity = activity
                        best_cell_x = gx
                        best_cell_y = gy
            
            # Return center of most active cell
            if max_activity > 100:  # Minimum activity threshold
                center_x = int((best_cell_x + 0.5) * cell_w)
                center_y = int((best_cell_y + 0.5) * cell_h)
                return (center_x, center_y)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error detecting activity zone: {e}")
            return None
    
    def smooth_focus_path(
        self,
        focus_path: List[Tuple[float, int, int]],
        smoothing_window: int = 5
    ) -> List[Tuple[float, int, int]]:
        """
        Smooth focus path to prevent jittery camera movements.
        
        Args:
            focus_path: List of (time, x, y) tuples
            smoothing_window: Number of points to average
            
        Returns:
            Smoothed focus path
        """
        if len(focus_path) < smoothing_window:
            return focus_path
        
        smoothed = []
        
        for i in range(len(focus_path)):
            # Get window of points around current point
            start = max(0, i - smoothing_window // 2)
            end = min(len(focus_path), i + smoothing_window // 2 + 1)
            
            window = focus_path[start:end]
            
            # Average positions
            avg_x = sum(p[1] for p in window) / len(window)
            avg_y = sum(p[2] for p in window) / len(window)
            
            smoothed.append((focus_path[i][0], int(avg_x), int(avg_y)))
        
        return smoothed
