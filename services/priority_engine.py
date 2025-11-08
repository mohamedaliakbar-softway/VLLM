"""
Priority-based decision engine for intelligent framing.
Decides what to focus on based on multiple factors and context.
"""
import numpy as np
from typing import List, Optional, Dict, Tuple
import logging
from dataclasses import dataclass
from collections import deque

from services.content_detector import Detection

logger = logging.getLogger(__name__)


@dataclass
class FocusTarget:
    """A target to focus the camera on."""
    detection: Detection
    final_priority: int
    reason: str  # Why this target was selected
    hold_until: float  # Hold focus until this timestamp


class PriorityDecisionEngine:
    """Intelligent decision making for camera focus."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Settings
        self.min_priority_to_focus = self.config.get('min_priority_to_focus', 70)
        self.priority_change_threshold = self.config.get('priority_change_threshold', 20)
        self.min_hold_duration = self.config.get('min_hold_duration', 2.0)  # seconds
        self.audio_boost_factor = self.config.get('audio_boost_factor', 20)
        self.keyword_match_boost = self.config.get('keyword_match_boost', 10)
        
        # State tracking
        self.current_focus: Optional[FocusTarget] = None
        self.focus_history: deque = deque(maxlen=20)  # Last 20 focuses
        self.detection_history: deque = deque(maxlen=100)  # Recent detections
        
        logger.info(f"PriorityDecisionEngine initialized:")
        logger.info(f"  - Min priority: {self.min_priority_to_focus}")
        logger.info(f"  - Change threshold: {self.priority_change_threshold}")
        logger.info(f"  - Hold duration: {self.min_hold_duration}s")
    
    def select_best_target(self, detections: List[Detection], 
                          audio_segment: Optional[Dict] = None,
                          current_time: float = 0.0) -> Optional[FocusTarget]:
        """
        Select the best target to focus on based on all factors.
        
        Args:
            detections: List of detected content
            audio_segment: Current audio context (text, keywords, intent)
            current_time: Current time in video
            
        Returns:
            FocusTarget with highest priority, or None
        """
        if not detections:
            logger.debug("No detections available")
            return self._get_default_target(current_time)
        
        # Calculate final priorities for all detections
        scored_targets = []
        
        for detection in detections:
            priority = self._calculate_comprehensive_priority(
                detection, audio_segment, current_time
            )
            
            scored_targets.append((priority, detection))
        
        # Sort by priority
        scored_targets.sort(key=lambda x: x[0], reverse=True)
        
        # Log top candidates
        if scored_targets:
            logger.debug(f"Top 3 targets at t={current_time:.1f}s:")
            for i, (priority, det) in enumerate(scored_targets[:3]):
                logger.debug(f"  {i+1}. {det.type} at {det.position}, priority={priority}")
        
        # Decision logic: Should we change focus?
        best_priority, best_detection = scored_targets[0]
        
        # Check if we should stay with current focus
        if self.current_focus:
            # Still within hold duration?
            if current_time < self.current_focus.hold_until:
                # Only switch if new target is significantly better
                current_priority = self.current_focus.final_priority
                if best_priority < current_priority + self.priority_change_threshold:
                    logger.debug(f"Holding current focus (current={current_priority}, "
                               f"new={best_priority}, need +{self.priority_change_threshold})")
                    return self.current_focus
        
        # Check minimum priority threshold
        if best_priority < self.min_priority_to_focus:
            logger.debug(f"Best priority {best_priority} below threshold "
                        f"{self.min_priority_to_focus}, using default")
            return self._get_default_target(current_time)
        
        # Create new focus target
        hold_until = current_time + self.min_hold_duration
        reason = self._explain_selection(best_detection, best_priority, audio_segment)
        
        new_target = FocusTarget(
            detection=best_detection,
            final_priority=best_priority,
            reason=reason,
            hold_until=hold_until
        )
        
        # Update state
        self.current_focus = new_target
        self.focus_history.append(new_target)
        
        logger.info(f"New focus at t={current_time:.1f}s: {best_detection.type} "
                   f"at {best_detection.position}, priority={best_priority}")
        logger.info(f"  Reason: {reason}")
        
        return new_target
    
    def _calculate_comprehensive_priority(self, detection: Detection, 
                                         audio_segment: Optional[Dict],
                                         current_time: float) -> int:
        """Calculate final priority score considering all factors."""
        priority = detection.base_priority
        boosts = []
        
        # 1. Audio context boost
        if audio_segment:
            audio_boost = self._calculate_audio_boost(detection, audio_segment)
            if audio_boost > 0:
                priority += audio_boost
                boosts.append(f"audio+{audio_boost}")
        
        # 2. Newness factor
        if self._is_new_detection(detection):
            newness_boost = 15
            priority += newness_boost
            boosts.append(f"new+{newness_boost}")
        
        # 3. Recency penalty (avoid ping-pong)
        if self._recently_focused_type(detection.type, current_time):
            recency_penalty = -10
            priority += recency_penalty
            boosts.append(f"recent{recency_penalty}")
        
        # 4. Position factor (centered content often more important)
        centrality_boost = self._calculate_centrality_boost(detection)
        if centrality_boost != 0:
            priority += centrality_boost
            boosts.append(f"center{centrality_boost:+d}")
        
        # 5. Size factor (larger = more prominent)
        size_boost = self._calculate_size_boost(detection)
        if size_boost > 0:
            priority += size_boost
            boosts.append(f"size+{size_boost}")
        
        # 6. Confidence factor
        confidence_boost = int(detection.confidence * 5)
        if confidence_boost > 0:
            priority += confidence_boost
            boosts.append(f"conf+{confidence_boost}")
        
        # 7. Current focus bonus (slight preference to stay)
        if self.current_focus and detection.type == self.current_focus.detection.type:
            stay_bonus = 8
            priority += stay_bonus
            boosts.append(f"stay+{stay_bonus}")
        
        # Update detection priority
        detection.priority = priority
        
        if boosts:
            logger.debug(f"  {detection.type} priority: {detection.base_priority} -> "
                        f"{priority} ({', '.join(boosts)})")
        
        return priority
    
    def _calculate_audio_boost(self, detection: Detection, 
                               audio_segment: Dict) -> int:
        """Calculate priority boost based on audio context."""
        boost = 0
        
        audio_text = audio_segment.get('text', '').lower()
        keywords = audio_segment.get('keywords', [])
        intent = audio_segment.get('intent', 'general')
        
        # Intent matching
        intent_match = {
            'face': ['explanation', 'general'],
            'text': ['code', 'demonstrative'],
            'motion': ['ui_interaction', 'demonstrative'],
            'object': ['product_focus', 'demonstrative']
        }
        
        if detection.type in intent_match and intent in intent_match[detection.type]:
            boost += self.audio_boost_factor
            logger.debug(f"  Audio intent match: {intent} -> {detection.type}")
        
        # Keyword matching for text detections
        if detection.type == 'text' and 'text' in detection.metadata:
            detection_text = detection.metadata['text'].lower()
            matches = sum(1 for keyword in keywords if keyword in detection_text)
            keyword_boost = matches * self.keyword_match_boost
            boost += keyword_boost
            if matches > 0:
                logger.debug(f"  Keyword matches: {matches} words -> +{keyword_boost}")
        
        # Demonstrative words boost for visible elements
        demonstrative_words = ['see', 'look', 'here', 'this', 'that', 'these', 'show']
        if any(word in audio_text for word in demonstrative_words):
            if detection.type in ['text', 'motion', 'object']:
                boost += 10
                logger.debug(f"  Demonstrative language detected -> +10")
        
        return boost
    
    def _is_new_detection(self, detection: Detection) -> bool:
        """Check if this is a new/fresh detection."""
        # Check if similar detection exists in recent history
        for hist_det in list(self.detection_history)[-10:]:  # Last 10 detections
            if hist_det.type == detection.type:
                # Check if positions are close
                dist = np.sqrt(
                    (hist_det.position[0] - detection.position[0])**2 +
                    (hist_det.position[1] - detection.position[1])**2
                )
                if dist < 100:  # Within 100 pixels
                    return False
        
        # Add to history
        self.detection_history.append(detection)
        return True
    
    def _recently_focused_type(self, detection_type: str, current_time: float) -> bool:
        """Check if this type was recently focused."""
        for focus in list(self.focus_history)[-5:]:  # Last 5 focuses
            if focus.detection.type == detection_type:
                time_since = current_time - focus.detection.timestamp
                if time_since < 3.0:  # Within last 3 seconds
                    return True
        return False
    
    def _calculate_centrality_boost(self, detection: Detection) -> int:
        """Boost for centered content (rule of thirds)."""
        # Assume 1920x1080 frame (will be adjusted in actual implementation)
        frame_center_x = 960
        frame_center_y = 540
        
        x, y = detection.position
        
        # Distance from center
        dist_from_center = np.sqrt(
            (x - frame_center_x)**2 + (y - frame_center_y)**2
        )
        
        # Normalize (0 = center, 1 = corner)
        max_dist = np.sqrt(frame_center_x**2 + frame_center_y**2)
        normalized_dist = dist_from_center / max_dist
        
        # Small boost for centered content (0-5 points)
        if normalized_dist < 0.2:  # Very centered
            return 5
        elif normalized_dist < 0.4:  # Somewhat centered
            return 3
        else:
            return 0
    
    def _calculate_size_boost(self, detection: Detection) -> int:
        """Boost for larger content."""
        if 'area' in detection.metadata:
            area = detection.metadata['area']
            # Larger elements get more attention (0-10 points)
            # Assuming frame is ~2MP (1920x1080)
            normalized_area = area / (1920 * 1080)
            return min(int(normalized_area * 100), 10)
        return 0
    
    def _explain_selection(self, detection: Detection, priority: int,
                          audio_segment: Optional[Dict]) -> str:
        """Generate human-readable explanation for selection."""
        reasons = [f"{detection.type} detected"]
        
        if audio_segment:
            intent = audio_segment.get('intent', '')
            if intent:
                reasons.append(f"matches '{intent}' audio intent")
        
        if detection.metadata.get('is_speaking'):
            reasons.append("person is speaking")
        
        if detection.type == 'text' and detection.metadata.get('is_large'):
            reasons.append("large/prominent text")
        
        if detection.confidence > 0.8:
            reasons.append("high confidence")
        
        return ", ".join(reasons)
    
    def _get_default_target(self, current_time: float) -> FocusTarget:
        """Return default center-frame target when nothing detected."""
        default_detection = Detection(
            type='default',
            position=(960, 540),  # Center of 1920x1080
            bbox=(640, 360, 640, 360),  # Center region
            confidence=0.5,
            base_priority=50,
            priority=50,
            metadata={'default': True},
            timestamp=current_time
        )
        
        return FocusTarget(
            detection=default_detection,
            final_priority=50,
            reason="no strong detections, using center frame",
            hold_until=current_time + self.min_hold_duration
        )
    
    def reset_state(self):
        """Reset engine state for new video."""
        self.current_focus = None
        self.focus_history.clear()
        self.detection_history.clear()
        logger.info("Priority engine state reset")
