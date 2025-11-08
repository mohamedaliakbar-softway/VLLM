"""AI Agent for video editing commands using Gemini API."""
from google import genai
from google.genai import types
from typing import Dict, List, Optional, Any
import logging
import re
import json
from config import settings

logger = logging.getLogger(__name__)


class VideoEditingAgent:
    """AI agent that understands and executes video editing commands."""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.0-flash-exp"
        
    def parse_and_execute(
        self, 
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse user message and determine editing action.
        
        Args:
            message: User's natural language command
            context: Current editing context (clips, selected clip, etc.)
            
        Returns:
            Dict with action, parameters, and response message
        """
        try:
            # Create a comprehensive prompt for the AI
            prompt = self._create_agent_prompt(message, context)
            
            # Call Gemini to understand the intent
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for more consistent commands
                    response_mime_type="application/json",
                )
            )
            
            # Parse the JSON response
            result = json.loads(response.text) if response.text else {}
            
            logger.info(f"AI Agent parsed command: {result}")
            
            return {
                "action": result.get("action"),
                "parameters": result.get("parameters", {}),
                "message": result.get("message", "Done!"),
                "updatedClips": result.get("updatedClips")
            }
            
        except Exception as e:
            logger.error(f"Error in AI agent: {str(e)}")
            return {
                "action": None,
                "parameters": {},
                "message": f"I couldn't understand that command. Could you rephrase it? Error: {str(e)}"
            }
    
    def _create_agent_prompt(self, message: str, context: Dict[str, Any]) -> str:
        """Create a detailed prompt for the AI agent."""
        
        clips = context.get("clips", [])
        selected_index = context.get("selectedClipIndex", 0)
        selected_clip = context.get("selectedClip", {})
        
        prompt = f"""You are an intelligent video editing assistant. Analyze the user's command and respond with a JSON object that contains the editing action to perform.

USER COMMAND: "{message}"

CURRENT CONTEXT:
- Total clips: {len(clips)}
- Selected clip index: {selected_index}
- Selected clip: {json.dumps(selected_clip, indent=2) if selected_clip else "None"}
- All clips: {json.dumps(clips, indent=2)}

AVAILABLE ACTIONS:
1. "trim_clip" - Trim a clip to specific start/end times
   Parameters: {{clipIndex, startTime (seconds), endTime (seconds)}}

2. "update_duration" - Change clip duration
   Parameters: {{clipIndex, duration (seconds)}}

3. "update_title" - Change clip title
   Parameters: {{clipIndex, title (string)}}

4. "select_clip" - Select a different clip
   Parameters: {{clipIndex}}

5. "delete_clip" - Delete a clip
   Parameters: {{clipIndex}}

6. "duplicate_clip" - Duplicate a clip
   Parameters: {{clipIndex}}

RESPONSE FORMAT (JSON only):
{{
  "action": "action_name",
  "parameters": {{
    "clipIndex": 0,
    ...other parameters...
  }},
  "message": "Friendly confirmation message to user"
}}

EXAMPLES:

User: "Trim this clip to 20 seconds"
Response:
{{
  "action": "update_duration",
  "parameters": {{
    "clipIndex": {selected_index},
    "duration": 20
  }},
  "message": "✂️ I've trimmed the clip to 20 seconds!"
}}

User: "Change the title to Marketing Tips"
Response:
{{
  "action": "update_title",
  "parameters": {{
    "clipIndex": {selected_index},
    "title": "Marketing Tips"
  }},
  "message": "📝 I've updated the title to 'Marketing Tips'!"
}}

User: "Delete this clip"
Response:
{{
  "action": "delete_clip",
  "parameters": {{
    "clipIndex": {selected_index}
  }},
  "message": "🗑️ Clip deleted successfully!"
}}

User: "Make it 30 seconds long"
Response:
{{
  "action": "update_duration",
  "parameters": {{
    "clipIndex": {selected_index},
    "duration": 30
  }},
  "message": "⏱️ I've set the duration to 30 seconds!"
}}

User: "Select clip 2" or "Switch to the second clip"
Response:
{{
  "action": "select_clip",
  "parameters": {{
    "clipIndex": 1
  }},
  "message": "✓ Switched to clip 2!"
}}

IMPORTANT:
- Always use the current selected clip index ({selected_index}) unless user specifies a different clip
- For duration/time values, extract numbers and convert to seconds
- Be conversational and friendly in messages
- If command is unclear, set action to null and ask for clarification in message
- Clip indices are 0-based (first clip is index 0)

Now analyze the user's command and respond with the appropriate JSON:"""

        return prompt
