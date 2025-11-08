"""FastAPI application for Video Shorts Generator SaaS."""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import logging
import uuid
import time
from datetime import datetime
from pathlib import Path
import asyncio
import os

from config import settings
from services.youtube_processor import YouTubeProcessor
from services.gemini_analyzer import GeminiAnalyzer
from services.video_agent import VideoEditingAgent
from services.video_clipper import VideoClipper
from services.social_publisher import SocialPublisher, build_post_text
from services.progress_tracker import progress_tracker
from services.youtube_data_api import YouTubeDataAPI
from services.caption_generator import CaptionGenerator
from services.caption_burner import CaptionBurner, CAPTION_STYLES
# DATABASE DISABLED - Using in-memory storage only
# Database operations are commented out, but imports kept for type hints
try:
    from database import get_db, SessionLocal
    from models import Project, Short, Publication, AccountToken
    DATABASE_AVAILABLE = False  # Set to False to disable all DB operations
except:
    # If database modules don't exist, create dummy classes for type hints
    class Project: pass
    class Short: pass
    class Publication: pass
    class AccountToken: pass
    DATABASE_AVAILABLE = False
# from migrate import main as run_migrations
from utils.logging_decorator import log_async_execution, StepLogger
import traceback

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

# ============================================================================
# Global Exception Handlers
# ============================================================================
# Note: More specific exception handlers should be registered first.
# FastAPI will match the most specific handler for each exception type.

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors (Pydantic validation failures)."""
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions with proper logging."""
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        }
    )

@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions."""
    logger.warning(
        f"Starlette HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return a proper error response.
    
    This is the fallback handler for any exception not caught by more specific handlers.
    """
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "query_params": dict(request.query_params),
        }
    )
    
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "type": type(exc).__name__,
        }
    )

# Run database migrations on startup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        # Run migration to add new columns to projects table
        from migrate import add_project_columns
        add_project_columns()
        logger.info("Database migration completed")
        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Error during startup: {e}")

# Initialize services
youtube_processor = YouTubeProcessor()
gemini_analyzer = GeminiAnalyzer()
video_clipper = VideoClipper()
ai_agent = VideoEditingAgent()
youtube_data_api = YouTubeDataAPI()
social_publisher = SocialPublisher()


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


# Constants
ERROR_SHORT_NOT_FOUND = "Short not found"

# In-memory job storage (use Redis/DB in production)
jobs = {}


