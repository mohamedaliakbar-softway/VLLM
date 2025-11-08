# YouTube Data API - Quick Reference Guide

## Setup (5 minutes)

### 1. Get API Key
- Go to https://console.cloud.google.com/
- Enable "YouTube Data API v3"
- Create an API key

### 2. Configure
```bash
# Add to .env file
YOUTUBE_API_KEY=your_api_key_here
```

### 3. Install
```bash
pip install google-api-python-client>=2.100.0
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/youtube/video/statistics/{id}` | GET | Get video stats (views, likes, comments) |
| `/api/v1/youtube/channel/statistics/{id}` | GET | Get channel stats (subscribers, views) |
| `/api/v1/youtube/video/comments/{id}` | GET | Get top comments |
| `/api/v1/youtube/search` | GET | Search videos |
| `/api/v1/youtube/trending` | GET | Get trending videos |
| `/api/v1/youtube/related/{id}` | GET | Get related videos |
| `/api/v1/youtube/playlist/{id}` | GET | Get playlist videos |
| `/api/v1/youtube/categories` | GET | Get video categories |

---

## Quick Examples

### Get Video Stats
```bash
curl "http://localhost:8000/api/v1/youtube/video/statistics/dQw4w9WgXcQ"
```

Response includes: title, views, likes, comments, duration, channel info, etc.

### Get Channel Stats
```bash
curl "http://localhost:8000/api/v1/youtube/channel/statistics/UC4JX40jDee_NI8pTrqCdO1A"
```

Response includes: subscriber count, video count, total views, etc.

### Search Videos
```bash
curl "http://localhost:8000/api/v1/youtube/search?query=machine+learning&max_results=5&order=date"
```

### Get Comments
```bash
curl "http://localhost:8000/api/v1/youtube/video/comments/dQw4w9WgXcQ?max_results=10"
```

### Get Trending
```bash
curl "http://localhost:8000/api/v1/youtube/trending?region_code=US&max_results=10"
```

### Get Related Videos
```bash
curl "http://localhost:8000/api/v1/youtube/related/dQw4w9WgXcQ?max_results=10"
```

---

## Python Usage

```python
from services.youtube_data_api import YouTubeDataAPI

# Initialize
youtube_api = YouTubeDataAPI()

# Get video statistics
stats = youtube_api.get_video_statistics("dQw4w9WgXcQ")
print(f"Views: {stats['view_count']:,}")
print(f"Likes: {stats['like_count']:,}")

# Search videos
videos = youtube_api.search_videos("machine learning", max_results=10)
for video in videos:
    print(video['title'])

# Get channel info
channel = youtube_api.get_channel_statistics("UC4JX40jDee_NI8pTrqCdO1A")
print(f"Subscribers: {channel['subscriber_count']:,}")

# Get comments
comments = youtube_api.get_video_comments("dQw4w9WgXcQ", max_results=20)
for comment in comments:
    print(f"{comment['author']}: {comment['text']}")

# Get trending
trending = youtube_api.get_trending_videos(region_code="US")
for video in trending:
    print(f"{video['title']} - {video['view_count']:,} views")

# Get related videos
related = youtube_api.get_related_videos("dQw4w9WgXcQ")
for video in related:
    print(video['title'])

# Get playlist videos
playlist = youtube_api.get_playlist_videos("PLxxxxx")
for video in playlist:
    print(video['title'])

# Get categories
categories = youtube_api.get_video_categories(region_code="US")
for cat in categories:
    print(f"{cat['id']}: {cat['title']}")
```

---

## Common Parameters

### max_results
- Range: 1-50 (or 1-100 for comments)
- Default: 25
- API automatically limits to max available

### order
- `relevance` (default)
- `date` (newest first)
- `rating` (highest rated)
- `viewCount` (most viewed)

### region_code
- 2-letter country code: "US", "GB", "IN", "DE", etc.
- Used for trending and search filtering

### published_after / published_before
- ISO 8601 format: "2024-01-01T00:00:00Z"
- Optional filters for search

---

## Response Structure

