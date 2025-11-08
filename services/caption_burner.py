"""
Caption Burner Service - Burn captions into video using FFmpeg
"""
import ffmpeg
import json
from pathlib import Path
from typing import Dict, List


# Caption Style Presets
CAPTION_STYLES = {
    "bold_modern": {
        "name": "Bold & Modern",
        "font": "Arial",  # Fallback to Arial (Windows default)
        "font_size": 48,
        "font_color": "white",
        "stroke_color": "black",
        "stroke_width": 4,
        "shadow_x": 5,
        "shadow_y": 5,
        "position": "bottom_center",
        "y_offset": 100
    },
    
    "elegant_serif": {
        "name": "Elegant Serif",
        "font": "Times New Roman",
        "font_size": 44,
        "font_color": "#F5F5DC",  # Beige
        "stroke_color": "#8B4513",  # Brown
        "stroke_width": 2,
        "shadow_x": 3,
        "shadow_y": 3,
        "position": "center",
        "y_offset": 0
    },
    
    "fun_playful": {
        "name": "Fun & Playful",
        "font": "Comic Sans MS",
        "font_size": 52,
        "font_color": "#FFD700",  # Gold
        "stroke_color": "#FF1493",  # Pink
        "stroke_width": 5,
        "shadow_x": 0,
        "shadow_y": 0,
        "position": "top_center",
        "y_offset": 50
    }
}


class CaptionBurner:
    def __init__(self):
        """Initialize CaptionBurner"""
        print("CaptionBurner initialized")
    
    def _get_y_position(self, style: Dict, video_height: int = 1080) -> str:
        """
        Calculate Y position based on style position
        
        Args:
            style: Caption style dictionary
            video_height: Video height in pixels
            
        Returns:
            FFmpeg y position expression
        """
        position = style.get("position", "bottom_center")
        y_offset = style.get("y_offset", 100)
        
        if position == "top_center":
            return f"{y_offset}"
        elif position == "center":
            return "(h-text_h)/2"
        else:  # bottom_center
            return f"h-text_h-{y_offset}"
    
    def _escape_text(self, text: str) -> str:
        """
        Escape special characters for FFmpeg drawtext filter
        
        Args:
            text: Input text
            
        Returns:
            Escaped text safe for FFmpeg
        """
        # Escape special FFmpeg characters
        text = text.replace("\\", "\\\\")
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace("%", "\\%")
        return text
    
    def burn_captions(
        self,
        video_path: str,
        captions: List[Dict],
        style_name: str,
        output_path: str
    ) -> str:
        """
        Burn captions into video with specified style
        
        Args:
            video_path: Path to input video
            captions: List of word dictionaries with start/end timestamps
            style_name: Name of the caption style to use
            output_path: Path for output video
            
        Returns:
            Path to output video with captions
        """
        if style_name not in CAPTION_STYLES:
            raise ValueError(f"Unknown style: {style_name}. Available: {list(CAPTION_STYLES.keys())}")
        
        style = CAPTION_STYLES[style_name]
        
        print(f"Burning captions with style: {style['name']}")
        print(f"Total words to render: {len(captions)}")
        
        # Build drawtext filters for each word
        filters = []
        
        for word_data in captions:
            word = self._escape_text(word_data["word"])
            start = word_data["start"]
            end = word_data["end"]
            
            # Build drawtext filter parameters
            drawtext_params = [
                f"text='{word}'",
                f"fontfile='{style['font']}'",
                f"fontsize={style['font_size']}",
                f"fontcolor={style['font_color']}",
                f"borderw={style['stroke_width']}",
                f"bordercolor={style['stroke_color']}",
                f"x=(w-text_w)/2",  # Center horizontally
                f"y={self._get_y_position(style)}",
                f"shadowx={style['shadow_x']}",
                f"shadowy={style['shadow_y']}",
                f"shadowcolor=black@0.5",
                f"enable='between(t,{start},{end})'"
            ]
            
            drawtext = "drawtext=" + ":".join(drawtext_params)
            filters.append(drawtext)
        
        # Combine all filters
        filter_complex = ",".join(filters)
        
        print(f"Rendering {len(filters)} caption words...")
        
        try:
            # Run FFmpeg with caption filters
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    vf=filter_complex,
                    vcodec='libx264',
                    acodec='aac',
                    preset='medium',
                    crf=23
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            print(f"Captions burned successfully to: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"FFmpeg error while burning captions: {error_msg}")
            raise RuntimeError(f"Caption burning failed: {error_msg}")
    
    def get_available_styles(self) -> Dict[str, str]:
        """
        Get list of available caption styles
        
        Returns:
            Dictionary of style names and descriptions
        """
        return {
            key: value["name"]
            for key, value in CAPTION_STYLES.items()
        }


# For testing
if __name__ == "__main__":
    burner = CaptionBurner()
    print("Available styles:")
    for key, name in burner.get_available_styles().items():
        print(f"  - {key}: {name}")