async def process_video_async(job_id: str, youtube_url: str, max_shorts: int, platform: str):
    """Background task to process video and emit progress updates (OPTIMIZED FOR 20 SECONDS)."""
    # DATABASE DISABLED - Using in-memory storage only
    # db = SessionLocal()
    logger.info("========== STARTING VIDEO PROCESSING ==========")
    logger.info(f"Job ID: {job_id}")
    logger.info(f"YouTube URL: {youtube_url}")
    logger.info(f"Max Shorts: {max_shorts}")
    logger.info(f"Platform: {platform}")
    logger.info("===============================================")
    
    try:
        jobs[job_id] = {"status": "processing", "progress": 0}
        
        # DATABASE DISABLED - Project tracking now in-memory only via jobs dict
        # # Create project record in database
        # with StepLogger("Create Database Project", {"job_id": job_id}):
        #     project = Project(
        #         id=job_id,
        #         youtube_url=str(youtube_url),
        #         video_id="",  # Will be updated after extracting video info
        #         status="processing"
        #     )
        #     db.add(project)
        #     db.commit()
        #     logger.info(f"Project {job_id} created in database")
        
        # STEP 1 & 2: Extract transcript and analyze with retry mechanism
        max_retries = settings.highlight_retry_max_attempts
        retry_delay = settings.highlight_retry_delay
        highlights = None
        video_info = None
        
        for attempt in range(1, max_retries + 1):
            try:
                # STEP 1: Extract transcript (2-3 seconds) - NO VIDEO DOWNLOAD
                if attempt == 1:
                    await progress_tracker.update_progress(job_id, "processing", 10, "Extracting video transcript...")
                    jobs[job_id] = {"status": "processing", "progress": "Extracting video transcript...", "percent": 10}
                else:
                    await progress_tracker.update_progress(
                        job_id, 
                        "processing", 
                        10, 
                        f"Retrying transcript extraction (attempt {attempt}/{max_retries})..."
                    )
                    jobs[job_id] = {"status": "processing", "progress": f"Retrying transcript extraction (attempt {attempt}/{max_retries})...", "percent": 10}
                
                with StepLogger("Extract Transcript", {"url": youtube_url, "attempt": attempt}):
                    try:
                        video_info = youtube_processor.get_transcript(youtube_url)
                        logger.info(f"Transcript extracted (attempt {attempt}): {len(video_info.get('transcript', ''))} chars")
                    except Exception as e:
                        logger.error(f"Failed to extract transcript (attempt {attempt}): {type(e).__name__}: {str(e)}")
                        
                        # On final attempt, try Vosk fallback before failing
                        if attempt == max_retries:
                            logger.warning("YouTube transcript failed. Attempting Vosk offline transcription fallback...")
                            try:
                                await progress_tracker.update_progress(job_id, "processing", 15, "Falling back to offline transcription (Vosk)...")
                                jobs[job_id] = {"status": "processing", "progress": "Falling back to offline transcription (Vosk)...", "percent": 15}
                                
                                # Download video for Vosk processing
                                video_download_info = youtube_processor.download_video(youtube_url)
                                video_path = video_download_info['file_path']
                                
                                # Use Vosk to transcribe
                                from services.caption_generator import CaptionGenerator
                                caption_gen = CaptionGenerator()
                                
                                if caption_gen.use_vosk:
                                    logger.info("Using Vosk for offline transcription...")
                                    audio_path = caption_gen.extract_audio(video_path)
                                    vosk_result = caption_gen.transcribe_with_vosk(audio_path)
                                    
                                    # Convert Vosk result to video_info format
                                    video_info = {
                                        'transcript': vosk_result.get('full_text', ''),
                                        'video_id': video_download_info.get('video_id', ''),
                                        'title': video_download_info.get('title', ''),
                                        'duration': video_download_info.get('duration', 0),
                                        'description': '',
                                        'file_path': video_path
                                    }
                                    logger.info(f"Vosk transcription successful: {len(video_info['transcript'])} chars")
                                    # Clean up audio file
                                    if os.path.exists(audio_path):
                                        os.remove(audio_path)
                                    break  # Success with Vosk, exit retry loop
                                else:
                                    logger.warning("Vosk not available, cannot use offline transcription fallback")
                                    raise RuntimeError(f"Transcript extraction failed after {max_retries} attempts and Vosk unavailable: {str(e)}") from e
                            except Exception as vosk_error:
                                logger.error(f"Vosk fallback also failed: {str(vosk_error)}")
                                logger.error(f"Traceback: {traceback.format_exc()}")
                                raise RuntimeError(f"All transcription methods failed. YouTube: {str(e)}, Vosk: {str(vosk_error)}") from e
                        else:
                            # Wait before retry
                            await asyncio.sleep(retry_delay * attempt)
                            continue
                
                if not video_info.get('transcript'):
                    logger.warning(f"No transcript found for {youtube_url} (attempt {attempt}), using title and description as fallback")
                    # Use existing video_info data - no need to call get_video_info() again
                    video_info['transcript'] = f"{video_info.get('title', '')}. {video_info.get('description', '')}"
                
                # DATABASE DISABLED - Video info now stored in jobs dict only
                # # Update project with video details and cache transcript (only on first successful attempt)
                # if attempt == 1:
                #     with StepLogger("Update Project Details"):
                #         project.video_id = video_info.get('video_id', '')
                #         project.video_title = video_info.get('title', '')
                #         project.video_duration = video_info.get('duration', 0)
                #         # Cache transcript and description to reduce future API calls
                #         project.transcript = video_info.get('transcript', '')
                #         project.video_description = video_info.get('description', '')
                #         project.transcript_fetched_at = datetime.utcnow()
                #         db.commit()
                #         logger.info(f"Project updated: video_id={project.video_id}, title={project.video_title}, duration={project.video_duration}s")
                #         logger.info(f"Transcript cached: {len(project.transcript)} chars")
                
                # Log video info (no DB storage)
                if attempt == 1:
                    logger.info(f"Video info: video_id={video_info.get('video_id', '')}, title={video_info.get('title', '')}, duration={video_info.get('duration', 0)}s")
                    logger.info(f"Transcript length: {len(video_info.get('transcript', ''))} chars")
                
                # STEP 2: Analyze transcript with Gemini (3-5 seconds) - MUCH FASTER than video analysis
                if attempt == 1:
                    await progress_tracker.update_progress(job_id, "processing", 30, "Analyzing content with AI...")
                    jobs[job_id] = {"status": "processing", "progress": "Analyzing content with AI...", "percent": 30}
                else:
                    await progress_tracker.update_progress(
                        job_id, 
                        "processing", 
                        30, 
                        f"Retrying AI analysis (attempt {attempt}/{max_retries})..."
                    )
                    jobs[job_id] = {"status": "processing", "progress": f"Retrying AI analysis (attempt {attempt}/{max_retries})...", "percent": 30}
                
                transcript = video_info.get('transcript', '')
                transcript_length = len(transcript) if transcript else 0
                video_duration = video_info.get('duration', 0)
                video_title = video_info.get('title', '')
                video_description = video_info.get('description', '')
                
                logger.info(f"Analyzing transcript for job {job_id} (attempt {attempt}):")
                logger.info(f"  - Transcript length: {transcript_length} chars")
                logger.info(f"  - Video duration: {video_duration}s")
                logger.info(f"  - Video title: {video_title}")
                logger.info(f"  - Video description length: {len(video_description) if video_description else 0} chars")
                
                # Validate duration
                if video_duration <= 0:
                    logger.warning(f"WARNING: Video duration is {video_duration}s - this may cause highlight detection to fail!")
                
                with StepLogger("Gemini AI Analysis", {"transcript_length": transcript_length, "duration": video_duration, "attempt": attempt}):
                    try:
                        highlights = gemini_analyzer.analyze_transcript_for_highlights(
                            transcript,
                            video_title,
                            video_description,
                            video_duration
                        )
                        logger.info(f"Gemini analysis completed (attempt {attempt}): {len(highlights) if highlights else 0} highlights found")
                        if highlights:
                            for idx, h in enumerate(highlights, 1):
                                logger.info(f"  Highlight {idx}: {h.get('start_time')} - {h.get('end_time')} ({h.get('duration_seconds')}s)")
                        else:
                            logger.warning(f"  No highlights returned from Gemini analyzer!")
                    except Exception as e:
                        logger.error(f"Gemini analysis failed (attempt {attempt}): {type(e).__name__}: {str(e)}")
                        if attempt == max_retries:
                            logger.error(f"Traceback: {traceback.format_exc()}")
                            raise RuntimeError(f"AI analysis failed after {max_retries} attempts: {str(e)}") from e
                        # Wait before retry
                        await asyncio.sleep(retry_delay * attempt)
                        continue
                
                # If highlights found, break out of retry loop
                if highlights and len(highlights) > 0:
                    logger.info(f"Successfully found {len(highlights)} highlights on attempt {attempt}")
                    break
                else:
                    logger.warning(f"No highlights found on attempt {attempt}/{max_retries}")
                    if attempt < max_retries:
                        await progress_tracker.update_progress(
                            job_id, 
                            "processing", 
                            30, 
                            f"No highlights found. Retrying in {retry_delay * attempt}s... (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(retry_delay * attempt)
                    else:
                        # Last attempt failed
                        error_msg = f"No highlights found after {max_retries} attempts (transcript length: {transcript_length} chars, duration: {video_info.get('duration', 0)}s)"
                        logger.warning(f"Job {job_id}: {error_msg}")
                        await progress_tracker.update_progress(job_id, "failed", 100, "No suitable highlights found after retries")
                        jobs[job_id] = {"status": "failed", "error": "No highlights found"}
                        # DATABASE DISABLED
                        # project.status = "failed"
                        # project.error_message = error_msg
                        # db.commit()
                        return
            
            except RuntimeError:
                # Re-raise RuntimeErrors (they're already logged)
                raise
            except Exception as e:
                logger.error(f"Unexpected error during retry attempt {attempt}: {type(e).__name__}: {str(e)}")
                if attempt == max_retries:
                    raise
                await asyncio.sleep(retry_delay * attempt)
                continue
        
        # If we get here without highlights, something went wrong
        if not highlights or len(highlights) == 0:
            error_msg = f"No highlights found after {max_retries} attempts"
            logger.error(f"Job {job_id}: {error_msg}")
            await progress_tracker.update_progress(job_id, "failed", 100, "No suitable highlights found after retries")
            jobs[job_id] = {"status": "failed", "error": "No highlights found"}
            # DATABASE DISABLED
            # project.status = "failed"
            # project.error_message = error_msg
            # db.commit()
            return
        
        max_shorts = min(max_shorts or settings.max_highlights, len(highlights))
        highlights = highlights[:max_shorts]
        logger.info(f"Processing {len(highlights)} highlights (max_shorts={max_shorts})")
        
        # STEP 3: Download ONLY the specific segments (5-8 seconds) - NOT the entire video
        await progress_tracker.update_progress(job_id, "processing", 50, f"Downloading {len(highlights)} segments...")
        jobs[job_id] = {"status": "processing", "progress": f"Downloading {len(highlights)} segments...", "percent": 50}
        
        with StepLogger("Download Video Segments", {"count": len(highlights)}):
            try:
                segment_files = youtube_processor.download_video_segments(
                    youtube_url,
                    highlights,
                    video_info.get('video_id')
                )
                logger.info(f"Downloaded {len(segment_files) if segment_files else 0} segment files")
                
                if segment_files:
                    for i, seg in enumerate(segment_files):
                        logger.info(f"  Segment {i+1}: {seg.get('file_path', 'unknown')}")
            except Exception as e:
                logger.error(f"Segment download failed: {type(e).__name__}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise RuntimeError(f"Video segment download failed: {str(e)}") from e
        
        if not segment_files:
            error_msg = "Failed to download segments - no files returned"
            logger.error(error_msg)
            await progress_tracker.update_progress(job_id, "failed", 100, error_msg)
            jobs[job_id] = {"status": "failed", "error": error_msg}
            # DATABASE DISABLED
            # project.status = "failed"
            # project.error_message = error_msg
            # db.commit()
            return
        
        # STEP 4: Create shorts with MoviePy and smart cropping in parallel (5-10 seconds) - proper landscape-to-portrait conversion
        await progress_tracker.update_progress(job_id, "processing", 70, f"Creating {len(highlights)} shorts...")
        jobs[job_id] = {"status": "processing", "progress": f"Creating {len(highlights)} shorts...", "percent": 70}
        
        with StepLogger("Create Shorts with Smart Cropping", {"count": len(segment_files), "platform": platform}):
            try:
                created_shorts = video_clipper.create_shorts_fast(
                    segment_files,
                    video_info['video_id'],
                    highlights,
                    platform=platform
                )
                logger.info(f"Created {len(created_shorts) if created_shorts else 0} shorts")
                
                if created_shorts:
                    for i, short in enumerate(created_shorts):
                        logger.info(f"  Short {i+1}: {short.get('filename', 'unknown')} ({short.get('duration_seconds', 0)}s)")
            except Exception as e:
                logger.error(f"Shorts creation failed: {type(e).__name__}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise RuntimeError(f"Video shorts creation failed: {str(e)}") from e
        
        if not created_shorts:
            error_msg = "Failed to create shorts - no shorts generated"
            logger.error(error_msg)
            await progress_tracker.update_progress(job_id, "failed", 100, error_msg)
            jobs[job_id] = {"status": "failed", "error": error_msg}
            # DATABASE DISABLED
            # project.status = "failed"
            # project.error_message = error_msg
            # db.commit()
            return
        
        # Helper function to convert timestamp string to seconds
        def timestamp_to_seconds(timestamp_str):
            """Convert timestamp string like '01:20' to seconds (80.0)"""
            if isinstance(timestamp_str, (int, float)):
                return float(timestamp_str)
            parts = str(timestamp_str).split(":")
            if len(parts) == 2:  # MM:SS
                return float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            return 0.0
        
        # Helper function to format seconds as timestamp
        def seconds_to_timestamp(seconds):
            """Convert seconds to MM:SS format"""
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins:02d}:{secs:02d}"
        
        shorts_info = []
        for idx, short in enumerate(created_shorts):
            # DATABASE DISABLED - Create in-memory short info only
            short_id = str(uuid.uuid4())
            
            # # Save short to database
            # db_short = Short(
            #     id=short_id,
            #     project_id=job_id,
            #     filename=short["filename"],
            #     title=short.get("title", f"Highlight {idx + 1}"),
            #     start_time=timestamp_to_seconds(short["start_time"]),
            #     end_time=timestamp_to_seconds(short["end_time"]),
            #     duration_seconds=short["duration_seconds"],
            #     engagement_score=short["engagement_score"],
            #     marketing_effectiveness=short["marketing_effectiveness"],
            #     suggested_cta=short["suggested_cta"]
            # )
            # db.add(db_short)
            
            shorts_info.append({
                "short_id": short_id,
                "title": short.get("title", f"Highlight {idx + 1}"),
                "filename": short["filename"],
                "start_time": seconds_to_timestamp(timestamp_to_seconds(short["start_time"])),
                "end_time": seconds_to_timestamp(timestamp_to_seconds(short["end_time"])),
                "duration": short["duration_seconds"],
                "duration_seconds": short["duration_seconds"],
                "engagement_score": short["engagement_score"],
                "marketing_effectiveness": short["marketing_effectiveness"],
                "suggested_cta": short["suggested_cta"],
                "download_url": f"/api/v1/download/{short['filename']}"
            })
        
        # DATABASE DISABLED - Project status tracking in jobs dict only
        # # Update project status
        # project.status = "completed"
        # db.commit()
        
        jobs[job_id] = {
            "status": "completed",
            "video_title": video_info.get('title', ''),
            "video_duration": video_info.get('duration', 0),
            "shorts": shorts_info,
            "percent": 100
        }
        
        await progress_tracker.update_progress(job_id, "completed", 100, f"Generated {len(shorts_info)} shorts successfully!")
        
        # Cleanup segment files
        await asyncio.sleep(1)
        for segment in segment_files:
            youtube_processor.cleanup(segment['file_path'])
        
    except Exception as e:
        # Comprehensive error logging
        error_type = type(e).__name__
        error_msg = str(e)
        
        logger.error("========== VIDEO PROCESSING FAILED ==========")
        logger.error(f"Job ID: {job_id}")
        logger.error(f"Error Type: {error_type}")
        logger.error(f"Error Message: {error_msg}")
        logger.error(f"Full Traceback:\n{traceback.format_exc()}")
        logger.error("============================================")
        
        # Create user-friendly error message
        user_error_msg = f"{error_type}: {error_msg}"
        
        jobs[job_id] = {"status": "failed", "error": user_error_msg}
        await progress_tracker.update_progress(job_id, "failed", 100, f"Error: {user_error_msg}")
        
        # DATABASE DISABLED - Error tracking in jobs dict only
        # # Update project status in database
        # try:
        #     project = db.query(Project).filter(Project.id == job_id).first()
        #     if project:
        #         project.status = "failed"
        #         project.error_message = user_error_msg
        #         db.commit()
        #         logger.info(f"Project {job_id} marked as failed in database")
        # except Exception as db_error:
        #     logger.error(f"Failed to update database: {type(db_error).__name__}: {str(db_error)}")
    finally:
        logger.info(f"Cleaning up job {job_id}")
        progress_tracker.cleanup_job(job_id)
        # DATABASE DISABLED
        # db.close()
        logger.info("========== VIDEO PROCESSING ENDED ==========\n")


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
async def download_short(filename: str, request: Request):
    """Download a generated short video with Range request support for video streaming."""
    file_path = Path(settings.output_dir) / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get file size
    file_size = file_path.stat().st_size
    
    # Check if Range header is present (required for HTML5 video streaming)
    range_header = request.headers.get('range')
    
    if range_header:
        # Parse range header (format: "bytes=start-end")
        try:
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1
            
            # Ensure valid range
            start = max(0, start)
            end = min(end, file_size - 1)
            content_length = end - start + 1
            
            # Read the requested byte range
            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(content_length)
            
            # Return 206 Partial Content response
            return Response(
                content=data,
                status_code=206,
                headers={
                    'Content-Range': f'bytes {start}-{end}/{file_size}',
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(content_length),
                    'Content-Type': 'video/mp4',
                },
                media_type='video/mp4'
            )
        except (ValueError, IndexError):
            # Invalid range header, fall through to full file response
            pass
    
    # Return full file (no range request or invalid range)
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="video/mp4",
        headers={
            'Accept-Ranges': 'bytes',
            'Content-Length': str(file_size),
        }
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


@app.get("/api/v1/projects")
async def list_projects(skip: int = 0, limit: int = 20):
    """List all projects from the database."""
    db = SessionLocal()
    try:
        projects = db.query(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for project in projects:
            result.append({
                "id": project.id,
                "youtube_url": project.youtube_url,
                "video_id": project.video_id,
                "video_title": project.video_title,
                "video_duration": project.video_duration,
                "status": project.status,
                "error_message": project.error_message,
                "shorts_count": len(project.shorts),
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None
            })
        
        return {"projects": result, "total": len(result)}
    finally:
        db.close()


# ============================================================================
# Share: Multi-platform Publishing
# ============================================================================

class ShareRequest(BaseModel):
    short_id: str
    platforms: List[str]  # e.g., ["linkedin", "instagram", "x"]
    text: Optional[str] = None  # optional override


async def _publish_publication_async(publication_id: str):
    """Background task to publish a single publication."""
    db = SessionLocal()
    try:
        pub = db.query(Publication).filter(Publication.id == publication_id).first()
        if not pub:
            return
        short = db.query(Short).filter(Short.id == pub.short_id).first()
        if not short:
            pub.status = "failed"
            pub.error_message = ERROR_SHORT_NOT_FOUND
            db.commit()
            return

        file_path = str(Path(settings.output_dir) / short.filename)
        # Validate file existence
        if not Path(file_path).exists():
            pub.status = "failed"
            pub.error_message = f"File not found: {file_path}"
            db.commit()
            return
        
        # Validate size against soft limit
        try:
            file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            if file_size_mb > settings.max_upload_mb:
                pub.status = "failed"
                pub.error_message = f"File too large: {file_size_mb:.1f}MB > {settings.max_upload_mb}MB"
                db.commit()
                return
        except Exception:
            pass

        # Ensure account token exists for platform
        token = db.query(AccountToken).filter(AccountToken.platform == pub.platform).first()
        if not token:
            pub.status = "failed"
            pub.error_message = f"No connected account/token for platform: {pub.platform}"
            db.commit()
            return

        # Build text: prefer provided platform_description/title/cta + hashtags
        base_text = short.platform_description or short.title or ""
        if short.cta:
            base_text = f"{base_text}\n\n{short.cta}".strip()
        text_to_post = build_post_text(pub.platform, base_text, short.hashtags)

        pub.status = "processing"
        db.commit()

        # Prepare metadata and persist payload snapshot
        # Parse hashtags from comma-separated string
        tags_list = []
        if short.hashtags:
            try:
                tags_list = [tag.strip() for tag in short.hashtags.split(',') if tag.strip()]
            except Exception:
                pass
        
        payload = {
            "platform": pub.platform,
            "file_path": file_path,
            "text": text_to_post,
            "metadata": {
                "title": short.platform_title or short.title or "",
                "description": short.platform_description or short.title or "",
                "tags": tags_list,
                "privacy": "public"  # Can be made configurable
            },
            "token_id": token.id
        }
        try:
            import json as _json
            pub.payload = _json.dumps(payload)
            db.commit()
        except Exception:
            pass

        # Retry with exponential backoff
        attempts = 0
        result = None
        last_error = None
        while attempts < (settings.share_max_retries or 1):
            attempts += 1
            result = social_publisher.publish(
                platform=pub.platform,
                file_path=file_path,
                text=text_to_post,
                metadata={**payload["metadata"], "token_id": token.id}
            )
            if result and result.success:
                break
            last_error = result.error if result else "unknown error"
            # Backoff: 0.5, 1.0, 2.0 ... seconds
            await asyncio.sleep(0.5 * (2 ** (attempts - 1)))

        if result and result.success:
            pub.status = "published"
            pub.external_post_id = result.external_post_id
            pub.external_url = result.external_url
            pub.error_message = None
        else:
            pub.status = "failed"
            pub.error_message = last_error or "publish failed"
        db.commit()
    except Exception as e:
        try:
            pub = db.query(Publication).filter(Publication.id == publication_id).first()
            if pub:
                pub.status = "failed"
                pub.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@app.post("/api/v1/share")
async def share_short(request: ShareRequest, background_tasks: BackgroundTasks):
    """Create per-platform publication jobs for a short and run them asynchronously."""
    db = SessionLocal()
    try:
        short = db.query(Short).filter(Short.id == request.short_id).first()
        if not short:
            raise HTTPException(status_code=404, detail=ERROR_SHORT_NOT_FOUND)

        # Validate platforms against allowed list
        allowed = {p.strip().lower() for p in (settings.allowed_platforms or "").split(',') if p.strip()}
        invalid = [p for p in request.platforms if p.lower() not in allowed]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unsupported platforms: {', '.join(invalid)}")

        created = []
        for platform in request.platforms:
            pub = Publication(
                id=str(uuid.uuid4()),
                short_id=short.id,
                platform=platform.lower(),
                status="queued",
                payload=None
            )
            db.add(pub)
            db.commit()

            background_tasks.add_task(_publish_publication_async, pub.id)
            created.append({
                "publication_id": pub.id,
                "platform": pub.platform,
                "status": pub.status
            })

        return {"short_id": short.id, "publications": created}
    finally:
        db.close()


@app.get("/api/v1/share/{publication_id}")
async def get_publication_status(publication_id: str):
    """Get status of a single publication job."""
    db = SessionLocal()
    try:
        pub = db.query(Publication).filter(Publication.id == publication_id).first()
        if not pub:
            raise HTTPException(status_code=404, detail="Publication not found")
        return {
            "publication_id": pub.id,
            "short_id": pub.short_id,
            "platform": pub.platform,
            "status": pub.status,
            "external_post_id": pub.external_post_id,
            "external_url": pub.external_url,
            "error_message": pub.error_message,
            "created_at": pub.created_at.isoformat() if pub.created_at else None,
            "updated_at": pub.updated_at.isoformat() if pub.updated_at else None,
        }
    finally:
        db.close()


@app.post("/api/v1/share/{publication_id}/retry")
async def retry_publication(publication_id: str, background_tasks: BackgroundTasks):
    """Retry a failed publication."""
    db = SessionLocal()
    try:
        pub = db.query(Publication).filter(Publication.id == publication_id).first()
        if not pub:
            raise HTTPException(status_code=404, detail="Publication not found")
        
        if pub.status == "published":
            raise HTTPException(status_code=400, detail="Publication already succeeded")
        
        # Reset status to queued
        pub.status = "queued"
        pub.error_message = None
        db.commit()
        
        # Queue background task
        background_tasks.add_task(_publish_publication_async, publication_id)
        
        return {
            "publication_id": pub.id,
            "status": "queued",
            "message": "Publication queued for retry"
        }
    finally:
        db.close()


# YouTube OAuth 2.0 Endpoints
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:5173/youtube-oauth-callback")


@app.get("/api/v1/youtube/oauth/authorize")
async def youtube_oauth_authorize():
    """Initiate YouTube OAuth 2.0 flow."""
    try:
        from google_auth_oauthlib.flow import Flow
        import secrets
        
        if not settings.youtube_client_id or not settings.youtube_client_secret:
            raise HTTPException(
                status_code=500,
                detail="YouTube OAuth not configured. Please set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET."
            )
        
        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.youtube_client_id,
                    "client_secret": settings.youtube_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [YOUTUBE_REDIRECT_URI]
                }
            },
            scopes=YOUTUBE_SCOPES
        )
        flow.redirect_uri = YOUTUBE_REDIRECT_URI
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Get authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent to get refresh token
        )
        
        return {
            "authorization_url": authorization_url,
            "state": state
        }
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="google-auth-oauthlib not installed. Please install it: pip install google-auth-oauthlib"
        )
    except Exception as e:
        logger.error(f"YouTube OAuth authorize error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth authorization failed: {str(e)}")


