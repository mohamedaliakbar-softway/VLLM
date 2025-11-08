"""YouTube video downloader and processor."""
import yt_dlp
import os
import time
import traceback
from pathlib import Path
from typing import Optional, Dict, List
from config import settings
import logging
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

logger = logging.getLogger(__name__)


class YouTubeProcessor:
    """Handles YouTube video downloading and processing."""
    
    def __init__(self):
        self.temp_dir = Path(settings.temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.cookies_file = getattr(settings, 'youtube_cookies_file', None)
        self.use_browser_cookies = getattr(settings, 'youtube_use_browser_cookies', True)
        self.browser = getattr(settings, 'youtube_browser', 'chrome').lower()
        # Rate limiting to prevent 429 errors
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds minimum delay between requests
    
    def get_video_info(self, youtube_url: str, video_id: Optional[str] = None) -> dict:
        """
        Get video information without downloading.
        
        Args:
            youtube_url: YouTube video URL
            video_id: Optional video ID for naming
            
        Returns:
            dict with video info including duration and title
        """
        # Rate limiting to prevent 429 errors
        self._rate_limit()
        
        try:
            if not video_id:
                video_id = self._extract_video_id(youtube_url)
            
            ydl_opts = self._get_ydl_opts({
                'quiet': True,
                'no_warnings': True,
            })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = self._extract_info_with_timeout(ydl, youtube_url, download=False)
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    if "Sign in to confirm you're not a bot" in error_msg or "bot" in error_msg.lower():
                        logger.error("YouTube bot detection triggered. Cookies may not be working.")
                        logger.error("Solution: Export cookies manually using ./export_youtube_cookies.sh")
                    raise
                
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
        # Rate limiting to prevent 429 errors
        self._rate_limit()
        
        try:
            # Extract video ID if not provided
            if not video_id:
                video_id = self._extract_video_id(youtube_url)
            
            output_path = self.temp_dir / f"{video_id}.mp4"
            
            ydl_opts = self._get_ydl_opts({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': str(output_path),
                'quiet': True,
                'no_warnings': True,
            })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first
                try:
                    info = self._extract_info_with_timeout(ydl, youtube_url, download=False)
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    if "Sign in to confirm you're not a bot" in error_msg or "bot" in error_msg.lower():
                        logger.error("YouTube bot detection triggered during video download.")
                        logger.error("Solution: Export cookies manually using ./export_youtube_cookies.sh")
                    raise
                
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
        # Rate limiting to prevent 429 errors
        self._rate_limit()
        
        try:
            if not video_id:
                video_id = self._extract_video_id(youtube_url)
            
            ydl_opts = self._get_ydl_opts({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'en-US', 'en-GB'],  # Broader language fallback
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
            })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = self._extract_info_with_timeout(ydl, youtube_url, download=False)
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    if "Sign in to confirm you're not a bot" in error_msg or "bot" in error_msg.lower():
                        logger.error("YouTube bot detection triggered. Cookies may not be working properly.")
                        logger.error("Try:")
                        logger.error("  1. Make sure you're signed into YouTube in Chrome")
                        logger.error("  2. Run: ./export_youtube_cookies.sh to export cookies")
                        logger.error("  3. Add to .env: YOUTUBE_COOKIES_FILE=./cookies.txt")
                        logger.error("  4. Add to .env: YOUTUBE_USE_BROWSER_COOKIES=false")
                    raise
                
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
                    import time
                    
                    # Retry logic with exponential backoff for rate limiting
                    max_retries = 5  # Increased from 3 to 5
                    base_retry_delay = 5  # Start with 5 seconds instead of 1
                    
                    for attempt in range(max_retries):
                        try:
                            resp = requests.get(subtitle_url, timeout=30)  # Increased timeout from 10s
                            resp.raise_for_status()
                            transcript_text = self._parse_subtitles(resp.text)
                            break  # Success, exit retry loop
                        except requests.exceptions.HTTPError as http_err:
                            if http_err.response.status_code == 429 and attempt < max_retries - 1:
                                # Rate limited - wait longer with exponential backoff
                                wait_time = base_retry_delay * (2 ** attempt)  # 5s, 10s, 20s, 40s, 80s
                                logger.warning(
                                    f"Rate limited (429) on attempt {attempt + 1}/{max_retries} for video {video_id}, "
                                    f"waiting {wait_time}s before retry..."
                                )
                                time.sleep(wait_time)
                            else:
                                # Re-raise on last attempt or non-429 errors
                                logger.error(f"Failed to fetch transcript after {attempt + 1} attempts: {http_err}")
                                raise
                        except Exception as e:
                            if attempt == max_retries - 1:
                                # Last attempt, re-raise
                                logger.error(f"Failed to fetch transcript after {max_retries} attempts: {str(e)}")
                                raise
                            # Other errors - retry with exponential backoff
                            wait_time = base_retry_delay * (2 ** attempt)
                            logger.warning(
                                f"Error on attempt {attempt + 1}/{max_retries}, retrying in {wait_time}s: {str(e)}"
                            )
                            time.sleep(wait_time)
                else:
                    logger.warning(f"No English subtitles found for video {video_id}")
                
                duration = info.get('duration', 0)
                
                # Validate duration
                if duration <= 0:
                    logger.warning(f"WARNING: Duration is {duration}s for video {video_id}. This may cause highlight detection to fail!")
                    logger.warning(f"Video info keys: {list(info.keys())}")
                    # Try to get duration from other fields
                    if 'duration_string' in info:
                        logger.info(f"Found duration_string: {info.get('duration_string')}")
                
                logger.info(f"Extracted transcript for video {video_id}:")
                logger.info(f"  - Transcript length: {len(transcript_text)} chars")
                logger.info(f"  - Duration: {duration}s")
                logger.info(f"  - Title: {info.get('title', 'N/A')}")
                
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
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return empty transcript on error - analysis can still proceed with title/description
            # But log a warning that duration is 0
            logger.warning("Returning empty transcript with duration=0 - highlight detection will likely fail!")
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
        # Rate limiting to prevent 429 errors
        self._rate_limit()
        
        try:
            if not video_id:
                video_id = self._extract_video_id(youtube_url)
            
            downloaded_segments = []
            
            # Get video stream URL without downloading
            ydl_opts = self._get_ydl_opts({
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
            })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = self._extract_info_with_timeout(ydl, youtube_url, download=False)
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    if "Sign in to confirm you're not a bot" in error_msg or "bot" in error_msg.lower():
                        logger.error("YouTube bot detection triggered during segment download.")
                        logger.error("Cookies may not be working. Try exporting cookies manually.")
                        logger.error("Run: ./export_youtube_cookies.sh")
                    raise
                
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
                        '-c', 'copy',  # Copy streams (no re-encoding, super fast)
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
    
    def _get_ydl_opts(self, base_opts: dict = None) -> dict:
        """
        Get yt-dlp options with cookie support to bypass bot detection.
        
        Args:
            base_opts: Base options dictionary
            
        Returns:
            Options dictionary with cookies configured
        """
        opts = base_opts.copy() if base_opts else {}
        
        # Add options to bypass bot detection
        # Use a modern user agent to appear more like a real browser
        opts.setdefault('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Add referer to appear more legitimate
        opts.setdefault('referer', 'https://www.youtube.com/')
        
        # Priority 1: Use cookies file if specified and exists
        if self.cookies_file and os.path.exists(self.cookies_file):
            opts['cookiefile'] = self.cookies_file
            logger.info(f"Using cookies file: {self.cookies_file}")
        # Priority 2: Use browser cookies if enabled
        elif self.use_browser_cookies:
            try:
                # Try to use browser cookies
                valid_browsers = ['chrome', 'firefox', 'safari', 'edge', 'opera', 'brave']
                if self.browser in valid_browsers:
                    # Try multiple browsers as fallback
                    browsers_to_try = [self.browser]
                    if self.browser != 'chrome':
                        browsers_to_try.append('chrome')  # Chrome as fallback
                    
                    for browser in browsers_to_try:
                        try:
                            opts['cookiesfrombrowser'] = (browser,)
                            logger.info(f"Using cookies from {browser} browser")
                            break
                        except Exception:
                            if browser == browsers_to_try[-1]:
                                raise
                            continue
                else:
                    logger.warning(f"Invalid browser '{self.browser}', defaulting to chrome")
                    opts['cookiesfrombrowser'] = ('chrome',)
            except Exception as e:
                logger.warning(f"Failed to configure browser cookies: {e}")
                logger.warning("Consider exporting cookies manually. Run: ./export_youtube_cookies.sh")
                # Don't fail completely, but log the warning
        
        # Add extractor args to help with YouTube bot detection
        if 'extractor_args' not in opts:
            opts['extractor_args'] = {}
        if 'youtube' not in opts['extractor_args']:
            opts['extractor_args']['youtube'] = {}
        
        # Try to use player client that's less likely to trigger bot detection
        # Try multiple clients as fallback: web, android, ios, tv_embedded
        # 'android' and 'ios' are often more reliable for bypassing bot detection
        if 'player_client' not in opts['extractor_args']['youtube']:
            opts['extractor_args']['youtube']['player_client'] = ['android', 'web']
        
        # Add additional headers to appear more like a browser
        if 'http_headers' not in opts:
            opts['http_headers'] = {}
        opts['http_headers'].setdefault('Accept-Language', 'en-US,en;q=0.9')
        opts['http_headers'].setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        opts['http_headers'].setdefault('Sec-Fetch-Mode', 'navigate')
        opts['http_headers'].setdefault('Sec-Fetch-Site', 'none')
        opts['http_headers'].setdefault('Sec-Fetch-User', '?1')
        
        # Add retry options for transient errors
        opts.setdefault('retries', 3)
        opts.setdefault('fragment_retries', 3)
        
        # Add timeout configuration to prevent hanging
        opts.setdefault('socket_timeout', 30)  # 30 second socket timeout
        opts.setdefault('extractor_timeout', 60)  # 60 second extractor timeout
        
        return opts
    
    def _rate_limit(self):
        """Ensure minimum time between requests to prevent 429 errors."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _extract_info_with_timeout(self, ydl, url: str, download: bool = False, timeout: int = 60):
        """
        Extract video info with timeout to prevent hanging.
        
        Args:
            ydl: yt-dlp YoutubeDL instance
            url: YouTube URL
            download: Whether to download (default: False)
            timeout: Timeout in seconds (default: 60)
            
        Returns:
            Video info dictionary
            
        Raises:
            TimeoutError: If extraction takes longer than timeout
        """
        with ThreadPoolExecutor() as executor:
            future = executor.submit(ydl.extract_info, url, download=download)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError:
                raise TimeoutError(f"yt-dlp extract_info timed out after {timeout}s")
    
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

