#!/usr/bin/env python3
"""
FastAPI Backend Server for JazzHR Resume Downloader

Provides REST API endpoints to start, monitor, and cancel resume downloads.
"""

import os
import sys
import re
import json
import uuid
import asyncio
import subprocess
import logging
import io
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import the downloader class
sys.path.insert(0, str(Path(__file__).parent))
from download_resumes_browser import JazzHRBrowserDownloader

app = FastAPI(title="JazzHR Resume Downloader API")

# CORS middleware to allow frontend requests
# IMPORTANT: CORS middleware must be added BEFORE routes
# Allow localhost for local development and Vercel domain for production
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://justlifehr.vercel.app",
]

# Allow additional origins from environment variable (comma-separated)
if os.getenv("CORS_ORIGINS"):
    additional_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS").split(",")]
    allowed_origins.extend(additional_origins)
    print(f"[CORS] Additional origins from env: {additional_origins}")

# Log allowed origins for debugging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"[CORS] Configured allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# In-memory store for download state
downloads: Dict[str, Dict] = {}
# Store active downloaders and futures for cancellation
active_downloaders: Dict[str, JazzHRBrowserDownloader] = {}
active_futures: Dict[str, asyncio.Future] = {}


class DownloadStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LOGIN_REQUIRED = "login_required"  # Special status for when user needs to authenticate


class StartDownloadRequest(BaseModel):
    job_id: str
    output_dir: Optional[str] = "resumes"
    cookies: Optional[List[Dict]] = None  # Optional cookies for authentication

class ProvideCookiesRequest(BaseModel):
    cookies: List[Dict]  # Required cookies for authentication


class StartDownloadResponse(BaseModel):
    download_id: str
    status: str
    job_id: str


def parse_progress_from_log(log_line: str, current_state: Dict) -> Optional[Dict]:
    """
    Parse progress information from log lines.
    Returns dict with progress data or None if no progress info found.
    """
    # Pattern: "Processing candidate 45/516"
    match = re.search(r'Processing candidate (\d+)/(\d+)', log_line)
    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        return {
            "current": current,
            "total": total,
            "percentage": round((current / total) * 100) if total > 0 else 0,
            "message": f"Processing candidate {current}/{total}",
        }
    
    # Pattern: "✓ Successfully downloaded resume 45/516"
    match = re.search(r'Successfully downloaded resume (\d+)/(\d+)', log_line)
    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        return {
            "current": current,
            "total": total,
            "percentage": round((current / total) * 100) if total > 0 else 0,
            "message": f"Downloaded {current}/{total} resumes",
        }
    
    # Pattern: "Total Candidates Found: 516"
    match = re.search(r'Total Candidates Found: (\d+)', log_line)
    if match:
        total = int(match.group(1))
        if "total" not in current_state or current_state["total"] != total:
            return {
                "total": total,
                "message": f"Found {total} candidates",
            }
    
    # Pattern: "Successfully Downloaded: 500"
    match = re.search(r'Successfully Downloaded: (\d+)', log_line)
    if match:
        downloaded = int(match.group(1))
        return {
            "current": downloaded,
            "message": f"Downloaded {downloaded} resumes",
        }
    
    return None