@app.get("/api/v1/youtube/oauth/callback")
async def youtube_oauth_callback(code: str, state: Optional[str] = None):
    """Handle YouTube OAuth 2.0 callback and store tokens."""
    db = SessionLocal()
    try:
        from google_auth_oauthlib.flow import Flow
        from google.oauth2.credentials import Credentials
        
        if not settings.youtube_client_id or not settings.youtube_client_secret:
            raise HTTPException(
                status_code=500,
                detail="YouTube OAuth not configured."
            )
        
        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.youtube_client_id,
                    "client_secret": settings.youtube_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [YOUTUBE_REDIRECT_URI]
                }
            },
            scopes=YOUTUBE_SCOPES
        )
        flow.redirect_uri = YOUTUBE_REDIRECT_URI
        
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get channel info to identify the account
        try:
            from googleapiclient.discovery import build
            youtube = build('youtube', 'v3', credentials=credentials)
            channel_response = youtube.channels().list(part='snippet', mine=True).execute()
            
            if channel_response.get('items'):
                channel = channel_response['items'][0]
                channel_id = channel['id']
                channel_title = channel['snippet'].get('title', 'Unknown')
            else:
                channel_id = "unknown"
                channel_title = "Unknown"
        except Exception as e:
            logger.warning(f"Could not fetch channel info: {str(e)}")
            channel_id = "unknown"
            channel_title = "Unknown"
        
        # Check if token already exists for this platform
        existing_token = db.query(AccountToken).filter(
            AccountToken.platform == "youtube_shorts"
        ).first()
        
        if existing_token:
            # Update existing token
            existing_token.access_token = credentials.token
            existing_token.refresh_token = credentials.refresh_token or existing_token.refresh_token
            existing_token.expires_at = credentials.expiry
            token_id = existing_token.id
            logger.info(f"Updated YouTube token {token_id}")
        else:
            # Create new token
            token_id = str(uuid.uuid4())
            new_token = AccountToken(
                id=token_id,
                platform="youtube_shorts",
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                expires_at=credentials.expiry
            )
            db.add(new_token)
            logger.info(f"Created new YouTube token {token_id}")
        
        db.commit()
        
        return {
            "success": True,
            "message": "YouTube account connected successfully",
            "channel_id": channel_id,
            "channel_title": channel_title,
            "token_id": token_id
        }
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="google-auth-oauthlib not installed. Please install it: pip install google-auth-oauthlib"
        )
    except Exception as e:
        logger.error(f"YouTube OAuth callback error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")
    finally:
        db.close()


