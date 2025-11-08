"""YouTube Data API v3 service for fetching video and channel information."""
import logging
from typing import Optional, Dict, List, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import settings
import re

logger = logging.getLogger(__name__)


class YouTubeDataAPI:
    """Handles YouTube Data API v3 interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize YouTube Data API client.
        
        Args:
            api_key: YouTube Data API key. If None, uses YOUTUBE_API_KEY from settings.
        """
        self.api_key = api_key or getattr(settings, 'youtube_api_key', None)
        if not self.api_key:
            logger.warning("YouTube API key not configured. Some features will be unavailable.")
            self.youtube = None
        else:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:v\/)([0-9A-Za-z_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    def get_video_statistics(self, video_url_or_id: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a YouTube video.
        
        Args:
            video_url_or_id: YouTube video URL or video ID
            
        Returns:
            Dictionary containing:
            - video_id: Video ID
            - title: Video title
            - description: Video description
            - duration: Video duration in seconds
            - view_count: Number of views
            - like_count: Number of likes
            - comment_count: Number of comments
            - upload_date: Upload date (ISO 8601 format)
            - channel_id: Channel ID
            - channel_title: Channel name
            - thumbnail_url: Video thumbnail URL
            - tags: Video tags
            - category_id: YouTube category ID
            - definition: Video definition (hd or sd)
            - caption: Whether video has captions
        """
        if not self.youtube:
            raise RuntimeError("YouTube API not configured. Set YOUTUBE_API_KEY in environment.")
        
        try:
            # Extract video ID if URL provided
            if "youtube.com" in video_url_or_id or "youtu.be" in video_url_or_id:
                video_id = self._extract_video_id(video_url_or_id)
            else:
                video_id = video_url_or_id
            
            # Fetch video details
            request = self.youtube.videos().list(
                part='snippet,statistics,contentDetails,fileDetails',
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                raise ValueError(f"Video not found: {video_id}")
            
            item = response['items'][0]
            snippet = item['snippet']
            statistics = item['statistics']
            content_details = item['contentDetails']
            
            # Parse ISO 8601 duration to seconds
            duration_seconds = self._parse_iso_duration(content_details.get('duration', 'PT0S'))
            
            return {
                'video_id': video_id,
                'title': snippet['title'],
                'description': snippet['description'],
                'duration': duration_seconds,
                'duration_formatted': self._format_duration(duration_seconds),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'upload_date': snippet['publishedAt'],
                'channel_id': snippet['channelId'],
                'channel_title': snippet['channelTitle'],
                'thumbnail_url': snippet['thumbnails']['high']['url'],
                'tags': snippet.get('tags', []),
                'category_id': snippet.get('categoryId', ''),
                'definition': content_details.get('definition', 'unknown'),
                'caption': content_details.get('caption', False),
                'licensed_content': content_details.get('licensedContent', True),
            }
        
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching video statistics: {str(e)}")
            raise
    
    def get_channel_statistics(self, channel_url_or_id: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a YouTube channel.
        
        Args:
            channel_url_or_id: YouTube channel URL, username, or channel ID
            
        Returns:
            Dictionary containing:
            - channel_id: Channel ID
            - title: Channel name
            - description: Channel description
            - subscriber_count: Number of subscribers
            - video_count: Number of videos
            - total_views: Total views across all videos
            - custom_url: Custom channel URL
            - thumbnail_url: Channel profile picture
            - banner_url: Channel banner image
            - country: Channel's country
            - keywords: Channel keywords/tags
        """
        if not self.youtube:
            raise RuntimeError("YouTube API not configured. Set YOUTUBE_API_KEY in environment.")
        
        try:
            channel_id = self._extract_channel_id(channel_url_or_id)
            
            # Fetch channel details
            request = self.youtube.channels().list(
                part='snippet,statistics,brandingSettings',
                id=channel_id
            )
            response = request.execute()
            
            if not response['items']:
                raise ValueError(f"Channel not found: {channel_id}")
            
            item = response['items'][0]
            snippet = item['snippet']
            statistics = item['statistics']
            branding = item.get('brandingSettings', {})
            
            return {
                'channel_id': channel_id,
                'title': snippet['title'],
                'description': snippet['description'],
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'subscriber_count_hidden': statistics.get('hiddenSubscriberCount', False),
                'video_count': int(statistics.get('videoCount', 0)),
                'total_views': int(statistics.get('viewCount', 0)),
                'custom_url': snippet.get('customUrl', ''),
                'thumbnail_url': snippet['thumbnails']['high']['url'],
                'country': snippet.get('country', ''),
                'keywords': branding.get('keywords', ''),
                'created_at': snippet['publishedAt'],
            }
        
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching channel statistics: {str(e)}")
            raise
    
    def get_video_comments(
        self,
        video_url_or_id: str,
        max_results: int = 20,
        text_format: str = 'plainText',
        order: str = 'relevance'
    ) -> List[Dict[str, Any]]:
        """
        Get top comments for a video.
        
        Args:
            video_url_or_id: YouTube video URL or ID
            max_results: Maximum number of comments to retrieve (1-100)
            text_format: 'html' or 'plainText'
            order: 'relevance' or 'time'
            
        Returns:
            List of comments containing:
            - author: Comment author name
            - author_channel_url: Link to author's channel
            - text: Comment text
            - likes: Number of likes
            - published_at: Comment publication date
            - reply_count: Number of replies
        """
        if not self.youtube:
            raise RuntimeError("YouTube API not configured. Set YOUTUBE_API_KEY in environment.")
        
        try:
            # Extract video ID
            if "youtube.com" in video_url_or_id or "youtu.be" in video_url_or_id:
                video_id = self._extract_video_id(video_url_or_id)
            else:
                video_id = video_url_or_id
            
            # Limit max_results to 100
            max_results = min(max_results, 100)
            
            # Fetch comments
            request = self.youtube.commentThreads().list(
                part='snippet,replies',
                videoId=video_id,
                maxResults=max_results,
                textFormat=text_format,
                order=order
            )
            response = request.execute()
            
            comments = []
            for item in response.get('items', []):
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'author': comment['authorDisplayName'],
                    'author_channel_url': comment.get('authorChannelUrl', ''),
                    'text': comment['textDisplay'],
                    'likes': comment['likeCount'],
                    'published_at': comment['publishedAt'],
                    'reply_count': item['snippet']['totalReplyCount'],
                })
            
            return comments
        
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching comments: {str(e)}")
            raise
    
    def search_videos(
        self,
        query: str,
        max_results: int = 25,
        order: str = 'relevance',
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
        region_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos.
        
        Args:
            query: Search query
            max_results: Maximum results (1-50)
            order: 'relevance', 'date', 'rating', 'viewCount'
            published_after: ISO 8601 format (e.g., '2024-01-01T00:00:00Z')
            published_before: ISO 8601 format
            region_code: 2-letter country code
            
        Returns:
            List of videos containing:
            - video_id: Video ID
            - title: Video title
            - description: Video description
            - published_at: Publication date
            - thumbnail_url: Video thumbnail
            - channel_title: Channel name
            - channel_id: Channel ID
        """
        if not self.youtube:
            raise RuntimeError("YouTube API not configured. Set YOUTUBE_API_KEY in environment.")
        
        try:
            # Limit max_results
            max_results = min(max_results, 50)
            
            kwargs = {
                'part': 'snippet',
                'q': query,
                'maxResults': max_results,
                'type': 'video',
                'order': order,
            }
            
            if published_after:
                kwargs['publishedAfter'] = published_after
            if published_before:
                kwargs['publishedBefore'] = published_before
            if region_code:
                kwargs['regionCode'] = region_code
            
            request = self.youtube.search().list(**kwargs)
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                snippet = item['snippet']
                videos.append({
                    'video_id': item['id']['videoId'],
                    'title': snippet['title'],
                    'description': snippet['description'],
                    'published_at': snippet['publishedAt'],
                    'thumbnail_url': snippet['thumbnails']['medium']['url'],
                    'channel_title': snippet['channelTitle'],
                    'channel_id': snippet['channelId'],
                })
            
            return videos
        
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error searching videos: {str(e)}")
            raise
    
    def get_trending_videos(
        self,
        region_code: str = 'US',
        max_results: int = 25,
        category_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get trending videos for a region.
        
        Args:
            region_code: 2-letter country code (e.g., 'US', 'GB', 'IN')
            max_results: Maximum results (1-50)
            category_id: Optional YouTube category ID
            
        Returns:
            List of trending videos with statistics
        """
        if not self.youtube:
            raise RuntimeError("YouTube API not configured. Set YOUTUBE_API_KEY in environment.")
        
        try:
            max_results = min(max_results, 50)
            
            kwargs = {
                'part': 'snippet,statistics',
                'chart': 'mostPopular',
                'regionCode': region_code,
                'maxResults': max_results,
            }
            
            if category_id:
                kwargs['videoCategoryId'] = category_id
            
            request = self.youtube.videos().list(**kwargs)
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                snippet = item['snippet']
                statistics = item['statistics']
                videos.append({
                    'video_id': item['id'],
                    'title': snippet['title'],
                    'channel_title': snippet['channelTitle'],
                    'channel_id': snippet['channelId'],
                    'published_at': snippet['publishedAt'],
                    'thumbnail_url': snippet['thumbnails']['medium']['url'],
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'comment_count': int(statistics.get('commentCount', 0)),
                })
            
            return videos
        
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching trending videos: {str(e)}")
            raise
    
    def get_related_videos(
        self,
        video_url_or_id: str,
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Get videos related to a specific video.
        
        Args:
            video_url_or_id: YouTube video URL or ID
            max_results: Maximum results (1-50)
            
        Returns:
            List of related videos
        """
        if not self.youtube:
            raise RuntimeError("YouTube API not configured. Set YOUTUBE_API_KEY in environment.")
        
        try:
            # Extract video ID
            if "youtube.com" in video_url_or_id or "youtu.be" in video_url_or_id:
                video_id = self._extract_video_id(video_url_or_id)
            else:
                video_id = video_url_or_id
            
            max_results = min(max_results, 50)
            
            request = self.youtube.search().list(
                part='snippet',
                relatedToVideoId=video_id,
                type='video',
                maxResults=max_results,
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                snippet = item['snippet']
                videos.append({
                    'video_id': item['id']['videoId'],
                    'title': snippet['title'],
                    'description': snippet['description'],
                    'published_at': snippet['publishedAt'],
                    'thumbnail_url': snippet['thumbnails']['medium']['url'],
                    'channel_title': snippet['channelTitle'],
                    'channel_id': snippet['channelId'],
                })
            
            return videos
        
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching related videos: {str(e)}")
            raise
    
    def get_playlist_videos(
        self,
        playlist_id: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get videos from a YouTube playlist.
        
        Args:
            playlist_id: YouTube playlist ID
            max_results: Maximum videos to retrieve
            
        Returns:
            List of videos in the playlist
        """
        if not self.youtube:
            raise RuntimeError("YouTube API not configured. Set YOUTUBE_API_KEY in environment.")
        
        try:
            videos = []
            next_page_token = None
            remaining = max_results
            
            while remaining > 0 and len(videos) < max_results:
                batch_size = min(remaining, 50)
                
                request = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=playlist_id,
                    maxResults=batch_size,
                    pageToken=next_page_token,
                )
                response = request.execute()
                
                for item in response.get('items', []):
                    snippet = item['snippet']
                    videos.append({
                        'video_id': snippet['resourceId']['videoId'],
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'published_at': snippet['publishedAt'],
                        'thumbnail_url': snippet['thumbnails']['medium']['url'],
                        'channel_title': snippet['videoOwnerChannelTitle'],
                        'position': snippet['position'],
                    })
                    
                    if len(videos) >= max_results:
                        break
                
                next_page_token = response.get('nextPageToken')
                remaining = max_results - len(videos)
                
                if not next_page_token:
                    break
            
            return videos[:max_results]
        
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching playlist videos: {str(e)}")
            raise
    
    def get_video_categories(self, region_code: str = 'US') -> List[Dict[str, Any]]:
        """
        Get all available YouTube video categories for a region.
        
        Args:
            region_code: 2-letter country code
            
        Returns:
            List of categories with IDs and titles
        """
        if not self.youtube:
            raise RuntimeError("YouTube API not configured. Set YOUTUBE_API_KEY in environment.")
        
        try:
            request = self.youtube.videoCategories().list(
                part='snippet',
                regionCode=region_code,
                hl='en',
            )
            response = request.execute()
            
            categories = []
            for item in response.get('items', []):
                snippet = item['snippet']
                if snippet.get('assignable', True):  # Only assignable categories
                    categories.append({
                        'id': item['id'],
                        'title': snippet['title'],
                    })
            
            return categories
        
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching video categories: {str(e)}")
            raise
    
    @staticmethod
    def _parse_iso_duration(duration_str: str) -> int:
        """
        Parse ISO 8601 duration string to seconds.
        Example: PT1H30M45S -> 5445 seconds
        """
        import re
        
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0
        
        return hours * 3600 + minutes * 60 + seconds
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Convert seconds to HH:MM:SS format."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def _extract_channel_id(channel_url_or_id: str) -> str:
        """Extract channel ID from URL or return as-is if already an ID."""
        # If it looks like a channel ID (starts with UC), return as-is
        if channel_url_or_id.startswith('UC') and len(channel_url_or_id) == 24:
            return channel_url_or_id
        
        # Extract from channel URL
        patterns = [
            r'(?:channel/|channels/)([^/?]+)',
            r'(?:/@([^/?]+))',
            r'(?:user/([^/?]+))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, channel_url_or_id)
            if match:
                return match.group(1)
        
        # If no match found, assume it's already a channel ID
        return channel_url_or_id
