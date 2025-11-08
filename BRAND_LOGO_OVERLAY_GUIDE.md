# Brand Logo Overlay Feature Guide

## 🎯 Overview

The Brand Logo Overlay feature allows users to add custom brand logos/watermarks to their video clips directly from the video editor interface. This feature works similarly to the live captions system, using MoviePy for video composition.

---

## ✨ Features

### User Capabilities
- **Upload Logo Images**: Upload PNG, JPG, GIF, or BMP images as brand logos
- **Image Validation**: Automatic validation of image format and size
- **Logo Library**: View and manage all uploaded logos
- **Position Control**: 7 position presets (corners, center, edges)
- **Size Adjustment**: Logo size as percentage of video width (1-50%)
- **Opacity Control**: Adjust logo transparency (0.0-1.0)
- **Padding Control**: Configure spacing from video edges
- **Background Processing**: Logo overlay applied asynchronously with progress tracking
- **Chatbot Integration**: Upload logos directly from the chat interface

### Technical Features
- **MoviePy Integration**: High-quality video composition
- **Aspect Ratio Preservation**: Logo maintains original aspect ratio
- **Format Support**: PNG (with transparency), JPG, GIF, BMP
- **File Size Limit**: 5MB max for frontend validation
- **Storage Management**: Organized logo storage in `uploads/logos/`
- **UUID Naming**: Unique filenames to prevent conflicts

---

## 📦 Components

### 1. Backend Services

#### `services/logo_overlay.py`
Core service for logo overlay operations.

**Key Class: LogoOverlay**

```python
class LogoOverlay:
    """Handles adding brand logos to videos."""
    
    # Position presets
    POSITIONS = {
        "top-left": (0.02, 0.02),
        "top-right": (0.98, 0.02),
        "bottom-left": (0.02, 0.98),
        "bottom-right": (0.98, 0.98),
        "center": (0.5, 0.5),
        "top-center": (0.5, 0.02),
        "bottom-center": (0.5, 0.98),
    }
```

**Methods:**

- `add_logo()`: Apply logo overlay to video
  - Parameters: video_path, logo_path, output_path, position, size_percent, opacity, padding
  - Returns: Path to output video with logo
  - Raises: FileNotFoundError, ValueError, Exception

- `validate_logo_image()`: Validate logo image file
  - Parameters: logo_path
  - Returns: Dict with validation results and image info
  - Includes: width, height, format, validity status

- `_calculate_position()`: Calculate exact pixel coordinates
  - Internal method for position calculation
  - Handles padding and alignment

**Example Usage:**

```python
from services.logo_overlay import LogoOverlay

overlay = LogoOverlay()

# Validate logo
validation = overlay.validate_logo_image("path/to/logo.png")
if validation['valid']:
    # Apply logo
    result = overlay.add_logo(
        video_path="input.mp4",
        logo_path="logo.png",
        output_path="output.mp4",
        position="bottom-right",
        size_percent=10.0,
        opacity=0.8,
        padding=20
    )
```

#### `services/video_clipper.py` (Updated)
Added logo overlay integration to VideoClipper class.

**New Method:**

```python
def add_logo(
    self,
    input_path: str,
    logo_path: str,
    output_path: str,
    position: str = "bottom-right",
    size_percent: float = 10.0,
    opacity: float = 0.8,
    padding: int = 20
) -> str:
    """Add brand logo overlay to a video."""
```

### 2. Backend API Endpoints

#### `POST /api/v1/upload-logo`
Upload a brand logo image.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: `file` (logo image file)

**Allowed File Types:**
- image/png
- image/jpeg
- image/jpg
- image/gif
- image/bmp

**Response:**

```json
{
  "success": true,
  "message": "Logo uploaded successfully",
  "logo_path": "uploads/logos/logo_<uuid>.png",
  "logo_info": {
    "valid": true,
    "width": 512,
    "height": 512,
    "format": "PNG",
    "path": "uploads/logos/logo_<uuid>.png"
  }
}
```

**Error Responses:**
- 400: Invalid file type or corrupt image
- 500: Server error during upload

---

#### `GET /api/v1/logos`
List all uploaded brand logos.

**Request:**
- Method: GET
- No parameters

**Response:**

```json
{
  "logos": [
    {
      "path": "uploads/logos/logo_<uuid>.png",
      "filename": "logo_<uuid>.png",
      "info": {
        "valid": true,
        "width": 512,
        "height": 512,
        "format": "PNG"
      }
    }
  ]
}
```

