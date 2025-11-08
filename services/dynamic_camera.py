"""
Dynamic camera system with smooth pan, zoom, and focus transitions.
Creates cinematic camera movements that follow content intelligently.
"""
import numpy as np
from typing import List, Tuple, Dict, Optional
import logging
from dataclasses import dataclass
from scipy.interpolate import interp1d
import cv2

from services.priority_engine import FocusTarget

logger = logging.getLogger(__name__)


@dataclass
class CameraKeyframe:
    """A keyframe in the camera movement timeline."""
    time: float  # Timestamp in video
    position: Tuple[float, float]  # (x, y) center position
    zoom_level: float  # 1.0 = normal, >1.0 = zoom in, <1.0 = zoom out
    movement_type: str  # 'hold', 'pan', 'zoom', 'pan_zoom'
    target_info: str  # Description of what we're focusing on


class DynamicCameraSystem:
    """
    Cinematic camera system with smooth movements.
    Generates keyframes and interpolates smooth transitions.
    """
    
    def __init__(self, frame_size: Tuple[int, int], crop_size: Tuple[int, int],
                 config: Optional[Dict] = None):
        self.frame_width, self.frame_height = frame_size
        self.crop_width, self.crop_height = crop_size
        self.config = config or {}
        
        # Movement constraints
        self.max_pan_speed = self.config.get('max_pan_speed', 200)  # px/sec
        self.max_zoom_speed = self.config.get('max_zoom_speed', 0.1)  # per sec
        self.min_hold_duration = self.config.get('min_hold_duration', 2.0)  # sec
        self.max_zoom = self.config.get('max_zoom', 1.5)
        self.min_zoom = self.config.get('min_zoom', 0.8)
        self.smooth_transitions = self.config.get('smooth_transitions', True)
        
        # Easing parameters
        self.ease_in_duration = 0.3  # seconds
        self.ease_out_duration = 0.3  # seconds
        
        logger.info(f"DynamicCameraSystem initialized:")
        logger.info(f"  - Frame size: {frame_size}")
        logger.info(f"  - Crop size: {crop_size}")
        logger.info(f"  - Max pan speed: {self.max_pan_speed} px/s")
        logger.info(f"  - Zoom range: {self.min_zoom} - {self.max_zoom}")
    
    def generate_camera_timeline(self, focus_targets: List[FocusTarget],
                                 video_duration: float) -> List[CameraKeyframe]:
        """
        Generate smooth camera movement timeline from focus targets.
        
        Args:
            focus_targets: List of targets to focus on over time
            video_duration: Total video duration in seconds
            
        Returns:
            List of camera keyframes for smooth interpolation
        """
        if not focus_targets:
            # Default: static center frame
            return [self._create_static_keyframe(0.0, video_duration)]
        
        keyframes = []
        current_time = 0.0
        current_position = self._get_frame_center()
        current_zoom = 1.0
        
        for i, target in enumerate(focus_targets):
            target_time = target.detection.timestamp
            target_position = target.detection.position
            target_zoom = self._calculate_optimal_zoom(target)
            
            # Skip if target is in the past
            if target_time < current_time:
                continue
            
            # Calculate movement duration
            distance = self._calculate_distance(current_position, target_position)
            zoom_change = abs(target_zoom - current_zoom)
            
            movement_duration = self._estimate_movement_duration(distance, zoom_change)
            transition_start = target_time
            
            # Ensure we have time for the movement
            if transition_start < current_time + movement_duration:
                transition_start = current_time
            
            # Generate transition keyframes
            if distance > 50 or zoom_change > 0.1:  # Significant movement needed
                transition_frames = self._create_smooth_transition(
                    current_position, target_position,
                    current_zoom, target_zoom,
                    current_time, transition_start + movement_duration
                )
                keyframes.extend(transition_frames)
            else:
                # Small adjustment, just add hold keyframe
                keyframes.append(CameraKeyframe(
                    time=transition_start,
                    position=target_position,
                    zoom_level=target_zoom,
                    movement_type='hold',
                    target_info=f"{target.detection.type} - {target.reason}"
                ))
            
            # Hold on target
            hold_end = target.hold_until if i < len(focus_targets) - 1 else video_duration
            keyframes.append(CameraKeyframe(
                time=hold_end,
                position=target_position,
                zoom_level=target_zoom,
                movement_type='hold',
                target_info=f"{target.detection.type} (holding)"
            ))
            
            # Update current state
            current_time = hold_end
            current_position = target_position
            current_zoom = target_zoom
        
        # Ensure we have keyframes at start and end
        if not keyframes or keyframes[0].time > 0:
            keyframes.insert(0, CameraKeyframe(
                time=0.0,
                position=self._get_frame_center(),
                zoom_level=1.0,
                movement_type='hold',
                target_info='initial position'
            ))
        
        if keyframes[-1].time < video_duration:
            keyframes.append(CameraKeyframe(
                time=video_duration,
                position=keyframes[-1].position,
                zoom_level=keyframes[-1].zoom_level,
                movement_type='hold',
                target_info='end hold'
            ))
        
        logger.info(f"Generated {len(keyframes)} camera keyframes")
        for kf in keyframes[:5]:  # Log first 5
            logger.debug(f"  t={kf.time:.1f}s: {kf.movement_type} -> {kf.position}, "
                        f"zoom={kf.zoom_level:.2f}, {kf.target_info}")
        
        return keyframes
    
    def interpolate_position_at_time(self, keyframes: List[CameraKeyframe],
                                     time: float) -> Tuple[Tuple[int, int], float]:
        """
        Get camera position and zoom at specific time through interpolation.
        
        Args:
            keyframes: List of camera keyframes
            time: Time to query
            
        Returns:
            ((x, y), zoom) - position and zoom level at this time
        """
        if not keyframes:
            return (self._get_frame_center(), 1.0)
        
        # Find surrounding keyframes
        if time <= keyframes[0].time:
            kf = keyframes[0]
            return (kf.position, kf.zoom_level)
        
        if time >= keyframes[-1].time:
            kf = keyframes[-1]
            return (kf.position, kf.zoom_level)
        
        # Find keyframes before and after
        prev_kf = keyframes[0]
        next_kf = keyframes[-1]
        
        for i in range(len(keyframes) - 1):
            if keyframes[i].time <= time <= keyframes[i + 1].time:
                prev_kf = keyframes[i]
                next_kf = keyframes[i + 1]
                break
        
        # Interpolate
        if prev_kf.time == next_kf.time:
            return (prev_kf.position, prev_kf.zoom_level)
        
        # Calculate interpolation factor with easing
        duration = next_kf.time - prev_kf.time
        t = (time - prev_kf.time) / duration  # Linear 0-1
        
        # Apply easing if movement type requires it
        if next_kf.movement_type in ['pan', 'zoom', 'pan_zoom']:
            t = self._ease_in_out_cubic(t)
        
        # Interpolate position
        x = prev_kf.position[0] + (next_kf.position[0] - prev_kf.position[0]) * t
        y = prev_kf.position[1] + (next_kf.position[1] - prev_kf.position[1]) * t
        
        # Interpolate zoom
        zoom = prev_kf.zoom_level + (next_kf.zoom_level - prev_kf.zoom_level) * t
        
        return ((int(x), int(y)), zoom)
    
    def apply_dynamic_crop(self, frame: np.ndarray, keyframes: List[CameraKeyframe],
                          time: float) -> np.ndarray:
        """
        Apply dynamic crop to a single frame based on camera timeline.
        
        Args:
            frame: Input frame (numpy array)
            keyframes: Camera movement timeline
            time: Current time in video
            
        Returns:
            Cropped and resized frame
        """
        # Get camera position and zoom at this time
        position, zoom = self.interpolate_position_at_time(keyframes, time)
        
        # Calculate crop dimensions based on zoom
        actual_crop_width = int(self.crop_width / zoom)
        actual_crop_height = int(self.crop_height / zoom)
        
        # Calculate crop position (centered on target)
        x = int(position[0] - actual_crop_width // 2)
        y = int(position[1] - actual_crop_height // 2)
        
        # Ensure crop is within frame bounds
        x = max(0, min(x, self.frame_width - actual_crop_width))
        y = max(0, min(y, self.frame_height - actual_crop_height))
        
        # Crop frame
        cropped = frame[y:y+actual_crop_height, x:x+actual_crop_width]
        
        # Resize to target size
        if cropped.shape[0] > 0 and cropped.shape[1] > 0:
            resized = cv2.resize(cropped, (self.crop_width, self.crop_height),
                                interpolation=cv2.INTER_LANCZOS4)
            return resized
        else:
            # Fallback: return center crop
            logger.warning(f"Invalid crop dimensions, using center fallback")
            return self._center_crop(frame)
    
    def _create_smooth_transition(self, start_pos: Tuple[float, float],
                                  end_pos: Tuple[float, float],
                                  start_zoom: float, end_zoom: float,
                                  start_time: float, end_time: float) -> List[CameraKeyframe]:
        """Create smooth transition with multiple keyframes for easing."""
        keyframes = []
        
        # Determine movement type
        distance = self._calculate_distance(start_pos, end_pos)
        zoom_change = abs(end_zoom - start_zoom)
        
        if distance > 100 and zoom_change > 0.1:
            movement_type = 'pan_zoom'
        elif distance > 100:
            movement_type = 'pan'
        elif zoom_change > 0.1:
            movement_type = 'zoom'
        else:
            movement_type = 'hold'
        
        # Create intermediate keyframes for smooth interpolation
        num_frames = max(int((end_time - start_time) * 10), 3)  # At least 3 keyframes
        
        for i in range(num_frames + 1):
            t = i / num_frames
            time = start_time + (end_time - start_time) * t
            
            # Apply easing
            eased_t = self._ease_in_out_cubic(t)
            
            # Interpolate position and zoom
            x = start_pos[0] + (end_pos[0] - start_pos[0]) * eased_t
            y = start_pos[1] + (end_pos[1] - start_pos[1]) * eased_t
            zoom = start_zoom + (end_zoom - start_zoom) * eased_t
            
            keyframes.append(CameraKeyframe(
                time=time,
                position=(x, y),
                zoom_level=zoom,
                movement_type=movement_type,
                target_info=f"transition {i}/{num_frames}"
            ))
        
        return keyframes
    
    def _create_static_keyframe(self, start_time: float, end_time: float) -> CameraKeyframe:
        """Create a static center-frame keyframe."""
        center = self._get_frame_center()
        return CameraKeyframe(
            time=start_time,
            position=center,
            zoom_level=1.0,
            movement_type='hold',
            target_info='static center frame'
        )
    
    def _calculate_optimal_zoom(self, target: FocusTarget) -> float:
        """Calculate optimal zoom level for a target."""
        detection = target.detection
        
        # Faces and text often benefit from slight zoom
        if detection.type == 'face':
            return 1.2  # Slight zoom on faces
        elif detection.type == 'text' and detection.metadata.get('is_large'):
            return 1.0  # Keep large text at normal zoom
        elif detection.type == 'text':
            return 1.3  # Zoom in on smaller text
        elif detection.type == 'motion' and detection.metadata.get('is_cursor'):
            return 1.4  # Zoom on cursor movements
        elif detection.type == 'object':
            return 1.1  # Slight zoom on objects
        else:
            return 1.0  # Normal zoom for everything else
    
    def _calculate_distance(self, pos1: Tuple[float, float],
                           pos2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two positions."""
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def _estimate_movement_duration(self, distance: float, zoom_change: float) -> float:
        """Estimate time needed for movement."""
        pan_time = distance / self.max_pan_speed if distance > 0 else 0
        zoom_time = zoom_change / self.max_zoom_speed if zoom_change > 0 else 0
        
        # Take the maximum + some blend time
        total_time = max(pan_time, zoom_time) + 0.5
        
        # Clamp to reasonable duration
        return min(max(total_time, 0.5), 3.0)  # Between 0.5 and 3 seconds
    
    def _get_frame_center(self) -> Tuple[int, int]:
        """Get center position of frame."""
        return (self.frame_width // 2, self.frame_height // 2)
    
    def _ease_in_out_cubic(self, t: float) -> float:
        """Cubic ease-in-out easing function for smooth motion."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
    
    def _ease_in_quad(self, t: float) -> float:
        """Quadratic ease-in for acceleration."""
        return t * t
    
    def _ease_out_quad(self, t: float) -> float:
        """Quadratic ease-out for deceleration."""
        return 1 - (1 - t) * (1 - t)
    
    def _center_crop(self, frame: np.ndarray) -> np.ndarray:
        """Fallback: simple center crop."""
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        x = center_x - self.crop_width // 2
        y = center_y - self.crop_height // 2
        
        x = max(0, min(x, w - self.crop_width))
        y = max(0, min(y, h - self.crop_height))
        
        cropped = frame[y:y+self.crop_height, x:x+self.crop_width]
        
        if cropped.shape[:2] != (self.crop_height, self.crop_width):
            return cv2.resize(frame, (self.crop_width, self.crop_height))
        
        return cropped
