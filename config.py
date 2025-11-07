"""Configuration settings for the Video Shorts Generator."""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Gemini API
    gemini_api_key: str  # Required - must be set in .env file
    
    # Server
    host: str = "0.0.0.0"
    port: int = 5000
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


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

# Ensure directories exist
os.makedirs(settings.temp_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)