async def run_download(download_id: str, job_id: str, output_dir: str = "resumes", cookies: Optional[List[Dict]] = None):
    """
    Run the download script in a background task.
    Updates download state and sends progress via the downloads dict.
    """
    download_state = downloads[download_id]
    download_state["status"] = DownloadStatus.IN_PROGRESS
    download_state["started_at"] = datetime.now().isoformat()
    
    try:
        # Get cookies from parameter, download state, or environment variable
        if cookies is None:
            cookies = download_state.get("cookies")
        
        if cookies is None and os.getenv("JAZZHR_COOKIES"):
            try:
                cookies = json.loads(os.getenv("JAZZHR_COOKIES"))
            except json.JSONDecodeError:
                logging.warning("Failed to parse JAZZHR_COOKIES environment variable")
        
        # Create downloader instance with specified output directory and cookies
        downloader = JazzHRBrowserDownloader(job_id, output_dir=output_dir, cookies=cookies)
        
        # Store downloader reference for cancellation
        active_downloaders[download_id] = downloader
        
        # We'll run the download in a thread pool since it's blocking
        loop = asyncio.get_event_loop()
        
        # Run download in executor and capture output
        def download_with_progress():
            """Run download and capture progress."""
            log_entries = []
            
            # Create a custom handler that captures logs
            class ProgressHandler(logging.Handler):
                def emit(self, record):
                    message = record.getMessage()
                    level = record.levelname.lower()
                    
                    # Map log levels to frontend types
                    log_type = 'info'
                    if level == 'error':
                        log_type = 'error'
                    elif level == 'warning':
                        log_type = 'warning'
                    elif level in ['info', 'debug'] and ('success' in message.lower() or '✓' in message or 'downloaded' in message.lower()):
                        log_type = 'success'
                    
                    # Format timestamp as HH:MM:SS
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    log_entry = {
                        "timestamp": timestamp,
                        "message": message,
                        "type": log_type,
                    }
                    log_entries.append(log_entry)
                    
                    # Update download state logs immediately so they appear in real-time
                    download_state["logs"] = log_entries[-50:]  # Keep last 50 entries
                    
                    # Parse progress from log line
                    try:
                        progress = parse_progress_from_log(message, download_state)
                        if progress:
                            # Update download state with progress
                            download_state.update(progress)
                    except Exception:
                        pass
            
            # Get the logger and add our handler
            logger = logging.getLogger('download_resumes_browser')
            handler = ProgressHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
            
            try:
                downloader.download_all_resumes()
                
                # Check if cancelled after download completes
                if downloader.cancelled:
                    download_state["status"] = DownloadStatus.CANCELLED
                    download_state["completed_at"] = datetime.now().isoformat()
                    download_state["logs"] = log_entries
                    return
                
                # Extract final stats
                final_files = list(downloader.output_dir.glob("*"))
                final_files = [f for f in final_files if f.is_file()]
                
                download_state["stats"] = {
                    "saved": downloader.downloaded_count,
                    "failed": downloader.failed_count,
                    "total_found": len(downloader.all_candidate_ids),
                    "total_downloaded": len(downloader.downloaded_candidate_ids),
                }
                download_state["file_location"] = str(downloader.output_dir.absolute())
                download_state["status"] = DownloadStatus.COMPLETED
                download_state["completed_at"] = datetime.now().isoformat()
                download_state["logs"] = log_entries
                
            except Exception as e:
                # Check if cancelled
                if downloader.cancelled:
                    download_state["status"] = DownloadStatus.CANCELLED
                else:
                    error_msg = str(e)
                    # Check if this is a login required error
                    if "LOGIN_REQUIRED" in error_msg:
                        download_state["status"] = "login_required"
                        download_state["error"] = error_msg
                        download_state["message"] = "Authentication required. Please provide JazzHR login cookies."
                    else:
                        download_state["status"] = DownloadStatus.FAILED
                        download_state["error"] = error_msg
                download_state["completed_at"] = datetime.now().isoformat()
                download_state["logs"] = log_entries
            finally:
                logger.removeHandler(handler)
        
        # Run in thread pool and store future for cancellation
        future = loop.run_in_executor(None, download_with_progress)
        active_futures[download_id] = future
        
        # Wait for completion or cancellation
        try:
            await future
        except asyncio.CancelledError:
            # Download was cancelled
            logging.info(f"Download {download_id} was cancelled")
            if downloader.driver:
                try:
                    downloader.driver.quit()
                except:
                    pass
            download_state["status"] = DownloadStatus.CANCELLED
            download_state["completed_at"] = datetime.now().isoformat()
        finally:
            # Clean up references
            active_downloaders.pop(download_id, None)
            active_futures.pop(download_id, None)
        
    except Exception as e:
        download_state["status"] = DownloadStatus.FAILED
        download_state["error"] = str(e)
        download_state["completed_at"] = datetime.now().isoformat()