---

#### `DELETE /api/v1/logos/{logo_filename}`
Delete a brand logo.

**Request:**
- Method: DELETE
- Path Parameter: `logo_filename` (name of logo file)

**Response:**

```json
{
  "success": true,
  "message": "Logo deleted successfully"
}
```

**Error Responses:**
- 403: Invalid logo path (security check)
- 404: Logo not found

---

#### `POST /api/v1/clips/{clip_id}/apply-logo`
Apply logo overlay to a video clip.

**Request:**
- Method: POST
- Path Parameter: `clip_id` (video clip ID)
- Query Parameter: `logo_path` (path to logo file)
- Body:

```json
{
  "position": "bottom-right",
  "size_percent": 10.0,
  "opacity": 0.8,
  "padding": 20
}
```

**Request Model: ApplyLogoRequest**

```python
class ApplyLogoRequest(BaseModel):
    position: str = "bottom-right"
    size_percent: float = 10.0
    opacity: float = 0.8
    padding: int = 20
```

**Response:**

```json
{
  "job_id": "<uuid>",
  "status": "processing",
  "message": "Applying logo overlay..."
}
```

**Error Responses:**
- 400: Invalid logo file
- 404: Clip or logo not found

---

### 3. Frontend Components

#### Updated `frontend/src/pages/VideoEditor.jsx`

**New State Variables:**

```javascript
// Brand logo states
const [brandLogos, setBrandLogos] = useState([]);
const [selectedLogo, setSelectedLogo] = useState(null);
const [logoSettings, setLogoSettings] = useState({
  position: "bottom-right",
  size_percent: 10.0,
  opacity: 0.8,
  padding: 20,
});
```

**New Functions:**

1. `handleLogoUpload(event)`: Handle logo file upload
   - Validates file type and size
   - Uploads to backend
   - Updates logo list
   - Shows success message in chat

2. `handleApplyLogo()`: Apply selected logo to current clip
   - Validates logo and clip selection
   - Calls backend API
   - Tracks job progress
   - Updates chat with status

**UI Changes:**

- **Logo Upload Button**: Image icon in chat input area
- **File Input**: Hidden file input for logo selection
- **Chat Feedback**: Success/error messages in chat history
- **Help Text**: Updated with logo upload instructions

---

## 🎨 Position Presets

### Available Positions

| Position         | Description                  | Coordinates |
|------------------|------------------------------|-------------|
| `top-left`       | Top-left corner              | (2%, 2%)    |
| `top-right`      | Top-right corner             | (98%, 2%)   |
| `bottom-left`    | Bottom-left corner           | (2%, 98%)   |
| `bottom-right`   | Bottom-right corner (default)| (98%, 98%)  |
| `center`         | Center of video              | (50%, 50%)  |
| `top-center`     | Top edge, centered           | (50%, 2%)   |
| `bottom-center`  | Bottom edge, centered        | (50%, 98%)  |

### Position Calculation

Positions are calculated based on relative coordinates and logo dimensions:

```python
# Left alignment (2%)
x = padding

# Right alignment (98%)
x = video_width - logo_width - padding

# Center alignment (50%)
x = (video_width - logo_width) // 2
```

---

## ⚙️ Configuration Options

### Size Control

**Parameter:** `size_percent`
- **Type:** float
- **Range:** 1.0 - 50.0
- **Default:** 10.0
- **Description:** Logo width as percentage of video width
- **Example:** 10.0 = logo is 10% of video width

### Opacity Control

**Parameter:** `opacity`
- **Type:** float
- **Range:** 0.0 - 1.0
- **Default:** 0.8
- **Description:** Logo transparency level
- **Values:**
  - 0.0 = completely transparent
  - 0.5 = semi-transparent
  - 1.0 = fully opaque

### Padding Control

**Parameter:** `padding`
- **Type:** int
- **Range:** 0 - unlimited
- **Default:** 20
- **Unit:** pixels
- **Description:** Spacing from video edges

---

## 📝 Usage Examples

### Example 1: Upload and Apply Logo (Frontend)

