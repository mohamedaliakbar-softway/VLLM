"""
Brand Logo Overlay Service
Adds brand logos/watermarks to videos using MoviePy
Similar to caption burning but for image overlays
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip

logger = logging.getLogger(__name__)


class LogoOverlay:
    """Handles adding brand logos to videos."""
    
    # Position presets (relative to video dimensions)
    POSITIONS = {
        "top-left": (0.02, 0.02),
        "top-right": (0.98, 0.02),
        "bottom-left": (0.02, 0.98),
        "bottom-right": (0.98, 0.98),
        "center": (0.5, 0.5),
        "top-center": (0.5, 0.02),
        "bottom-center": (0.5, 0.98),
    }
    
    def __init__(self):
        """Initialize logo overlay service."""
        self.logger = logger
        
    def add_logo(
        self,
        video_path: str,
        logo_path: str,
        output_path: str,
        position: str = "bottom-right",
        size_percent: float = 10.0,
        opacity: float = 0.8,
        padding: int = 20
    ) -> str:
        """
        Add a brand logo overlay to a video.
        
        Args:
            video_path: Path to input video
            logo_path: Path to logo image (PNG with transparency recommended)
            output_path: Path for output video
            position: Logo position ("top-left", "top-right", "bottom-left", "bottom-right", 
                     "center", "top-center", "bottom-center")
            size_percent: Logo size as percentage of video width (default 10%)
            opacity: Logo opacity 0.0-1.0 (default 0.8)
            padding: Padding from edges in pixels (default 20)
            
        Returns:
            Path to output video with logo
            
        Raises:
            Exception: If video processing fails
        """
        try:
            self.logger.info(f"Adding logo to video: {video_path}")
            self.logger.info(f"Logo: {logo_path}, Position: {position}, Size: {size_percent}%")
            
            # Validate inputs
            if not Path(video_path).exists():
                raise FileNotFoundError(f"Video not found: {video_path}")
            if not Path(logo_path).exists():
                raise FileNotFoundError(f"Logo not found: {logo_path}")
            if position not in self.POSITIONS:
                raise ValueError(f"Invalid position: {position}. Must be one of {list(self.POSITIONS.keys())}")
            if not 1.0 <= size_percent <= 50.0:
                raise ValueError(f"Size percent must be between 1 and 50, got {size_percent}")
            if not 0.0 <= opacity <= 1.0:
                raise ValueError(f"Opacity must be between 0 and 1, got {opacity}")
            
            # Load video
            video = VideoFileClip(video_path)
            video_width, video_height = video.size
            self.logger.info(f"Video dimensions: {video_width}x{video_height}")
            
            # Calculate logo size
            logo_width = int(video_width * (size_percent / 100.0))
            
            # Load and resize logo
            logo = ImageClip(logo_path)
            logo = logo.resized(width=logo_width)  # Maintains aspect ratio
            logo_width, logo_height = logo.size
            self.logger.info(f"Logo dimensions: {logo_width}x{logo_height}")
            
            # Set logo opacity
            logo = logo.with_opacity(opacity)
            
            # Calculate position
            pos_x, pos_y = self._calculate_position(
                position,
                video_width,
                video_height,
                logo_width,
                logo_height,
                padding
            )
            
            # Set logo position and duration
            logo = logo.with_position((pos_x, pos_y))
            logo = logo.with_duration(video.duration)
            
            # Composite logo over video
            self.logger.info(f"Compositing logo at position ({pos_x}, {pos_y})")
            final_video = CompositeVideoClip([video, logo])
            
            # Write output
            self.logger.info(f"Writing video with logo to: {output_path}")
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger=None  # Suppress MoviePy's verbose logging
            )
            
            # Clean up
            video.close()
            logo.close()
            final_video.close()
            
            self.logger.info(f"Logo overlay completed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error adding logo overlay: {str(e)}")
            raise
    
    def _calculate_position(
        self,
        position: str,
        video_width: int,
        video_height: int,
        logo_width: int,
        logo_height: int,
        padding: int
    ) -> Tuple[int, int]:
        """
        Calculate exact pixel position for logo.
        
        Args:
            position: Position preset name
            video_width: Video width in pixels
            video_height: Video height in pixels
            logo_width: Logo width in pixels
            logo_height: Logo height in pixels
            padding: Padding from edges in pixels
            
        Returns:
            Tuple of (x, y) coordinates in pixels
        """
        rel_x, rel_y = self.POSITIONS[position]
        
        # Calculate base position (using approximate comparison)
        if abs(rel_x - 0.02) < 0.01:  # Left
            x = padding
        elif abs(rel_x - 0.98) < 0.01:  # Right
            x = video_width - logo_width - padding
        else:  # Center (0.5)
            x = (video_width - logo_width) // 2
        
        if abs(rel_y - 0.02) < 0.01:  # Top
            y = padding
        elif abs(rel_y - 0.98) < 0.01:  # Bottom
            y = video_height - logo_height - padding
        else:  # Center (0.5)
            y = (video_height - logo_height) // 2
        
        return (x, y)
    
    def validate_logo_image(self, logo_path: str) -> dict:
        """
        Validate a logo image file.
        
        Args:
            logo_path: Path to logo image
            
        Returns:
            Dict with validation results and image info
        """
        try:
            if not Path(logo_path).exists():
                return {
                    "valid": False,
                    "error": "File not found"
                }
            
            # Check file extension
            ext = Path(logo_path).suffix.lower()
            valid_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
            if ext not in valid_exts:
                return {
                    "valid": False,
                    "error": f"Invalid file type. Supported: {', '.join(valid_exts)}"
                }
            
            # Try to load image
            try:
                logo = ImageClip(logo_path)
                width, height = logo.size
                logo.close()
                
                return {
                    "valid": True,
                    "width": width,
                    "height": height,
                    "format": ext[1:].upper(),
                    "path": logo_path
                }
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Failed to load image: {str(e)}"
                }
                
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }


def test_logo_overlay():
    """Test function for logo overlay."""
    import os
    
    # Test paths (update these for actual testing)
    video_path = "test_video.mp4"
    logo_path = "test_logo.png"
    output_path = "test_output.mp4"
    
    if os.path.exists(video_path) and os.path.exists(logo_path):
        overlay = LogoOverlay()
        
        # Validate logo first
        validation = overlay.validate_logo_image(logo_path)
        print(f"Logo validation: {validation}")
        
        if validation['valid']:
            # Add logo
            result = overlay.add_logo(
                video_path=video_path,
                logo_path=logo_path,
                output_path=output_path,
                position="bottom-right",
                size_percent=12.0,
                opacity=0.85,
                padding=25
            )
            print(f"Logo added successfully: {result}")
    else:
        print("Test files not found. Create test_video.mp4 and test_logo.png to test.")


if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    test_logo_overlay()
