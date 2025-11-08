"""OCR-based focus detection to find text on screen."""
import cv2
import numpy as np
import logging
from typing import Optional, Tuple, List
import re

logger = logging.getLogger(__name__)


class OCRFocusDetector:
    """Detect text on screen using OCR to find focus points."""
    
    def __init__(self, enable_ocr: bool = False):
        """Initialize OCR detector (DISABLED BY DEFAULT for performance)."""
        self.ocr_available = False
        self.pytesseract = None
        
        if not enable_ocr:
            logger.info("OCR focus detection disabled (enable_ocr=False)")
            return
        
        try:
            import pytesseract
            # Test if Tesseract is actually installed
            pytesseract.get_tesseract_version()
            self.pytesseract = pytesseract
            self.ocr_available = True
            logger.info("✅ OCR (Tesseract) initialized successfully")
        except ImportError:
            logger.warning("⚠️ pytesseract not installed, OCR disabled (pip install pytesseract)")
        except Exception as e:
            logger.warning(f"⚠️ Tesseract not found on system, OCR disabled: {e}")
    
    def find_text_regions(
        self,
        frame: np.ndarray,
        target_text: Optional[str] = None,
        timeout_seconds: int = 2
    ) -> List[Tuple[int, int, int, int]]:
        """
        Find bounding boxes of text on screen (with timeout for performance).
        
        Args:
            frame: Video frame (RGB numpy array)
            target_text: Optional specific text to search for
            timeout_seconds: Max time to spend on OCR (prevents hanging)
            
        Returns:
            List of (x, y, width, height) tuples for text regions
        """
        if not self.ocr_available or self.pytesseract is None:
            return []
        
        try:
            import signal
            
            # Set timeout to prevent hanging
            def timeout_handler(signum, frame):
                raise TimeoutError("OCR timeout")
            
            # Note: signal.alarm only works on Unix, skip timeout on Windows
            try:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)
            except AttributeError:
                pass  # Windows doesn't have SIGALRM
            
            # Convert to grayscale for better OCR
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # Apply thresholding to improve text detection
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # OCR with bounding boxes (FAST mode)
            data = self.pytesseract.image_to_data(
                thresh,
                output_type=self.pytesseract.Output.DICT,
                config='--psm 11 --oem 1'  # Sparse text detection, LSTM only (faster)
            )
            
            # Cancel timeout
            try:
                signal.alarm(0)
            except AttributeError:
                pass
            
            text_regions = []
            
            # Find all text regions
            for i, text in enumerate(data['text']):
                if not text or not text.strip():
                    continue
                
                # If target_text specified, only return matching regions
                if target_text:
                    if target_text.lower() not in text.lower():
                        continue
                
                # Get confidence score
                conf = int(data['conf'][i])
                if conf < 30:  # Skip low-confidence detections
                    continue
                
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                
                # Skip tiny regions (likely noise)
                if w < 10 or h < 10:
                    continue
                
                text_regions.append((x, y, w, h))
            
            logger.info(f"Found {len(text_regions)} text regions on screen")
            return text_regions
            
        except TimeoutError:
            logger.warning(f"OCR timed out after {timeout_seconds}s, skipping")
            return []
        except Exception as e:
            logger.debug(f"OCR error (non-critical): {e}")
            return []
    
    def find_largest_text_region(
        self,
        frame: np.ndarray,
        target_text: Optional[str] = None
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Find the largest text region on screen.
        
        Args:
            frame: Video frame (RGB numpy array)
            target_text: Optional specific text to search for
            
        Returns:
            (x, y, width, height) of largest text region, or None
        """
        regions = self.find_text_regions(frame, target_text)
        
        if not regions:
            return None
        
        # Find largest region by area
        largest = max(regions, key=lambda r: r[2] * r[3])
        return largest
    
    def get_text_center(
        self,
        frame: np.ndarray,
        target_text: Optional[str] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Get the center point of text on screen.
        
        Args:
            frame: Video frame (RGB numpy array)
            target_text: Optional specific text to search for
            
        Returns:
            (x, y) center point, or None if no text found
        """
        region = self.find_largest_text_region(frame, target_text)
        
        if not region:
            return None
        
        x, y, w, h = region
        center_x = x + w // 2
        center_y = y + h // 2
        
        return (center_x, center_y)
    
    def detect_ui_elements(
        self,
        frame: np.ndarray
    ) -> List[Dict]:
        """
        Detect common UI elements (buttons, labels, etc.) on screen.
        
        Args:
            frame: Video frame (RGB numpy array)
            
        Returns:
            List of detected UI elements with type and position
        """
        if not self.ocr_available:
            return []
        
        try:
            # Get all text regions
            regions = self.find_text_regions(frame)
            
            # Classify regions as potential UI elements
            ui_elements = []
            
            for x, y, w, h in regions:
                # Extract text
                roi = frame[y:y+h, x:x+w]
                text = self.pytesseract.image_to_string(roi, config='--psm 7').strip()
                
                if not text:
                    continue
                
                # Classify based on text content and size
                element_type = self._classify_ui_element(text, w, h)
                
                ui_elements.append({
                    'type': element_type,
                    'text': text,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'center': (x + w // 2, y + h // 2)
                })
            
            logger.info(f"Detected {len(ui_elements)} UI elements")
            return ui_elements
            
        except Exception as e:
            logger.error(f"Error detecting UI elements: {e}")
            return []
    
    def _classify_ui_element(self, text: str, width: int, height: int) -> str:
        """Classify UI element type based on text and dimensions."""
        text_lower = text.lower()
        
        # Button patterns
        button_keywords = ['click', 'submit', 'ok', 'cancel', 'save', 'delete', 'edit', 'add', 'remove']
        if any(keyword in text_lower for keyword in button_keywords):
            return 'button'
        
        # Menu patterns
        menu_keywords = ['menu', 'file', 'edit', 'view', 'help', 'settings']
        if any(keyword in text_lower for keyword in menu_keywords):
            return 'menu'
        
        # Label patterns (short text, small height)
        if len(text) < 20 and height < 30:
            return 'label'
        
        # Title patterns (larger text)
        if height > 30 and len(text) < 50:
            return 'title'
        
        # Text field patterns (wide, short)
        if width > 100 and height < 40:
            return 'text_field'
        
        # Default
        return 'text'
