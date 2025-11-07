"""FastAPI application for Video Shorts Generator SaaS."""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import logging
import uuid
from pathlib import Path

from config import settings
from services.youtube_processor import YouTubeProcessor
from services.gemini_analyzer import GeminiAnalyzer
from services.video_clipper import VideoClipper

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Video Shorts Generator API",
    description="AI-powered SaaS for creating engaging marketing shorts from long-form videos",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
youtube_processor = YouTubeProcessor()
gemini_analyzer = GeminiAnalyzer()
video_clipper = VideoClipper()


# Request/Response models
class ShortsRequest(BaseModel):
    """Request model for generating shorts."""
    youtube_url: HttpUrl
    max_shorts: Optional[int] = 3
    platform: Optional[str] = "default"  # youtube_shorts, instagram_reels, facebook, linkedin, whatsapp, square, default


class ShortInfo(BaseModel):
    """Information about a generated short."""
    short_id: int
    filename: str
    start_time: str
    end_time: str
    duration_seconds: int
    engagement_score: int
    marketing_effectiveness: str
    suggested_cta: str
    download_url: str


class ShortsResponse(BaseModel):
    """Response model for shorts generation."""
    job_id: str
    status: str
    video_title: str
    video_duration: int
    shorts: List[ShortInfo]
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None


# In-memory job storage (use Redis/DB in production)
jobs = {}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Video Shorts Generator API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/v1/generate-shorts", response_model=ShortsResponse)
async def generate_shorts(
    request: ShortsRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate marketing shorts from a YouTube video.
    
    This endpoint:
    1. Downloads the video from YouTube
    2. Analyzes it using Gemini AI to find engaging highlights
    3. Creates 15-30 second shorts from the best segments
    4. Returns information about the generated shorts
    """
    job_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Starting job {job_id} for URL: {request.youtube_url}")
        
        # Step 1: Get video info (validate duration, get title)
        logger.info("Getting video information...")
        video_info = youtube_processor.get_video_info(str(request.youtube_url))
        
        # Step 2: Analyze video for highlights using Gemini (uses YouTube URL directly)
        logger.info("Analyzing video for highlights with Gemini AI...")
        highlights = gemini_analyzer.analyze_video_for_highlights(
            str(request.youtube_url),
            video_info.get('title', '')
        )
        
        if not highlights:
            raise HTTPException(
                status_code=404,
                detail="No suitable highlights found in the video"
            )
        
        # Limit highlights based on request
        max_shorts = min(request.max_shorts or settings.max_highlights, len(highlights))
        highlights = highlights[:max_shorts]
        
        # Step 3: Download video only if we have valid highlights
        logger.info("Downloading video for clipping...")
        video_file_info = youtube_processor.download_video(
            str(request.youtube_url),
            video_info.get('video_id')
        )
        
        # Step 4: Create video shorts
        platform = request.platform or "default"
        logger.info(f"Creating {len(highlights)} shorts for platform: {platform}...")
        created_shorts = video_clipper.create_shorts(
            video_file_info['file_path'],
            highlights,
            video_info['video_id'],
            platform=platform
        )
        
        if not created_shorts:
            raise HTTPException(
                status_code=500,
                detail="Failed to create video shorts"
            )
        
        # Step 5: Prepare response
        shorts_info = []
        for short in created_shorts:
            shorts_info.append(ShortInfo(
                short_id=short["short_id"],
                filename=short["filename"],
                start_time=short["start_time"],
                end_time=short["end_time"],
                duration_seconds=short["duration_seconds"],
                engagement_score=short["engagement_score"],
                marketing_effectiveness=short["marketing_effectiveness"],
                suggested_cta=short["suggested_cta"],
                download_url=f"/api/v1/download/{short['filename']}"
            ))
        
        # Schedule cleanup of source video
        background_tasks.add_task(
            youtube_processor.cleanup,
            video_file_info['file_path']
        )
        
        # Store job info
        jobs[job_id] = {
            "status": "completed",
            "video_title": video_info.get('title', ''),
            "shorts": shorts_info
        }
        
        logger.info(f"Job {job_id} completed successfully")
        
        return ShortsResponse(
            job_id=job_id,
            status="completed",
            video_title=video_info.get('title', ''),
            video_duration=video_info.get('duration', 0),
            shorts=shorts_info,
            message=f"Successfully generated {len(shorts_info)} marketing shorts"
        )
    
    except ValueError as e:
        logger.error(f"Validation error in job {job_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error in job {job_id}: {str(e)}")
        jobs[job_id] = {"status": "failed", "error": str(e)}
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate shorts: {str(e)}"
        )


@app.get("/api/v1/download/{filename}")
async def download_short(filename: str):
    """Download a generated short video."""
    file_path = Path(settings.output_dir) / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="video/mp4"
    )


@app.get("/api/v1/job/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@app.delete("/api/v1/shorts/{filename}")
async def delete_short(filename: str, background_tasks: BackgroundTasks):
    """Delete a generated short video."""
    file_path = Path(settings.output_dir) / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    background_tasks.add_task(video_clipper.cleanup, str(file_path))
    
    return {"message": f"Short {filename} scheduled for deletion"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

