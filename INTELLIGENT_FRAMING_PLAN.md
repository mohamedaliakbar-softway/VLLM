# Intelligent Dynamic Framing System - Implementation Plan

## 🎯 Vision

Create a cinematic, AI-powered dynamic framing system that intelligently follows content, understands context, and creates smooth camera movements (pan, zoom, focus) that keep the most important content in frame at all times.

---

## 🧠 Core Concept

The system will act like an **intelligent camera operator** that:
- **Sees** what's on screen (faces, text, objects, motion)
- **Listens** to what's being said (audio transcription)
- **Understands** context (product demo vs podcast vs tutorial)
- **Decides** what to focus on based on priority
- **Moves** smoothly with cinematic camera work (pan, zoom, transitions)

---

## 📊 Multi-Layer Content Detection System

### Layer 1: Face Detection (Highest Priority)
**Technology:** OpenCV Haar Cascade + DNN Face Detector
**Purpose:** Detect and track human faces
**Priority:** 100 (Highest)
**Output:** Face bounding boxes, confidence scores, positions

```python
Priority Rules:
- Speaking face: 100 (highest)
- Face visible: 90
- Multiple faces: Track the largest/most centered
- No face: Fall through to next layer
```

### Layer 2: Text Detection (High Priority)
**Technology:** Tesseract OCR + OpenCV text detection
**Purpose:** Detect and read text on screen (UI elements, titles, code, subtitles)
**Priority:** 80-90
**Output:** Text regions, content, importance scores

```python
Priority Rules:
- Large text/titles: 90
- Code/terminal: 85
- UI labels/buttons: 80
- Small text: 70
- Text mentioned in audio: +20 boost
```

### Layer 3: Motion & Activity Detection (Medium-High Priority)
**Technology:** Optical Flow + Edge Detection
**Purpose:** Track mouse cursor, animations, screen transitions
**Priority:** 70-80
**Output:** Motion vectors, activity hotspots

```python
Priority Rules:
- Mouse cursor movement: 80
- Active UI interactions: 75
- Animations/transitions: 70
- Static content: 50
```

### Layer 4: Object Detection (Medium Priority)
**Technology:** OpenCV contours + YOLO (optional lightweight model)
**Purpose:** Detect products, devices, objects being demonstrated
**Priority:** 60-75
**Output:** Object bounding boxes, classifications

```python
Priority Rules:
- Product being demonstrated: 75
- Device/hardware: 70
- Props/objects: 60
```

### Layer 5: Visual Saliency (Low Priority)
**Technology:** Edge detection + contrast analysis
**Purpose:** Find visually interesting regions when nothing else detected
**Priority:** 40-50
**Output:** Saliency maps, interest regions

---

## 🎬 Dynamic Camera Movement System

### Camera States

1. **Static** - Frame locked on subject
2. **Panning** - Smooth horizontal/vertical movement
3. **Zooming In** - Focusing on detail
4. **Zooming Out** - Showing context
5. **Following** - Tracking moving subject
6. **Transitioning** - Smooth movement between subjects

### Movement Parameters

```python
class CameraState:
    position: (x, y)           # Current frame center
    zoom_level: float          # 1.0 = normal, 1.5 = 50% zoom in, 0.7 = zoom out
    velocity: (vx, vy)         # Movement speed
    acceleration: float        # Smooth acceleration/deceleration
    target: (x, y)            # Where camera wants to go
    
Movement Constraints:
- Max velocity: 200 px/second (smooth, not jarring)
- Max acceleration: 100 px/s² (natural feel)
- Min movement threshold: 30px (avoid jitter)
- Zoom speed: 0.1x per second (smooth zoom)
- Hold duration: 2-5 seconds before moving (let viewers see content)
```

### Movement Decision Logic