```javascript
// User clicks image icon in chat
// Selects logo.png from file picker
// handleLogoUpload is triggered

const handleLogoUpload = async (event) => {
  const file = event.target.files?.[0];
  
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post('/api/v1/upload-logo', formData);
  
  // Logo is now available for use
  setSelectedLogo(response.data.logo_path);
};

// Apply logo to current clip
const handleApplyLogo = async () => {
  const response = await axios.post(
    `/api/v1/clips/${currentClip.id}/apply-logo`,
    {
      position: "bottom-right",
      size_percent: 12.0,
      opacity: 0.85,
      padding: 25,
    },
    {
      params: { logo_path: selectedLogo }
    }
  );
  
  // Poll job status
  pollJobStatus(response.data.job_id);
};
```

### Example 2: Direct Service Usage (Backend)

```python
from services.logo_overlay import LogoOverlay

overlay = LogoOverlay()

# Apply watermark to video
result = overlay.add_logo(
    video_path="short_1.mp4",
    logo_path="uploads/logos/brand_logo.png",
    output_path="short_1_branded.mp4",
    position="top-right",
    size_percent=8.0,
    opacity=0.7,
    padding=15
)

print(f"Branded video created: {result}")
```

### Example 3: Batch Logo Application

```python
from services.video_clipper import VideoClipper
from pathlib import Path

clipper = VideoClipper()
logo_path = "uploads/logos/company_logo.png"

# Apply logo to all clips
clips = Path("outputs").glob("short_*.mp4")
for clip in clips:
    output = clip.with_stem(f"{clip.stem}_branded")
    clipper.add_logo(
        input_path=str(clip),
        logo_path=logo_path,
        output_path=str(output),
        position="bottom-right",
        size_percent=10.0,
        opacity=0.8,
        padding=20
    )
```

---

## 🔄 Processing Flow

### Upload Flow

```
User selects image → Frontend validates (type, size) → 
POST /api/v1/upload-logo → Backend validates (format, corruption) → 
Save to uploads/logos/ → Return logo info → 
Update frontend state → Show success message
```

### Application Flow

```
User triggers apply → Frontend validates (logo, clip) → 
POST /api/v1/clips/{id}/apply-logo → Create background job → 
Return job_id → Background task starts → 
Load video and logo → Calculate position → 
Composite with MoviePy → Save output → 
Update database → Complete job → 
Frontend polls and updates
```

---

## 🛠️ Technical Implementation

### MoviePy Video Composition

```python
# Load video
video = VideoFileClip(video_path)

# Load and resize logo
logo = ImageClip(logo_path)
logo = logo.resized(width=logo_width)

# Set opacity
logo = logo.with_opacity(opacity)

# Position and duration
logo = logo.with_position((x, y))
logo = logo.with_duration(video.duration)

# Composite
final_video = CompositeVideoClip([video, logo])

# Export
final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')
```

### Background Task Pattern

```python
async def apply_logo_task(job_id, clip_id, video_path, logo_path, ...):
    try:
        # Update progress: Starting
        await progress_tracker.update_progress(job_id, "processing", 20, "Preparing...")
        
        # Apply logo
        clipper = VideoClipper()
        result = clipper.add_logo(...)
        
        # Update progress: Processing
        await progress_tracker.update_progress(job_id, "processing", 90, "Finalizing...")
        
        # Update database
        db = SessionLocal()
        short = db.query(Short).filter(Short.id == clip_id).first()
        short.file_path = result
        db.commit()
        
        # Complete
        await progress_tracker.update_progress(job_id, "completed", 100, "Done!")
        
    except Exception as e:
        await progress_tracker.update_progress(job_id, "failed", 0, str(e))
```

---

## 🧪 Testing

### Manual Testing

1. **Upload Logo**
   - Navigate to VideoEditor
   - Click image icon in chat input
   - Select a PNG logo file
   - Verify success message in chat
   - Check logo appears in logos list

2. **Apply Logo**
   - Select a video clip
   - Upload a logo (if not already done)
   - Use chat command or UI button to apply
   - Wait for background processing
   - Verify video has logo overlay

3. **Position Testing**
   - Apply logo with different positions
   - Verify logo appears in correct location
   - Check padding is respected

4. **Size and Opacity Testing**
   - Apply with size_percent = 5, 10, 15
   - Apply with opacity = 0.5, 0.8, 1.0
   - Verify visual appearance

### Automated Testing (Example)

