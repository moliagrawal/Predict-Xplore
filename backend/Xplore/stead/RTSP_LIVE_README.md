# RTSP Live Processing for STEAD Anomaly Detection

## Overview

This module provides real-time RTSP stream processing with STEAD anomaly detection. It supports:

1. **Input**: RTSP URL, TCP stream, UDP stream, or video file
2. **Processing**: STEAD model inference on video chunks (16 frames)
3. **Output**: Annotated MP4 video with anomaly markers
4. **Streaming**: FFmpeg-based HLS and web-ready video streaming

## Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   RTSP/Video    │────▶│  STEAD Model    │────▶│   Annotated     │────▶│ FFmpeg Streaming│
│     Input       │     │   Inference     │     │   MP4 Output    │     │  (HLS/Web MP4)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

## API Endpoints

### 1. Start RTSP Live Processing

**POST** `/api/stead/rtsp/live/start/`

Start processing an RTSP stream or video file.

**Request:**
```json
{
    "stream_url": "rtsp://camera.local:554/stream",
    "fps": 15,
    "threshold": 0.7,
    "max_duration": 300
}
```

**Parameters:**
- `stream_url` (required): RTSP URL, TCP stream URL, or video file path
- `fps` (optional): Target frames per second (default: 15)
- `threshold` (optional): Anomaly detection threshold 0-1 (default: 0.7)
- `max_duration` (optional): Maximum recording duration in seconds

**Response:**
```json
{
    "success": true,
    "job_id": "abc123-def456-...",
    "message": "RTSP live processing started",
    "stream_url": "rtsp://...",
    "status": {
        "is_running": true,
        "stats": {...}
    }
}
```

### 2. Test with Local Video (No RTSP Camera Required)

**POST** `/api/stead/rtsp/test/simulate/`

Use a local video file as a simulated RTSP stream for testing.

**Request:**
```json
{
    "video_path": "/path/to/test_video.mp4",
    "fps": 15,
    "threshold": 0.7,
    "max_duration": 60
}
```

If `video_path` is not provided, the system will look for test videos in:
- `/home/maaza/predict-xplore-iit-b/Predict-Xplore/VID-20250814-WA0006.mp4`
- `/home/maaza/predict-xplore-iit-b/Predict-Xplore/predict Xplore nov25.mp4`

### 3. Check Job Status

**GET** `/api/stead/rtsp/live/<job_id>/status/`

Get real-time status of a processing job.

**Response:**
```json
{
    "job_id": "abc123...",
    "stream_url": "rtsp://...",
    "is_running": true,
    "is_paused": false,
    "stats": {
        "start_time": "2026-02-18T10:00:00",
        "total_frames": 1500,
        "total_clips_processed": 93,
        "anomalies_detected": 5,
        "anomaly_clips": [...],
        "current_fps": 14.8,
        "status": "running"
    }
}
```

### 4. Stop Job and Get Results

**POST** `/api/stead/rtsp/live/<job_id>/stop/`

Stop processing and finalize output video.

**Response:**
```json
{
    "success": true,
    "job_id": "abc123...",
    "stats": {
        "total_frames": 3600,
        "anomalies_detected": 12,
        ...
    },
    "output": {
        "output_video": "/path/to/output.mp4",
        "web_ready": "/path/to/output_web.mp4",
        "hls_playlist": "/path/to/hls/playlist.m3u8",
        "thumbnail": "/path/to/thumbnail.jpg"
    },
    "streaming_urls": {
        "output_video": "http://localhost:8000/media/...",
        "web_ready": "http://localhost:8000/media/...",
        "hls_playlist": "http://localhost:8000/media/...",
        "thumbnail": "http://localhost:8000/media/..."
    }
}
```

### 5. Control Job (Pause/Resume)

**POST** `/api/stead/rtsp/live/<job_id>/control/`

**Request:**
```json
{
    "action": "pause"  // or "resume"
}
```

### 6. List All Jobs

**GET** `/api/stead/rtsp/live/`

List all active and completed RTSP live processing jobs.

### 7. Stream Output Video

**GET** `/api/stead/rtsp/live/<job_id>/stream/`

Stream the output video directly (MP4, supports range requests).

### 8. Stream via HLS

**GET** `/api/stead/rtsp/live/<job_id>/hls/`

Get HLS playlist for adaptive streaming.

**GET** `/api/stead/rtsp/live/<job_id>/hls/<filename>`

Get HLS segments.

## Testing Without RTSP Camera

### Option 1: Using Test Simulator API

```bash
# Start processing with test video
curl -X POST http://localhost:8000/api/stead/rtsp/test/simulate/ \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "fps": 15,
        "threshold": 0.7,
        "max_duration": 60
    }'
```

### Option 2: Using RTSP Server Simulator Script

Run the simulator in one terminal:
```bash
cd backend/Xplore/stead
python rtsp_server_simulator.py --video /path/to/video.mp4 --method tcp --port 8554
```

Then start live processing with the TCP URL:
```bash
curl -X POST http://localhost:8000/api/stead/rtsp/live/start/ \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "stream_url": "tcp://localhost:8554",
        "fps": 15,
        "threshold": 0.7
    }'
```

### Option 3: Using FFmpeg as RTSP Server

```bash
# Install mediamtx (RTSP server)
# Then stream video to it:
ffmpeg -re -stream_loop -1 -i test_video.mp4 \
    -c:v libx264 -preset ultrafast \
    -f rtsp rtsp://localhost:8554/live
```

## Example: Complete Test Flow

```bash
# 1. Login and get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"email": "test@test.com", "password": "password123"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# 2. Start processing
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/stead/rtsp/test/simulate/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"max_duration": 30}')
JOB_ID=$(echo $JOB_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

# 3. Check status
curl -X GET "http://localhost:8000/api/stead/rtsp/live/${JOB_ID}/status/" \
    -H "Authorization: Bearer $TOKEN"

# 4. Wait for processing (or use max_duration)
sleep 35

# 5. Stop and get results
curl -X POST "http://localhost:8000/api/stead/rtsp/live/${JOB_ID}/stop/" \
    -H "Authorization: Bearer $TOKEN"

# 6. Stream output video
curl -o output.mp4 "http://localhost:8000/api/stead/rtsp/live/${JOB_ID}/stream/" \
    -H "Authorization: Bearer $TOKEN"
```

## Output Video Annotations

The output video includes:
- **Red border**: Anomaly detected in current clip
- **Green border**: Normal activity
- **Score display**: Real-time anomaly score
- **Timestamp**: Frame timestamp
- **Progress bar**: Processing progress indicator

## File Structure

```
stead/
├── rtsp_live_processor.py    # Core RTSP live processing logic
├── rtsp_server_simulator.py  # Test RTSP server from video file
├── rtsp_processor.py         # Original frame buffer processor
├── video_streaming.py        # FFmpeg video processing
├── views.py                  # API views (includes RTSP Live views)
├── urls.py                   # URL routing
├── test_rtsp_live.sh         # Test script
└── RTSP_LIVE_README.md       # This documentation
```

## Dependencies

- FFmpeg (required for video streaming)
- OpenCV (python-opencv)
- PyTorch
- performer-pytorch

## Troubleshooting

### "Cannot open stream" error
- Check if FFmpeg is installed: `ffmpeg -version`
- Verify stream URL is accessible
- For TCP streams, ensure the server is running first

### "HLS stream not available"
- Job must be stopped first to generate HLS
- Check if FFmpeg is installed and working

### Low FPS during processing
- Reduce resolution of input stream
- Use GPU acceleration if available
- Increase threshold to reduce false positives
