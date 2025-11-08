"""Gemini API integration for video analysis and highlight detection."""
from google import genai
from google.genai import types
from typing import List, Dict, Optional
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import settings

logger = logging.getLogger(__name__)


class GeminiAnalyzer:
    """Analyzes videos using Gemini API to find engaging highlights."""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash"
        self.sample_interval = 30  # Sample every 30 seconds
        self.sample_duration = 30  # Analyze 30-second segments
    
    def analyze_transcript_for_highlights(
        self, 
        transcript: str,
        video_title: Optional[str] = None,
        video_description: Optional[str] = None,
        duration: int = 0
    ) -> List[Dict]:
        """
        Analyze video transcript to find the most engaging highlights for marketing shorts.
        This is MUCH faster than analyzing the full video.
        
        Args:
            transcript: Video transcript/subtitle text
            video_title: Optional video title for context
            video_description: Optional video description
            duration: Video duration in seconds
            
        Returns:
            List of highlight segments with timestamps and descriptions
        """
        try:
            # Validate transcript
            transcript_length = len(transcript.strip()) if transcript else 0
            if not transcript or transcript_length < 50:
                logger.warning(f"Transcript too short or empty (length: {transcript_length} chars)")
                return []
            
            logger.info(f"Analyzing transcript (length: {transcript_length} chars, duration: {duration}s)")
            
            # Create a comprehensive prompt for transcript-based highlight detection
            prompt = self._create_transcript_highlight_prompt(
                transcript, video_title, video_description, duration
            )
            
            # Analyze transcript with Gemini (text-only, super fast)
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                )
            )
            
            # Parse the response to extract highlights
            response_text = response.text if response.text else ""
            if not response_text:
                logger.error("Empty response from Gemini API")
                return []
            
            logger.debug(f"Gemini response preview: {response_text[:300]}...")
            
            highlights = self._parse_highlights_response(response_text)
            
            logger.info(f"Found {len(highlights)} highlights from transcript analysis")
            return highlights
        
        except Exception as e:
            logger.error(f"Error analyzing transcript: {str(e)}")
            raise
    
    def analyze_video_for_highlights(
        self, 
        video_url: str, 
        video_title: Optional[str] = None,
        video_duration: Optional[int] = None
    ) -> List[Dict]:
        """
        DEPRECATED: Use analyze_transcript_for_highlights for 10x faster analysis.
        Analyze video to find the most engaging highlights for marketing shorts.
        Uses optimized sampling with Gemini API (5 workers in parallel).
        
        Args:
            video_url: YouTube URL or file URI
            video_title: Optional video title for context
            video_duration: Optional video duration in seconds for optimization
            
        Returns:
            List of highlight segments with timestamps and descriptions
        """
        start_time = time.time()
        try:
            # Use optimized sampling with Gemini API
            if video_duration:
                highlights = self._fast_sample_analysis(video_url, video_title, video_duration)
            else:
                # Fallback: use simple time-based sampling
                highlights = self._simple_time_based_highlights(video_title)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Found {len(highlights)} highlights in {elapsed_time:.2f} seconds")
            return highlights
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error analyzing video after {elapsed_time:.2f}s: {str(e)}")
            raise
    
    def _fast_sample_analysis(
        self,
        video_url: str,
        video_title: Optional[str],
        video_duration: int
    ) -> List[Dict]:
        """
        Fast analysis by sampling key segments and analyzing them with Gemini API.
        Uses 5 workers in parallel to analyze up to 5 segments simultaneously.
        Each segment is 30 seconds, analyzed independently for speed.
        """
        logger.info(f"Using optimized sampling strategy with Gemini API for {video_duration}s video")
        
        # Sample key segments: beginning, strategic points throughout video
        sample_segments = []
        
        # Always analyze the beginning (most important for hooks)
        if video_duration >= settings.short_duration_min:
            sample_segments.append((0, min(30, video_duration)))
        
        # Analyze strategic points throughout the video
        if video_duration > 60:
            # 20% point
            twenty_percent = int(video_duration * 0.2)
            sample_segments.append((max(0, twenty_percent - 15), min(twenty_percent + 15, video_duration)))
        
        if video_duration > 90:
            # 40% point
            forty_percent = int(video_duration * 0.4)
            sample_segments.append((max(0, forty_percent - 15), min(forty_percent + 15, video_duration)))
        
        if video_duration > 120:
            # 60% point (middle)
            sixty_percent = int(video_duration * 0.6)
            sample_segments.append((max(0, sixty_percent - 15), min(sixty_percent + 15, video_duration)))
        
        if video_duration > 180:
            # 80% point
            eighty_percent = int(video_duration * 0.8)
            sample_segments.append((max(0, eighty_percent - 15), min(eighty_percent + 15, video_duration)))
        
        # Limit to 5 segments for 5 workers
        sample_segments = sample_segments[:5]
        
        logger.info(f"Analyzing {len(sample_segments)} key segments with Gemini API (5 workers in parallel)...")
        analysis_start = time.time()
        
        # Analyze segments in parallel with 5 workers
        all_highlights = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for start_time, end_time in sample_segments:
                future = executor.submit(
                    self._analyze_segment_with_gemini,
                    video_url,
                    video_title,
                    start_time,
                    end_time
                )
                futures.append((future, start_time, end_time))
            
            for future, start_time, end_time in futures:
                try:
                    segment_highlights = future.result(timeout=15)  # 15s timeout per segment
                    all_highlights.extend(segment_highlights)
                    logger.debug(f"Segment {start_time}-{end_time}s analyzed successfully")
                except Exception as e:
                    logger.warning(f"Error analyzing segment {start_time}-{end_time}s: {str(e)}")
                    continue
        
        analysis_time = time.time() - analysis_start
        logger.info(f"Gemini API analysis completed in {analysis_time:.2f} seconds")
        
        # Sort by engagement score and return top highlights
        all_highlights.sort(key=lambda x: x.get("engagement_score", 0), reverse=True)
        return all_highlights[:settings.max_highlights]
    
    def _analyze_segment_with_gemini(
        self,
        video_url: str,
        video_title: Optional[str],
        start_time: int,
        end_time: int
    ) -> List[Dict]:
        """
        Analyze a specific 30-second segment using Gemini API.
        This method is called in parallel by worker threads.
        """
        segment_start = time.time()
        try:
            start_min = start_time // 60
            start_sec = start_time % 60
            end_min = end_time // 60
            end_sec = end_time % 60
            
            # Create focused prompt for this specific segment
            prompt = f"""
Analyze ONLY the video segment from {start_min:02d}:{start_sec:02d} to {end_min:02d}:{end_sec:02d}.

Identify the most engaging 15-30 second highlight within this segment for marketing shorts.

Focus on:
- High energy moments
- Clear value propositions
- Product demonstrations
- Customer testimonials
- Visual demonstrations

Return JSON:
{{
  "highlights": [
    {{
      "start_time": "MM:SS (relative to {start_min:02d}:{start_sec:02d})",
      "end_time": "MM:SS (relative to {start_min:02d}:{start_sec:02d})",
      "duration_seconds": 15-30,
      "engagement_score": 1-10,
      "marketing_effectiveness": "brief explanation",
      "key_elements": ["element1", "element2"],
      "suggested_cta": "call to action",
      "category": "podcast" or "product_demo",
      "tracking_focus": "what to track and center"
    }}
  ]
}}

If no suitable highlight found, return empty highlights array.
Return ONLY valid JSON, no additional text.
"""
            
            if video_title:
                prompt = f"Video Title: {video_title}\n\n{prompt}"
            
            # Call Gemini API for this segment
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
            
            # Parse highlights from this segment
            highlights = self._parse_highlights_response(response.text)
            
            # Adjust timestamps to absolute video time
            for highlight in highlights:
                highlight["start_seconds"] += start_time
                highlight["end_seconds"] += start_time
                start_total = highlight["start_seconds"]
                end_total = highlight["end_seconds"]
                highlight["start_time"] = f"{start_total // 60:02d}:{start_total % 60:02d}"
                highlight["end_time"] = f"{end_total // 60:02d}:{end_total % 60:02d}"
            
            segment_time = time.time() - segment_start
            logger.debug(f"Segment {start_time}-{end_time}s: {len(highlights)} highlights found in {segment_time:.2f}s")
            
            return highlights
        
        except Exception as e:
            segment_time = time.time() - segment_start
            logger.warning(f"Error analyzing segment {start_time}-{end_time}s after {segment_time:.2f}s: {str(e)}")
            return []
    
    def _simple_time_based_highlights(self, video_title: Optional[str]) -> List[Dict]:
        """Fallback: simple time-based highlights when duration is unknown."""
        return [
            {
                "start_time": "00:00",
                "end_time": "00:30",
                "start_seconds": 0,
                "end_seconds": 30,
                "duration_seconds": 30,
                "engagement_score": 8,
                "marketing_effectiveness": "Opening segment with strong hook",
                "key_elements": ["Opening content"],
                "suggested_cta": "Learn more!",
                "category": "podcast",
                "tracking_focus": "speaking person",
            }
        ]
    
    def _analyze_segment(
        self,
        video_url: str,
        video_title: Optional[str],
        start_time: int,
        end_time: int
    ) -> List[Dict]:
        """
        Analyze a specific video segment.
        Note: Gemini API doesn't support time ranges directly, so we use a prompt
        that instructs it to focus on the specified time range.
        """
        try:
            # Create prompt for segment analysis
            start_min = start_time // 60
            start_sec = start_time % 60
            end_min = end_time // 60
            end_sec = end_time % 60
            
            prompt = self._create_segment_prompt(
                video_title,
                f"{start_min:02d}:{start_sec:02d}",
                f"{end_min:02d}:{end_sec:02d}"
            )
            
            # Analyze this segment
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
            
            # Parse highlights from this segment
            highlights = self._parse_highlights_response(response.text)
            
            # Adjust timestamps to absolute video time
            for highlight in highlights:
                highlight["start_seconds"] += start_time
                highlight["end_seconds"] += start_time
                # Update time strings
                start_total = highlight["start_seconds"]
                end_total = highlight["end_seconds"]
                highlight["start_time"] = f"{start_total // 60:02d}:{start_total % 60:02d}"
                highlight["end_time"] = f"{end_total // 60:02d}:{end_total % 60:02d}"
            
            return highlights
        
        except Exception as e:
            logger.warning(f"Error analyzing segment {start_time}-{end_time}s: {str(e)}")
            return []
    
    def _full_video_analysis(
        self,
        video_url: str,
        video_title: Optional[str]
    ) -> List[Dict]:
        """Fallback: full video analysis (slower, used only if duration not available)."""
        logger.warning("Using full video analysis (slower method)")
        prompt = self._create_highlight_prompt(video_title)
        
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
        
        return self._parse_highlights_response(response.text)
    
    def _create_transcript_highlight_prompt(
        self, 
        transcript: str, 
        video_title: Optional[str] = None,
        video_description: Optional[str] = None,
        duration: int = 0
    ) -> str:
        """Create a prompt for transcript-based highlight detection."""
        context = ""
        if video_title:
            context += f"Video Title: {video_title}\n"
        if video_description:
            context += f"Description: {video_description}\n"
        if duration:
            context += f"Duration: {duration} seconds\n"
        
        base_prompt = f"""{context}

Transcript:
{transcript}

---

You are an expert video analyst specializing in creating engaging marketing shorts for social media platforms.

Based on the transcript above, identify the MOST ENGAGING and MARKETING-EFFECTIVE segments that would:
1. Capture attention immediately (hook viewers in first 3 seconds)
2. Showcase key product features, benefits, or value propositions
3. Create urgency or desire for the product/service
4. Be suitable for 15-30 second marketing shorts

Analyze the transcript and identify up to 3 best highlight segments. For each segment, provide:
- Start time (in MM:SS format, estimated from the transcript flow)
- End time (in MM:SS format)
- Duration (should be 15-30 seconds)
- Engagement score (1-10, where 10 is most engaging)
- Why this segment is effective for marketing
- Key elements that make it engaging
- Suggested call-to-action
- Category: "podcast" (person speaking/interview) or "product_demo" (screen recording/product)
- Tracking focus: What should be centered in the frame

Format your response as JSON with this structure:
{{
  "highlights": [
    {{
      "start_time": "MM:SS",
      "end_time": "MM:SS",
      "duration_seconds": 15-30,
      "engagement_score": 1-10,
      "marketing_effectiveness": "explanation",
      "key_elements": ["element1", "element2"],
      "suggested_cta": "call to action text",
      "category": "podcast" or "product_demo",
      "tracking_focus": "description of what to track"
    }}
  ]
}}

Return ONLY valid JSON, no additional text.
"""
        return base_prompt
    
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
    
    def _create_segment_prompt(
        self,
        video_title: Optional[str],
        segment_start: str,
        segment_end: str
    ) -> str:
        """Create a prompt for analyzing a specific video segment."""
        base_prompt = f"""
You are an expert video analyst specializing in creating engaging marketing shorts.

IMPORTANT: Focus ONLY on the video segment from {segment_start} to {segment_end}. Analyze this specific time range.

Your task is to identify the MOST ENGAGING and MARKETING-EFFECTIVE segments within this time range that would:
1. Capture attention immediately (hook viewers in first 3 seconds)
2. Showcase key product features, benefits, or value propositions
3. Include compelling visuals, demonstrations, or testimonials
4. Create urgency or desire for the product/service
5. Be suitable for 15-30 second marketing shorts

Analyze the segment from {segment_start} to {segment_end} and identify the best highlight(s) within this range. For each highlight, provide:
- Start timestamp (MM:SS format, relative to {segment_start})
- End timestamp (MM:SS format, relative to {segment_start})
- Duration (should be 15-30 seconds)
- Engagement score (1-10, where 10 is most engaging)
- Why this segment is effective for marketing (brief explanation)
- Key visual/audio elements that make it engaging
- Suggested call-to-action for this segment
- Video category: "podcast" (person speaking/interview) or "product_demo" (screen recording/product demonstration)
- Tracking focus: What should be centered in the frame (e.g., "speaking person", "mouse cursor", "product feature being demonstrated")

Format your response as JSON with this structure:
{{
  "highlights": [
    {{
      "start_time": "MM:SS",
      "end_time": "MM:SS",
      "duration_seconds": 15-30,
      "engagement_score": 1-10,
      "marketing_effectiveness": "explanation",
      "key_elements": ["element1", "element2"],
      "suggested_cta": "call to action text",
      "category": "podcast" or "product_demo",
      "tracking_focus": "description of what to track and center"
    }}
  ]
}}

Note: Timestamps should be relative to the segment start ({segment_start}). If no suitable highlights are found in this segment, return an empty highlights array.

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
            
            raw_highlights = data.get("highlights", [])
            logger.info(f"Parsed {len(raw_highlights)} highlights from Gemini response")
            
            highlights = []
            filtered_count = 0
            for highlight in raw_highlights:
                # Validate and convert timestamps
                start_seconds = self._timestamp_to_seconds(highlight.get("start_time", "00:00"))
                end_seconds = self._timestamp_to_seconds(highlight.get("end_time", "00:00"))
                duration = end_seconds - start_seconds
                
                # Validate duration
                if duration < settings.short_duration_min or duration > settings.short_duration_max:
                    logger.warning(f"Skipping highlight with invalid duration: {duration}s (start: {highlight.get('start_time')}, end: {highlight.get('end_time')})")
                    filtered_count += 1
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
            
            if filtered_count > 0:
                logger.warning(f"Filtered out {filtered_count} highlights due to invalid duration")
            
            logger.info(f"After duration filtering: {len(highlights)} highlights remain")
            
            # Sort by engagement score (highest first) and limit to max_highlights
            highlights.sort(key=lambda x: x["engagement_score"], reverse=True)
            highlights = highlights[:settings.max_highlights]
            
            return highlights
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Response text (first 1000 chars): {response_text[:1000]}")
            # Fallback: try to extract timestamps using regex
            fallback_result = self._fallback_parse(response_text)
            logger.info(f"Fallback parse found {len(fallback_result)} highlights")
            return fallback_result
    
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

