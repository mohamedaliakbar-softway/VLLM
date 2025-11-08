"""
Audio-visual synchronization for content-aware framing.
Analyzes audio transcript to guide camera focus decisions.
"""
import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AudioVisualSync:
    """Synchronize camera movements with audio content."""
    
    # Intent keywords
    DEMONSTRATIVE_WORDS = ['see', 'look', 'here', 'this', 'that', 'these', 'those', 'show', 'watch', 'notice']
    CODE_WORDS = ['code', 'function', 'class', 'variable', 'method', 'error', 'debug', 'compile', 'syntax']
    UI_WORDS = ['click', 'button', 'menu', 'icon', 'tab', 'window', 'dialog', 'screen', 'interface']
    PRODUCT_WORDS = ['product', 'feature', 'design', 'quality', 'build', 'material', 'finish']
    EXPLANATION_WORDS = ['because', 'so', 'therefore', 'means', 'why', 'reason', 'explain']
    
    def __init__(self):
        logger.info("AudioVisualSync initialized")
    
    def analyze_transcript_segments(self, transcript: List[Dict]) -> List[Dict]:
        """
        Analyze transcript and extract timing, keywords, and intent.
        
        Args:
            transcript: List of transcript entries with 'start', 'end', 'text'
            
        Returns:
            List of analyzed segments with intent and priority
        """
        segments = []
        
        for i, entry in enumerate(transcript):
            text = entry.get('text', '').lower().strip()
            start_time = entry.get('start', 0)
            end_time = entry.get('end', start_time + 3)
            
            if not text:
                continue
            
            # Extract keywords
            keywords = self._extract_keywords(text)
            
            # Detect intent
            intent = self._detect_intent(text, keywords)
            
            # Calculate priority boost
            priority_boost = self._calculate_priority_boost(intent, keywords, text)
            
            # Extract specific mentioned items
            mentioned_items = self._extract_mentioned_items(text)
            
            segment = {
                'start': start_time,
                'end': end_time,
                'text': text,
                'keywords': keywords,
                'intent': intent,
                'priority_boost': priority_boost,
                'mentioned_items': mentioned_items,
                'index': i
            }
            
            segments.append(segment)
            
            logger.debug(f"Segment {i}: t={start_time:.1f}-{end_time:.1f}s, "
                        f"intent={intent}, boost={priority_boost}, "
                        f"keywords={keywords[:3] if keywords else []}")
        
        logger.info(f"Analyzed {len(segments)} transcript segments")
        return segments
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Remove common stop words
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'can', 'of', 'to', 'in',
                     'on', 'at', 'by', 'for', 'with', 'from', 'as', 'but', 'or',
                     'and', 'not', 'it', 'its', 'if', 'then', 'than', 'so'}
        
        # Extract words
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Filter and return
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords[:10]  # Return top 10
    
    def _detect_intent(self, text: str, keywords: List[str]) -> str:
        """
        Detect the speaker's intent based on text analysis.
        
        Returns:
            Intent string: 'demonstrative', 'code', 'ui_interaction', 
                          'product_focus', 'explanation', or 'general'
        """
        text_lower = text.lower()
        
        # Count matches for each intent
        demonstrative_count = sum(1 for word in self.DEMONSTRATIVE_WORDS if word in text_lower)
        code_count = sum(1 for word in self.CODE_WORDS if word in text_lower)
        ui_count = sum(1 for word in self.UI_WORDS if word in text_lower)
        product_count = sum(1 for word in self.PRODUCT_WORDS if word in text_lower)
        explanation_count = sum(1 for word in self.EXPLANATION_WORDS if word in text_lower)
        
        # Determine primary intent
        max_count = max(demonstrative_count, code_count, ui_count, product_count, explanation_count)
        
        if max_count == 0:
            return 'general'
        
        if demonstrative_count == max_count:
            return 'demonstrative'
        elif code_count == max_count:
            return 'code'
        elif ui_count == max_count:
            return 'ui_interaction'
        elif product_count == max_count:
            return 'product_focus'
        elif explanation_count == max_count:
            return 'explanation'
        
        return 'general'
    
    def _calculate_priority_boost(self, intent: str, keywords: List[str], text: str) -> int:
        """Calculate priority boost value based on intent and content."""
        boost = 0
        
        # Intent-based boost
        intent_boosts = {
            'demonstrative': 20,
            'code': 15,
            'ui_interaction': 18,
            'product_focus': 20,
            'explanation': 10,
            'general': 5
        }
        boost += intent_boosts.get(intent, 5)
        
        # Urgency/emphasis detection
        if any(word in text for word in ['important', 'key', 'critical', 'essential', 'must']):
            boost += 10
        
        # Question detection (often introduces new topics)
        if '?' in text or any(word in text for word in ['what', 'how', 'why', 'when', 'where']):
            boost += 5
        
        # Transition detection
        if any(word in text for word in ['now', 'next', 'first', 'second', 'finally', 'then']):
            boost += 5
        
        return boost
    
    def _extract_mentioned_items(self, text: str) -> List[str]:
        """Extract specific items mentioned in text (for matching with visual detections)."""
        mentioned = []
        
        # Common technical terms
        tech_terms = ['button', 'menu', 'icon', 'window', 'tab', 'panel', 'bar',
                     'field', 'form', 'list', 'table', 'chart', 'graph', 'code',
                     'function', 'class', 'variable', 'error', 'warning']
        
        # Product terms
        product_terms = ['product', 'device', 'phone', 'laptop', 'camera', 'screen',
                        'display', 'keyboard', 'mouse', 'port', 'cable']
        
        text_lower = text.lower()
        
        # Extract mentioned technical terms
        for term in tech_terms:
            if term in text_lower:
                mentioned.append(term)
        
        # Extract mentioned product terms
        for term in product_terms:
            if term in text_lower:
                mentioned.append(term)
        
        # Extract quoted terms (often specific UI elements or features)
        quoted = re.findall(r'"([^"]+)"', text)
        mentioned.extend(quoted)
        
        return mentioned
    
    def match_audio_to_detections(self, audio_segment: Dict,
                                  detections: List) -> List:
        """
        Match audio segment with visual detections and boost priorities.
        
        Args:
            audio_segment: Analyzed audio segment
            detections: List of Detection objects
            
        Returns:
            Updated detections with audio-context boosts
        """
        if not detections:
            return []
        
        intent = audio_segment.get('intent', 'general')
        keywords = audio_segment.get('keywords', [])
        mentioned_items = audio_segment.get('mentioned_items', [])
        priority_boost = audio_segment.get('priority_boost', 0)
        
        # Intent to detection type mapping
        intent_detection_map = {
            'demonstrative': ['text', 'motion', 'object'],
            'code': ['text'],
            'ui_interaction': ['motion', 'text'],
            'product_focus': ['object', 'face'],
            'explanation': ['face', 'text'],
            'general': ['face']
        }
        
        preferred_types = intent_detection_map.get(intent, ['face'])
        
        for detection in detections:
            # Base boost for matching intent
            if detection.type in preferred_types:
                detection.priority += priority_boost
                logger.debug(f"  Audio boost: {detection.type} matches intent '{intent}' +{priority_boost}")
            
            # Keyword matching for text detections
            if detection.type == 'text' and 'text' in detection.metadata:
                detection_text = detection.metadata['text'].lower()
                matches = sum(1 for keyword in keywords if keyword in detection_text)
                if matches > 0:
                    keyword_boost = matches * 10
                    detection.priority += keyword_boost
                    logger.debug(f"  Keyword match: {matches} words in text detection +{keyword_boost}")
            
            # Mentioned items matching
            if mentioned_items:
                for item in mentioned_items:
                    if detection.type == 'text' and 'text' in detection.metadata:
                        if item in detection.metadata['text'].lower():
                            detection.priority += 15
                            logger.debug(f"  Mentioned item '{item}' found in text +15")
        
        # Sort by priority
        detections.sort(key=lambda d: d.priority, reverse=True)
        
        return detections
    
    def create_timeline_with_audio(self, audio_segments: List[Dict],
                                   detections_by_time: Dict[float, List]) -> List[Dict]:
        """
        Create a synchronized timeline of focus targets guided by audio.
        
        Args:
            audio_segments: Analyzed audio segments
            detections_by_time: Dict mapping timestamps to detection lists
            
        Returns:
            Timeline of focus recommendations
        """
        timeline = []
        
        for segment in audio_segments:
            start_time = segment['start']
            end_time = segment['end']
            
            # Find detections in this time window
            relevant_detections = []
            for time, detections in detections_by_time.items():
                if start_time <= time <= end_time:
                    relevant_detections.extend(detections)
            
            if not relevant_detections:
                continue
            
            # Apply audio context to detections
            boosted_detections = self.match_audio_to_detections(segment, relevant_detections)
            
            # Select best detection for this segment
            if boosted_detections:
                best_detection = boosted_detections[0]  # Highest priority
                
                timeline.append({
                    'start': start_time,
                    'end': end_time,
                    'detection': best_detection,
                    'audio_context': segment,
                    'reason': f"{segment['intent']} - {best_detection.type}"
                })
        
        logger.info(f"Created audio-visual timeline with {len(timeline)} entries")
        return timeline
