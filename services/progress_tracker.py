"""Progress tracking for real-time updates using Server-Sent Events."""
import asyncio
from typing import Dict, AsyncGenerator
import json


class ProgressTracker:
    """Track progress of video generation jobs and provide SSE updates."""
    
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self.queues: Dict[str, asyncio.Queue] = {}
    
    def create_job(self, job_id: str):
        """Create a new job for tracking."""
        self.jobs[job_id] = {
            "status": "initializing",
            "progress": 0,
            "message": "Starting video analysis..."
        }
        self.queues[job_id] = asyncio.Queue()
    
    async def update_progress(self, job_id: str, status: str, progress: int, message: str):
        """Update job progress and notify listeners."""
        if job_id in self.jobs:
            self.jobs[job_id] = {
                "status": status,
                "progress": progress,
                "message": message
            }
            
            if job_id in self.queues:
                await self.queues[job_id].put({
                    "status": status,
                    "progress": progress,
                    "message": message
                })
    
    async def get_progress_stream(self, job_id: str) -> AsyncGenerator[str, None]:
        """Get SSE stream for a job."""
        if job_id not in self.queues:
            self.queues[job_id] = asyncio.Queue()
        
        queue = self.queues[job_id]
        
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(data)}\n\n"
                
                if data.get("status") in ["completed", "failed"]:
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    def cleanup_job(self, job_id: str):
        """Clean up job data after completion."""
        if job_id in self.jobs:
            del self.jobs[job_id]
        if job_id in self.queues:
            del self.queues[job_id]


progress_tracker = ProgressTracker()
