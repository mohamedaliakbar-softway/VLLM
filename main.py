"""FastAPI application for Video Shorts Generator SaaS."""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import logging
import uuid
import time
from pathlib import Path
import asyncio
import os

from config import settings
from services.youtube_processor import YouTubeProcessor
from services.gemini_analyzer import GeminiAnalyzer
from services.ai_agent import VideoEditingAgent
from services.video_clipper import VideoClipper
from services.social_publisher import SocialPublisher, build_post_text
from services.progress_tracker import progress_tracker
from services.youtube_data_api import YouTubeDataAPI
from services.caption_generator import CaptionGenerator
from services.caption_burner import CaptionBurner, CAPTION_STYLES
from database import get_db, SessionLocal
from models import Project, Short, Publication, AccountToken
from migrate import main as run_migrations
import auth

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

# Add session middleware for authentication
SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not SESSION_SECRET:
    logger.warning("SESSION_SECRET not set, using default (not secure for production)")
    SESSION_SECRET = "dev-secret-key-change-in-production"

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="session",
    max_age=7 * 24 * 60 * 60,
    same_site="lax",
    https_only=False,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register authentication routes
app.include_router(auth.router)

# Run database migrations on startup
@app.on_event("startup")
async def startup_event():
    """Run database migrations on startup."""
    try:
        run_migrations()
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")

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


# In-memory job storage (use Redis/DB in production)
jobs = {}


async def process_video_async(job_id: str, youtube_url: str, max_shorts: int, platform: str):
    """Background task to process video and emit progress updates (OPTIMIZED FOR 20 SECONDS)."""
    db = SessionLocal()
    try:
        jobs[job_id] = {"status": "processing", "progress": 0}
        
        # Create project record in database
        project = Project(
            id=job_id,
            youtube_url=str(youtube_url),
            video_id="",  # Will be updated after extracting video info
            status="processing"
        )
        db.add(project)
        db.commit()
        
        # STEP 1: Extract transcript (2-3 seconds) - NO VIDEO DOWNLOAD
        await progress_tracker.update_progress(job_id, "processing", 10, "Extracting video transcript...")
        video_info = youtube_processor.get_transcript(youtube_url)
        
        if not video_info.get('transcript'):
            logger.warning(f"No transcript found for {youtube_url}, falling back to basic video info")
            video_info = youtube_processor.get_video_info(youtube_url)
            video_info['transcript'] = f"{video_info.get('title', '')}. {video_info.get('description', '')}"
        
        # Update project with video details
        project.video_id = video_info.get('video_id', '')
        project.video_title = video_info.get('title', '')
        project.video_duration = video_info.get('duration', 0)
        db.commit()
        
        # STEP 2: Analyze transcript with Gemini (3-5 seconds) - MUCH FASTER than video analysis
        await progress_tracker.update_progress(job_id, "processing", 30, "Analyzing content with AI...")
        
        transcript = video_info.get('transcript', '')
        transcript_length = len(transcript) if transcript else 0
        logger.info(f"Analyzing transcript for job {job_id}: {transcript_length} chars, duration: {video_info.get('duration', 0)}s")
        
        highlights = gemini_analyzer.analyze_transcript_for_highlights(
            transcript,
            video_info.get('title', ''),
            video_info.get('description', ''),
            video_info.get('duration', 0)
        )
        
        if not highlights:
            error_msg = f"No highlights found (transcript length: {transcript_length} chars, duration: {video_info.get('duration', 0)}s)"
            logger.warning(f"Job {job_id}: {error_msg}")
            await progress_tracker.update_progress(job_id, "failed", 100, "No suitable highlights found")
            jobs[job_id] = {"status": "failed", "error": "No highlights found"}
            project.status = "failed"
            project.error_message = error_msg
            db.commit()
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
            project.status = "failed"
            project.error_message = "Failed to download segments"
            db.commit()
            return
        
        # STEP 4: Create shorts with MoviePy and smart cropping in parallel (5-10 seconds) - proper landscape-to-portrait conversion
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
            project.status = "failed"
            project.error_message = "Failed to create shorts"
            db.commit()
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
        
        shorts_info = []
        for idx, short in enumerate(created_shorts):
            # Save short to database
            db_short = Short(
                id=str(uuid.uuid4()),
                project_id=job_id,
                filename=short["filename"],
                title=short.get("title", f"Highlight {idx + 1}"),
                start_time=timestamp_to_seconds(short["start_time"]),
                end_time=timestamp_to_seconds(short["end_time"]),
                duration_seconds=short["duration_seconds"],
                engagement_score=short["engagement_score"],
                marketing_effectiveness=short["marketing_effectiveness"],
                suggested_cta=short["suggested_cta"]
            )
            db.add(db_short)
            
            # Helper function to format seconds as timestamp
            def seconds_to_timestamp(seconds):
                """Convert seconds to MM:SS format"""
                mins = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{mins:02d}:{secs:02d}"
            
            shorts_info.append({
                "short_id": db_short.id,
                "title": db_short.title,
                "filename": db_short.filename,
                "start_time": seconds_to_timestamp(db_short.start_time),
                "end_time": seconds_to_timestamp(db_short.end_time),
                "duration": db_short.duration_seconds,
                "duration_seconds": db_short.duration_seconds,
                "engagement_score": db_short.engagement_score,
                "marketing_effectiveness": db_short.marketing_effectiveness,
                "suggested_cta": db_short.suggested_cta,
                "download_url": f"/api/v1/download/{db_short.filename}"
            })
        
        # Update project status
        project.status = "completed"
        db.commit()
        
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
        
        # Update project status in database
        try:
            project = db.query(Project).filter(Project.id == job_id).first()
            if project:
                project.status = "failed"
                project.error_message = str(e)
                db.commit()
        except:
            pass
    finally:
        progress_tracker.cleanup_job(job_id)
        db.close()


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
    total_start_time = time.time()
    
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
            pub.error_message = "Short not found"
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
        payload = {
            "platform": pub.platform,
            "file_path": file_path,
            "text": text_to_post,
            "metadata": {"title": short.platform_title or short.title or ""},
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
        except:
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
            raise HTTPException(status_code=404, detail="Short not found")

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


# AI Agent Endpoint
class AIAgentRequest(BaseModel):
    """Request model for AI agent commands."""
    message: str
    context: dict


@app.post("/api/v1/ai-agent/execute")
async def execute_ai_command(request: AIAgentRequest):
    """
    Execute AI agent command for video editing.
    
    Args:
        message: User's natural language command
        context: Current editing context (clips, selected clip, etc.)
    
    Returns:
        Action to execute and response message
    """
    try:
        result = ai_agent.parse_and_execute(
            message=request.message,
            context=request.context
        )
        
        return result
        
    except Exception as e:
        logger.error(f"AI Agent error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI Agent error: {str(e)}"
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


def _fetch_project_and_transcript(db, project_id: Optional[str] = None, short: Optional[Short] = None):
    """Helper to get project, transcript text, and ensure basic availability."""
    project = None
    if short and not project_id:
        project = db.query(Project).filter(Project.id == short.project_id).first()
    elif project_id:
        project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        info = youtube_processor.get_transcript(project.youtube_url)
    except Exception as e:
        logger.warning(f"Transcript fetch failed, falling back to video info: {e}")
        info = youtube_processor.get_video_info(project.youtube_url)
        info["transcript"] = f"{info.get('title','')}. {info.get('description','')}"
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
                raise HTTPException(status_code=404, detail="Short not found")
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
            raise HTTPException(status_code=404, detail="Short not found")
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
            raise HTTPException(status_code=404, detail="Short not found")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

