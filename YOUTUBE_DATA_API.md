# YouTube Data API Implementation

This document describes the YouTube Data API implementation integrated into the Video Shorts Generator.

## Overview

The YouTube Data API service provides comprehensive access to YouTube metadata, statistics, and content information without needing to download videos. This includes:

- **Video Statistics**: Views, likes, comments, duration, channel info
- **Channel Statistics**: Subscriber count, total views, video count
- **Comments**: Top comments with engagement metrics
- **Search**: Video search with filtering
- **Trending**: Popular videos by region
- **Related Videos**: Videos related to a specific video
- **Playlist**: Videos within a playlist
- **Categories**: Available video categories

## Setup

### 1. Get YouTube Data API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the "YouTube Data API v3"
4. Create an API key (Credentials → Create Credentials → API Key)
5. Add the key to your `.env` file:

```bash
YOUTUBE_API_KEY=your_api_key_here
```

### 2. Install Dependencies

The required dependency is already in `requirements.txt`:

```bash
pip install google-api-python-client>=2.100.0
```

## API Endpoints

### Video Statistics

Get detailed statistics for a YouTube video.

**Endpoint:** `GET /api/v1/youtube/video/statistics/{video_id_or_url}`

**Parameters:**
- `video_id_or_url` (string, required): YouTube video ID or full URL

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/youtube/video/statistics/dQw4w9WgXcQ"
```

or with URL:
```bash
curl "http://localhost:8000/api/v1/youtube/video/statistics/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DdQw4w9WgXcQ"
```

**Example Response:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up (Official Video)",
  "description": "Rick Astley's official music video...",
  "duration": 212,
  "duration_formatted": "03:32",
  "view_count": 1400000000,
  "like_count": 12000000,
  "comment_count": 1500000,
  "upload_date": "2009-10-25T06:57:33Z",
  "channel_id": "UC4JX40jDee_NI8pTrqCdO1A",
  "channel_title": "Rick Astley",
  "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
  "tags": ["music", "video"],
  "category_id": "10",
  "definition": "hd",
  "caption": true,
  "licensed_content": true
}
```

---

### Channel Statistics

Get detailed statistics for a YouTube channel.

**Endpoint:** `GET /api/v1/youtube/channel/statistics/{channel_id_or_url}`

**Parameters:**
- `channel_id_or_url` (string, required): Channel ID or channel URL

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/youtube/channel/statistics/UC4JX40jDee_NI8pTrqCdO1A"
```

**Example Response:**
```json
{
  "channel_id": "UC4JX40jDee_NI8pTrqCdO1A",
  "title": "Rick Astley",
  "description": "Rick Astley's official YouTube channel",
  "subscriber_count": 12500000,
  "subscriber_count_hidden": false,
  "video_count": 45,
  "total_views": 2000000000,
  "custom_url": "rickastley",
  "thumbnail_url": "https://yt3.googleapis.com/...",
  "country": "GB",
  "keywords": "music, pop, 80s",
  "created_at": "2007-08-22T18:29:09Z"
}
```

---

### Video Comments

Get top comments for a video.

**Endpoint:** `GET /api/v1/youtube/video/comments/{video_id_or_url}`

**Query Parameters:**
- `max_results` (integer, optional, default=20): Maximum comments (1-100)
- `order` (string, optional, default="relevance"): Sort order - "relevance" or "time"

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/youtube/video/comments/dQw4w9WgXcQ?max_results=10&order=relevance"
```

**Example Response:**
```json
{
  "comments": [
    {
      "author": "John Doe",
      "author_channel_url": "http://www.youtube.com/channel/UCxxxx",
      "text": "This is an amazing video!",
      "likes": 5000,
      "published_at": "2024-01-15T10:30:00Z",
      "reply_count": 150
    },
    {
      "author": "Jane Smith",
      "author_channel_url": "http://www.youtube.com/channel/UCyyyy",
      "text": "Best music ever",
      "likes": 3200,
      "published_at": "2024-01-14T15:45:00Z",
      "reply_count": 80
    }
  ],
  "count": 2
}
```

---

### Search Videos

Search for YouTube videos.

**Endpoint:** `GET /api/v1/youtube/search`