@app.get("/api/v1/youtube/oauth/status")
async def youtube_oauth_status():
    """Check if YouTube account is connected and token is valid."""
    db = SessionLocal()
    try:
        token = db.query(AccountToken).filter(
            AccountToken.platform == "youtube_shorts"
        ).first()
        
        if not token:
            return {
                "connected": False,
                "message": "YouTube account not connected"
            }
        
        # Check if token is expired
        is_expired = False
        if token.expires_at:
            from datetime import datetime, timezone
            is_expired = token.expires_at < datetime.now(timezone.utc)
        
        # Try to validate token by fetching channel info
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            if not settings.youtube_client_id or not settings.youtube_client_secret:
                return {
                    "connected": True,
                    "expired": is_expired,
                    "message": "Token exists but OAuth not fully configured"
                }
            
            creds_data = {
                "token": token.access_token,
                "refresh_token": token.refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": settings.youtube_client_id,
                "client_secret": settings.youtube_client_secret,
                "scopes": YOUTUBE_SCOPES
            }
            
            credentials = Credentials.from_authorized_user_info(creds_data)
            
            # Try to refresh if expired
            if is_expired and token.refresh_token:
                try:
                    from google.auth.transport.requests import Request as GoogleRequest
                    credentials.refresh(GoogleRequest())
                    
                    # Update token in database
                    token.access_token = credentials.token
                    if credentials.refresh_token:
                        token.refresh_token = credentials.refresh_token
                    if credentials.expiry:
                        token.expires_at = credentials.expiry
                    db.commit()
                    is_expired = False
                except Exception as refresh_error:
                    logger.error(f"Token refresh failed: {str(refresh_error)}")
            
            # Test token by fetching channel info
            youtube = build('youtube', 'v3', credentials=credentials)
            channel_response = youtube.channels().list(part='snippet', mine=True).execute()
            
            if channel_response.get('items'):
                channel = channel_response['items'][0]
                return {
                    "connected": True,
                    "expired": is_expired,
                    "channel_id": channel['id'],
                    "channel_title": channel['snippet'].get('title', 'Unknown'),
                    "message": "YouTube account connected and token is valid"
                }
            else:
                return {
                    "connected": True,
                    "expired": is_expired,
                    "message": "Token exists but could not fetch channel info"
                }
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return {
                "connected": True,
                "expired": True,
                "message": f"Token exists but validation failed: {str(e)}"
            }
    finally:
        db.close()


