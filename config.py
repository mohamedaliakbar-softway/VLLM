"""Configuration settings for the Video Shorts Generator."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables not defined in the model
    )
    
    # Gemini API
    gemini_api_key: Optional[str] = None  # Optional - set in environment or .env file
    
    # YouTube Data API
    youtube_api_key: Optional[str] = None  # Optional - for YouTube Data API features
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True
    
    # Video Processing
    max_video_duration: int = 1800  # 30 minutes
    min_video_duration: int = 180   # 3 minutes
    short_duration_min: int = 15    # seconds
    short_duration_max: int = 30    # seconds
    max_highlights: int = 3
    
    # Storage
    temp_dir: str = "./temp"
    output_dir: str = "./output"
    
    # Sharing / Publishing
    allowed_platforms: str = "linkedin,instagram,x,youtube,youtube_shorts"  # comma-separated
    max_upload_mb: int = 250  # soft limit; actual APIs may vary
    share_max_retries: int = 3
    
    # YouTube OAuth (for publishing)
    youtube_client_id: Optional[str] = None
    youtube_client_secret: Optional[str] = None
    youtube_redirect_uri: Optional[str] = None  # Auto-generated if not set
    
    # Twitter/X API (for publishing)
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None


# Platform-specific video dimensions (width, height)
PLATFORM_DIMENSIONS = {
    "youtube_shorts": (1080, 1920),  # 9:16 vertical
    "instagram_reels": (1080, 1920),  # 9:16 vertical
    "facebook": (1080, 1920),  # 9:16 vertical
    "linkedin": (1080, 1920),  # 9:16 vertical
    "whatsapp": (1080, 1920),  # 9:16 vertical
    "square": (1080, 1080),  # 1:1 square
    "default": (1080, 1920),  # Default to 9:16
}


# Create settings instance
settings = Settings()

# Auto-generate redirect URI if not set
if not settings.youtube_redirect_uri:
    if settings.debug:
        settings.youtube_redirect_uri = f"http://localhost:{settings.port}/api/v1/auth/youtube/callback"
    else:
        # In production, this should be set explicitly in .env
        settings.youtube_redirect_uri = f"http://{settings.host}:{settings.port}/api/v1/auth/youtube/callback"

# Ensure directories exist
os.makedirs(settings.temp_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)