```python
def decide_camera_movement(current_state, targets, audio_context, duration):
    """
    Intelligent camera movement based on multiple factors.
    """
    
    # 1. Calculate target priorities
    for target in targets:
        priority = base_priority
        
        # Boost priority if mentioned in audio
        if mentioned_in_audio(target, audio_context):
            priority += 20
        
        # Boost priority if new/changed
        if is_new_target(target):
            priority += 15
        
        # Reduce priority if off-screen
        if is_off_screen(target):
            priority -= 30
        
        # Reduce priority if recently focused
        if recently_focused(target):
            priority -= 10
    
    # 2. Select highest priority target
    best_target = max(targets, key=lambda t: t.priority)
    
    # 3. Determine movement type
    if far_from_current(best_target):
        if requires_context():
            return zoom_out_pan_zoom_in(best_target)  # Show journey
        else:
            return smooth_pan(best_target)  # Direct movement
    
    elif requires_detail(best_target):
        return zoom_in(best_target, zoom_level=1.3)
    
    elif requires_context(best_target):
        return zoom_out(zoom_level=0.8)
    
    else:
        return hold_current()  # Stay focused
```

---

## 🎙️ Audio-Visual Synchronization

### Audio Analysis Integration

```python
class AudioVisualSync:
    def analyze_transcript_segments(self, transcript, timestamps):
        """
        Extract keywords and timing from transcript to guide framing.
        """
        segments = []
        
        for segment in transcript:
            keywords = extract_keywords(segment.text)
            
            # Identify content type from keywords
            if has_keywords(keywords, ["see", "look", "here", "this"]):
                focus_type = "demonstrative"  # User pointing at something
            
            elif has_keywords(keywords, ["code", "function", "class"]):
                focus_type = "code"  # Show code area
            
            elif has_keywords(keywords, ["button", "click", "menu"]):
                focus_type = "ui_element"  # Show UI component
            
            elif has_keywords(keywords, ["product", "feature", "design"]):
                focus_type = "product"  # Show product closeup
            
            else:
                focus_type = "speaker"  # Show person talking
            
            segments.append({
                'start': segment.start_time,
                'end': segment.end_time,
                'focus_type': focus_type,
                'keywords': keywords,
                'priority_boost': calculate_boost(keywords)
            })
        
        return segments
```

### Synchronization Algorithm

```python
def synchronize_framing_with_audio(video_clip, transcript, detections):
    """
    Align camera movements with what's being said.
    """
    timeline = []
    
    for i, segment in enumerate(transcript):
        start_time = segment['start']
        end_time = segment['end']
        focus_type = segment['focus_type']
        
        # Find relevant detections in this time window
        active_detections = filter_by_time(detections, start_time, end_time)
        
        # Apply audio-based priority boost
        for detection in active_detections:
            if detection.type == focus_type:
                detection.priority += segment['priority_boost']
            
            # Keyword matching
            if any(keyword in detection.text for keyword in segment['keywords']):
                detection.priority += 15
        
        # Select best target for this time segment
        best_target = max(active_detections, key=lambda d: d.priority)
        
        # Generate camera keyframe
        timeline.append({
            'time': start_time,
            'target': best_target,
            'movement': decide_movement(best_target, current_position),
            'duration': end_time - start_time
        })
    
    return timeline
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Video Input + Audio                       │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────────┐        ┌──────▼───────┐
│  Video     │        │   Audio      │
│  Analysis  │        │   Analysis   │
│  Pipeline  │        │   Pipeline   │
└───┬────────┘        └──────┬───────┘
    │                         │
    │  ┌──────────────────────┘
    │  │
    │  │   Detection Layers:
    │  │   1. Face Detection → 100 priority
    │  │   2. Text Detection (OCR) → 80-90 priority
    │  │   3. Motion Detection → 70-80 priority
    │  │   4. Object Detection → 60-75 priority
    │  │   5. Saliency → 40-50 priority
    │  │
    ▼  ▼
┌────────────────────────────┐
│  Priority Decision Engine  │
│  - Combines all detections │
│  - Audio context boost     │
│  - Temporal smoothing      │
│  - Priority resolution     │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│  Camera Movement Planner   │
│  - Pan/zoom decisions      │
│  - Smooth interpolation    │
│  - Keyframe generation     │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│  Dynamic Crop Renderer     │
│  - Apply crop per frame    │
│  - Render transitions      │
│  - Export final video      │
└────────────────────────────┘
```

---

## 📝 Implementation Steps

### Phase 1: Enhanced Content Detection (Week 1)

#### Step 1.1: Upgrade Face Detection
```python
class EnhancedFaceDetector:
    """
    Multi-method face detection with confidence scoring.
    """
    - Add MediaPipe Face Detection (more accurate)
    - Keep OpenCV Haar Cascade (fast fallback)
    - Implement confidence scoring
    - Track face across frames
    - Detect speaking face (mouth movement analysis)
```

