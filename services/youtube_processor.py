"""YouTube video downloader and processor."""
import yt_dlp
import os
from pathlib import Path
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class YouTubeProcessor:
    """Handles YouTube video downloading and processing."""
    
    def __init__(self):
        self.temp_dir = Path(settings.temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
    
    def get_video_info(self, youtube_url: str, video_id: Optional[str] = None) -> dict:
        """
        Get video information without downloading.
        
        Args:
            youtube_url: YouTube video URL
            video_id: Optional video ID for naming
            
        Returns:
            dict with video info including duration and title
        """
        try:
            if not video_id:
                video_id = self._extract_video_id(youtube_url)
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                duration = info.get('duration', 0)
                
                # Validate duration
                if duration < settings.min_video_duration:
                    raise ValueError(
                        f"Video duration ({duration}s) is less than minimum "
                        f"required ({settings.min_video_duration}s)"
                    )
                if duration > settings.max_video_duration:
                    raise ValueError(
                        f"Video duration ({duration}s) exceeds maximum "
                        f"allowed ({settings.max_video_duration}s)"
                    )
                
                return {
                    'duration': duration,
                    'title': info.get('title', ''),
                    'video_id': video_id,
                    'thumbnail': info.get('thumbnail', ''),
                }
        
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise
    
    def download_video(self, youtube_url: str, video_id: Optional[str] = None) -> dict:
        """
        Download video from YouTube URL.
        
        Args:
            youtube_url: YouTube video URL
            video_id: Optional video ID for naming
            
        Returns:
            dict with video info including file path and duration
        """
        try:
            # Extract video ID if not provided
            if not video_id:
                video_id = self._extract_video_id(youtube_url)
            
            output_path = self.temp_dir / f"{video_id}.mp4"
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': str(output_path),
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first
                info = ydl.extract_info(youtube_url, download=False)
                duration = info.get('duration', 0)
                
                # Validate duration
                if duration < settings.min_video_duration:
                    raise ValueError(
                        f"Video duration ({duration}s) is less than minimum "
                        f"required ({settings.min_video_duration}s)"
                    )
                if duration > settings.max_video_duration:
                    raise ValueError(
                        f"Video duration ({duration}s) exceeds maximum "
                        f"allowed ({settings.max_video_duration}s)"
                    )
                
                # Download the video
                ydl.download([youtube_url])
                
                logger.info(f"Downloaded video: {output_path}, Duration: {duration}s")
                
                return {
                    'file_path': str(output_path),
                    'duration': duration,
                    'title': info.get('title', ''),
                    'video_id': video_id,
                    'thumbnail': info.get('thumbnail', ''),
                }
        
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        import re
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
    
    def cleanup(self, file_path: str):
        """Remove temporary video file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Error cleaning up file {file_path}: {str(e)}")