@app.post("/api/downloads/start", response_model=StartDownloadResponse)
async def start_download(request: StartDownloadRequest, background_tasks: BackgroundTasks):
    """
    Start a new resume download job.
    Handles CORS preflight automatically via CORSMiddleware.
    """
    """Start a new download for the given job ID."""
    job_id = request.job_id.strip()
    output_dir = (request.output_dir or "resumes").strip()
    
    if not job_id:
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    # Generate unique download ID
    download_id = str(uuid.uuid4())
    
    # Initialize download state
    downloads[download_id] = {
        "download_id": download_id,
        "job_id": job_id,
        "status": DownloadStatus.PENDING,
        "created_at": datetime.now().isoformat(),
        "current": 0,
        "total": 0,
        "percentage": 0,
        "message": "Initializing download...",
        "logs": [],
        "cookies": request.cookies,  # Store cookies for use in download task
    }
    
    # Start download in background
    background_tasks.add_task(run_download, download_id, job_id, output_dir, request.cookies)
    
    return StartDownloadResponse(
        download_id=download_id,
        status="started",
        job_id=job_id,
    )


@app.get("/api/downloads/{download_id}/progress")
async def get_download_progress(download_id: str):
    """Stream download progress via Server-Sent Events (SSE)."""
    if download_id not in downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    async def event_generator():
        try:
            download_state = downloads[download_id]
            last_status = None
            
            while True:
                current_state = downloads.get(download_id)
                if not current_state:
                    # Send a final message before closing
                    yield f"data: {json.dumps({'status': 'not_found', 'message': 'Download not found'})}\n\n"
                    break
                
                status = current_state["status"]
                
                # Convert log entries to the format expected by frontend
                log_entries = current_state.get("logs", [])
                if isinstance(log_entries, list) and len(log_entries) > 0:
                    # Take last 50 entries for display
                    recent_logs = log_entries[-50:]
                    formatted_logs = [
                        {
                            "timestamp": log.get("timestamp", datetime.now().strftime('%H:%M:%S')),
                            "message": log.get("message", str(log)),
                            "type": log.get("type", log.get("level", "info")),
                        }
                        for log in recent_logs
                    ]
                else:
                    formatted_logs = []
                
                # Send progress update
                progress_data = {
                    "current": current_state.get("current", 0),
                    "total": current_state.get("total", 0),
                    "percentage": current_state.get("percentage", 0),
                    "message": current_state.get("message", ""),
                    "status": status,
                    "logs": formatted_logs,
                }
                
                # If login is required, include VNC connection info
                if status == "login_required":
                    # Try to get Railway public domain or use request host
                    railway_public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
                    if railway_public_domain:
                        # Provide both VNC client URL and web-based noVNC URL
                        progress_data["vnc_url"] = f"vnc://{railway_public_domain}:5900"
                        progress_data["novnc_url"] = f"http://{railway_public_domain}:6080/vnc.html"
                        progress_data["message"] = f"Login required. Open browser at: {progress_data['novnc_url']} to log in directly"
                    else:
                        progress_data["message"] = "Login required. Please connect via VNC or provide authentication cookies."
                
                # Calculate estimated time remaining if we have progress
                # Only calculate after minimum progress to avoid inaccurate early estimates
                if current_state.get("total", 0) > 0 and current_state.get("current", 0) > 0:
                    elapsed = (datetime.now() - datetime.fromisoformat(current_state["created_at"])).total_seconds()
                    current = current_state.get("current", 0)
                    total = current_state.get("total", 0)
                    
                    # Only calculate if we have meaningful progress (at least 3 candidates or 30 seconds elapsed)
                    # This avoids inaccurate estimates during login/initialization
                    if current >= 3 or elapsed >= 30:
                        rate = current / elapsed if elapsed > 0 else 0
                        if rate > 0:
                            remaining = (total - current) / rate
                            # Cap at reasonable maximum (e.g., 24 hours) to avoid unrealistic estimates
                            max_remaining = 24 * 60 * 60  # 24 hours in seconds
                            remaining = min(remaining, max_remaining)
                            progress_data["estimated_time_remaining"] = int(remaining)
                        else:
                            progress_data["estimated_time_remaining"] = None
                    else:
                        # Too early to calculate - show None
                        progress_data["estimated_time_remaining"] = None
                
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # If completed or failed, send final update and break
                if status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
                    # Send final results
                    final_data = {
                        **progress_data,
                        "stats": current_state.get("stats", {}),
                        "file_location": current_state.get("file_location", ""),
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                    break
                
                # Wait before next update
                await asyncio.sleep(1)
        except Exception as e:
            # Send error message before closing
            error_data = {
                "status": "error",
                "message": f"Error in progress stream: {str(e)}",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/downloads/{download_id}")
async def get_download_results(download_id: str):
    """Get final download results."""
    if download_id not in downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    download_state = downloads[download_id]
    
    # Calculate duration
    duration = 0
    if "started_at" in download_state and "completed_at" in download_state:
        start = datetime.fromisoformat(download_state["started_at"])
        end = datetime.fromisoformat(download_state["completed_at"])
        duration = int((end - start).total_seconds())
    
    return {
        "download_id": download_id,
        "job_id": download_state["job_id"],
        "status": download_state["status"],
        "stats": download_state.get("stats", {}),
        "file_location": download_state.get("file_location", ""),
        "duration": duration,
        "created_at": download_state["created_at"],
        "completed_at": download_state.get("completed_at"),
    }


@app.delete("/api/downloads/{download_id}")
async def cancel_download(download_id: str):
    """Cancel an active download."""
    if download_id not in downloads:
        # Return success even if not found (idempotent operation)
        return {"message": "Download not found or already cancelled", "download_id": download_id}
    
    download_state = downloads[download_id]
    
    if download_state["status"] not in [DownloadStatus.PENDING, DownloadStatus.IN_PROGRESS]:
        # Already completed/failed/cancelled - return success (idempotent)
        return {
            "message": f"Download already {download_state['status']}", 
            "download_id": download_id,
            "status": download_state["status"]
        }
    
    # Mark as cancelled in state
    download_state["status"] = DownloadStatus.CANCELLED
    download_state["completed_at"] = datetime.now().isoformat()
    
    # Actually stop the download process
    downloader = active_downloaders.get(download_id)
    if downloader:
        # Set cancellation flag on downloader
        downloader.cancelled = True
        
        # Close browser if it's open
        if downloader.driver:
            try:
                downloader.driver.quit()
            except Exception as e:
                logging.warning(f"Error closing browser: {e}")
    
    # Cancel the future if it exists
    future = active_futures.get(download_id)
    if future and not future.done():
        try:
            future.cancel()
        except Exception as e:
            logging.warning(f"Error cancelling future: {e}")
    
    # Clean up references
    active_downloaders.pop(download_id, None)
    active_futures.pop(download_id, None)
    
    # TODO: Actually kill the download process if possible
    # This would require storing the process reference
    
    return {"message": "Download cancelled", "download_id": download_id, "status": "cancelled"}


@app.post("/api/downloads/{download_id}/authenticate")
async def provide_authentication(download_id: str, request: ProvideCookiesRequest, background_tasks: BackgroundTasks):
    """Provide authentication cookies for a download that requires login."""
    if download_id not in downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    download_state = downloads[download_id]
    
    # Check if download is in login_required state
    if download_state["status"] != "login_required":
        raise HTTPException(status_code=400, detail=f"Download is not waiting for authentication. Current status: {download_state['status']}")
    
    # Store cookies and restart download
    download_state["cookies"] = request.cookies
    download_state["status"] = DownloadStatus.PENDING
    download_state["message"] = "Authentication provided. Restarting download..."
    download_state["logs"].append({
        "timestamp": datetime.now().strftime('%H:%M:%S'),
        "message": "Authentication cookies provided. Restarting download...",
        "type": "info"
    })
    
    # Get job_id and output_dir from download state
    job_id = download_state["job_id"]
    output_dir = download_state.get("output_dir", "resumes")
    
    # Cancel any existing downloader
    if download_id in active_downloaders:
        try:
            active_downloaders[download_id].cancelled = True
            if active_downloaders[download_id].driver:
                active_downloaders[download_id].driver.quit()
        except:
            pass
    
    # Restart the download with cookies
    background_tasks.add_task(run_download, download_id, job_id, output_dir, request.cookies)
    
    return {
        "message": "Authentication provided. Download restarted.",
        "download_id": download_id,
        "status": "restarted"
    }


if __name__ == "__main__":
    import uvicorn
    import json
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