#### Step 1.2: Implement Text Detection
```python
class TextDetector:
    """
    Detect and read text on screen using Tesseract + OpenCV.
    """
    - Use EAST text detector for region detection
    - Apply Tesseract OCR on detected regions
    - Extract text content and position
    - Calculate importance based on size, position, contrast
    - Match text with audio keywords
```

#### Step 1.3: Enhanced Motion Detection
```python
class MotionDetector:
    """
    Track movement, cursor, and activity hotspots.
    """
    - Implement optical flow analysis
    - Detect cursor/pointer movements
    - Track UI interactions (clicks, hovers)
    - Identify animation/transition regions
    - Calculate motion vectors and velocities
```

#### Step 1.4: Basic Object Detection
```python
class ObjectDetector:
    """
    Detect products, devices, and objects.
    """
    - Use OpenCV contour detection
    - Optional: YOLOv5-nano for lightweight object detection
    - Identify product demonstrations
    - Track object positions across frames
```

---

### Phase 2: Priority Decision Engine (Week 1-2)

```python
class PriorityDecisionEngine:
    """
    Intelligent decision making for what to focus on.
    """
    
    def __init__(self):
        self.detection_history = []
        self.focus_history = []
        self.current_focus = None
    
    def calculate_target_priority(self, detection, audio_segment, frame_time):
        """
        Calculate comprehensive priority score for each detection.
        """
        priority = detection.base_priority
        
        # Audio context boost
        if self.mentioned_in_audio(detection, audio_segment):
            priority += 20
            logger.info(f"Audio boost: {detection.type} mentioned")
        
        # Keyword matching
        keyword_matches = self.match_keywords(detection, audio_segment)
        priority += len(keyword_matches) * 5
        
        # Newness factor
        if self.is_new_detection(detection):
            priority += 15
            logger.info(f"New detection: {detection.type}")
        
        # Recency penalty (avoid ping-pong)
        if self.recently_focused(detection):
            priority -= 10
        
        # Position factor (centered content often important)
        centrality = self.calculate_centrality(detection)
        priority += centrality * 5
        
        # Size factor (larger = more important)
        size_factor = self.calculate_size_factor(detection)
        priority += size_factor * 10
        
        # Temporal consistency (stay with same target for a while)
        if detection == self.current_focus:
            priority += 8  # Slight boost to current focus
        
        return priority
    
    def select_best_target(self, detections, audio_segment, frame_time):
        """
        Select the highest priority target to focus on.
        """
        if not detections:
            return self.default_target()  # Center frame
        
        # Calculate priorities for all detections
        scored_targets = []
        for detection in detections:
            priority = self.calculate_target_priority(
                detection, audio_segment, frame_time
            )
            scored_targets.append((priority, detection))
        
        # Sort by priority
        scored_targets.sort(key=lambda x: x[0], reverse=True)
        
        # Get best target
        best_priority, best_target = scored_targets[0]
        
        # Minimum priority threshold to change focus
        if self.current_focus and best_priority < 75:
            # Keep current focus unless new target is significantly better
            if best_priority < self.current_focus.priority + 20:
                return self.current_focus
        
        logger.info(f"Selected target: {best_target.type} (priority: {best_priority})")
        return best_target
```

---

### Phase 3: Dynamic Camera System (Week 2)

