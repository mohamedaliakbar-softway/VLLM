"""FastAPI application for Video Shorts Generator SaaS."""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import logging
import uuid
from pathlib import Path
import asyncio

from config import settings
from services.youtube_processor import YouTubeProcessor
from services.gemini_analyzer import GeminiAnalyzer
from services.video_clipper import VideoClipper
from services.progress_tracker import progress_tracker

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


async def process_video_async(job_id: str, youtube_url: str, max_shorts: int, platform: str):
    """Background task to process video and emit progress updates (OPTIMIZED FOR 20 SECONDS)."""
    try:
        jobs[job_id] = {"status": "processing", "progress": 0}
        
        # STEP 1: Extract transcript (2-3 seconds) - NO VIDEO DOWNLOAD
        await progress_tracker.update_progress(job_id, "processing", 10, "Extracting video transcript...")
        video_info = youtube_processor.get_transcript(youtube_url)
        
        if not video_info.get('transcript'):
            logger.warning(f"No transcript found for {youtube_url}, falling back to basic video info")
            video_info = youtube_processor.get_video_info(youtube_url)
            video_info['transcript'] = f"{video_info.get('title', '')}. {video_info.get('description', '')}"
        
        # STEP 2: Analyze transcript with Gemini (3-5 seconds) - MUCH FASTER than video analysis
        await progress_tracker.update_progress(job_id, "processing", 30, "Analyzing content with AI...")
        highlights = gemini_analyzer.analyze_transcript_for_highlights(
            video_info.get('transcript', ''),
            video_info.get('title', ''),
            video_info.get('description', ''),
            video_info.get('duration', 0)
        )
        
        if not highlights:
            await progress_tracker.update_progress(job_id, "failed", 100, "No suitable highlights found")
            jobs[job_id] = {"status": "failed", "error": "No highlights found"}
            return
        
        max_shorts = min(max_shorts or settings.max_highlights, len(highlights))
        highlights = highlights[:max_shorts]
        
        # STEP 3: Download ONLY the specific segments (5-8 seconds) - NOT the entire video
        await progress_tracker.update_progress(job_id, "processing", 50, f"Downloading {len(highlights)} segments...")
        segment_files = youtube_processor.download_video_segments(
            youtube_url,
            highlights,
            video_info.get('video_id')
        )
        
        if not segment_files:
            await progress_tracker.update_progress(job_id, "failed", 100, "Failed to download segments")
            jobs[job_id] = {"status": "failed", "error": "Failed to download segments"}
            return
        
        # STEP 4: Create shorts with FFmpeg in parallel (3-5 seconds) - 10x faster than MoviePy
        await progress_tracker.update_progress(job_id, "processing", 70, f"Creating {len(highlights)} shorts...")
        created_shorts = video_clipper.create_shorts_fast(
            segment_files,
            video_info['video_id'],
            highlights,
            platform=platform
        )
        
        if not created_shorts:
            await progress_tracker.update_progress(job_id, "failed", 100, "Failed to create shorts")
            jobs[job_id] = {"status": "failed", "error": "Failed to create shorts"}
            return
        
        shorts_info = []
        for short in created_shorts:
            shorts_info.append({
                "short_id": short["short_id"],
                "filename": short["filename"],
                "start_time": short["start_time"],
                "end_time": short["end_time"],
                "duration_seconds": short["duration_seconds"],
                "engagement_score": short["engagement_score"],
                "marketing_effectiveness": short["marketing_effectiveness"],
                "suggested_cta": short["suggested_cta"],
                "download_url": f"/api/v1/download/{short['filename']}"
            })
        
        jobs[job_id] = {
            "status": "completed",
            "video_title": video_info.get('title', ''),
            "video_duration": video_info.get('duration', 0),
            "shorts": shorts_info
        }
        
        await progress_tracker.update_progress(job_id, "completed", 100, f"Generated {len(shorts_info)} shorts successfully!")
        
        # Cleanup segment files
        await asyncio.sleep(1)
        for segment in segment_files:
            youtube_processor.cleanup(segment['file_path'])
        
    except Exception as e:
        logger.error(f"Error in background job {job_id}: {str(e)}")
        jobs[job_id] = {"status": "failed", "error": str(e)}
        await progress_tracker.update_progress(job_id, "failed", 100, f"Error: {str(e)}")
    finally:
        progress_tracker.cleanup_job(job_id)


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


@app.post("/api/v1/generate-shorts")
async def generate_shorts(
    request: ShortsRequest,
    background_tasks: BackgroundTasks
):
    """
    Start video processing job and return immediately with job ID.
    
    Use GET /api/v1/progress/{job_id} to get real-time progress via SSE.
    Use GET /api/v1/job/{job_id} to check completion status and get results.
    """
    job_id = str(uuid.uuid4())
    
    logger.info(f"Creating job {job_id} for URL: {request.youtube_url}")
    
    progress_tracker.create_job(job_id)
    jobs[job_id] = {"status": "queued", "progress": 0}
    
    background_tasks.add_task(
        process_video_async,
        job_id,
        str(request.youtube_url),
        request.max_shorts or 3,
        request.platform or "default"
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Video processing started. Connect to /api/v1/progress/{job_id} for real-time updates."
    }


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


@app.get("/api/v1/progress/{job_id}")
async def get_progress(job_id: str):
    """Get real-time progress updates for a job via Server-Sent Events."""
    progress_tracker.create_job(job_id)
    
    return StreamingResponse(
        progress_tracker.get_progress_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

