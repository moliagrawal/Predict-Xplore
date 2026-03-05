"""
RTSP Stream Processor for STEAD Anomaly Detection.

This module handles RTSP stream capture, frame buffering, and integration
with the STEAD model for real-time anomaly detection.
"""

import cv2
import threading
import time
from collections import deque
import logging
import os
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)


class RTSPProcessor:
    """
    Handles RTSP stream capture and frame buffering for STEAD model.
    Buffers 16 frames at a time for anomaly detection.
    """
    
    FRAME_BUFFER_SIZE = 16  # STEAD requires 16 frames
    
    def __init__(self, stream_url: str, fps: int = 15):
        """
        Args:
            stream_url: RTSP stream URL or camera index (0 for webcam)
            fps: Target frames per second
        """
        self.stream_url = stream_url
        self.fps = fps
        self.frame_buffer = deque(maxlen=self.FRAME_BUFFER_SIZE)
        self.raw_frame_buffer = deque(maxlen=self.FRAME_BUFFER_SIZE)
        self.is_running = False
        self.capture_thread = None
        self.cap = None
        self.lock = threading.Lock()
        self.frame_counter = 0
        self.last_frame = None
        self.error_message = None
        
    def _get_video_capture(self):
        """Create VideoCapture object based on stream type."""
        # Handle webcam index
        if isinstance(self.stream_url, int):
            return cv2.VideoCapture(int(self.stream_url))
        elif isinstance(self.stream_url, str) and self.stream_url.isdigit():
            return cv2.VideoCapture(int(self.stream_url))
        else:
            return cv2.VideoCapture(self.stream_url)
        
    def validate_stream(self) -> tuple:
        """
        Validate if the stream URL is accessible.
        
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        try:
            cap = self._get_video_capture()
            
            if not cap.isOpened():
                return False, "Cannot open video stream"
                
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return False, "Cannot read frames from stream"
                
            return True, "Stream is accessible"
            
        except Exception as e:
            logger.error(f"Stream validation failed: {e}")
            return False, str(e)
    
    def start_capture(self):
        """Start capturing frames from the stream."""
        self.is_running = True
        self.error_message = None
        self.cap = self._get_video_capture()
        
        if not self.cap.isOpened():
            self.error_message = f"Cannot open stream: {self.stream_url}"
            raise ConnectionError(self.error_message)
        
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info(f"Started capture for: {self.stream_url}")
        
    def _capture_loop(self):
        """Main capture loop running in separate thread."""
        frame_interval = 1.0 / self.fps
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        
        while self.is_running:
            start_time = time.time()
            
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame, attempting reconnect...")
                reconnect_attempts += 1
                
                if reconnect_attempts > max_reconnect_attempts:
                    self.error_message = "Max reconnection attempts exceeded"
                    logger.error(self.error_message)
                    self.is_running = False
                    break
                    
                self._reconnect()
                continue
            
            # Reset reconnect counter on successful read
            reconnect_attempts = 0
            
            with self.lock:
                self.frame_buffer.append(frame.copy())
                self.raw_frame_buffer.append(frame.copy())
                self.last_frame = frame.copy()
                self.frame_counter += 1
            
            # Maintain target FPS
            elapsed = time.time() - start_time
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)
    
    def _reconnect(self):
        """Attempt to reconnect to the stream."""
        if self.cap:
            self.cap.release()
        time.sleep(2)
        self.cap = self._get_video_capture()
        
    def stop_capture(self):
        """Stop capturing frames."""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=5)
        if self.cap:
            self.cap.release()
        logger.info("Stopped capture")
    
    def get_frames_for_inference(self) -> list:
        """
        Get 16 frames for STEAD inference.
        Returns empty list if not enough frames.
        """
        with self.lock:
            if len(self.frame_buffer) < self.FRAME_BUFFER_SIZE:
                return []
            frames = list(self.frame_buffer)
            self.frame_buffer.clear()
            return frames
    
    def get_raw_frames(self) -> list:
        """Get raw frames for saving suspicious clips."""
        with self.lock:
            return list(self.raw_frame_buffer)
    
    def has_enough_frames(self) -> bool:
        """Check if buffer has enough frames for inference."""
        return len(self.frame_buffer) >= self.FRAME_BUFFER_SIZE
    
    def get_frame_count(self) -> int:
        """Get total frames processed."""
        return self.frame_counter
    
    def get_last_frame(self):
        """Get the most recent frame."""
        with self.lock:
            return self.last_frame.copy() if self.last_frame is not None else None
    
    def get_status(self) -> dict:
        """Get current processor status."""
        return {
            'is_running': self.is_running,
            'frame_count': self.frame_counter,
            'buffer_size': len(self.frame_buffer),
            'has_enough_frames': self.has_enough_frames(),
            'error': self.error_message
        }
    
    def save_clip(self, output_path: str = None) -> str:
        """
        Save current buffer as a video clip.
        
        Args:
            output_path: Optional output path. If None, creates temp file.
            
        Returns:
            Path to the saved video file.
        """
        frames = self.get_raw_frames()
        
        if not frames:
            raise ValueError("No frames available to save")
        
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.mp4')
        
        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))
        
        for frame in frames:
            out.write(frame)
        
        out.release()
        logger.info(f"Saved clip with {len(frames)} frames: {output_path}")
        return output_path


class RTSPStreamManager:
    """
    Manages multiple RTSP streams for different cameras.
    Singleton pattern ensures only one manager exists.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.streams = {}
            cls._instance.lock = threading.Lock()
        return cls._instance
    
    def add_stream(self, job_id: str, stream_url: str, fps: int = 15) -> RTSPProcessor:
        """
        Add and start a new stream.
        
        Args:
            job_id: Unique identifier for this stream
            stream_url: RTSP URL or camera index
            fps: Target frames per second
            
        Returns:
            RTSPProcessor instance
        """
        with self.lock:
            if job_id in self.streams:
                raise ValueError(f"Stream with job_id {job_id} already exists")
            
            processor = RTSPProcessor(stream_url, fps)
            
            is_valid, message = processor.validate_stream()
            if not is_valid:
                raise ConnectionError(f"Cannot connect to stream: {message}")
            
            processor.start_capture()
            self.streams[job_id] = processor
            logger.info(f"Added stream {job_id}: {stream_url}")
            return processor
    
    def get_stream(self, job_id: str) -> RTSPProcessor:
        """Get a stream by job_id."""
        return self.streams.get(job_id)
    
    def remove_stream(self, job_id: str):
        """Stop and remove a stream."""
        with self.lock:
            if job_id in self.streams:
                self.streams[job_id].stop_capture()
                del self.streams[job_id]
                logger.info(f"Removed stream {job_id}")
    
    def list_streams(self) -> list:
        """List all active stream job_ids."""
        return list(self.streams.keys())
    
    def get_all_statuses(self) -> dict:
        """Get status of all streams."""
        statuses = {}
        for job_id, processor in self.streams.items():
            statuses[job_id] = processor.get_status()
        return statuses
    
    def stop_all(self):
        """Stop all streams."""
        with self.lock:
            for job_id in list(self.streams.keys()):
                self.streams[job_id].stop_capture()
            self.streams.clear()
            logger.info("Stopped all streams")


# Global stream manager instance
stream_manager = RTSPStreamManager()