```python
class DynamicCameraSystem:
    """
    Cinematic camera movements with smooth transitions.
    """
    
    def __init__(self):
        self.max_velocity = 200  # px/sec
        self.max_acceleration = 100  # px/sec²
        self.min_hold_duration = 2.0  # seconds
        self.zoom_speed = 0.1  # per second
    
    def generate_camera_timeline(self, targets, duration):
        """
        Generate smooth camera movements across the video timeline.
        """
        timeline = []
        current_time = 0
        current_position = (0, 0)
        current_zoom = 1.0
        
        for target in targets:
            target_time = target['time']
            target_position = target['position']
            target_zoom = self.calculate_optimal_zoom(target)
            
            # Calculate movement duration
            distance = self.calculate_distance(current_position, target_position)
            movement_duration = min(
                distance / self.max_velocity,
                target_time - current_time - self.min_hold_duration
            )
            
            # Decide movement type
            if distance > 400:  # Far away
                movement = self.create_pan_movement(
                    current_position, target_position, movement_duration
                )
            elif abs(target_zoom - current_zoom) > 0.2:  # Significant zoom change
                movement = self.create_zoom_movement(
                    current_zoom, target_zoom, movement_duration
                )
            else:  # Small adjustment
                movement = self.create_smooth_transition(
                    current_position, target_position, movement_duration
                )
            
            timeline.append(movement)
            
            # Hold on target
            hold_duration = target['duration'] - movement_duration
            timeline.append(self.create_hold(target_position, target_zoom, hold_duration))
            
            current_time = target_time + target['duration']
            current_position = target_position
            current_zoom = target_zoom
        
        return timeline
    
    def create_smooth_transition(self, start_pos, end_pos, duration):
        """
        Create smooth eased transition between positions.
        """
        # Use cubic ease-in-out for natural feeling
        def ease_in_out_cubic(t):
            if t < 0.5:
                return 4 * t * t * t
            else:
                return 1 - pow(-2 * t + 2, 3) / 2
        
        keyframes = []
        num_frames = int(duration * 30)  # 30 fps
        
        for i in range(num_frames):
            t = i / num_frames
            eased_t = ease_in_out_cubic(t)
            
            x = start_pos[0] + (end_pos[0] - start_pos[0]) * eased_t
            y = start_pos[1] + (end_pos[1] - start_pos[1]) * eased_t
            
            keyframes.append({
                'time': i / 30,
                'position': (x, y),
                'type': 'transition'
            })
        
        return keyframes
    
    def apply_dynamic_crop(self, clip, timeline, crop_size):
        """
        Apply frame-by-frame dynamic cropping based on timeline.
        """
        def crop_frame_function(get_frame, t):
            # Get original frame
            frame = get_frame(t)
            
            # Find current camera position from timeline
            camera_pos = self.interpolate_position(timeline, t)
            zoom_level = self.interpolate_zoom(timeline, t)
            
            # Calculate crop region
            crop_width = int(crop_size[0] / zoom_level)
            crop_height = int(crop_size[1] / zoom_level)
            
            x = int(camera_pos[0] - crop_width // 2)
            y = int(camera_pos[1] - crop_height // 2)
            
            # Ensure within bounds
            x = max(0, min(x, frame.shape[1] - crop_width))
            y = max(0, min(y, frame.shape[0] - crop_height))
            
            # Crop frame
            cropped = frame[y:y+crop_height, x:x+crop_width]
            
            # Resize to target size
            resized = cv2.resize(cropped, crop_size, interpolation=cv2.INTER_LANCZOS4)
            
            return resized
        
        return clip.transform(crop_frame_function)
```

---

### Phase 4: Audio-Visual Integration (Week 2-3)

```python
class AudioVisualIntegration:
    """
    Synchronize camera movements with audio content.
    """
    
    def analyze_audio_context(self, transcript, timestamps):
        """
        Extract semantic meaning from audio to guide framing.
        """
        segments = []
        
        for i, entry in enumerate(transcript):
            text = entry['text'].lower()
            start_time = entry['start']
            end_time = entry['end']
            
            # Keyword extraction
            keywords = self.extract_keywords(text)
            
            # Intent detection
            intent = self.detect_intent(text, keywords)
            
            # Priority calculation
            priority_boost = self.calculate_audio_priority(intent, keywords)
            
            segments.append({
                'start': start_time,
                'end': end_time,
                'text': text,
                'keywords': keywords,
                'intent': intent,
                'priority_boost': priority_boost
            })
        
        return segments
    
    def detect_intent(self, text, keywords):
        """
        Understand what the speaker is trying to show/demonstrate.
        """
        # Demonstrative intent
        if any(word in text for word in ['see', 'look', 'here', 'this', 'that', 'these']):
            return 'demonstrative'
        
        # Code/technical intent
        if any(word in text for word in ['code', 'function', 'class', 'variable', 'error']):
            return 'code'
        
        # UI interaction intent
        if any(word in text for word in ['click', 'button', 'menu', 'icon', 'tab']):
            return 'ui_interaction'
        
        # Product focus intent
        if any(word in text for word in ['product', 'feature', 'design', 'quality']):
            return 'product_focus'
        
        # Explanation intent
        if any(word in text for word in ['because', 'so', 'therefore', 'means']):
            return 'explanation'
        
        return 'general'
    
    def sync_detections_with_audio(self, visual_detections, audio_segments):
        """
        Boost visual detection priorities based on audio context.
        """
        synced_timeline = []
        
        for audio_seg in audio_segments:
            # Find visual detections in this time window
            visual_in_window = [
                d for d in visual_detections 
                if audio_seg['start'] <= d['time'] <= audio_seg['end']
            ]
            
            # Apply audio-based priority boosts
            for detection in visual_in_window:
                # Intent matching
                if detection['type'] == audio_seg['intent']:
                    detection['priority'] += audio_seg['priority_boost']
                
                # Keyword matching
                if detection.get('text'):  # For text detections
                    matches = set(audio_seg['keywords']) & set(detection['text'].lower().split())
                    detection['priority'] += len(matches) * 10
            
            # Select best target for this segment
            if visual_in_window:
                best_target = max(visual_in_window, key=lambda d: d['priority'])
                synced_timeline.append({
                    'start': audio_seg['start'],
                    'end': audio_seg['end'],
                    'target': best_target,
                    'audio_context': audio_seg
                })
        
        return synced_timeline
```

