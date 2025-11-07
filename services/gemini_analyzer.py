"""Gemini API integration for video analysis and highlight detection."""
from google import genai
from google.genai import types
from typing import List, Dict, Optional
import logging
from config import settings

logger = logging.getLogger(__name__)


class GeminiAnalyzer:
    """Analyzes videos using Gemini API to find engaging highlights."""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash"
    
    def analyze_video_for_highlights(
        self, 
        video_url: str, 
        video_title: Optional[str] = None
    ) -> List[Dict]:
        """
        Analyze video to find the most engaging highlights for marketing shorts.
        
        Args:
            video_url: YouTube URL or file URI
            video_title: Optional video title for context
            
        Returns:
            List of highlight segments with timestamps and descriptions
        """
        try:
            # Create a comprehensive prompt for marketing-focused highlight detection
            prompt = self._create_highlight_prompt(video_title)
            
            # Use YouTube URL directly with Gemini (as per documentation)
            # YouTube URLs can be passed directly as file_uri
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part(
                        file_data=types.FileData(
                            file_uri=video_url,
                            mime_type="video/*"
                        )
                    ),
                    types.Part(text=prompt)
                ],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                )
            )
            
            # Parse the response to extract highlights
            highlights = self._parse_highlights_response(response.text)
            
            logger.info(f"Found {len(highlights)} highlights from video analysis")
            return highlights
        
        except Exception as e:
            logger.error(f"Error analyzing video: {str(e)}")
            raise
    
    def _create_highlight_prompt(self, video_title: Optional[str] = None) -> str:
        """Create a prompt optimized for marketing highlight detection."""
        base_prompt = """
You are an expert video analyst specializing in creating engaging marketing shorts for social media platforms (YouTube Shorts, Instagram Reels, Facebook, LinkedIn, WhatsApp).

Your task is to analyze this video and identify the MOST ENGAGING and MARKETING-EFFECTIVE segments that would:
1. Capture attention immediately (hook viewers in first 3 seconds)
2. Showcase key product features, benefits, or value propositions
3. Include compelling visuals, demonstrations, or testimonials
4. Create urgency or desire for the product/service
5. End with a strong call-to-action opportunity
6. Be suitable for 15-30 second marketing shorts

Analyze the video and identify up to 3 best highlight segments. For each segment, provide:
- Start timestamp (MM:SS format)
- End timestamp (MM:SS format)
- Duration (should be 15-30 seconds)
- Engagement score (1-10, where 10 is most engaging)
- Why this segment is effective for marketing (brief explanation)
- Key visual/audio elements that make it engaging
- Suggested call-to-action for this segment
- Video category: "podcast" (person speaking/interview) or "product_demo" (screen recording/product demonstration)
- Tracking focus: What should be centered in the frame (e.g., "speaking person", "mouse cursor", "product feature being demonstrated")

Format your response as JSON with this structure:
{
  "highlights": [
    {
      "start_time": "MM:SS",
      "end_time": "MM:SS",
      "duration_seconds": 15-30,
      "engagement_score": 1-10,
      "marketing_effectiveness": "explanation",
      "key_elements": ["element1", "element2"],
      "suggested_cta": "call to action text",
      "category": "podcast" or "product_demo",
      "tracking_focus": "description of what to track and center"
    }
  ]
}

Prioritize segments that:
- Show product demos or features
- Include customer testimonials or success stories
- Demonstrate clear value propositions
- Have high energy or emotional appeal
- Include visual demonstrations
- Have clear audio (no background noise)
- Show before/after comparisons
- Include statistics or impressive results

Return ONLY valid JSON, no additional text.
"""
        
        if video_title:
            base_prompt = f"Video Title: {video_title}\n\n{base_prompt}"
        
        return base_prompt
    
    def _parse_highlights_response(self, response_text: str) -> List[Dict]:
        """Parse Gemini response to extract highlight segments."""
        import json
        import re
        
        try:
            # Try to extract JSON from response
            # Remove markdown code blocks if present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r'^```(?:json)?\s*', '', cleaned_text)
                cleaned_text = re.sub(r'\s*```$', '', cleaned_text)
            
            # Parse JSON
            data = json.loads(cleaned_text)
            
            highlights = []
            for highlight in data.get("highlights", []):
                # Validate and convert timestamps
                start_seconds = self._timestamp_to_seconds(highlight.get("start_time", "00:00"))
                end_seconds = self._timestamp_to_seconds(highlight.get("end_time", "00:00"))
                duration = end_seconds - start_seconds
                
                # Validate duration
                if duration < settings.short_duration_min or duration > settings.short_duration_max:
                    logger.warning(f"Skipping highlight with invalid duration: {duration}s")
                    continue
                
                highlights.append({
                    "start_time": highlight.get("start_time"),
                    "end_time": highlight.get("end_time"),
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "duration_seconds": duration,
                    "engagement_score": highlight.get("engagement_score", 0),
                    "marketing_effectiveness": highlight.get("marketing_effectiveness", ""),
                    "key_elements": highlight.get("key_elements", []),
                    "suggested_cta": highlight.get("suggested_cta", ""),
                    "category": highlight.get("category", "product_demo"),
                    "tracking_focus": highlight.get("tracking_focus", ""),
                })
            
            # Sort by engagement score (highest first) and limit to max_highlights
            highlights.sort(key=lambda x: x["engagement_score"], reverse=True)
            highlights = highlights[:settings.max_highlights]
            
            return highlights
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}")
            # Fallback: try to extract timestamps using regex
            return self._fallback_parse(response_text)
    
    def _timestamp_to_seconds(self, timestamp: str) -> int:
        """Convert MM:SS timestamp to seconds."""
        try:
            parts = timestamp.split(":")
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            else:
                return int(timestamp)
        except:
            return 0
    
    def _fallback_parse(self, response_text: str) -> List[Dict]:
        """Fallback parsing method if JSON parsing fails."""
        import re
        highlights = []
        
        # Try to extract timestamps from text
        timestamp_pattern = r'(\d{1,2}):(\d{2})'
        matches = re.findall(timestamp_pattern, response_text)
        
        if len(matches) >= 2:
            # Use first two timestamps as a highlight
            start_min, start_sec = map(int, matches[0])
            end_min, end_sec = map(int, matches[1])
            
            start_seconds = start_min * 60 + start_sec
            end_seconds = end_min * 60 + end_sec
            duration = end_seconds - start_seconds
            
            if settings.short_duration_min <= duration <= settings.short_duration_max:
                highlights.append({
                    "start_time": f"{start_min:02d}:{start_sec:02d}",
                    "end_time": f"{end_min:02d}:{end_sec:02d}",
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "duration_seconds": duration,
                    "engagement_score": 7,
                    "marketing_effectiveness": "Extracted from video analysis",
                    "key_elements": [],
                    "suggested_cta": "Book a demo today!",
                })
        
        return highlights