**Query Parameters:**
- `query` (string, required): Search query
- `max_results` (integer, optional, default=25): Results to return (1-50)
- `order` (string, optional, default="relevance"): Sort order - "relevance", "date", "rating", "viewCount"
- `published_after` (string, optional): ISO 8601 date (e.g., "2024-01-01T00:00:00Z")
- `published_before` (string, optional): ISO 8601 date
- `region_code` (string, optional): 2-letter country code

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/youtube/search?query=machine+learning&max_results=5&order=date&region_code=US"
```

**Example Response:**
```json
{
  "videos": [
    {
      "video_id": "dQw4w9WgXcQ",
      "title": "Machine Learning Basics",
      "description": "Learn ML basics...",
      "published_at": "2024-01-20T12:00:00Z",
      "thumbnail_url": "https://i.ytimg.com/vi/...",
      "channel_title": "Tech Channel",
      "channel_id": "UCxxxxx"
    }
  ],
  "count": 1
}
```

---

### Trending Videos

Get trending videos for a specific region.

**Endpoint:** `GET /api/v1/youtube/trending`

**Query Parameters:**
- `region_code` (string, optional, default="US"): 2-letter country code
- `max_results` (integer, optional, default=25): Results (1-50)
- `category_id` (string, optional): YouTube category ID for filtering

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/youtube/trending?region_code=US&max_results=10"
```

**Example Response:**
```json
{
  "videos": [
    {
      "video_id": "abc123",
      "title": "Trending Video Title",
      "channel_title": "Channel Name",
      "channel_id": "UCxxxxx",
      "published_at": "2024-01-20T12:00:00Z",
      "thumbnail_url": "https://i.ytimg.com/vi/...",
      "view_count": 5000000,
      "like_count": 250000,
      "comment_count": 50000
    }
  ],
  "count": 1
}
```

---

### Related Videos

Get videos related to a specific video.

**Endpoint:** `GET /api/v1/youtube/related/{video_id_or_url}`

**Query Parameters:**
- `max_results` (integer, optional, default=25): Results (1-50)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/youtube/related/dQw4w9WgXcQ?max_results=10"
```

**Example Response:**
```json
{
  "videos": [
    {
      "video_id": "abc123",
      "title": "Related Video Title",
      "description": "Video description...",
      "published_at": "2024-01-15T10:00:00Z",
      "thumbnail_url": "https://i.ytimg.com/vi/...",
      "channel_title": "Channel Name",
      "channel_id": "UCxxxxx"
    }
  ],
  "count": 1
}
```

---

### Playlist Videos

Get all videos from a YouTube playlist.

**Endpoint:** `GET /api/v1/youtube/playlist/{playlist_id}`

**Query Parameters:**
- `max_results` (integer, optional, default=50): Maximum videos to retrieve

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/youtube/playlist/PLxxxxx?max_results=20"
```

**Example Response:**
```json
{
  "videos": [
    {
      "video_id": "abc123",
      "title": "Video 1",
      "description": "Description...",
      "published_at": "2024-01-15T10:00:00Z",
      "thumbnail_url": "https://i.ytimg.com/vi/...",
      "channel_title": "Channel Name",
      "position": 1
    }
  ],
  "count": 1
}
```

---

### Video Categories

Get available video categories for a region.

**Endpoint:** `GET /api/v1/youtube/categories`

**Query Parameters:**
- `region_code` (string, optional, default="US"): 2-letter country code

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/youtube/categories?region_code=US"
```

**Example Response:**
```json
{
  "categories": [
    {
      "id": "1",
      "title": "Film & Animation"
    },
    {
      "id": "2",
      "title": "Autos & Vehicles"
    },
    {
      "id": "10",
      "title": "Music"
    }
  ],
  "count": 30
}
```

---

## Python Usage Examples

### Example 1: Get Video Statistics

```python
from services.youtube_data_api import YouTubeDataAPI

# Initialize the API
youtube_api = YouTubeDataAPI()

# Get video statistics
stats = youtube_api.get_video_statistics("dQw4w9WgXcQ")
print(f"Title: {stats['title']}")
print(f"Views: {stats['view_count']:,}")
print(f"Likes: {stats['like_count']:,}")
print(f"Duration: {stats['duration_formatted']}")
```

### Example 2: Search and Filter Videos

```python
# Search for machine learning videos
videos = youtube_api.search_videos(
    query="machine learning tutorial",
    max_results=10,
    order="date",
    published_after="2024-01-01T00:00:00Z",
    region_code="US"
)