### Video Statistics
```json
{
  "video_id": "abc123",
  "title": "Video Title",
  "view_count": 1000000,
  "like_count": 50000,
  "comment_count": 10000,
  "duration": 212,
  "channel_title": "Channel Name",
  "upload_date": "2024-01-15T10:00:00Z"
}
```

### Channel Statistics
```json
{
  "channel_id": "UCxxxxx",
  "title": "Channel Name",
  "subscriber_count": 1000000,
  "video_count": 500,
  "total_views": 100000000
}
```

### Comments
```json
{
  "author": "John Doe",
  "text": "Great video!",
  "likes": 1500,
  "published_at": "2024-01-15T10:00:00Z",
  "reply_count": 50
}
```

---

## URL Formats

Videos accept multiple formats:
- Video ID: `dQw4w9WgXcQ`
- Full URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- Short URL: `https://youtu.be/dQw4w9WgXcQ`
- Embed URL: `https://www.youtube.com/embed/dQw4w9WgXcQ`

Channels accept:
- Channel ID: `UC4JX40jDee_NI8pTrqCdO1A`
- Channel URL: `https://www.youtube.com/channel/UC4JX40jDee_NI8pTrqCdO1A`
- Custom URL: `https://www.youtube.com/@rickastley`

---

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request (invalid parameters) |
| 404 | Video/Channel not found |
| 401 | Invalid API key |
| 403 | API quota exceeded |
| 500 | Server error |

---

## Rate Limits

**Free tier**: 10,000 quota units/day

**Quota costs**:
- `videos().list()`: 1 unit
- `channels().list()`: 1 unit
- `search().list()`: 100 units
- `commentThreads().list()`: 1 unit
- `playlistItems().list()`: 1 unit

Example:
- 10 video stats queries = 10 units
- 1 search query = 100 units
- 100 comment queries = 100 units
- Total = 210 units used

---

## Integration Examples

### Analyze Video Engagement
```python
from services.youtube_data_api import YouTubeDataAPI

youtube_api = YouTubeDataAPI()
stats = youtube_api.get_video_statistics("dQw4w9WgXcQ")

engagement_rate = (stats['like_count'] / stats['view_count'] * 100)
print(f"Engagement: {engagement_rate:.2f}%")

comments_per_view = (stats['comment_count'] / stats['view_count'] * 100)
print(f"Comment rate: {comments_per_view:.3f}%")
```

### Find Popular Topics
```python
youtube_api = YouTubeDataAPI()

# Search trending topics
trending = youtube_api.get_trending_videos(region_code="US", max_results=50)

# Group by channel
channels = {}
for video in trending:
    if video['channel_id'] not in channels:
        channels[video['channel_id']] = []
    channels[video['channel_id']].append(video)

# Find most active channels in trending
for channel_id, videos in sorted(channels.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
    print(f"Channel {channel_id}: {len(videos)} trending videos")
```

### Content Research
```python
youtube_api = YouTubeDataAPI()

# Search for video ideas
search_terms = ["AI", "machine learning", "deep learning"]

for term in search_terms:
    videos = youtube_api.search_videos(term, max_results=25, order="viewCount")
    
    total_views = sum(v['view_count'] for v in videos)
    avg_views = total_views / len(videos)
    
    print(f"{term}: Avg {avg_views:,.0f} views")
```

---

## Troubleshooting

### "YouTube API not configured"
- Check `.env` has `YOUTUBE_API_KEY`
- Restart the server
- Verify API key is valid

### "quotaExceeded"
- Check daily quota at Google Cloud Console
- Reduce API calls or upgrade quota
- Use caching to reduce repeated calls

### "Video not found"
- Verify video ID is correct
- Check if video is deleted or private
- Some videos may be restricted by region

### "HTTP 403 - Forbidden"
- API key may be invalid
- Check API is enabled in Google Cloud Console
- Verify key permissions

---

## Run Examples

```bash
# Make sure server is running
python main.py

# In another terminal, run examples
python youtube_data_api_examples.py
```

---

## Next Steps

1. ✅ Get YouTube API key
2. ✅ Add to `.env`
3. ✅ Install dependencies
4. ✅ Run server
5. ✅ Test endpoints
6. ✅ Integrate with your application

See `YOUTUBE_DATA_API.md` for detailed documentation.