```python
import pytest
from services.logo_overlay import LogoOverlay
from pathlib import Path

def test_logo_validation():
    overlay = LogoOverlay()
    
    # Valid PNG
    result = overlay.validate_logo_image("test_logo.png")
    assert result['valid'] == True
    assert 'width' in result
    assert 'height' in result
    
    # Invalid file
    result = overlay.validate_logo_image("nonexistent.png")
    assert result['valid'] == False
    assert 'error' in result

def test_logo_overlay():
    overlay = LogoOverlay()
    
    output = overlay.add_logo(
        video_path="test_video.mp4",
        logo_path="test_logo.png",
        output_path="test_output.mp4",
        position="bottom-right",
        size_percent=10.0,
        opacity=0.8,
        padding=20
    )
    
    assert Path(output).exists()
    assert Path(output).stat().st_size > 0
```

---

## 📊 File Structure

```
VLLM/
├── services/
│   ├── logo_overlay.py          # Core logo overlay service
│   ├── video_clipper.py          # Updated with add_logo method
│   └── __pycache__/
│
├── frontend/
│   └── src/
│       └── pages/
│           └── VideoEditor.jsx   # Updated with logo upload UI
│
├── uploads/
│   └── logos/                    # Logo storage directory
│       ├── logo_<uuid>.png
│       └── ...
│
├── main.py                       # Backend API endpoints
└── BRAND_LOGO_OVERLAY_GUIDE.md   # This documentation
```

---

## 🚀 Best Practices

### Logo Image Recommendations

1. **Format**: Use PNG with transparency for best results
2. **Size**: 512x512 or 1024x1024 pixels (square aspect ratio)
3. **File Size**: Keep under 1MB for faster uploads
4. **Color**: High contrast with video background
5. **Transparency**: Use semi-transparent logos (opacity 0.7-0.9)

### Position Guidelines

1. **Bottom-right**: Standard watermark position (default)
2. **Top-right**: Alternative for bottom-heavy content
3. **Bottom-center**: Good for centered branding
4. **Avoid center**: Don't obstruct main content

### Size Guidelines

1. **Small (5-8%)**: Subtle watermark
2. **Medium (10-12%)**: Standard branding
3. **Large (15-20%)**: Prominent logo (use sparingly)

### Performance Tips

1. **Optimize logos**: Compress images before upload
2. **Batch processing**: Apply logos to multiple clips in background
3. **Reuse logos**: Store frequently used logos for quick access
4. **Cache**: Frontend caches logo list to reduce API calls

---

## 🐛 Troubleshooting

### Common Issues

**Issue:** "Invalid file type" error
- **Cause:** Unsupported image format
- **Solution:** Convert to PNG, JPG, GIF, or BMP

**Issue:** "Logo file size must be less than 5MB"
- **Cause:** File too large
- **Solution:** Compress image using tools like TinyPNG

**Issue:** "Failed to load image"
- **Cause:** Corrupt image file
- **Solution:** Re-save image in a standard editor

**Issue:** Logo appears blurry
- **Cause:** Logo too small, scaled up
- **Solution:** Use higher resolution logo (min 512x512)

**Issue:** Logo overlay takes too long
- **Cause:** Large video file + high-resolution logo
- **Solution:** Optimize video, use smaller logo

### Debug Logging

Enable debug logging to troubleshoot:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

overlay = LogoOverlay()
# Detailed logs will show processing steps
```

---

## 📈 Future Enhancements

### Planned Features

1. **Animation**
   - Fade in/out effects
   - Slide-in transitions
   - Pulsing animation

2. **Advanced Positioning**
   - Custom X/Y coordinates
   - Multiple logos per video
   - Time-based logo changes

3. **Effects**
   - Drop shadow
   - Glow effect
   - Border/outline

4. **Templates**
   - Preset logo configurations
   - Save custom presets
   - Apply preset to all clips

5. **Logo Library**
   - Logo management UI
   - Preview thumbnails
   - Organize by tags/categories

---

## 📚 Related Documentation

- [Caption System Documentation](IMPLEMENTATION_PLAN.md) - Similar architecture
- [Video Processing Guide](README.md) - Video processing overview
- [API Reference](main.py) - Complete API endpoints
- [Frontend Components](frontend/README.md) - UI components

---

## 🤝 Contributing

When extending this feature:

1. Follow existing code patterns (similar to caption system)
2. Add error handling for all user inputs
3. Update this documentation
4. Add unit tests for new functionality
5. Maintain backward compatibility

---

## 📄 License

Same as project license.

---

## 👥 Support

For issues or questions:
1. Check troubleshooting section above
2. Review backend logs for errors
3. Test with simple PNG logo first
4. Verify video file is valid MP4

---

**Last Updated:** 2024
**Version:** 1.0.0
**Status:** ✅ Production Ready