for video in videos:
    print(f"{video['title']} - {video['channel_title']}")
```

### Example 3: Get Channel Information

```python
# Get channel statistics
channel = youtube_api.get_channel_statistics("UC4JX40jDee_NI8pTrqCdO1A")
print(f"Channel: {channel['title']}")
print(f"Subscribers: {channel['subscriber_count']:,}")
print(f"Total Videos: {channel['video_count']}")
print(f"Total Views: {channel['total_views']:,}")
```

### Example 4: Analyze Video Comments

```python
# Get top comments
comments = youtube_api.get_video_comments(
    "dQw4w9WgXcQ",
    max_results=50,
    order="relevance"
)

# Calculate engagement
total_likes = sum(c['likes'] for c in comments)
total_replies = sum(c['reply_count'] for c in comments)

print(f"Top 50 comments have {total_likes:,} likes and {total_replies:,} replies")

# Find most engaging comments
top_comments = sorted(comments, key=lambda c: c['likes'], reverse=True)[:5]
for comment in top_comments:
    print(f"{comment['author']}: {comment['text'][:50]}... ({comment['likes']} likes)")
```

### Example 5: Find Trending Content

```python
# Get trending videos in different regions
for region in ["US", "GB", "IN", "DE"]:
    trending = youtube_api.get_trending_videos(region_code=region, max_results=5)
    print(f"\nTrending in {region}:")
    for video in trending[:3]:
        print(f"  {video['title']} - {video['view_count']:,} views")
```

### Example 6: Explore Related Content

```python
# Find related videos
related = youtube_api.get_related_videos("dQw4w9WgXcQ", max_results=10)

print(f"Found {len(related)} related videos:")
for video in related:
    print(f"  - {video['title']} by {video['channel_title']}")
```

---

## Integration with Shorts Generation

You can combine YouTube Data API with the video shorts generation pipeline:

```python
from services.youtube_data_api import YouTubeDataAPI
from services.youtube_processor import YouTubeProcessor

# Get video statistics before processing
youtube_api = YouTubeDataAPI()
stats = youtube_api.get_video_statistics(video_url)

# Log engagement metrics
print(f"Processing video with {stats['view_count']:,} views and {stats['comment_count']:,} comments")

# Generate shorts
youtube_processor = YouTubeProcessor()
video_info = youtube_processor.get_video_info(video_url)

# Combine data for context
enriched_data = {**stats, **video_info}
```

---

## Error Handling

```python
from googleapiclient.errors import HttpError

try:
    stats = youtube_api.get_video_statistics("invalid_id")
except ValueError as e:
    print(f"Invalid input: {e}")
except HttpError as e:
    print(f"YouTube API error: {e}")
except Exception as e:
    print(f"Error: {e}")
```

---

## Rate Limits

YouTube Data API has rate limits:

- **Free tier**: 10,000 quota units per day
- **Each request type uses different quota**:
  - `videos().list()`: 1 unit
  - `channels().list()`: 1 unit
  - `search().list()`: 100 units
  - `commentThreads().list()`: 1 unit
  - `playlistItems().list()`: 1 unit

Plan your requests accordingly to stay within limits.

---

## Common Issues & Solutions

### Issue: "YouTube API key not configured"

**Solution**: Set the `YOUTUBE_API_KEY` environment variable:

```bash
export YOUTUBE_API_KEY=your_api_key_here
```

or in `.env`:

```
YOUTUBE_API_KEY=your_api_key_here
```

### Issue: "quotaExceeded" error

**Solution**: You've exceeded your daily quota. Wait 24 hours or upgrade your API quota in Google Cloud Console.

### Issue: "Permission denied" error

**Solution**: Ensure YouTube Data API v3 is enabled in Google Cloud Console for your project.

### Issue: Video/Channel not found

**Solution**: Verify the video ID or channel ID is correct. Some videos may be private or age-restricted.

---

## Conclusion

The YouTube Data API implementation provides powerful metadata retrieval capabilities to enhance your video processing pipeline. Combine it with the AI analysis and video clipping features for a complete content generation solution.

For more information, see the [Official YouTube Data API Documentation](https://developers.google.com/youtube/v3).
