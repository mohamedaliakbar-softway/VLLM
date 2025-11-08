"""Audio-to-Focus Analyzer using Gemini AI to determine screen focus points."""
import logging
from typing import List, Dict, Optional
import json
from services.gemini_analyzer import GeminiAnalyzer

logger = logging.getLogger(__name__)


class AudioFocusAnalyzer:
    """Analyze audio transcript to determine what UI elements are being discussed."""
    
    def __init__(self):
        self.gemini = GeminiAnalyzer()
    
    def analyze_audio_for_focus(
        self,
        transcript: str,
        timestamps: List[float],
        duration: float
    ) -> List[Dict]:
        """
        Ask Gemini: "What UI element is being discussed at each timestamp?"
        
        Args:
            transcript: Full video transcript
            timestamps: List of timestamps to analyze
            duration: Total video duration
            
        Returns:
            List of focus points with timestamps and screen regions
            Example: [
                {
                    "start_time": 0.0,
                    "end_time": 3.5,
                    "focus_element": "menu button",
                    "screen_region": "top-left",
                    "action": "click",
                    "importance": "high"
                },
                ...
            ]
        """
        if not transcript or len(transcript) < 50:
            logger.warning("Transcript too short for audio focus analysis")
            return []
        
        try:
            prompt = self._build_focus_analysis_prompt(transcript, duration)
            
            # Use Gemini to analyze the transcript
            response = self.gemini.client.models.generate_content(
                model=self.gemini.model,
                contents=prompt,
                config={
                    'temperature': 0.3,  # Lower temperature for more consistent analysis
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': 2048,
                }
            )
            
            # Parse the response
            focus_points = self._parse_focus_response(response.text, duration)
            
            logger.info(f"Audio focus analysis found {len(focus_points)} focus points")
            return focus_points
            
        except Exception as e:
            logger.error(f"Error analyzing audio for focus: {str(e)}")
            return []
    
    def _build_focus_analysis_prompt(self, transcript: str, duration: float) -> str:
        """Build prompt for Gemini to analyze UI focus from transcript."""
        return f"""You are analyzing a screen recording transcript to determine what UI elements or screen regions are being discussed at different times.

Video Duration: {duration} seconds
Transcript:
{transcript}

Analyze this transcript and identify:
1. What UI elements or screen regions are mentioned (e.g., "menu button", "settings icon", "text field", "sidebar")
2. When they are mentioned (approximate timestamps)
3. What action is being performed (e.g., "click", "type", "scroll", "hover")
4. The approximate screen region (e.g., "top-left", "top-right", "center", "bottom-left", "bottom-right")
5. Importance level ("high", "medium", "low")

Return ONLY a valid JSON array with this structure:
[
  {{
    "start_time": 0.0,
    "end_time": 5.0,
    "focus_element": "menu button",
    "screen_region": "top-left",
    "action": "click",
    "importance": "high"
  }},
  {{
    "start_time": 5.0,
    "end_time": 10.0,
    "focus_element": "settings panel",
    "screen_region": "center",
    "action": "navigate",
    "importance": "medium"
  }}
]

Important:
- Return ONLY the JSON array, no other text
- Times should be in seconds
- Screen regions: "top-left", "top-right", "top-center", "center", "bottom-left", "bottom-right", "bottom-center"
- Actions: "click", "type", "scroll", "hover", "navigate", "select", "drag"
- Importance: "high", "medium", "low"
- If no specific UI elements are mentioned, return an empty array []
"""
    
    def _parse_focus_response(self, response_text: str, duration: float) -> List[Dict]:
        """Parse Gemini's focus analysis response."""
        try:
            # Extract JSON from response
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1] if len(lines) > 2 else lines)
            
            # Remove 'json' prefix if present
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
            
            # Parse JSON
            focus_points = json.loads(response_text)
            
            if not isinstance(focus_points, list):
                logger.warning("Focus response is not a list, returning empty")
                return []
            
            # Validate and clean focus points
            validated_points = []
            for point in focus_points:
                if self._validate_focus_point(point, duration):
                    validated_points.append(point)
            
            return validated_points
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse focus response as JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return []
        except Exception as e:
            logger.error(f"Error parsing focus response: {e}")
            return []
    
    def _validate_focus_point(self, point: Dict, duration: float) -> bool:
        """Validate a focus point has required fields."""
        required_fields = ['start_time', 'end_time', 'focus_element', 'screen_region']
        
        # Check required fields
        for field in required_fields:
            if field not in point:
                logger.warning(f"Focus point missing required field: {field}")
                return False
        
        # Validate times
        if not (0 <= point['start_time'] <= duration):
            logger.warning(f"Invalid start_time: {point['start_time']}")
            return False
        
        if not (0 <= point['end_time'] <= duration):
            logger.warning(f"Invalid end_time: {point['end_time']}")
            return False
        
        if point['start_time'] >= point['end_time']:
            logger.warning(f"start_time >= end_time: {point['start_time']} >= {point['end_time']}")
            return False
        
        # Validate screen region
        valid_regions = [
            'top-left', 'top-right', 'top-center',
            'center', 'center-left', 'center-right',
            'bottom-left', 'bottom-right', 'bottom-center'
        ]
        if point['screen_region'] not in valid_regions:
            logger.warning(f"Invalid screen_region: {point['screen_region']}")
            return False
        
        return True
    
    def map_region_to_coordinates(
        self,
        region: str,
        video_width: int,
        video_height: int
    ) -> tuple:
        """
        Map screen region name to (x, y) coordinates.
        
        Args:
            region: Screen region name (e.g., "top-left", "center")
            video_width: Video width in pixels
            video_height: Video height in pixels
            
        Returns:
            (x, y) tuple representing the center of that region
        """
        region_map = {
            'top-left': (video_width * 0.25, video_height * 0.25),
            'top-center': (video_width * 0.5, video_height * 0.25),
            'top-right': (video_width * 0.75, video_height * 0.25),
            'center-left': (video_width * 0.25, video_height * 0.5),
            'center': (video_width * 0.5, video_height * 0.5),
            'center-right': (video_width * 0.75, video_height * 0.5),
            'bottom-left': (video_width * 0.25, video_height * 0.75),
            'bottom-center': (video_width * 0.5, video_height * 0.75),
            'bottom-right': (video_width * 0.75, video_height * 0.75),
        }
        
        coords = region_map.get(region, (video_width * 0.5, video_height * 0.5))
        return (int(coords[0]), int(coords[1]))
