# FastAPI Backend Server

This FastAPI server provides REST API endpoints for the JazzHR Resume Downloader frontend.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server:**
   ```bash
   python api_server.py
   ```
   
   Or use the convenience script:
   ```bash
   ./start_api_server.sh
   ```

3. **Server will run on:** `http://localhost:8000`

## API Endpoints

### POST `/api/downloads/start`
Start a new download for a job ID.

**Request:**
```json
{
  "job_id": "10545457"
}
```

**Response:**
```json
{
  "download_id": "abc123-def456-...",
  "status": "started",
  "job_id": "10545457"
}
```

### GET `/api/downloads/{download_id}/progress`
Stream download progress via Server-Sent Events (SSE).

**Response (SSE stream):**
```
data: {"current": 45, "total": 516, "percentage": 9, "message": "Processing candidate 45/516", "status": "in_progress", "logs": [...]}

data: {"current": 516, "total": 516, "percentage": 100, "message": "Download complete", "status": "completed", "stats": {...}}
```

### GET `/api/downloads/{download_id}`
Get final download results.

**Response:**
```json
{
  "download_id": "abc123-def456-...",
  "job_id": "10545457",
  "status": "completed",
  "stats": {
    "saved": 500,
    "failed": 16,
    "total_found": 516,
    "total_downloaded": 500
  },
  "file_location": "/path/to/resumes/job_10545457",
  "duration": 3600,
  "created_at": "2024-01-01T12:00:00",
  "completed_at": "2024-01-01T13:00:00"
}
```

### DELETE `/api/downloads/{download_id}`
Cancel an active download.

**Response:**
```json
{
  "message": "Download cancelled",
  "download_id": "abc123-def456-..."
}
```

## How It Works

1. **Start Download**: Frontend calls `POST /api/downloads/start` with a job ID
2. **Background Task**: Server starts the download in a background task
3. **Progress Updates**: Frontend connects to SSE endpoint to receive real-time progress
4. **Completion**: When done, final stats are sent via SSE and available via GET endpoint

## Notes

- Downloads run in background threads (blocking Selenium operations)
- Progress is parsed from log output in real-time
- Download state is stored in-memory (resets on server restart)
- For production, consider using a database or Redis for state management

## Troubleshooting

**Port already in use:**
- Change port in `api_server.py`: `uvicorn.run(app, host="0.0.0.0", port=8001)`
- Update frontend `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8001`

**CORS errors:**
- Ensure frontend URL is in `allow_origins` list in `api_server.py`

**Download not starting:**
- Check that `download_resumes_browser.py` is in the same directory
- Verify Python dependencies are installed
- Check server logs for errors
