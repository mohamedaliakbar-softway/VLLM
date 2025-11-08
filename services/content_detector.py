"""
Multi-layer content detection system for intelligent framing.
Detects faces, text, motion, objects, and visual saliency.
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from moviepy import VideoFileClip

logger = logging.getLogger(__name__)

# Check for optional dependencies
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available - text detection will be disabled")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class Detection:
    """A single content detection with position and metadata."""
    type: str  # 'face', 'text', 'motion', 'object', 'saliency'
    position: Tuple[int, int]  # Center (x, y)
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float  # 0.0 to 1.0
    base_priority: int  # Base priority score
    priority: int  # Final priority score (calculated later)
    metadata: Dict  # Additional info (text content, size, etc.)
    timestamp: float  # When detected in video


class ContentDetector:
    """Multi-layer content detection system."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize face detector (OpenCV Haar Cascade)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Initialize eye cascade for speaking detection
        eye_cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
        self.eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
        
        # Settings
        self.enable_face_detection = self.config.get('enable_face_detection', True)
        self.enable_text_detection = self.config.get('enable_text_detection', True) and TESSERACT_AVAILABLE
        self.enable_motion_tracking = self.config.get('enable_motion_tracking', True)
        self.enable_object_detection = self.config.get('enable_object_detection', False)
        
        logger.info(f"ContentDetector initialized:")
        logger.info(f"  - Face detection: {self.enable_face_detection}")
        logger.info(f"  - Text detection: {self.enable_text_detection}")
        logger.info(f"  - Motion tracking: {self.enable_motion_tracking}")
        logger.info(f"  - Object detection: {self.enable_object_detection}")
    
    def detect_all_layers(self, frame: np.ndarray, timestamp: float, 
                          prev_frame: Optional[np.ndarray] = None) -> List[Detection]:
        """
        Run all detection layers on a frame and return all detections.
        
        Args:
            frame: Current frame (RGB format from MoviePy)
            timestamp: Time in video
            prev_frame: Previous frame for motion detection
            
        Returns:
            List of Detection objects
        """
        detections = []
        
        # Convert frame to BGR for OpenCV
        frame_bgr = cv2.cvtColor((frame * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # Layer 1: Face Detection (Highest Priority)
        if self.enable_face_detection:
            face_detections = self._detect_faces(frame_bgr, gray, timestamp)
            detections.extend(face_detections)
        
        # Layer 2: Text Detection (High Priority)
        if self.enable_text_detection:
            text_detections = self._detect_text(frame_bgr, timestamp)
            detections.extend(text_detections)
        
        # Layer 3: Motion Detection (Medium-High Priority)
        if self.enable_motion_tracking and prev_frame is not None:
            motion_detections = self._detect_motion(frame_bgr, prev_frame, timestamp)
            detections.extend(motion_detections)
        
        # Layer 4: Object Detection (Medium Priority)
        if self.enable_object_detection:
            object_detections = self._detect_objects(frame_bgr, timestamp)
            detections.extend(object_detections)
        
        # Layer 5: Visual Saliency (Low Priority - fallback)
        if not detections:
            saliency_detection = self._detect_saliency(gray, timestamp)
            if saliency_detection:
                detections.append(saliency_detection)
        
        return detections
    
    def _detect_faces(self, frame_bgr: np.ndarray, gray: np.ndarray, 
                      timestamp: float) -> List[Detection]:
        """Detect faces with priority based on size and position."""
        detections = []
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        for (x, y, w, h) in faces:
            # Calculate center
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Check if face is speaking (detect eyes/mouth movement)
            face_roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(face_roi_gray)
            is_speaking = len(eyes) >= 2  # Simple heuristic
            
            # Calculate confidence based on size
            face_area = w * h
            frame_area = gray.shape[0] * gray.shape[1]
            confidence = min(face_area / (frame_area * 0.05), 1.0)  # Normalized
            
            # Priority: speaking face = 100, static face = 90
            base_priority = 100 if is_speaking else 90
            
            detections.append(Detection(
                type='face',
                position=(center_x, center_y),
                bbox=(x, y, w, h),
                confidence=confidence,
                base_priority=base_priority,
                priority=base_priority,
                metadata={
                    'is_speaking': is_speaking,
                    'size': (w, h),
                    'area': face_area
                },
                timestamp=timestamp
            ))
            
            logger.debug(f"Face detected at ({center_x}, {center_y}), "
                        f"size: {w}x{h}, speaking: {is_speaking}")
        
        return detections
    
    def _detect_text(self, frame_bgr: np.ndarray, timestamp: float) -> List[Detection]:
        """Detect text regions using EAST detector + OCR with Tesseract."""
        if not TESSERACT_AVAILABLE or not PIL_AVAILABLE:
            return []
        
        detections = []
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Use MSER for text region detection (fast)
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        
        # Group nearby regions into text blocks
        text_regions = self._group_text_regions(regions, gray.shape)
        
        # Method 2: Fallback - divide frame into grid and check for text
        if len(text_regions) < 3:
            text_regions.extend(self._grid_text_search(gray))
        
        # Run OCR on detected regions
        for (x, y, w, h) in text_regions[:10]:  # Limit to top 10 regions
            if w < 20 or h < 10:  # Skip tiny regions
                continue
            
            # Extract region
            roi = gray[y:y+h, x:x+w]
            
            # Preprocess for better OCR
            roi = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            try:
                # Run Tesseract OCR
                text = pytesseract.image_to_string(
                    Image.fromarray(roi),
                    config='--psm 6'  # Assume uniform block of text
                ).strip()
                
                if len(text) > 2:  # Valid text found
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    # Calculate priority based on text characteristics
                    text_area = w * h
                    is_large = text_area > (gray.shape[0] * gray.shape[1] * 0.02)
                    is_title = len(text) < 50 and h > 30
                    is_code = any(char in text for char in ['(', ')', '{', '}', '=', ';'])
                    
                    if is_title or is_large:
                        base_priority = 90  # Large text/title
                    elif is_code:
                        base_priority = 85  # Code
                    else:
                        base_priority = 70  # Regular text
                    
                    confidence = min(len(text) / 20.0, 1.0)  # Longer text = more confident
                    
                    detections.append(Detection(
                        type='text',
                        position=(center_x, center_y),
                        bbox=(x, y, w, h),
                        confidence=confidence,
                        base_priority=base_priority,
                        priority=base_priority,
                        metadata={
                            'text': text,
                            'size': (w, h),
                            'area': text_area,
                            'is_large': is_large,
                            'is_code': is_code
                        },
                        timestamp=timestamp
                    ))
                    
                    logger.debug(f"Text detected: '{text[:30]}...' at ({center_x}, {center_y})")
            
            except Exception as e:
                logger.debug(f"OCR failed for region: {e}")
                continue
        
        return detections
    
    def _group_text_regions(self, mser_regions: List, frame_shape: Tuple) -> List[Tuple]:
        """Group MSER regions into text blocks."""
        if not mser_regions:
            return []
        
        # Get bounding boxes for all regions
        bboxes = []
        for region in mser_regions:
            if len(region) < 10:  # Skip tiny regions
                continue
            x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))
            if w > 15 and h > 10:  # Minimum text size
                bboxes.append([x, y, w, h])
        
        if not bboxes:
            return []
        
        # Group nearby bounding boxes
        grouped = []
        for bbox in bboxes:
            merged = False
            for i, group in enumerate(grouped):
                # Check if bbox overlaps or is near existing group
                if self._boxes_near(bbox, group, threshold=30):
                    grouped[i] = self._merge_boxes(bbox, group)
                    merged = True
                    break
            if not merged:
                grouped.append(bbox)
        
        return grouped[:20]  # Return top 20
    
    def _boxes_near(self, box1: List, box2: List, threshold: int = 30) -> bool:
        """Check if two boxes are near each other."""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        # Calculate distance between centers
        c1_x, c1_y = x1 + w1//2, y1 + h1//2
        c2_x, c2_y = x2 + w2//2, y2 + h2//2
        
        distance = np.sqrt((c1_x - c2_x)**2 + (c1_y - c2_y)**2)
        return distance < threshold
    
    def _merge_boxes(self, box1: List, box2: List) -> List:
        """Merge two bounding boxes."""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        x = min(x1, x2)
        y = min(y1, y2)
        w = max(x1 + w1, x2 + w2) - x
        h = max(y1 + h1, y2 + h2) - y
        
        return [x, y, w, h]
    
    def _grid_text_search(self, gray: np.ndarray) -> List[Tuple]:
        """Divide frame into grid and search for text-like regions."""
        h, w = gray.shape
        grid_size = 8
        cell_w, cell_h = w // grid_size, h // grid_size
        
        text_regions = []
        
        for gy in range(grid_size):
            for gx in range(grid_size):
                x1, y1 = gx * cell_w, gy * cell_h
                x2, y2 = x1 + cell_w, y1 + cell_h
                
                cell = gray[y1:y2, x1:x2]
                
                # Check for text characteristics (high edge density in horizontal patterns)
                edges = cv2.Canny(cell, 50, 150)
                edge_density = np.sum(edges) / (cell_w * cell_h * 255)
                
                if edge_density > 0.05:  # Threshold for text-like patterns
                    text_regions.append((x1, y1, cell_w, cell_h))
        
        return text_regions
    
    def _detect_motion(self, frame_bgr: np.ndarray, prev_frame_bgr: np.ndarray, 
                       timestamp: float) -> List[Detection]:
        """Detect motion and activity hotspots using optical flow."""
        detections = []
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(prev_frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # Calculate dense optical flow
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        
        # Calculate magnitude and angle of flow
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        # Find high motion regions
        motion_threshold = np.percentile(magnitude, 85)  # Top 15% motion
        motion_mask = magnitude > motion_threshold
        
        # Find contours of motion regions
        motion_mask_uint8 = (motion_mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(motion_mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Process significant motion regions
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 100:  # Skip tiny movements
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Calculate average motion magnitude in this region
            region_magnitude = magnitude[y:y+h, x:x+w]
            avg_magnitude = np.mean(region_magnitude)
            
            # Determine if it's cursor-like movement (small, fast)
            is_cursor = area < 5000 and avg_magnitude > 5
            
            base_priority = 80 if is_cursor else 75
            confidence = min(avg_magnitude / 10.0, 1.0)
            
            detections.append(Detection(
                type='motion',
                position=(center_x, center_y),
                bbox=(x, y, w, h),
                confidence=confidence,
                base_priority=base_priority,
                priority=base_priority,
                metadata={
                    'area': area,
                    'magnitude': avg_magnitude,
                    'is_cursor': is_cursor
                },
                timestamp=timestamp
            ))
            
            logger.debug(f"Motion detected at ({center_x}, {center_y}), "
                        f"magnitude: {avg_magnitude:.2f}, cursor: {is_cursor}")
        
        return detections
    
    def _detect_objects(self, frame_bgr: np.ndarray, timestamp: float) -> List[Detection]:
        """Detect objects using contour detection (placeholder for future YOLO integration)."""
        detections = []
        
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # Simple contour-based object detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find significant objects
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1000 or area > frame_bgr.shape[0] * frame_bgr.shape[1] * 0.5:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Basic shape analysis
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            confidence = min(area / 10000.0, 1.0)
            
            detections.append(Detection(
                type='object',
                position=(center_x, center_y),
                bbox=(x, y, w, h),
                confidence=confidence,
                base_priority=60,
                priority=60,
                metadata={
                    'area': area,
                    'circularity': circularity,
                    'size': (w, h)
                },
                timestamp=timestamp
            ))
        
        return detections[:5]  # Return top 5 objects
    
    def _detect_saliency(self, gray: np.ndarray, timestamp: float) -> Optional[Detection]:
        """Find most visually salient region as fallback."""
        # Use edge detection to find interesting regions
        edges = cv2.Canny(gray, 50, 150)
        
        # Divide into grid and find most active cell
        h, w = gray.shape
        grid_size = 6
        cell_w, cell_h = w // grid_size, h // grid_size
        
        max_activity = 0
        best_cell = (grid_size // 2, grid_size // 2)  # Default to center
        
        for gy in range(grid_size):
            for gx in range(grid_size):
                x1, y1 = gx * cell_w, gy * cell_h
                x2, y2 = x1 + cell_w, y1 + cell_h
                
                cell_edges = edges[y1:y2, x1:x2]
                activity = np.sum(cell_edges)
                
                if activity > max_activity:
                    max_activity = activity
                    best_cell = (gx, gy)
        
        # Calculate center of best cell
        center_x = int((best_cell[0] + 0.5) * cell_w)
        center_y = int((best_cell[1] + 0.5) * cell_h)
        
        return Detection(
            type='saliency',
            position=(center_x, center_y),
            bbox=(best_cell[0] * cell_w, best_cell[1] * cell_h, cell_w, cell_h),
            confidence=0.5,
            base_priority=50,
            priority=50,
            metadata={'activity': max_activity},
            timestamp=timestamp
        )
