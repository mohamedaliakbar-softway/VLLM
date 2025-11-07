# Video Shorts Generator - AI-Powered SaaS

An AI-powered SaaS product that helps marketing teams create engaging 15-30 second shorts from long-form YouTube videos (15-30 minutes). The system uses Google's Gemini AI to automatically identify the most engaging and marketing-effective segments, then generates optimized shorts for platforms like YouTube Shorts, Instagram Reels, Facebook, LinkedIn, and WhatsApp.

## Features

- 🎥 **YouTube Video Processing**: Direct YouTube URL input (15-30 min videos)
- 🤖 **AI-Powered Analysis**: Uses Gemini 2.5 Flash to identify engaging highlights
- ✂️ **Smart Clipping**: Automatically creates 15-30 second shorts from best segments
- 📊 **Engagement Scoring**: Ranks highlights by marketing effectiveness
- 🎯 **Marketing Optimized**: Focuses on segments that drive demo bookings and purchases
- 📱 **Multi-Platform Ready**: Generates shorts suitable for all major social platforms
- 🔄 **Multiple Highlights**: Can generate up to 3 different highlight shorts per video

## How It Works

1. **Input**: Provide a YouTube URL (15-30 minute video)
2. **Validation**: System validates video duration and gets metadata
3. **AI Analysis**: Gemini AI analyzes the YouTube video directly (no download needed) to find:
   - Most engaging segments
   - Product demonstrations
   - Customer testimonials
   - Value propositions
   - High-energy moments
4. **Highlight Detection**: Identifies up to 3 best segments (15-30 seconds each) with engagement scores
5. **Video Download**: Downloads video only for the segments that will be clipped
6. **Short Generation**: Creates optimized video clips ready for marketing
7. **Output**: Returns downloadable shorts with engagement scores and CTAs

## Installation

### Prerequisites

- Python 3.9+
- Gemini API key ([Get one here](https://ai.google.dev/gemini-api/docs/video-understanding))
- FFmpeg (for video processing)

### Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd VLLM
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install FFmpeg**:
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

4. **Configure environment**:
```bash
cp .env.example .env
```

5. **Edit `.env` file** and add your Gemini API key:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage

### Verify Setup

Before starting, verify your setup:

```bash
python check_setup.py
```

This will check:
- Python version
- Required dependencies
- FFmpeg installation
- Environment configuration
- Required directories

### Start the Server

**Option 1: Using the startup script (recommended)**
```bash
./start.sh
```

**Option 2: Manual start**
```bash
python main.py
```

**Option 3: Using uvicorn directly**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Generate Shorts

**Endpoint**: `POST /api/v1/generate-shorts`

**Request**:
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "max_shorts": 3
}
```

**Response**:
```json
{
  "job_id": "uuid",
  "status": "completed",
  "video_title": "Video Title",
  "video_duration": 1800,
  "shorts": [
    {
      "short_id": 1,
      "filename": "video_id_short_1.mp4",
      "start_time": "05:23",
      "end_time": "05:48",
      "duration_seconds": 25,
      "engagement_score": 9,
      "marketing_effectiveness": "Shows product demo with clear value proposition",
      "suggested_cta": "Book a demo today!",
      "download_url": "/api/v1/download/video_id_short_1.mp4"
    }
  ],
  "message": "Successfully generated 3 marketing shorts"
}
```

### Download Shorts

**Endpoint**: `GET /api/v1/download/{filename}`

Download any generated short video file.

### Example with cURL

```bash
curl -X POST "http://localhost:8000/api/v1/generate-shorts" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "max_shorts": 3
  }'
```

### Example with Python

**Using the provided example script:**
```bash
python example_usage.py
```

**Or programmatically:**
```python
import requests

url = "http://localhost:8000/api/v1/generate-shorts"
payload = {
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "max_shorts": 3
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Generated {len(result['shorts'])} shorts")
for short in result['shorts']:
    print(f"Short {short['short_id']}: {short['start_time']} - {short['end_time']}")
    print(f"Engagement Score: {short['engagement_score']}/10")
    print(f"Download: http://localhost:8000{short['download_url']}")
```

## Architecture

```
┌─────────────────┐
│  YouTube URL    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ YouTube Processor│  Downloads video
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Gemini Analyzer │  AI analysis for highlights
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Video Clipper  │  Creates shorts
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Marketing      │  Ready-to-use shorts
│  Shorts Output  │
└─────────────────┘
```

## Configuration

Edit `.env` file to customize:

- `MAX_VIDEO_DURATION`: Maximum input video duration (default: 1800s / 30 min)
- `MIN_VIDEO_DURATION`: Minimum input video duration (default: 900s / 15 min)
- `SHORT_DURATION_MIN`: Minimum short duration (default: 15s)
- `SHORT_DURATION_MAX`: Maximum short duration (default: 30s)
- `MAX_HIGHLIGHTS`: Maximum number of shorts to generate (default: 3)

## Project Structure

```
VLLM/
├── main.py                 # FastAPI application
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── check_setup.py         # Setup verification script
├── start.sh               # Startup script
├── example_usage.py       # Example API usage
├── services/
│   ├── __init__.py
│   ├── youtube_processor.py  # YouTube downloader
│   ├── gemini_analyzer.py    # AI video analysis
│   └── video_clipper.py      # Video clipping service
├── temp/                   # Temporary video storage
└── output/                 # Generated shorts storage
```

## How Highlight Detection Works

The Gemini AI analyzes videos looking for:

1. **Attention Hooks**: First 3 seconds that capture interest
2. **Product Features**: Clear demonstrations of key features
3. **Value Propositions**: Benefits and outcomes shown
4. **Social Proof**: Testimonials, reviews, case studies
5. **Emotional Appeal**: High-energy moments, transformations
6. **Visual Quality**: Clear visuals, good lighting, professional
7. **Audio Quality**: Clear speech, minimal background noise
8. **CTA Opportunities**: Natural places for call-to-action

Each segment is scored 1-10 for engagement and marketing effectiveness.

## Production Considerations

For production deployment, consider:

1. **Storage**: Use cloud storage (S3, GCS) instead of local filesystem
2. **Queue System**: Use Celery or similar for async job processing
3. **Database**: Store job status and metadata in a database
4. **Caching**: Cache video analysis results
5. **Rate Limiting**: Implement API rate limiting
6. **Authentication**: Add API key or OAuth authentication
7. **Monitoring**: Add logging and monitoring (Sentry, DataDog)
8. **CDN**: Serve video files via CDN
9. **Scaling**: Use container orchestration (Kubernetes, Docker Swarm)

## Limitations

- Maximum input video: 30 minutes
- Minimum input video: 15 minutes
- Short duration: 15-30 seconds
- Maximum shorts per video: 3 (configurable)
- Requires Gemini API key with video understanding access

## Troubleshooting

### Video download fails
- Check YouTube URL is valid
- Ensure video is publicly accessible
- Verify network connection

### Gemini API errors
- Verify API key is correct
- Check API quota/limits
- Ensure video format is supported

### Video processing errors
- Ensure FFmpeg is installed
- Check available disk space
- Verify video file is not corrupted

## License

MIT License

## Support

For issues and questions, please open an issue on the repository.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

