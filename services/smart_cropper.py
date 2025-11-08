"""Smart cropping service with intelligent subject tracking."""
import cv2
import numpy as np
from moviepy import VideoFileClip
from typing import Dict, List, Tuple, Optional
import logging
from scipy.interpolate import interp1d, CubicSpline
import os

# Import new intelligent framing modules
from services.content_detector import ContentDetector
from services.priority_engine import PriorityDecisionEngine
from services.dynamic_camera import DynamicCameraSystem
from services.audio_visual_sync import AudioVisualSync

logger = logging.getLogger(__name__)


class SmartCropper:
    """Intelligent cropping with subject tracking for podcasts and product demos."""

    def __init__(self, enable_smooth_transitions: bool = True, use_intelligent_framing: bool = True):
        # Configuration
        self.use_intelligent_framing = use_intelligent_framing
        self.enable_smooth_transitions = enable_smooth_transitions
        
        if self.use_intelligent_framing:
            # Initialize new intelligent framing system
            logger.info("Initializing Intelligent Framing System...")
            
            self.content_detector = ContentDetector(config={
                'enable_face_detection': True,
                'enable_text_detection': True,
                'enable_motion_tracking': True,
                'enable_object_detection': False  # Disabled for performance
            })
            
            self.priority_engine = PriorityDecisionEngine(config={
                'min_priority_to_focus': 70,
                'priority_change_threshold': 20,
                'min_hold_duration': 2.0,
                'audio_boost_factor': 20,
                'keyword_match_boost': 10
            })
            
            self.audio_visual_sync = AudioVisualSync()
            
            logger.info("✅ Intelligent Framing System ready")
        else:
            # Legacy face detector for fallback
            logger.info("Using legacy framing system")
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
            else:
                self.face_cascade = None
                logger.warning("Face detection not available, will use fallback methods")
        
        # Smooth transition settings
        self.max_velocity = 200  # Max pixels per second movement
        self.min_movement_threshold = 50  # Only apply smoothing if movement > this many pixels

    def apply_smart_crop(self, clip: VideoFileClip, category: str,
                         tracking_focus: str,
                         target_size: Tuple[int, int],
                         transcript: Optional[List[Dict]] = None) -> VideoFileClip:
        """
        Apply intelligent cropping based on video category and tracking focus.

        Args:
            clip: Video clip to crop
            category: "podcast" or "product_demo"
            tracking_focus: Description of what to track (e.g., "speaking person", "product feature", "mouse cursor")
            target_size: Target (width, height) tuple
            transcript: Optional transcript for audio-visual sync

        Returns:
            Cropped and resized video clip
        """
        target_width, target_height = target_size
        target_aspect = target_width / target_height

        # Get video properties
        original_width = clip.w
        original_height = clip.h
        original_aspect = original_width / original_height
        duration = clip.duration

        # If aspect ratios match, just resize
        if abs(original_aspect - target_aspect) < 0.01:
            return clip.resized(new_size=(target_width, target_height))

        # Determine crop dimensions
        if original_aspect > target_aspect:
            # Video is wider - need to crop width
            crop_width = int(original_height * target_aspect)
            crop_height = original_height
        else:
            # Video is taller - need to crop height
            crop_width = original_width
            crop_height = int(original_width / target_aspect)

        # Use intelligent framing system if enabled
        if self.use_intelligent_framing:
            logger.info("Using Intelligent Framing System with dynamic camera movements")
            return self._apply_intelligent_framing(
                clip, crop_width, crop_height, target_size, 
                category, tracking_focus, transcript
            )
        else:
            # Legacy method: Intelligent tracking based on category and tracking_focus
            logger.info("Using legacy framing system")
            crop_positions = self._smart_track_subject(
                clip, crop_width, crop_height, duration, category, tracking_focus
            )
            return self._apply_dynamic_crop(clip, crop_positions, crop_width,
                                            crop_height, target_size)
    
    def _apply_intelligent_framing(self, clip: VideoFileClip, crop_width: int,
                                   crop_height: int, target_size: Tuple[int, int],
                                   category: str, tracking_focus: str,
                                   transcript: Optional[List[Dict]] = None) -> VideoFileClip:
        """
        Apply intelligent framing with multi-layer detection and audio-visual sync.
        
        This creates cinematic camera movements that follow content intelligently.
        """
        logger.info(f"Analyzing video with intelligent framing...")
        logger.info(f"  Duration: {clip.duration:.1f}s, Size: {clip.w}x{clip.h}")
        logger.info(f"  Category: {category}, Focus: {tracking_focus}")
        
        # Reset priority engine for new video
        self.priority_engine.reset_state()
        
        # Step 1: Analyze audio if transcript available
        audio_segments = []
        if transcript:
            logger.info(f"Analyzing transcript ({len(transcript)} segments)...")
            audio_segments = self.audio_visual_sync.analyze_transcript_segments(transcript)
            logger.info(f"  \u2192 Extracted {len(audio_segments)} audio segments with intent")
        
        # Step 2: Sample video and detect content
        logger.info("Detecting content in video frames...")
        sample_interval = 3  # Analyze every 3rd frame for performance
        sample_times = np.arange(0.5, clip.duration, 1.0 / clip.fps * sample_interval)
        
        all_detections = []
        prev_frame = None
        
        for i, t in enumerate(sample_times):
            if i % 30 == 0:  # Log progress every 30 frames
                logger.info(f"  Processing frame at t={t:.1f}s ({i}/{len(sample_times)})...")
            
            try:
                # Get frame
                frame = clip.get_frame(t)
                
                # Detect content in this frame
                detections = self.content_detector.detect_all_layers(frame, t, prev_frame)
                
                # Find relevant audio segment for this time
                audio_segment = None
                if audio_segments:
                    for segment in audio_segments:
                        if segment['start'] <= t <= segment['end']:
                            audio_segment = segment
                            break
                
                # Apply audio boost if available
                if audio_segment and detections:
                    detections = self.audio_visual_sync.match_audio_to_detections(
                        audio_segment, detections
                    )
                
                # Select best target using priority engine
                best_target = self.priority_engine.select_best_target(
                    detections, audio_segment, t
                )
                
                if best_target:
                    all_detections.append(best_target)
                
                prev_frame = frame
                
            except Exception as e:
                logger.warning(f"Error processing frame at t={t:.1f}s: {e}")
                continue
        
        logger.info(f"Content detection complete: {len(all_detections)} focus targets identified")
        
        # Step 3: Generate camera movement timeline
        logger.info("Generating smooth camera movements...")
        camera_system = DynamicCameraSystem(
            frame_size=(clip.w, clip.h),
            crop_size=(crop_width, crop_height),
            config={
                'max_pan_speed': 200,
                'max_zoom_speed': 0.1,
                'min_hold_duration': 2.0,
                'max_zoom': 1.5,
                'min_zoom': 0.8,
                'smooth_transitions': self.enable_smooth_transitions
            }
        )
        
        camera_keyframes = camera_system.generate_camera_timeline(
            all_detections, clip.duration
        )
        
        logger.info(f"Camera timeline generated: {len(camera_keyframes)} keyframes")
        
        # Step 4: Apply dynamic crop frame-by-frame
        logger.info("Applying dynamic crop with smooth camera movements...")
        
        def crop_frame_function(get_frame, t):
            """Apply dynamic crop to each frame."""
            frame = get_frame(t)
            cropped = camera_system.apply_dynamic_crop(frame, camera_keyframes, t)
            return cropped
        
        # Transform clip with dynamic cropping
        cropped_clip = clip.transform(crop_frame_function)
        
        # Resize to target size
        final_clip = cropped_clip.resized(new_size=target_size)
        
        logger.info("\u2705 Intelligent framing complete!")
        return final_clip

    def _track_person(self, clip: VideoFileClip, crop_width: int,
                      crop_height: int,
                      duration: float) -> List[Tuple[float, int, int]]:
        """Enhanced person tracking with multi-frame analysis and predictive positioning."""
        logger.info("Fast tracking person/face in video...")

        # Get video dimensions
        video_width = clip.w
        video_height = clip.h

        # OPTIMIZATION: Sample strategically at beginning, middle, and end
        # This catches face position changes while being 12x faster than every-0.5s sampling
        sample_times = []
        if duration <= 10:
            # Short video: sample at 25%, 50%, 75%
            sample_times = [duration * 0.25, duration * 0.5, duration * 0.75]
        elif duration <= 30:
            # Medium video: sample at 20%, 40%, 60%, 80%
            sample_times = [
                duration * 0.2, duration * 0.4, duration * 0.6, duration * 0.8
            ]
        else:
            # Long video: sample every 10 seconds
            num_samples = min(5, max(3, int(duration / 10)))
            sample_times = [
                duration * i /
                (num_samples - 1) if num_samples > 1 else duration / 2
                for i in range(num_samples)
            ]

        face_positions = []
        best_face = None
        best_face_size = 0

        # Find the best (largest) face across all samples
        for t in sample_times:
            if t >= duration:
                t = duration - 0.1

            try:
                # Get frame at time t
                frame = clip.get_frame(t)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

                # Detect faces using Haar Cascade (optimized parameters)
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(
                        frame_gray,
                        scaleFactor=
                        1.15,  # Balanced: not too slow, not too imprecise
                        minNeighbors=
                        4,  # Balanced: reduce false positives while staying fast
                        minSize=(60,
                                 60),  # Larger minimum for better detection
                        maxSize=(int(video_width * 0.8),
                                 int(video_height * 0.8)
                                 )  # Ignore unrealistic sizes
                    )

                    if len(faces) > 0:
                        # Find the largest face in this frame
                        largest_face = max(faces, key=lambda f: f[2] * f[3])
                        face_size = largest_face[2] * largest_face[3]

                        # Keep track of the best face found across all samples
                        if face_size > best_face_size:
                            best_face = largest_face
                            best_face_size = face_size

            except Exception as e:
                logger.warning(f"Error tracking face at {t}s: {str(e)}")

        # Enhanced crop positioning with golden ratio composition
        if best_face is not None:
            x, y, w, h = best_face

            # Calculate face center
            face_center_x = x + w // 2
            face_center_y = y + h // 2

            # Apply golden ratio for more aesthetic composition (1.618)
            golden_ratio = 1.618

            # Position face using enhanced rule of thirds with golden ratio
            if face_center_x < video_width / 2:
                # Face on left, give more space on right
                crop_x = max(
                    0,
                    min(face_center_x - crop_width // 3,
                        video_width - crop_width))
            else:
                # Face on right, give more space on left
                crop_x = max(
                    0,
                    min(face_center_x - int(crop_width / golden_ratio),
                        video_width - crop_width))

            # Vertical positioning with headroom consideration
            face_top_third = y + h // 3
            crop_y = max(
                0,
                min(face_top_third - crop_height // 3,
                    video_height - crop_height))

            # Add subtle zoom effect for faces that are too small
            face_area_ratio = (w * h) / (crop_width * crop_height)
            if face_area_ratio < 0.15:  # Face too small
                logger.info(
                    f"Face too small ({face_area_ratio:.2%}), adjusting crop for better visibility"
                )
                # Zoom in slightly by adjusting crop position
                crop_x = max(
                    0,
                    min(face_center_x - crop_width // 2,
                        video_width - crop_width))
                crop_y = max(
                    0,
                    min(face_center_y - crop_height // 2,
                        video_height - crop_height))

            logger.info(f"Face detected: {w}x{h}px at ({x}, {y})")
            logger.info(
                f"Enhanced crop position: ({crop_x}, {crop_y}) with golden ratio composition"
            )
        else:
            # Intelligent center crop with slight offset for dynamism
            crop_x = (video_width - crop_width) // 2
            crop_y = (video_height - crop_height
                      ) // 2 - crop_height // 20  # Slight upward bias
            logger.info(
                f"No face detected, using dynamic center crop at ({crop_x}, {crop_y})"
            )

        # Return static crop positions (smooth transitions disabled for performance)
        positions = [(0.0, crop_x, crop_y), (duration, crop_x, crop_y)]

        return positions

    def _track_mouse_or_feature(
            self, clip: VideoFileClip, crop_width: int, crop_height: int,
            duration: float,
            tracking_focus: str) -> List[Tuple[float, int, int]]:
        """Track mouse cursor or product feature for demo videos (Enhanced Smart Activity Analysis)."""
        logger.info(
            f"Analyzing screen recording for optimal crop: {tracking_focus}")

        video_width = clip.w
        video_height = clip.h

        # Enhanced activity analysis with motion detection
        sample_times = [0.15, 0.3, 0.5, 0.7, 0.85
                        ] if duration > 5 else [0.3, 0.5, 0.7]
        activity_zones = []

        for t_ratio in sample_times:
            t = min(duration * t_ratio, duration - 0.1)
            try:
                frame = clip.get_frame(t)

                # Convert to grayscale for edge detection
                gray = cv2.cvtColor((frame * 255).astype(np.uint8),
                                    cv2.COLOR_RGB2GRAY)

                # Apply edge detection to find areas with content
                edges = cv2.Canny(gray, 50, 150)

                # Divide frame into grid to find activity zones
                grid_size = 4
                cell_width = video_width // grid_size
                cell_height = video_height // grid_size

                max_activity = 0
                best_cell_x = grid_size // 2
                best_cell_y = grid_size // 2

                for grid_y in range(grid_size):
                    for grid_x in range(grid_size):
                        # Extract cell
                        y1 = grid_y * cell_height
                        y2 = min((grid_y + 1) * cell_height, video_height)
                        x1 = grid_x * cell_width
                        x2 = min((grid_x + 1) * cell_width, video_width)

                        cell = edges[y1:y2, x1:x2]
                        activity = np.sum(cell) / 255  # Count edge pixels

                        if activity > max_activity:
                            max_activity = activity
                            best_cell_x = grid_x
                            best_cell_y = grid_y

                # Store the center of the most active cell with weight
                center_x = (best_cell_x + 0.5) * cell_width
                center_y = (best_cell_y + 0.5) * cell_height
                activity_zones.append((center_x, center_y, max_activity))

                logger.debug(
                    f"Activity at {t_ratio*100:.0f}%: cell ({best_cell_x}, {best_cell_y}), activity score: {max_activity:.0f}"
                )

            except Exception as e:
                logger.warning(f"Error analyzing activity at {t}s: {str(e)}")

        # Calculate weighted average of activity zones
        if activity_zones:
            total_weight = sum(zone[2] for zone in activity_zones)
            if total_weight > 0:
                weighted_x = sum(zone[0] * zone[2]
                                 for zone in activity_zones) / total_weight
                weighted_y = sum(zone[1] * zone[2]
                                 for zone in activity_zones) / total_weight

                # Apply slight upward bias for better UI element capture
                weighted_y = weighted_y - crop_height // 15

                # Calculate crop position centered on activity zone
                crop_x = int(
                    max(
                        0,
                        min(weighted_x - crop_width // 2,
                            video_width - crop_width)))
                crop_y = int(
                    max(
                        0,
                        min(weighted_y - crop_height // 2,
                            video_height - crop_height)))

                logger.info(
                    f"Activity center at ({int(weighted_x)}, {int(weighted_y)}), crop at ({crop_x}, {crop_y})"
                )
            else:
                # No significant activity - use intelligent default
                crop_x = (video_width - crop_width) // 2
                crop_y = (video_height - crop_height
                          ) // 2 - crop_height // 10  # Slight upward bias
                logger.info(
                    f"Low activity, using optimized center crop at ({crop_x}, {crop_y})"
                )
        else:
            # Fallback to intelligent center
            crop_x = (video_width - crop_width) // 2
            crop_y = (video_height - crop_height) // 2 - crop_height // 10
            logger.info(
                f"Analysis incomplete, using smart center crop at ({crop_x}, {crop_y})"
            )

        # Return optimized static crop positions
        positions = [(0.0, crop_x, crop_y), (duration, crop_x, crop_y)]

        return positions

    def _create_simple_smooth_path(
            self,
            start_pos: Tuple[int, int],
            end_pos: Tuple[int, int],
            duration: float,
            fps: int = 30) -> List[Tuple[float, int, int]]:
        """Create simple linear smooth path between two points (SIMPLIFIED for performance)."""
        if duration <= 0:
            return [(0.0, start_pos[0], start_pos[1])]

        # Check if movement is significant enough to warrant smoothing
        movement = np.sqrt((end_pos[0] - start_pos[0])**2 +
                           (end_pos[1] - start_pos[1])**2)
        if movement < self.min_movement_threshold:
            # Not enough movement, use static
            return [(0.0, start_pos[0], start_pos[1]),
                    (duration, start_pos[0], start_pos[1])]

        # Create simple linear interpolation
        num_frames = int(duration * fps)
        path = []

        for i in range(num_frames):
            t = i / fps
            progress = i / (num_frames - 1) if num_frames > 1 else 0

            # Simple linear interpolation (fast and smooth enough)
            x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * progress)
            y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * progress)

            path.append((t, x, y))

        return path

    def _smart_track_subject(
            self, clip: VideoFileClip, crop_width: int, crop_height: int,
            duration: float, category: str, tracking_focus: str) -> List[Tuple[float, int, int]]:
        """
        Intelligently track subject based on category and tracking_focus with priority.
        
        Priority order:
        1. tracking_focus keywords (person, face, speaker, product, mouse, cursor, screen)
        2. category (podcast -> person, product_demo -> product)
        3. fallback to hybrid detection
        """
        logger.info(f"Smart tracking: category='{category}', focus='{tracking_focus}'")
        
        # Normalize tracking_focus for comparison
        focus_lower = tracking_focus.lower() if tracking_focus else ""
        
        # Priority 1: Check tracking_focus keywords
        person_keywords = ["person", "face", "speaker", "speaking", "interview", "host", "guest"]
        product_keywords = ["product", "mouse", "cursor", "screen", "demo", "feature", "ui", "interface"]
        
        focus_on_person = any(keyword in focus_lower for keyword in person_keywords)
        focus_on_product = any(keyword in focus_lower for keyword in product_keywords)
        
        # Determine tracking strategy
        if focus_on_person:
            logger.info("Tracking focus: PERSON (from tracking_focus keywords)")
            return self._track_person(clip, crop_width, crop_height, duration)
        elif focus_on_product:
            logger.info("Tracking focus: PRODUCT (from tracking_focus keywords)")
            return self._track_mouse_or_feature(clip, crop_width, crop_height, duration, tracking_focus)
        
        # Priority 2: Use category
        if category == "podcast":
            logger.info("Tracking focus: PERSON (from category='podcast')")
            return self._track_person(clip, crop_width, crop_height, duration)
        elif category == "product_demo":
            logger.info("Tracking focus: PRODUCT (from category='product_demo')")
            return self._track_mouse_or_feature(clip, crop_width, crop_height, duration, tracking_focus)
        
        # Priority 3: Hybrid detection - try both and pick the best
        logger.info("Tracking focus: HYBRID (trying both person and product detection)")
        return self._hybrid_track(clip, crop_width, crop_height, duration, tracking_focus)
    
    def _hybrid_track(
            self, clip: VideoFileClip, crop_width: int, crop_height: int,
            duration: float, tracking_focus: str) -> List[Tuple[float, int, int]]:
        """
        Hybrid tracking: detect both person and product, choose the best based on confidence.
        """
        video_width = clip.w
        video_height = clip.h
        
        # Try person detection first
        person_positions = self._track_person(clip, crop_width, crop_height, duration)
        
        # Check if person was detected (non-center position indicates detection)
        center_x = (video_width - crop_width) // 2
        center_y = (video_height - crop_height) // 2
        
        person_detected = False
        if person_positions:
            # Check if any position is significantly different from center
            for _, x, y in person_positions:
                if abs(x - center_x) > 50 or abs(y - center_y) > 50:
                    person_detected = True
                    break
        
        if person_detected:
            logger.info("Hybrid: Person detected, using person tracking")
            return person_positions
        else:
            logger.info("Hybrid: No person detected, using product/activity tracking")
            return self._track_mouse_or_feature(clip, crop_width, crop_height, duration, tracking_focus)
    
    def _center_crop_positions(
            self, crop_width: int, crop_height: int,
            duration: float) -> List[Tuple[float, int, int]]:
        """Generate center crop positions (fallback)."""
        return [(0.0, 0, 0), (duration, 0, 0)]

    def _smooth_positions_simple(
            self, positions: List[Tuple[float, int, int]],
            duration: float) -> List[Tuple[float, int, int]]:
        """Simple position smoothing (DEPRECATED - use static crop for performance)."""
        # This method is kept for backward compatibility but not used
        # Static cropping is faster and good enough for most use cases
        logger.warning(
            "Smooth positions called but static crop is recommended for performance"
        )
        return positions

    def _apply_dynamic_crop(self, clip: VideoFileClip,
                            crop_positions: List[Tuple[float, int, int]],
                            crop_width: int, crop_height: int,
                            target_size: Tuple[int, int]) -> VideoFileClip:
        """Apply static cropping (OPTIMIZED - removed slow dynamic cropping)."""
        target_width, target_height = target_size

        try:
            # ALWAYS use static crop for best performance
            # Dynamic frame-by-frame cropping is 10-20x slower with minimal visual benefit

            # Calculate average position from all samples
            avg_x = sum(p[1] for p in crop_positions) // len(crop_positions)
            avg_y = sum(p[2] for p in crop_positions) // len(crop_positions)

            # Ensure crop position is within bounds
            avg_x = max(0, min(avg_x, clip.w - crop_width))
            avg_y = max(0, min(avg_y, clip.h - crop_height))

            # Use MoviePy's built-in crop and resize (fast and reliable)
            logger.info(
                f"Applying static crop at ({avg_x}, {avg_y}) size {crop_width}x{crop_height}"
            )
            cropped = clip.cropped(x1=avg_x,
                                   y1=avg_y,
                                   x2=avg_x + crop_width,
                                   y2=avg_y + crop_height)
            resized = cropped.resized(new_size=(target_width, target_height))

            logger.info(
                f"✅ Crop applied successfully, resized to {target_width}x{target_height}"
            )
            return resized

        except Exception as e:
            logger.error(f"Error applying crop: {e}")
            logger.warning(f"Falling back to simple resize without cropping")
            # Fallback: just resize without cropping
            try:
                return clip.resized(new_size=(target_width, target_height))
            except Exception as e2:
                logger.error(f"Resize fallback also failed: {e2}")
                raise Exception(f"Crop and resize both failed: {e}, {e2}")

    def _detect_faces(self, frame: np.ndarray) -> List:
        """Detect faces in frame using OpenCV."""
        try:
            # Convert to BGR for OpenCV
            frame_bgr = cv2.cvtColor((frame * 255).astype(np.uint8),
                                     cv2.COLOR_RGB2BGR)
            frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

            if self.face_cascade is not None:
                # Use Haar Cascade
                faces = self.face_cascade.detectMultiScale(frame_gray,
                                                           scaleFactor=1.1,
                                                           minNeighbors=4,
                                                           minSize=(30, 30))
                return faces.tolist() if len(faces) > 0 else []

            return []
        except Exception as e:
            logger.debug(f"Face detection error: {e}")
            return []
