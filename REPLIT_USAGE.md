# Using Video Shorts Generator on Replit

## Quick Start

Your Video Shorts Generator API is now running! 🎉

### Access the API Documentation
Visit the **Webview** tab to see your API's interactive documentation at:
- **Swagger UI**: `/docs` - Interactive API testing interface
- **ReDoc**: `/redoc` - Beautiful API documentation

### API Endpoints

#### 1. Generate Shorts from YouTube Video
```bash
POST /api/v1/generate-shorts
```

**Example Request:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "max_shorts": 3,
  "platform": "youtube_shorts"
}
```

**Platform Options:**
- `youtube_shorts` - 9:16 vertical format
- `instagram_reels` - 9:16 vertical format
- `facebook` - 9:16 vertical format
- `linkedin` - 9:16 vertical format
- `whatsapp` - 9:16 vertical format
- `square` - 1:1 square format
- `default` - 9:16 vertical format (default)

**Example Response:**
```json
{
  "job_id": "uuid-here",
  "status": "completed",
  "video_title": "Your Video Title",
  "video_duration": 1800,
  "shorts": [
    {
      "short_id": 1,
      "filename": "video_id_short_1.mp4",
      "start_time": "05:23",
      "end_time": "05:48",
      "duration_seconds": 25,
      "engagement_score": 9,
      "marketing_effectiveness": "Shows product demo with clear value",
      "suggested_cta": "Book a demo today!",
      "download_url": "/api/v1/download/video_id_short_1.mp4"
    }
  ],
  "message": "Successfully generated 3 marketing shorts"
}
```

#### 2. Download a Generated Short
```bash
GET /api/v1/download/{filename}
```

#### 3. Check Job Status
```bash
GET /api/v1/job/{job_id}
```

#### 4. Delete a Short
```bash
DELETE /api/v1/shorts/{filename}
```

### Testing with cURL

You can test the API using cURL in the Shell:

```bash
curl -X POST "http://localhost:5000/api/v1/generate-shorts" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
    "max_shorts": 2,
    "platform": "instagram_reels"
  }'
```

### Video Requirements
- **Duration**: 3-30 minutes (configurable)
- **Format**: Any YouTube-supported video format
- **Access**: Video must be publicly accessible
- **Content**: Works best with talking head videos, product demos, tutorials

### How the AI Analysis Works

The Gemini AI analyzes your video looking for:
1. **Attention Hooks** - Compelling opening moments
2. **Product Features** - Clear demonstrations
3. **Value Propositions** - Benefits and outcomes
4. **Social Proof** - Testimonials and case studies
5. **Emotional Appeal** - High-energy transformations
6. **Visual Quality** - Clear visuals and good lighting
7. **Audio Quality** - Clear speech, minimal noise
8. **CTA Opportunities** - Natural call-to-action moments

Each segment receives an engagement score (1-10) for marketing effectiveness.

### Configuration

All settings are in `config.py`:
- Max video duration: 30 minutes
- Min video duration: 3 minutes
- Short duration: 15-30 seconds
- Max highlights: 3 per video

### Storage

Generated videos are stored in:
- `./temp/` - Temporary downloaded videos (auto-cleanup)
- `./output/` - Generated shorts (persist until deleted)

### Tips for Best Results

1. **Choose Videos Wisely**: Marketing content, product demos, and tutorials work best
2. **Optimal Length**: 15-20 minute videos provide enough content for good highlights
3. **Clear Audio**: Videos with clear speech get better analysis
4. **Visual Quality**: Well-lit, professional videos score higher
5. **Platform Selection**: Choose the right format for your target platform

### Need Help?

- Check `/docs` for interactive API documentation
- View `/health` for system status
- Read the main README.md for detailed information