---

## 🎨 Priority Matrix

| Content Type | Base Priority | Audio Match | New Detection | Size Bonus | Total Range |
|--------------|--------------|-------------|---------------|------------|-------------|
| **Speaking Face** | 100 | +20 | +15 | +10 | 100-145 |
| **Face (Static)** | 90 | +20 | +15 | +5 | 90-130 |
| **Large Text/Title** | 90 | +20 | +15 | +10 | 90-135 |
| **Code/Terminal** | 85 | +20 | +15 | +5 | 85-125 |
| **Mouse Cursor** | 80 | +20 | +15 | +0 | 80-115 |
| **UI Element** | 80 | +20 | +15 | +5 | 80-120 |
| **Active Motion** | 75 | +15 | +15 | +5 | 75-110 |
| **Product** | 75 | +20 | +15 | +10 | 75-120 |
| **Small Text** | 70 | +15 | +10 | +0 | 70-95 |
| **Object** | 60 | +15 | +15 | +5 | 60-95 |
| **Saliency** | 50 | +10 | +10 | +5 | 50-75 |

---

## 🚀 Performance Optimizations

### 1. Selective Frame Analysis
- Analyze every 3rd-5th frame for detections
- Use previous frame's detections for in-between frames
- Full analysis only when scene changes

### 2. Hierarchical Processing
- Run fast detections first (face, motion)
- Run expensive detections (OCR, object) only in relevant regions
- Skip detailed analysis if high-priority target already found

### 3. Caching & Reuse
- Cache face detection models
- Reuse OCR results for static text
- Store detection history for temporal consistency

### 4. Multi-threading
- Parallel processing of different detection layers
- Async audio analysis
- Background rendering of camera movements

---

## 📈 Success Metrics

1. **Focus Accuracy**: Target should be in frame 95%+ of the time
2. **Smooth Movement**: No jerky movements, smooth transitions
3. **Context Awareness**: Camera follows what's being discussed
4. **Processing Time**: Max 2x realtime for full analysis
5. **User Satisfaction**: Professional, cinematic output

---

## 🔧 Configuration Options

```python
class IntelligentFramingConfig:
    # Detection settings
    enable_face_detection: bool = True
    enable_text_detection: bool = True
    enable_motion_tracking: bool = True
    enable_object_detection: bool = False  # Optional, requires YOLO
    
    # Camera settings
    max_pan_speed: int = 200  # px/sec
    max_zoom: float = 1.5
    min_zoom: float = 0.8
    min_hold_duration: float = 2.0  # seconds
    smooth_transitions: bool = True
    
    # Priority thresholds
    min_priority_to_focus: int = 70
    priority_change_threshold: int = 20  # How much better to switch focus
    
    # Audio integration
    enable_audio_sync: bool = True
    audio_boost_factor: int = 20
    keyword_match_boost: int = 10
    
    # Performance
    analysis_frame_interval: int = 3  # Analyze every N frames
    enable_caching: bool = True
    max_threads: int = 4
```

---

This comprehensive system will create professional, context-aware video shorts that intelligently follow the content and create engaging, cinematic framing! 🎬
