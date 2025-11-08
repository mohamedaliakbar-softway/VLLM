"""Logging decorator for comprehensive error tracking and performance monitoring."""
import functools
import logging
import time
import traceback
from typing import Any, Callable

logger = logging.getLogger(__name__)


def log_execution(step_name: str, log_args: bool = False):
    """
    Decorator to log function execution with timing, errors, and optional arguments.
    
    Args:
        step_name: Descriptive name for the step being executed
        log_args: Whether to log function arguments (default: False for security)
    
    Usage:
        @log_execution("Extract Transcript")
        def get_transcript(self, url):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            # Log start
            if log_args:
                logger.info(f"[{step_name}] Starting with args={args[1:]}, kwargs={kwargs}")
            else:
                logger.info(f"[{step_name}] Starting...")
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log success
                elapsed = time.time() - start_time
                logger.info(f"[{step_name}] ✅ Completed successfully in {elapsed:.2f}s")
                
                return result
                
            except Exception as e:
                # Log failure with full context
                elapsed = time.time() - start_time
                error_type = type(e).__name__
                error_msg = str(e)
                
                logger.error(f"[{step_name}] ❌ Failed after {elapsed:.2f}s")
                logger.error(f"[{step_name}] Error Type: {error_type}")
                logger.error(f"[{step_name}] Error Message: {error_msg}")
                logger.error(f"[{step_name}] Full Traceback:\n{traceback.format_exc()}")
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator


def log_async_execution(step_name: str, log_args: bool = False):
    """
    Async version of log_execution decorator.
    
    Usage:
        @log_async_execution("Process Video")
        async def process_video_async(job_id, url):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            # Log start
            if log_args:
                logger.info(f"[{step_name}] Starting with args={args[1:]}, kwargs={kwargs}")
            else:
                logger.info(f"[{step_name}] Starting...")
            
            try:
                # Execute async function
                result = await func(*args, **kwargs)
                
                # Log success
                elapsed = time.time() - start_time
                logger.info(f"[{step_name}] ✅ Completed successfully in {elapsed:.2f}s")
                
                return result
                
            except Exception as e:
                # Log failure with full context
                elapsed = time.time() - start_time
                error_type = type(e).__name__
                error_msg = str(e)
                
                logger.error(f"[{step_name}] ❌ Failed after {elapsed:.2f}s")
                logger.error(f"[{step_name}] Error Type: {error_type}")
                logger.error(f"[{step_name}] Error Message: {error_msg}")
                logger.error(f"[{step_name}] Full Traceback:\n{traceback.format_exc()}")
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator


class StepLogger:
    """Context manager for logging steps with automatic success/failure tracking."""
    
    def __init__(self, step_name: str, log_context: dict = None):
        self.step_name = step_name
        self.log_context = log_context or {}
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        context_str = f" | Context: {self.log_context}" if self.log_context else ""
        logger.info(f"[{self.step_name}] Starting...{context_str}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        
        if exc_type is None:
            # Success
            logger.info(f"[{self.step_name}] ✅ Completed successfully in {elapsed:.2f}s")
        else:
            # Failure
            error_type = exc_type.__name__
            error_msg = str(exc_val)
            
            logger.error(f"[{self.step_name}] ❌ Failed after {elapsed:.2f}s")
            logger.error(f"[{self.step_name}] Error Type: {error_type}")
            logger.error(f"[{self.step_name}] Error Message: {error_msg}")
            logger.error(f"[{self.step_name}] Full Traceback:\n{traceback.format_exc()}")
        
        # Don't suppress the exception
        return False
