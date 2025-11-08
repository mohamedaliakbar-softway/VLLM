"""YouTube video downloader and processor."""
import yt_dlp
import os
from pathlib import Path
from typing import Optional, Dict, List
from config import settings
import logging
import subprocess
import json

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
                if not info:
                    raise ValueError("Failed to extract video information")
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
                if not info:
                    raise ValueError("Failed to extract video information")
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
    
    def get_transcript(self, youtube_url: str, video_id: Optional[str] = None) -> Dict:
        """
        Extract transcript/subtitles from YouTube video without downloading.
        This is much faster than downloading the entire video.
        
        Args:
            youtube_url: YouTube video URL
            video_id: Optional video ID for naming
            
        Returns:
            dict with transcript text and video metadata
        """
        try:
            if not video_id:
                video_id = self._extract_video_id(youtube_url)
            
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'en-US', 'en-GB'],  # Broader language fallback
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                if not info:
                    raise ValueError("Failed to extract video information")
                
                # Get transcript/subtitles
                transcript_text = ""
                human_subs = info.get('subtitles', {}) or {}
                auto_subs = info.get('automatic_captions', {}) or {}
                
                # Prefer human subtitles; fall back to automatic captions
                tracks = None
                chosen_lang = None
                for lang in ['en', 'en-US', 'en-GB', 'en-AU']:
                    if lang in human_subs and human_subs[lang]:
                        tracks = human_subs[lang]
                        chosen_lang = lang
                        break
                    if lang in auto_subs and auto_subs[lang]:
                        tracks = auto_subs[lang]
                        chosen_lang = lang
                        break
                
                if tracks:
                    # Prefer VTT, then JSON3/SRV3, then TTML/SRV1/SRV2, else first available
                    preferred = None
                    for ext in ['vtt', 'json3', 'srv3', 'ttml', 'srv1', 'srv2']:
                        for t in tracks:
                            if t.get('ext') == ext:
                                preferred = t
                                break
                        if preferred:
                            break
                    if not preferred:
                        preferred = tracks[0]
                    subtitle_url = preferred.get('url')
                    import requests
                    resp = requests.get(subtitle_url)
                    resp.raise_for_status()
                    transcript_text = self._parse_subtitles(resp.text)
                else:
                    logger.warning(f"No English subtitles found for video {video_id}")
                
                duration = info.get('duration', 0)
                
                logger.info(f"Extracted transcript for video {video_id}, length: {len(transcript_text)} chars")
                
                return {
                    'transcript': transcript_text,
                    'duration': duration,
                    'title': info.get('title', ''),
                    'video_id': video_id,
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', '')[:500]  # First 500 chars
                }
        
        except Exception as e:
            logger.error(f"Error extracting transcript: {str(e)}")
            # Return empty transcript on error - analysis can still proceed with title/description
            return {
                'transcript': '',
                'duration': 0,
                'title': '',
                'video_id': video_id or '',
                'thumbnail': '',
                'description': ''
            }
    
    def download_video_segments(
        self, 
        youtube_url: str, 
        segments: List[Dict], 
        video_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Download only specific segments from a video using FFmpeg (much faster).
        
        Args:
            youtube_url: YouTube video URL
            segments: List of segments with start_seconds and end_seconds
            video_id: Optional video ID for naming
            
        Returns:
            List of downloaded segment file paths
        """
        try:
            if not video_id:
                video_id = self._extract_video_id(youtube_url)
            
            downloaded_segments = []
            
            # Get video stream URL without downloading
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                if not info:
                    raise ValueError("Failed to extract video information")
                video_url = info['url']  # Direct video URL
                
                # Download each segment using FFmpeg (parallel would be even faster)
                for idx, segment in enumerate(segments, 1):
                    start_time = segment.get('start_seconds', 0)
                    duration = segment.get('duration_seconds', 30)
                    
                    output_path = self.temp_dir / f"{video_id}_segment_{idx}.mp4"
                    
                    # Use FFmpeg to download only the segment
                    # This is MUCH faster than downloading the entire video
                    cmd = [
                        'ffmpeg',
                        '-ss', str(start_time),  # Start time
                        '-i', video_url,  # Input URL
                        '-t', str(duration),  # Duration
                        '-c:v', 'libx264',  # Re-encode video to ensure proper MP4
                        '-c:a', 'aac',  # Re-encode audio to AAC
                        '-movflags', '+faststart',  # Enable fast start for web playback
                        '-reset_timestamps', '1',  # Reset timestamps for proper duration
                        '-y',  # Overwrite output
                        str(output_path)
                    ]
                    
                    subprocess.run(cmd, capture_output=True, check=True)
                    
                    end_time = start_time + duration
                    downloaded_segments.append({
                        'segment_id': idx,
                        'file_path': str(output_path),
                        'start_time': start_time,  # Keep for backward compatibility
                        'start_seconds': start_time,  # Add for consistency
                        'duration': duration,  # Keep for backward compatibility
                        'duration_seconds': duration,  # Add for consistency
                        'end_time': end_time,  # Add for convenience
                        'end_seconds': end_time,  # Add for consistency
                    })
                    
                    logger.info(f"Downloaded segment {idx}: {output_path}")
            
            return downloaded_segments
        
        except Exception as e:
            logger.error(f"Error downloading video segments: {str(e)}")
            raise
    
    def _parse_subtitles(self, subtitle_content: str) -> str:
        """Parse VTT, JSON (YouTube json3), or XML/TTML subtitle formats and extract plain text."""
        import re
        import html as _html
        
        # Try JSON first (YouTube json3 format)
        try:
            data = json.loads(subtitle_content)
            texts = []
            events = data.get('events', []) if isinstance(data, dict) else []
            for ev in events:
                segs = ev.get('segs', []) or []
                for s in segs:
                    t = s.get('utf8', '')
                    if t and t.strip():
                        texts.append(t)
            if texts:
                joined = ' '.join(texts)
                return _html.unescape(re.sub(r'\s+', ' ', joined)).strip()
        except Exception:
            pass
        
        content = subtitle_content
        
        # Detect and strip WebVTT header if present
        content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.DOTALL | re.MULTILINE)
        
        # Remove timestamps supporting HH:MM:SS.mmm or MM:SS.mmm ranges
        content = re.sub(r'(?:\d{2}:)?\d{2}:\d{2}\.\d{3}\s*-->\s*(?:\d{2}:)?\d{2}:\d{2}\.\d{3}.*?\n', '', content)
        
        # Remove cue identifiers (numbers at start of lines)
        content = re.sub(r'^\d+\s*$\n?', '', content, flags=re.MULTILINE)
        
        # Remove alignment tags and formatting (works for HTML/TTML/XML)
        content = re.sub(r'<[^>]+>', '', content)
        
        # HTML entities to text
        content = _html.unescape(content)
        
        # Clean up extra whitespace and newlines
        content = re.sub(r'\n+', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
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

