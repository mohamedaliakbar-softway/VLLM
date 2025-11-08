# Brand Logo Overlay - Quick Reference

## 🚀 Quick Start

### 1. Upload Logo (Frontend)
```javascript
// Click image icon (🖼️) in chat input
// Select PNG/JPG/GIF/BMP file (max 5MB)
// Logo auto-uploads and appears in chat confirmation
```

### 2. Apply Logo (Frontend)
```javascript
// Select a video clip
// Say in chat: "Apply logo" or use UI button
// Logo applies in background with progress tracking
```

### 3. Direct Usage (Backend)
```python
from services.logo_overlay import LogoOverlay

overlay = LogoOverlay()
overlay.add_logo(
    video_path="input.mp4",
    logo_path="logo.png",
    output_path="output.mp4",
    position="bottom-right",  # See positions below
    size_percent=10.0,         # 1-50
    opacity=0.8,               # 0.0-1.0
    padding=20                 # pixels
)
```

---

## 📍 Position Presets

| Position | Location | Best For |
|----------|----------|----------|
| `bottom-right` | ↘️ Bottom-right corner (DEFAULT) | Standard watermark |
| `bottom-left` | ↙️ Bottom-left corner | Alternative watermark |
| `top-right` | ↗️ Top-right corner | Top branding |
| `top-left` | ↖️ Top-left corner | Alternative top |
| `bottom-center` | ⬇️ Bottom center | Centered branding |
| `top-center` | ⬆️ Top center | Header branding |
| `center` | ⏺️ Center of video | Prominent logo (use sparingly) |

---

## ⚙️ Parameter Reference

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `position` | str | See above | `"bottom-right"` | Logo placement |
| `size_percent` | float | 1.0-50.0 | 10.0 | Logo width (% of video) |
| `opacity` | float | 0.0-1.0 | 0.8 | Transparency (0=invisible, 1=solid) |
| `padding` | int | 0+ | 20 | Distance from edges (pixels) |

---

## 🌐 API Endpoints

### Upload Logo
```http
POST /api/v1/upload-logo
Content-Type: multipart/form-data

Body: file=<logo-image>

Response:
{
  "success": true,
  "logo_path": "uploads/logos/logo_<uuid>.png",
  "logo_info": { "width": 512, "height": 512, ... }
}
```

### List Logos
```http
GET /api/v1/logos

Response:
{
  "logos": [
    { "path": "...", "filename": "...", "info": {...} }
  ]
}
```

### Delete Logo
```http
DELETE /api/v1/logos/{filename}

Response:
{ "success": true, "message": "Logo deleted" }
```

### Apply Logo to Clip
```http
POST /api/v1/clips/{clip_id}/apply-logo?logo_path=<path>

Body:
{
  "position": "bottom-right",
  "size_percent": 10.0,
  "opacity": 0.8,
  "padding": 20
}

Response:
{
  "job_id": "<uuid>",
  "status": "processing",
  "message": "Applying logo overlay..."
}
```

---

## 💡 Common Use Cases

### Subtle Watermark
```python
overlay.add_logo(
    ...,
    position="bottom-right",
    size_percent=6.0,
    opacity=0.6,
    padding=15
)
```

### Prominent Branding
```python
overlay.add_logo(
    ...,
    position="top-center",
    size_percent=15.0,
    opacity=0.9,
    padding=30
)
```

### Corner Logo (Transparent)
```python
overlay.add_logo(
    ...,
    position="top-right",
    size_percent=8.0,
    opacity=0.75,
    padding=20
)
```

---

## 📋 Supported Image Formats

✅ PNG (recommended for transparency)  
✅ JPG/JPEG  
✅ GIF  
✅ BMP  

**Best Practice:** Use PNG with transparent background

---

## ⚡ File Size Limits

- **Frontend validation:** 5MB max
- **Backend:** No hard limit (reasonable sizes recommended)
- **Recommendation:** Keep logos under 1MB

---

## 🎨 Logo Design Tips

1. **Resolution:** 512x512 or 1024x1024 pixels
2. **Format:** PNG with alpha channel
3. **Contrast:** Ensure visibility on video background
4. **Simplicity:** Clean, simple designs work best
5. **File size:** Compress to < 500KB

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Invalid file type" | Use PNG, JPG, GIF, or BMP |
| "File too large" | Compress image (< 5MB) |
| Logo appears blurry | Use higher resolution (min 512x512) |
| Processing takes long | Use smaller logo file |
| Logo not visible | Increase opacity or size_percent |

---

## 📁 File Locations

```
VLLM/
├── services/logo_overlay.py      # Logo service
├── services/video_clipper.py     # Integration
├── main.py                       # API endpoints
├── frontend/src/pages/VideoEditor.jsx  # UI
└── uploads/logos/                # Logo storage
```

---

## 🧪 Quick Test

```python
# Test script
from services.logo_overlay import LogoOverlay

overlay = LogoOverlay()

# Validate logo
validation = overlay.validate_logo_image("test_logo.png")
print(f"Valid: {validation['valid']}")
print(f"Size: {validation.get('width')}x{validation.get('height')}")

# Apply logo
if validation['valid']:
    result = overlay.add_logo(
        video_path="test.mp4",
        logo_path="test_logo.png",
        output_path="test_with_logo.mp4",
        position="bottom-right",
        size_percent=10.0,
        opacity=0.8,
        padding=20
    )
    print(f"Output: {result}")
```

---

## 📖 Full Documentation

See [BRAND_LOGO_OVERLAY_GUIDE.md](BRAND_LOGO_OVERLAY_GUIDE.md) for complete documentation.

---

**Version:** 1.0.0  
**Last Updated:** 2024  
**Status:** ✅ Ready to Use
