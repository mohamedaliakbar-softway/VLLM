# Video Shorts Generator - Replit Setup

## Overview
An AI-powered SaaS application that automatically creates engaging 15-30 second marketing shorts from long-form YouTube videos (15-30 minutes). Uses Google's Gemini AI to identify the most compelling segments.

## Project Type
- **Backend**: FastAPI REST API (Python 3.11)
- **Port**: 5000
- **AI Service**: Google Gemini 2.5 Flash for video analysis
- **Video Processing**: FFmpeg, yt-dlp, moviepy

## Key Features
- Direct YouTube URL processing (no manual download needed for analysis)
- AI-powered highlight detection with engagement scoring
- Automatic video clipping for multiple social platforms
- Supports YouTube Shorts, Instagram Reels, Facebook, LinkedIn, WhatsApp formats
- Generates up to 3 optimized shorts per video

## Setup Status
✅ Python 3.11 installed
✅ FFmpeg installed (system dependency)
✅ All Python dependencies installed via pip
✅ Gemini API key configured in Replit Secrets
✅ Port configured to 5000 for Replit webview
✅ Workflow configured to run FastAPI server

## API Endpoints
- `GET /` - Service status
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation
- `POST /api/v1/generate-shorts` - Generate shorts from YouTube URL
- `GET /api/v1/download/{filename}` - Download generated short
- `GET /api/v1/job/{job_id}` - Get job status
- `DELETE /api/v1/shorts/{filename}` - Delete a short

## Environment Configuration
The application uses Replit Secrets for the Gemini API key:
- `GEMINI_API_KEY` - Required for AI video analysis

Other settings are configured in `config.py` with sensible defaults:
- Max video duration: 30 minutes
- Min video duration: 3 minutes
- Short duration: 15-30 seconds
- Max highlights per video: 3

## Project Structure
```
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── services/                  # Service layer
│   ├── youtube_processor.py  # YouTube video download
│   ├── gemini_analyzer.py    # AI video analysis
│   ├── video_clipper.py      # Video clipping
│   └── smart_cropper.py      # Smart video cropping
├── temp/                      # Temporary video storage (gitignored)
└── output/                    # Generated shorts (gitignored)
```

## How It Works
1. User provides YouTube URL
2. System validates video duration (15-30 min)
3. Gemini AI analyzes video directly via URL
4. AI identifies top 3 engaging segments with scores
5. Video is downloaded only for selected segments
6. Shorts are created and optimized for target platforms
7. Files are made available for download

## Technology Stack
**Frontend:**
- React 19 with Vite
- React Router for navigation
- Axios for API calls
- Lucide React for icons
- Custom CSS with modern dark theme

**Backend:**
- FastAPI (Python 3.11)
- Google Gemini AI for video analysis
- yt-dlp for YouTube downloads
- FFmpeg for video processing
- MoviePy for video editing
- Server-Sent Events (SSE) for real-time updates

## Application Flow
1. **Landing Page**: User enters YouTube URL
2. **Video Processing**: Backend downloads and analyzes video with Gemini AI
3. **Editor Interface**: Split-screen with:
   - Left: AI chat interface for conversational editing
   - Right: Generated shorts preview and management
4. **Editing Features**: Add captions, voice dubbing, timing adjustments
5. **Publishing**: One-click share to multiple platforms with AI-generated copy

## Recent Changes
- November 8, 2025: Complete redesign based on HighlightAI reference images
  - **Landing Page Redesign:**
    - Added professional navigation bar with HighlightAI branding
    - Navigation links: Features, How It Works, Pricing, Sign In, Get Started
    - Hero section with "AI-Powered Video Highlights" badge
    - Title "Transform Videos into" with gradient block
    - Single URL input field with "Generate" button
    - "No credit card required • Free trial available" notice
    - Three feature badges: AI-Powered Detection, 2-Minute Processing, Multi-Platform Export
    - Clean dark theme matching reference design
  
  - **Video Editor Three-Panel Layout:**
    - Left panel (280px): Assistant chat with Gemini
      - Quick action buttons (Use example video, Add live captions, Dub in Kannada, etc.)
      - Chat history with user and assistant messages
      - Message input with send button
    - Center panel: Video preview with playback controls
      - Play/pause overlay button
      - Clip label showing current clip number
      - Bottom timeline section with all clips
      - Timeline controls: Add Clip, Move Up, Move Down
      - Clip selection and reordering functionality
    - Right panel (350px): Properties panel
      - Clip title editing
      - Time range display (start/end times)
      - Duration slider with presets (15s, 30s, 60s)
      - Trim controls (Trim Start, Trim End)
      - Order display (clip position in timeline)
  
  - **State Management:**
    - Proper state synchronization between panels
    - Properties panel reflects selected clip
    - Edits persist back to clips array
    - Timeline updates in real-time with changes
    - Add/remove/reorder clips with full state management

- November 7, 2025: Full application built
  - Created React + Vite frontend with landing page and editor
  - Implemented AI conversation interface with chat UI
  - Added Server-Sent Events for real-time progress updates
  - Split backend (port 8000) and frontend (port 5000) architecture
  - Created beautiful dark-themed UI with gradient effects
  - Set up dual-server workflow (backend + frontend)
  - Configured proper CORS and API proxying
  - Added progress tracking infrastructure for live updates

## Future Enhancements
The following features are planned for future releases:
- Real-time video captioning/subtitle generation
- Multi-language voice dubbing (Kannada, Hindi, etc.) with AI TTS
- Advanced video editing via conversational AI
- Social media OAuth integrations (YouTube, Instagram, Facebook, LinkedIn, TikTok)
- AI-generated platform-specific marketing copy
- Video preview player in the editor
- Batch processing for multiple videos
- Analytics dashboard for engagement metrics
