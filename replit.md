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

## Recent Changes
- November 7, 2025: Initial Replit setup
  - Configured for port 5000 (was 8000)
  - Set up workflow for FastAPI server
  - Installed Python 3.11 and all dependencies
  - Installed FFmpeg system dependency
  - Configured Gemini API key via Replit Secrets