@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project with all its shorts from the database."""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Helper function to format seconds as timestamp
        def seconds_to_timestamp(seconds):
            """Convert seconds to MM:SS format"""
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins:02d}:{secs:02d}"
        
        shorts_info = []
        for short in project.shorts:
            shorts_info.append({
                "short_id": short.id,
                "title": short.title,
                "filename": short.filename,
                "start_time": seconds_to_timestamp(short.start_time),
                "end_time": seconds_to_timestamp(short.end_time),
                "duration": short.duration_seconds,
                "duration_seconds": short.duration_seconds,
                "engagement_score": short.engagement_score,
                "marketing_effectiveness": short.marketing_effectiveness,
                "suggested_cta": short.suggested_cta,
                "download_url": f"/api/v1/download/{short.filename}",
                "created_at": short.created_at.isoformat() if short.created_at else None
            })
        
        return {
            "id": project.id,
            "youtube_url": project.youtube_url,
            "video_id": project.video_id,
            "video_title": project.video_title,
            "video_duration": project.video_duration,
            "status": project.status,
            "error_message": project.error_message,
            "shorts": shorts_info,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None
        }
    finally:
        db.close()


# ============================================================================
# YouTube Data API Endpoints
# ============================================================================

@app.get("/api/v1/youtube/video/statistics/{video_id_or_url}")
async def get_video_statistics(video_id_or_url: str):
    """
    Get detailed statistics for a YouTube video including views, likes, comments.
    
    Args:
        video_id_or_url: YouTube video ID or full URL
    
    Returns:
        Video statistics including views, likes, comments, duration, etc.
    """
    try:
        stats = youtube_data_api.get_video_statistics(video_id_or_url)
        return stats
    except Exception as e:
        logger.error(f"Error getting video statistics: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/youtube/channel/statistics/{channel_id_or_url}")
async def get_channel_statistics(channel_id_or_url: str):
    """
    Get detailed statistics for a YouTube channel.
    
    Args:
        channel_id_or_url: YouTube channel ID or channel URL
    
    Returns:
        Channel statistics including subscriber count, video count, total views, etc.
    """
    try:
        stats = youtube_data_api.get_channel_statistics(channel_id_or_url)
        return stats
    except Exception as e:
        logger.error(f"Error getting channel statistics: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/youtube/video/comments/{video_id_or_url}")
async def get_video_comments(
    video_id_or_url: str,
    max_results: int = 20,
    order: str = "relevance"
):
    """
    Get top comments for a YouTube video.
    
    Args:
        video_id_or_url: YouTube video ID or URL
        max_results: Maximum number of comments (1-100)
        order: Sort order - 'relevance' or 'time'
    
    Returns:
        List of comments with author, text, likes, and reply count
    """
    try:
        if max_results > 100:
            max_results = 100
        
        comments = youtube_data_api.get_video_comments(
            video_id_or_url,
            max_results=max_results,
            order=order
        )
        return {"comments": comments, "count": len(comments)}
    except Exception as e:
        logger.error(f"Error getting video comments: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/youtube/search")
async def search_videos(
    query: str,
    max_results: int = 25,
    order: str = "relevance",
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
    region_code: Optional[str] = None
):
    """
    Search for YouTube videos.
    
    Args:
        query: Search query string
        max_results: Maximum results (1-50)
        order: Sort order - 'relevance', 'date', 'rating', or 'viewCount'
        published_after: ISO 8601 date (e.g., '2024-01-01T00:00:00Z')
        published_before: ISO 8601 date
        region_code: 2-letter country code (e.g., 'US', 'GB')
    
    Returns:
        List of matching videos with metadata
    """
    try:
        if max_results > 50:
            max_results = 50
        
        videos = youtube_data_api.search_videos(
            query=query,
            max_results=max_results,
            order=order,
            published_after=published_after,
            published_before=published_before,
            region_code=region_code
        )
        return {"videos": videos, "count": len(videos)}
    except Exception as e:
        logger.error(f"Error searching videos: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/youtube/trending")
async def get_trending_videos(
    region_code: str = "US",
    max_results: int = 25,
    category_id: Optional[str] = None
):
    """
    Get trending videos for a region.
    
    Args:
        region_code: 2-letter country code (e.g., 'US', 'GB', 'IN')
        max_results: Maximum results (1-50)
        category_id: Optional YouTube category ID for filtering
    
    Returns:
        List of trending videos with statistics
    """
    try:
        if max_results > 50:
            max_results = 50
        
        videos = youtube_data_api.get_trending_videos(
            region_code=region_code,
            max_results=max_results,
            category_id=category_id
        )
        return {"videos": videos, "count": len(videos)}
    except Exception as e:
        logger.error(f"Error fetching trending videos: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/youtube/related/{video_id_or_url}")
async def get_related_videos(
    video_id_or_url: str,
    max_results: int = 25
):
    """
    Get videos related to a specific YouTube video.
    
    Args:
        video_id_or_url: YouTube video ID or URL
        max_results: Maximum results (1-50)
    
    Returns:
        List of related videos
    """
    try:
        if max_results > 50:
            max_results = 50
        
        videos = youtube_data_api.get_related_videos(
            video_id_or_url,
            max_results=max_results
        )
        return {"videos": videos, "count": len(videos)}
    except Exception as e:
        logger.error(f"Error fetching related videos: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/youtube/playlist/{playlist_id}")
async def get_playlist_videos(
    playlist_id: str,
    max_results: int = 50
):
    """
    Get all videos from a YouTube playlist.
    
    Args:
        playlist_id: YouTube playlist ID
        max_results: Maximum videos to retrieve
    
    Returns:
        List of videos in the playlist
    """
    try:
        videos = youtube_data_api.get_playlist_videos(
            playlist_id,
            max_results=max_results
        )
        return {"videos": videos, "count": len(videos)}
    except Exception as e:
        logger.error(f"Error fetching playlist videos: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/youtube/categories")
async def get_video_categories(region_code: str = "US"):
    """
    Get all available YouTube video categories for a region.
    
    Args:
        region_code: 2-letter country code (e.g., 'US', 'GB', 'IN')
    
    Returns:
        List of video categories with IDs and titles
    """
    try:
        categories = youtube_data_api.get_video_categories(region_code=region_code)
        return {"categories": categories, "count": len(categories)}
    except Exception as e:
        logger.error(f"Error fetching video categories: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# AI Agent Chat Endpoint
class ChatRequest(BaseModel):
    """Request model for AI chat commands."""
    message: str
    clips: List[dict]
    selected_clip_index: Optional[int] = 0
    project_id: Optional[str] = None


@app.post("/api/v1/chat")
async def chat_with_ai(request: ChatRequest):
    """
    Chat with AI agent for conversational video editing.
    
    Args:
        message: User's natural language command
        clips: Current list of video clips
        selected_clip_index: Index of currently selected clip
        project_id: Optional project ID for context
    
    Returns:
        Updated clips and AI response
    """
    try:
        # Parse the command using AI agent
        result = ai_agent.process_command(
            user_message=request.message,
            clips=request.clips,
            selected_clip_index=request.selected_clip_index
        )
        
        if not result.get("success", False):
            return {
                "clips": request.clips,
                "response": result.get("response", "Sorry, I couldn't understand that."),
                "success": False
            }
        
        # Get operations to execute
        operations = result.get("operations", [])
        updated_clips = request.clips.copy()
        
        # Execute each operation
        for op in operations:
            op_type = op.get("type", "none")
            clip_index = op.get("clip_index", request.selected_clip_index)
            params = op.get("parameters", {})
            
            # Validate clip index
            if clip_index < 0 or clip_index >= len(updated_clips):
                logger.warning(f"Invalid clip index {clip_index}, skipping operation")
                continue
            
            clip = updated_clips[clip_index]
            
            # Try to get file path from various possible fields
            clip_path = clip.get("file_path") or clip.get("path")
            
            # If no path, try to derive from filename
            if not clip_path:
                filename = clip.get("filename")
                if filename:
                    # Construct path from output directory + filename
                    clip_path = str(Path(settings.output_dir) / filename)
                    logger.info(f"Derived clip path from filename: {clip_path}")
            
            # Validate file exists
            if not clip_path:
                logger.error(f"Clip {clip_index} has no file path or filename: {clip}")
                continue
                
            if not Path(clip_path).exists():
                logger.error(f"Clip file not found: {clip_path} (clip data: {clip})")
                continue
            
            logger.info(f"Processing {op_type} operation on clip {clip_index}: {clip_path}")
            
            try:
                # Execute operation based on type
                if op_type == "trim":
                    new_start = params.get("new_start")
                    new_end = params.get("new_end")
                    new_path = video_clipper.trim_clip(
                        clip_path, 
                        new_start=new_start, 
                        new_end=new_end
                    )
                    # Update both file_path and filename
                    updated_clips[clip_index]["file_path"] = new_path
                    updated_clips[clip_index]["path"] = new_path
                    updated_clips[clip_index]["filename"] = Path(new_path).name
                    updated_clips[clip_index]["download_url"] = f"/api/v1/download/{Path(new_path).name}"
                    if new_start is not None:
                        updated_clips[clip_index]["start_time"] = new_start
                    if new_end is not None:
                        updated_clips[clip_index]["end_time"] = new_end
                        if new_start is not None:
                            updated_clips[clip_index]["duration"] = new_end - new_start
                
                elif op_type == "shorten":
                    target_duration = params.get("target_duration")
                    reduce_by = params.get("reduce_by")
                    new_path = video_clipper.adjust_duration(
                        clip_path,
                        target_duration=target_duration,
                        reduce_by=reduce_by
                    )
                    updated_clips[clip_index]["file_path"] = new_path
                    updated_clips[clip_index]["path"] = new_path
                    updated_clips[clip_index]["filename"] = Path(new_path).name
                    updated_clips[clip_index]["download_url"] = f"/api/v1/download/{Path(new_path).name}"
                    if target_duration:
                        updated_clips[clip_index]["duration"] = target_duration
                
                elif op_type == "extend":
                    extend_by = params.get("extend_by")
                    target_duration = params.get("target_duration")
                    new_path = video_clipper.adjust_duration(
                        clip_path,
                        target_duration=target_duration,
                        extend_by=extend_by
                    )
                    updated_clips[clip_index]["file_path"] = new_path
                    updated_clips[clip_index]["path"] = new_path
                    updated_clips[clip_index]["filename"] = Path(new_path).name
                    updated_clips[clip_index]["download_url"] = f"/api/v1/download/{Path(new_path).name}"
                    if target_duration:
                        updated_clips[clip_index]["duration"] = target_duration
                
                elif op_type == "speed_adjust":
                    speed_factor = params.get("speed_factor", 1.0)
                    new_path = video_clipper.change_speed(clip_path, speed_factor)
                    updated_clips[clip_index]["file_path"] = new_path
                    updated_clips[clip_index]["path"] = new_path
                    updated_clips[clip_index]["filename"] = Path(new_path).name
                    updated_clips[clip_index]["download_url"] = f"/api/v1/download/{Path(new_path).name}"
                    # Adjust duration based on speed
                    current_duration = clip.get("duration", 30)
                    updated_clips[clip_index]["duration"] = current_duration / speed_factor
                
                elif op_type == "split":
                    split_at = params.get("split_at", 0)
                    part1_path, part2_path = video_clipper.split_clip(clip_path, split_at)
                    # Replace original clip with first part
                    updated_clips[clip_index]["file_path"] = part1_path
                    updated_clips[clip_index]["path"] = part1_path
                    updated_clips[clip_index]["filename"] = Path(part1_path).name
                    updated_clips[clip_index]["download_url"] = f"/api/v1/download/{Path(part1_path).name}"
                    updated_clips[clip_index]["duration"] = split_at
                    # Insert second part after current clip
                    new_clip = clip.copy()
                    new_clip["file_path"] = part2_path
                    new_clip["path"] = part2_path
                    new_clip["filename"] = Path(part2_path).name
                    new_clip["download_url"] = f"/api/v1/download/{Path(part2_path).name}"
                    new_clip["title"] = f"{clip.get('title', 'Clip')} - Part 2"
                    new_clip["start_time"] = clip.get("start_time", 0) + split_at
                    updated_clips.insert(clip_index + 1, new_clip)
                
                elif op_type == "add_captions":
                    style = params.get("style", "bold_modern")
                    new_path = video_clipper.add_captions(clip_path, style=style)
                    # Only update if captioning succeeded
                    if new_path and Path(new_path).exists():
                        updated_clips[clip_index]["file_path"] = new_path
                        updated_clips[clip_index]["path"] = new_path
                        updated_clips[clip_index]["filename"] = Path(new_path).name
                        updated_clips[clip_index]["download_url"] = f"/api/v1/download/{Path(new_path).name}"
                        updated_clips[clip_index]["has_captions"] = True
                    else:
                        logger.warning(f"Captions operation returned invalid path: {new_path}")
                
                elif op_type == "delete":
                    # Remove clip from list
                    updated_clips.pop(clip_index)
                
                elif op_type == "reorder":
                    new_index = params.get("new_index", clip_index)
                    if 0 <= new_index < len(updated_clips):
                        clip_to_move = updated_clips.pop(clip_index)
                        updated_clips.insert(new_index, clip_to_move)
                
                logger.info(f"Executed {op_type} operation on clip {clip_index}")
            
            except Exception as op_error:
                logger.error(f"Error executing {op_type} operation: {str(op_error)}")
                # Continue with other operations even if one fails
                continue
        
        return {
            "clips": updated_clips,
            "response": result.get("response", "Done!"),
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat error: {str(e)}"
        )

# ============================================================================
# AI Text Features: Metadata, Captions, Thumbnail
# ============================================================================

class GenerateMetadataRequest(BaseModel):
    project_id: Optional[str] = None
    short_id: Optional[str] = None
    platform: Optional[str] = "default"
    tone: Optional[str] = None


class GenerateCaptionsRequest(BaseModel):
    short_id: str
    language: Optional[str] = "en"
    variants: Optional[int] = 3
    words_per_minute: Optional[int] = None


class GenerateThumbnailPromptRequest(BaseModel):
    short_id: str
    platform: Optional[str] = "default"


def _fetch_project_and_transcript(db, project_id: Optional[str] = None, short: Optional[Short] = None):  # DATABASE DISABLED - DB operations commented out
    """Helper to get project, transcript text, and ensure basic availability.
    
    Uses cached transcript if available to reduce YouTube API calls.
    """
    project = None
    if short and not project_id:
        project = db.query(Project).filter(Project.id == short.project_id).first()
    elif project_id:
        project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Use cached transcript if available
    if project.transcript and project.transcript.strip():
        logger.info(f"Using cached transcript for project {project.id} ({len(project.transcript)} chars)")
        info = {
            'transcript': project.transcript,
            'duration': project.video_duration or 0,
            'title': project.video_title or '',
            'video_id': project.video_id or '',
            'thumbnail': '',
            'description': project.video_description or ''
        }
        return project, info
    
    # Fetch transcript if not cached
    try:
        logger.info(f"Fetching transcript for project {project.id} (not cached)")
        info = youtube_processor.get_transcript(project.youtube_url)
        # Cache the transcript for future use
        project.transcript = info.get('transcript', '')
        project.video_description = info.get('description', '')
        project.transcript_fetched_at = datetime.utcnow()
        db.commit()
        logger.info(f"Cached transcript for project {project.id}")
    except Exception as e:
        logger.warning(f"Transcript fetch failed, falling back to video info: {e}")
        info = youtube_processor.get_video_info(project.youtube_url)
        info["transcript"] = f"{info.get('title','')}. {info.get('description','')}"
        # Cache the fallback transcript
        project.transcript = info.get('transcript', '')
        project.video_description = info.get('description', '')
        project.transcript_fetched_at = datetime.utcnow()
        db.commit()
    
    return project, info


@app.post("/api/v1/generate-metadata")
async def generate_metadata(request: GenerateMetadataRequest):
    """Generate platform-specific title, description, hashtags, and CTA for a short or project."""
    db = SessionLocal()
    try:
        short = None
        if request.short_id:
            short = db.query(Short).filter(Short.id == request.short_id).first()
            if not short:
                raise HTTPException(status_code=404, detail=ERROR_SHORT_NOT_FOUND)
        project, info = _fetch_project_and_transcript(db, project_id=request.project_id, short=short)

        transcript = info.get("transcript", "")
        meta = gemini_analyzer.generate_metadata(
            transcript=transcript,
            platform=request.platform or "default"
        )

        if short:
            short.platform_title = meta.get("title", "")
            short.platform_description = meta.get("description", "")
            # store hashtags as comma-separated for simplicity
            hashtags_list = meta.get("hashtags", []) or []
            short.hashtags = ",".join(hashtags_list)
            short.cta = meta.get("cta", "")
            # keep suggested_cta for backward compatibility surfaces
            short.suggested_cta = short.cta or short.suggested_cta
            db.commit()

        return {
            "project_id": project.id,
            "short_id": short.id if short else None,
            "metadata": meta
        }
    finally:
        db.close()


@app.post("/api/v1/captions")
async def generate_captions(request: GenerateCaptionsRequest):
    """Generate SRT captions and variants for a short using the video transcript."""
    db = SessionLocal()
    try:
        short = db.query(Short).filter(Short.id == request.short_id).first()
        if not short:
            raise HTTPException(status_code=404, detail=ERROR_SHORT_NOT_FOUND)
        project, info = _fetch_project_and_transcript(db, short=short)

        transcript = info.get("transcript", "")
        caps = gemini_analyzer.generate_captions(
            transcript=transcript,
            language=request.language or "en",
            variants=request.variants or 3,
            words_per_minute=request.words_per_minute
        )

        short.captions_srt = caps.get("srt", "")
        import json as _json
        try:
            short.captions_alt = _json.dumps(caps.get("variants", []))
        except Exception:
            short.captions_alt = "[]"
        short.language = request.language or "en"
        db.commit()

        return {
            "project_id": project.id,
            "short_id": short.id,
            "captions": caps
        }
    finally:
        db.close()


@app.post("/api/v1/thumbnail/prompt")
async def generate_thumbnail_prompt(request: GenerateThumbnailPromptRequest):
    """Generate thumbnail headline and style guidance for a short."""
    db = SessionLocal()
    try:
        short = db.query(Short).filter(Short.id == request.short_id).first()
        if not short:
            raise HTTPException(status_code=404, detail=ERROR_SHORT_NOT_FOUND)
        project, info = _fetch_project_and_transcript(db, short=short)

        transcript = info.get("transcript", "")
        th = gemini_analyzer.generate_thumbnail_prompt(
            transcript=transcript,
            platform=request.platform or "default"
        )

        import json as _json
        short.thumbnail_copy = th.get("headline", "")
        try:
            short.thumbnail_style = _json.dumps(th.get("style", {}))
        except Exception:
            short.thumbnail_style = "{}"
        db.commit()

        return {
            "project_id": project.id,
            "short_id": short.id,
            "thumbnail": th
        }
    finally:
        db.close()


# ============================================================================
# CAPTION GENERATION ENDPOINTS
# ============================================================================

# In-memory caption storage (upgrade to database in production)
captions_storage = {}

@app.post("/api/v1/clips/{clip_id}/generate-captions")
async def generate_captions(clip_id: int, background_tasks: BackgroundTasks):
    """Generate captions for a video clip using Gemini AI"""
    try:
        db = SessionLocal()
        try:
            # Get clip/short from database
            short = db.query(Short).filter(Short.id == clip_id).first()
            
            if not short:
                raise HTTPException(status_code=404, detail="Clip not found")
            
            # Get video file path
            video_path = short.file_path
            if not video_path or not Path(video_path).exists():
                raise HTTPException(status_code=404, detail="Video file not found")
            
            # Create background job
            job_id = str(uuid.uuid4())
            
            # Add background task
            background_tasks.add_task(
                generate_captions_task,
                job_id=job_id,
                clip_id=clip_id,
                video_path=video_path
            )
            
            return {
                "job_id": job_id,
                "status": "processing",
                "message": "Generating captions from video audio..."
            }
        finally:
            db.close()
            
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_captions_task(job_id: str, clip_id: int, video_path: str):
    """Background task to generate captions"""
    try:
        # Update progress
        await progress_tracker.update_progress(job_id, "processing", 10, "Extracting audio...")
        
        # Initialize caption generator
        generator = CaptionGenerator()
        
        # Generate captions
        await progress_tracker.update_progress(job_id, "processing", 30, "Transcribing audio with AI...")
        caption_file = generator.generate_caption_file(clip_id, video_path)
        
        # Load caption data
        import json
        with open(caption_file, 'r', encoding='utf-8') as f:
            captions_data = json.load(f)
        
        await progress_tracker.update_progress(job_id, "processing", 80, "Finalizing captions...")
        
        # Store captions
        captions_storage[clip_id] = captions_data
        
        await progress_tracker.update_progress(
            job_id,
            "completed",
            100,
            "Captions generated successfully",
            result={
                "captions": captions_data,
                "caption_file": caption_file
            }
        )
        
    except RuntimeError as e:
        await progress_tracker.update_progress(
            job_id,
            "failed",
            0,
            f"Caption generation failed: {str(e)}"
        )


@app.get("/api/v1/clips/{clip_id}/captions")
async def get_captions(clip_id: int):
    """Get generated captions for a clip"""
    if clip_id not in captions_storage:
        raise HTTPException(
            status_code=404,
            detail="Captions not found. Generate them first using /generate-captions"
        )
    
    return {
        "clip_id": clip_id,
        "captions": captions_storage[clip_id],
        "available_styles": list(CAPTION_STYLES.keys()),
        "styles": {
            key: value["name"]
            for key, value in CAPTION_STYLES.items()
        }
    }


@app.post("/api/v1/clips/{clip_id}/apply-captions")
async def apply_captions(
    clip_id: int,
    style_name: str,
    background_tasks: BackgroundTasks
):
    """Burn captions into video with selected style"""
    try:
        # Validate style
        if style_name not in CAPTION_STYLES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid style. Choose from: {list(CAPTION_STYLES.keys())}"
            )
        
        # Check if captions exist
        if clip_id not in captions_storage:
            raise HTTPException(
                status_code=404,
                detail="Captions not found. Generate them first using /generate-captions"
            )
        
        # Get clip from database
        db = SessionLocal()
        try:
            short = db.query(Short).filter(Short.id == clip_id).first()
            
            if not short:
                raise HTTPException(status_code=404, detail="Clip not found")
            
            video_path = short.file_path
            if not video_path or not Path(video_path).exists():
                raise HTTPException(status_code=404, detail="Video file not found")
            
            captions = captions_storage[clip_id]
            
            # Create background job
            job_id = str(uuid.uuid4())
            
            background_tasks.add_task(
                burn_captions_task,
                job_id=job_id,
                clip_id=clip_id,
                video_path=video_path,
                captions=captions["words"],
                style_name=style_name
            )
            
            return {
                "job_id": job_id,
                "status": "processing",
                "message": f"Applying {CAPTION_STYLES[style_name]['name']} style..."
            }
        finally:
            db.close()
            
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


async def burn_captions_task(
    job_id: str,
    clip_id: int,
    video_path: str,
    captions: list,
    style_name: str
):
    """Background task to burn captions into video"""
    try:
        await progress_tracker.update_progress(job_id, "processing", 20, "Preparing caption render...")
        
        # Initialize caption burner
        burner = CaptionBurner()
        
        # Generate output path
        output_path = str(Path(video_path).with_stem(f"{Path(video_path).stem}_captioned_{style_name}"))
        
        await progress_tracker.update_progress(job_id, "processing", 40, "Rendering captions into video...")
        
        # Burn captions
        result_path = burner.burn_captions(video_path, captions, style_name, output_path)
        
        await progress_tracker.update_progress(job_id, "processing", 90, "Updating database...")
        
        # Update database with new file path
        db = SessionLocal()
        try:
            short = db.query(Short).filter(Short.id == clip_id).first()
            if short:
                short.file_path = result_path
                short.has_captions = True
                db.commit()
        finally:
            db.close()
        
        await progress_tracker.update_progress(
            job_id,
            "completed",
            100,
            "Captions applied successfully",
            result={
                "new_file_path": result_path,
                "style": style_name
            }
        )
        
    except RuntimeError as e:
        await progress_tracker.update_progress(
            job_id,
            "failed",
            0,
            f"Caption burning failed: {str(e)}"
        )


# ==================== BRAND LOGO ENDPOINTS ====================

class LogoUploadResponse(BaseModel):
    """Response for logo upload."""
    success: bool
    message: str
    logo_path: Optional[str] = None
    logo_info: Optional[dict] = None


class ApplyLogoRequest(BaseModel):
    """Request for applying logo to clip."""
    position: str = "bottom-right"
    size_percent: float = 10.0
    opacity: float = 0.8
    padding: int = 20
    create_new_clip: bool = False  # If True, creates new clip; if False, replaces original


@app.post("/api/v1/upload-logo")
async def upload_logo(file: UploadFile = File(...)) -> LogoUploadResponse:
    """
    Upload a brand logo image for video overlay.
    
    Args:
        file: Logo image file (PNG, JPG, GIF, BMP)
        
    Returns:
        LogoUploadResponse with upload status and logo info
    """
    try:
        from services.logo_overlay import LogoOverlay
        
        # Validate file type
        allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/bmp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: PNG, JPG, GIF, BMP. Got: {file.content_type}"
            )
        
        # Create logos directory
        logos_dir = Path("uploads/logos")
        logos_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        logo_filename = f"logo_{uuid.uuid4()}{file_ext}"
        logo_path = logos_dir / logo_filename
        
        # Save uploaded file
        with open(logo_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Logo uploaded: {logo_path}")
        
        # Validate logo image
        overlay = LogoOverlay()
        validation = overlay.validate_logo_image(str(logo_path))
        
        if not validation['valid']:
            # Remove invalid file
            logo_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Invalid logo image: {validation['error']}"
            )
        
        return LogoUploadResponse(
            success=True,
            message="Logo uploaded successfully",
            logo_path=str(logo_path),
            logo_info=validation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading logo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Logo upload failed: {str(e)}")


@app.get("/api/v1/logos")
async def list_logos():
    """
    List all uploaded brand logos.
    
    Returns:
        List of available logos with their info
    """
    try:
        from services.logo_overlay import LogoOverlay
        
        logos_dir = Path("uploads/logos")
        if not logos_dir.exists():
            return {"logos": []}
        
        overlay = LogoOverlay()
        logos = []
        
        for logo_file in logos_dir.glob("logo_*"):
            validation = overlay.validate_logo_image(str(logo_file))
            if validation['valid']:
                logos.append({
                    "path": str(logo_file),
                    "filename": logo_file.name,
                    "info": validation
                })
        
        return {"logos": logos}
        
    except Exception as e:
        logger.error(f"Error listing logos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/logos/{logo_filename}")
async def delete_logo(logo_filename: str):
    """
    Delete a brand logo.
    
    Args:
        logo_filename: Name of the logo file to delete
        
    Returns:
        Success message
    """
    try:
        logos_dir = Path("uploads/logos")
        logo_path = logos_dir / logo_filename
        
        if not logo_path.exists():
            raise HTTPException(status_code=404, detail="Logo not found")
        
        # Security check: ensure file is in logos directory
        if not str(logo_path.resolve()).startswith(str(logos_dir.resolve())):
            raise HTTPException(status_code=403, detail="Invalid logo path")
        
        logo_path.unlink()
        logger.info(f"Logo deleted: {logo_filename}")
        
        return {"success": True, "message": "Logo deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting logo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/clips/{clip_id}/apply-logo")
async def apply_logo_to_clip(
    clip_id: int,
    logo_path: str,
    request: ApplyLogoRequest,
    background_tasks: BackgroundTasks
):
    """
    Apply brand logo overlay to a video clip.
    
    Args:
        clip_id: ID of the video clip
        logo_path: Path to the logo image
        request: Logo settings (position, size, opacity, padding)
        background_tasks: FastAPI background tasks
        
    Returns:
        Job ID for tracking the logo overlay process
    """
    try:
        from services.logo_overlay import LogoOverlay
        
        # Validate logo exists
        if not Path(logo_path).exists():
            raise HTTPException(status_code=404, detail="Logo file not found")
        
        # Validate logo image
        overlay = LogoOverlay()
        validation = overlay.validate_logo_image(logo_path)
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid logo: {validation['error']}"
            )
        
        # Get clip from database
        db = SessionLocal()
        try:
            short = db.query(Short).filter(Short.id == clip_id).first()
            
            if not short:
                raise HTTPException(status_code=404, detail="Clip not found")
            
            video_path = short.file_path
            if not video_path or not Path(video_path).exists():
                raise HTTPException(status_code=404, detail="Video file not found")
            
            # Create background job
            job_id = str(uuid.uuid4())
            
            background_tasks.add_task(
                apply_logo_task,
                job_id=job_id,
                clip_id=clip_id,
                video_path=video_path,
                logo_path=logo_path,
                position=request.position,
                size_percent=request.size_percent,
                opacity=request.opacity,
                padding=request.padding,
                create_new_clip=request.create_new_clip,
                project_id=short.project_id  # Pass project_id for creating new clip
            )
            
            return {
                "job_id": job_id,
                "status": "processing",
                "message": "Applying logo overlay..."
            }
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying logo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def apply_logo_task(
    job_id: str,
    clip_id: int,
    video_path: str,
    logo_path: str,
    position: str,
    size_percent: float,
    opacity: float,
    padding: int,
    create_new_clip: bool = False,
    project_id: int = None
):
    """Background task to apply logo overlay to video"""
    try:
        from services.video_clipper import VideoClipper
        
        await progress_tracker.update_progress(
            job_id,
            "processing",
            20,
            "Preparing logo overlay..."
        )
        
        # Initialize video clipper
        clipper = VideoClipper()
        
        # Generate output path
        if create_new_clip:
            # Create new file for new clip
            output_path = str(Path(video_path).with_stem(f"{Path(video_path).stem}_branded"))
        else:
            # Replace original - use temp name first, then replace
            output_path = str(Path(video_path).with_stem(f"{Path(video_path).stem}_temp_logo"))
        
        await progress_tracker.update_progress(
            job_id,
            "processing",
            40,
            "Applying logo to video..."
        )
        
        # Apply logo overlay
        result_path = clipper.add_logo(
            input_path=video_path,
            logo_path=logo_path,
            output_path=output_path,
            position=position,
            size_percent=size_percent,
            opacity=opacity,
            padding=padding
        )
        
        await progress_tracker.update_progress(
            job_id,
            "processing",
            90,
            "Updating database..."
        )
        
        # Update database
        db = SessionLocal()
        try:
            if create_new_clip:
                # Create new clip entry
                original_short = db.query(Short).filter(Short.id == clip_id).first()
                if original_short:
                    new_short = Short(
                        project_id=project_id,
                        file_path=result_path,
                        start_time=original_short.start_time,
                        end_time=original_short.end_time,
                        duration=original_short.duration,
                        title=f"{original_short.title} (Branded)",
                        thumbnail_url=original_short.thumbnail_url,
                        has_captions=original_short.has_captions
                    )
                    db.add(new_short)
                    db.commit()
                    db.refresh(new_short)
                    
                    await progress_tracker.update_progress(
                        job_id,
                        "completed",
                        100,
                        "Logo applied successfully - new clip created",
                        result={
                            "new_clip_id": new_short.id,
                            "new_file_path": result_path,
                            "original_clip_id": clip_id,
                            "position": position,
                            "size_percent": size_percent,
                            "opacity": opacity
                        }
                    )
            else:
                # Replace original clip
                short = db.query(Short).filter(Short.id == clip_id).first()
                if short:
                    # Delete old file
                    old_path = Path(short.file_path)
                    
                    # Rename temp file to original name
                    final_path = old_path
                    if old_path.exists():
                        old_path.unlink()  # Delete original
                    
                    Path(result_path).rename(final_path)  # Rename temp to original name
                    
                    # Update database (path stays same)
                    short.file_path = str(final_path)
                    db.commit()
                    
                    await progress_tracker.update_progress(
                        job_id,
                        "completed",
                        100,
                        "Logo applied successfully - original clip updated",
                        result={
                            "clip_id": clip_id,
                            "file_path": str(final_path),
                            "position": position,
                            "size_percent": size_percent,
                            "opacity": opacity,
                            "replaced": True
                        }
                    )
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Logo overlay task failed: {str(e)}")
        await progress_tracker.update_progress(
            job_id,
            "failed",
            0,
            f"Logo overlay failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

