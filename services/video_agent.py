"""AI Agent for conversational video editing using Gemini."""
from google import genai
from google.genai import types
from typing import List, Dict, Optional, Any
import logging
import json
import re
from config import settings

logger = logging.getLogger(__name__)


class VideoEditingAgent:
    """AI agent that understands natural language commands and converts them to video editing operations."""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash"
        
        # Define supported operations
        self.operations = {
            "trim": "Adjust start/end time of a clip",
            "shorten": "Reduce clip duration",
            "extend": "Increase clip duration",
            "speed_adjust": "Change playback speed (speed up or slow down)",
            "split": "Split one clip into multiple clips",
            "delete": "Remove a clip",
            "reorder": "Change clip order in timeline",
            "add_captions": "Add text captions to video",
            "adjust_volume": "Change audio volume",
            "none": "No editing operation, just conversation"
        }
    
    def process_command(
        self, 
        user_message: str,
        clips: List[Dict],
        selected_clip_index: Optional[int] = 0
    ) -> Dict[str, Any]:
        """
        Process a natural language command and return structured editing operations.
        
        Args:
            user_message: User's natural language command
            clips: Current list of video clips
            selected_clip_index: Index of currently selected clip
            
        Returns:
            Dict containing:
            - operations: List of operations to execute
            - response: AI's natural language response
            - success: Boolean indicating if command was understood
        """
        try:
            # Build context about current clips
            clips_context = self._build_clips_context(clips, selected_clip_index)
            
            # Create prompt for Gemini
            prompt = self._create_command_parsing_prompt(
                user_message, clips_context, selected_clip_index
            )
            
            # Call Gemini to parse the command
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for more consistent parsing
                    top_p=0.9,
                    response_mime_type="application/json",  # Request JSON response
                )
            )
            
            response_text = response.text if response.text else "{}"
            logger.debug(f"Gemini response: {response_text}")
            
            # Parse JSON response
            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback: extract JSON from markdown code blocks if present
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(1))
                else:
                    logger.error(f"Failed to parse JSON response: {response_text}")
                    return {
                        "operations": [],
                        "response": "I couldn't understand that command. Could you rephrase it?",
                        "success": False
                    }
            
            return {
                "operations": parsed.get("operations", []),
                "response": parsed.get("response", "Operation understood!"),
                "success": True
            }
        
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}", exc_info=True)
            return {
                "operations": [],
                "response": f"I encountered an error: {str(e)}. Please try again.",
                "success": False
            }
    
    def _build_clips_context(self, clips: List[Dict], selected_index: int) -> str:
        """Build a text description of the current clips for context."""
        if not clips:
            return "No clips available yet."
        
        context_lines = ["Current video clips:"]
        for i, clip in enumerate(clips):
            is_selected = " (SELECTED)" if i == selected_index else ""
            duration = clip.get('duration', 0)
            title = clip.get('title', f'Clip {i+1}')
            start = clip.get('start_time', 0)
            end = clip.get('end_time', duration)
            
            context_lines.append(
                f"  Clip {i+1}{is_selected}: '{title}' - "
                f"Duration: {duration}s, Start: {start}s, End: {end}s"
            )
        
        return "\n".join(context_lines)
    
    def _create_command_parsing_prompt(
        self, 
        user_message: str, 
        clips_context: str,
        selected_index: int
    ) -> str:
        """Create a prompt for Gemini to parse the user's command."""
        return f"""You are an AI video editing assistant. Parse the user's command into structured editing operations.

Available operations:
{json.dumps(self.operations, indent=2)}

{clips_context}

Currently selected clip index: {selected_index}

User command: "{user_message}"

Parse the command and respond with JSON in this EXACT format:
{{
  "operations": [
    {{
      "type": "operation_name",
      "clip_index": 0,
      "parameters": {{}}
    }}
  ],
  "response": "Natural language response to user"
}}

Operation types and their parameters:

1. "trim": Adjust clip start/end times
   Parameters: {{ "new_start": seconds, "new_end": seconds }}

2. "shorten": Reduce duration by amount or to specific length
   Parameters: {{ "target_duration": seconds }} OR {{ "reduce_by": seconds }}

3. "extend": Increase duration
   Parameters: {{ "target_duration": seconds }} OR {{ "extend_by": seconds }}

4. "speed_adjust": Change playback speed
   Parameters: {{ "speed_factor": number }}  (e.g., 2.0 for 2x speed, 0.5 for half speed)

5. "split": Split clip at timestamp
   Parameters: {{ "split_at": seconds }}

6. "delete": Remove clip
   Parameters: {{}}

7. "reorder": Move clip to new position
   Parameters: {{ "new_index": number }}

8. "add_captions": Add text captions
   Parameters: {{ "style": "bold_modern" | "elegant_serif" }}

9. "adjust_volume": Change audio volume
   Parameters: {{ "volume_factor": number }}  (e.g., 1.5 for 150%, 0.5 for 50%)

10. "none": Just conversation, no editing
    Parameters: {{}}

Rules:
- If user says "this clip" or "current clip", use the selected_index
- If user says "all clips", create operations for all clips
- If user says "clip 2" or "second clip", use index 1 (zero-based)
- For duration commands like "shorten to 20 seconds", use {{ "target_duration": 20 }}
- For duration commands like "make it 5 seconds shorter", use {{ "reduce_by": 5 }}
- For speed commands like "2x faster" or "double the speed", use {{ "speed_factor": 2.0 }}
- Be conversational and helpful in your response
- If command is unclear, ask for clarification and use "none" operation

Examples:

User: "Make this clip 20 seconds long"
Response:
{{
  "operations": [{{ "type": "shorten", "clip_index": {selected_index}, "parameters": {{ "target_duration": 20 }} }}],
  "response": "I'll shorten the current clip to 20 seconds."
}}

User: "Speed up the video by 2x"
Response:
{{
  "operations": [{{ "type": "speed_adjust", "clip_index": {selected_index}, "parameters": {{ "speed_factor": 2.0 }} }}],
  "response": "I'll speed up the video to 2x the original speed."
}}

User: "Delete clip 2"
Response:
{{
  "operations": [{{ "type": "delete", "clip_index": 1, "parameters": {{}} }}],
  "response": "I'll delete the second clip for you."
}}

User: "Trim the first 5 seconds"
Response:
{{
  "operations": [{{ "type": "trim", "clip_index": {selected_index}, "parameters": {{ "new_start": 5 }} }}],
  "response": "I'll remove the first 5 seconds from this clip."
}}

Now parse the user's command above and respond with ONLY valid JSON, no other text."""
