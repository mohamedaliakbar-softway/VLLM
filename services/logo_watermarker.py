"""
Logo Watermarker Service
Adds brand logo watermarks to videos using FFmpeg
"""
import ffmpeg
import os
import base64
from pathlib import Path
from typing import Optional


class LogoWatermarker:
    """Add brand logo watermarks to videos"""
    
    def __init__(self):
        self.temp_dir = Path("uploads/temp_logos")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def decode_logo(self, data_url: str) -> str:
        """
        Convert base64 data URL to temporary PNG file
        
        Args:
            data_url: Base64 encoded image data URL
            
        Returns:
            Path to temporary logo file
        """
        # Remove data URL prefix (e.g., "data:image/png;base64,")
        if ',' in data_url:
            header, encoded = data_url.split(',', 1)
        else:
            encoded = data_url
        
        # Decode base64 to bytes
        logo_data = base64.b64decode(encoded)
        
        # Create unique temp file
        logo_filename = f"logo_{os.urandom(8).hex()}.png"
        logo_path = self.temp_dir / logo_filename
        
        # Write logo file
        with open(logo_path, 'wb') as f:
            f.write(logo_data)
        
        print(f"Logo decoded to: {logo_path}")
        return str(logo_path)
    
    def add_logo_to_video(
        self,
        video_path: str,
        logo_data_url: str,
        output_path: Optional[str] = None,
        position: str = "top_right",
        opacity: float = 0.9,
        padding: int = 20,
        logo_size: int = 80
    ) -> str:
        """
        Add logo watermark to video using FFmpeg overlay
        
        Args:
            video_path: Input video file path
            logo_data_url: Base64 data URL of logo image
            output_path: Output video file path (optional, auto-generated if None)
            position: Logo position - "top_right", "top_left", "bottom_right", "bottom_left", "center"
            opacity: Logo opacity (0.0 to 1.0)
            padding: Pixels from edge (>= 0)
            logo_size: Logo display size in pixels (1-1000)
            
        Returns:
            Output video file path
            
        Raises:
            ValueError: If parameters are invalid
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If FFmpeg processing fails
        """
        # Input validation
        valid_positions = ['top_right', 'top_left', 'bottom_right', 'bottom_left', 'center']
        if position not in valid_positions:
            raise ValueError(f"Invalid position '{position}'. Must be one of {valid_positions}")
        
        if not 0.0 <= opacity <= 1.0:
            raise ValueError(f"Opacity must be between 0.0 and 1.0, got {opacity}")
        
        if padding < 0:
            raise ValueError(f"Padding must be >= 0, got {padding}")
        
        if logo_size <= 0:
            raise ValueError(f"Logo size must be > 0, got {logo_size}")
        
        if logo_size > 1000:
            raise ValueError(f"Logo size too large (max 1000px), got {logo_size}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        # Generate output path if not provided
        if output_path is None:
            base_path = Path(video_path)
            output_path = str(base_path.parent / f"{base_path.stem}_with_logo{base_path.suffix}")
        
        # Decode logo to temp file
        logo_path = self.decode_logo(logo_data_url)
        
        try:
            print(f"Adding logo to video: {video_path}")
            
            # Get video dimensions
            probe = ffmpeg.probe(video_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            video_width = int(video_info['width'])
            video_height = int(video_info['height'])
            
            print(f"Video dimensions: {video_width}x{video_height}")
            
            # Calculate logo position based on video size and position parameter
            # Format: x:y where (0,0) is top-left
            positions = {
                "top_right": f"W-w-{padding}:{padding}",
                "top_left": f"{padding}:{padding}",
                "bottom_right": f"W-w-{padding}:H-h-{padding}",
                "bottom_left": f"{padding}:H-h-{padding}",
                "center": "(W-w)/2:(H-h)/2"
            }
            
            overlay_position = positions.get(position, positions["top_right"])
            
            # Build FFmpeg filter complex
            # 1. Scale logo to desired size
            # 2. Apply opacity
            # 3. Overlay on video
            filter_complex = (
                f"[1:v]scale={logo_size}:-1[scaled_logo];"
                f"[scaled_logo]format=rgba,colorchannelmixer=aa={opacity}[logo];"
                f"[0:v][logo]overlay={overlay_position}"
            )
            
            print(f"Filter: {filter_complex}")
            
            # Build and run FFmpeg command
            (
                ffmpeg
                .input(video_path)
                .input(logo_path)
                .filter_complex(filter_complex)
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='copy',  # Copy audio without re-encoding
                    preset='medium',
                    crf=23,  # Quality level (lower = better, 18-28 is good range)
                    movflags='faststart',  # Enable web streaming
                    pix_fmt='yuv420p'  # Compatibility
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            
            print(f"✅ Logo added successfully: {output_path}")
            return output_path
            
        except Exception as e:
            # Handle both ffmpeg.Error and other exceptions
            if hasattr(e, 'stderr'):
                error_msg = e.stderr.decode() if e.stderr else str(e)
            else:
                error_msg = str(e)
            print(f"❌ FFmpeg error: {error_msg}")
            raise RuntimeError(f"Failed to add logo: {error_msg}")
            
        finally:
            # Cleanup temp logo file
            if os.path.exists(logo_path):
                os.remove(logo_path)
                print(f"Cleaned up temp logo: {logo_path}")
    
    def remove_logo_from_video(self, video_path_with_logo: str) -> Optional[str]:
        """
        Find and return the original video path without logo
        
        Args:
            video_path_with_logo: Path to video with logo
            
        Returns:
            Original video path if it exists, None otherwise
        """
        # Check if this is a logo video
        if "_with_logo" in video_path_with_logo:
            original_path = video_path_with_logo.replace("_with_logo", "")
            if os.path.exists(original_path):
                return original_path
        
        return None
    
    @staticmethod
    def cleanup_temp_logos(temp_dir: str = "uploads/temp_logos"):
        """
        Remove old temporary logo files (older than 1 hour)
        
        Args:
            temp_dir: Directory containing temporary logo files
        """
        import time
        
        temp_dir_path = Path(temp_dir)
        if not temp_dir_path.exists():
            return
        
        current_time = time.time()
        removed_count = 0
        
        for logo_file in temp_dir_path.glob("logo_*.png"):
            try:
                # Remove files older than 1 hour
                file_age = current_time - logo_file.stat().st_mtime
                if file_age > 3600:  # 1 hour in seconds
                    logo_file.unlink()
                    removed_count += 1
                    print(f"Removed old temp logo: {logo_file}")
            except Exception as e:
                print(f"Failed to remove {logo_file}: {e}")
        
        if removed_count > 0:
            print(f"Cleaned up {removed_count} old temporary logo files")


# Test function
if __name__ == "__main__":
    watermarker = LogoWatermarker()
    print("Logo Watermarker initialized")
    print(f"Temp directory: {watermarker.temp_dir}")
