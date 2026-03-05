"""
RTSP Server Simulator for Testing.

Converts a local video file to an RTSP stream using FFmpeg.
This allows testing the RTSP processing pipeline without an actual RTSP camera.

Usage:
    python rtsp_server_simulator.py --video /path/to/video.mp4
    python rtsp_server_simulator.py --video /path/to/video.mp4 --port 8554 --stream_name live
"""

import subprocess
import os
import sys
import argparse
import signal
import threading
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RTSPServerSimulator:
    """
    Simulates an RTSP server using FFmpeg.
    
    Uses FFmpeg to stream a local video file as an RTSP stream.
    Can also work with rtsp-simple-server (mediamtx) for a full RTSP server.
    """
    
    def __init__(
        self,
        video_path: str,
        port: int = 8554,
        stream_name: str = "live",
        loop: bool = True
    ):
        """
        Args:
            video_path: Path to the input video file
            port: RTSP server port
            stream_name: Name of the RTSP stream
            loop: Whether to loop the video continuously
        """
        self.video_path = Path(video_path)
        self.port = port
        self.stream_name = stream_name
        self.loop = loop
        self.process = None
        self.mediamtx_process = None
        self.is_running = False
        
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
    
    @property
    def rtsp_url(self) -> str:
        """Get the RTSP URL for this stream."""
        return f"rtsp://localhost:{self.port}/{self.stream_name}"
    
    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable."""
        import shutil
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            return ffmpeg
        
        common_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/homebrew/bin/ffmpeg',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
    
    def start_simple(self) -> str:
        """
        Start streaming using FFmpeg to UDP (simpler, no RTSP server needed).
        
        This method streams to UDP which can be captured by OpenCV.
        Returns the stream URL.
        """
        ffmpeg_path = self._find_ffmpeg()
        
        # Stream to UDP instead of RTSP (works without a separate RTSP server)
        udp_url = f"udp://localhost:{self.port}"
        
        loop_args = ['-stream_loop', '-1'] if self.loop else []
        
        cmd = [
            ffmpeg_path,
            *loop_args,
            '-re',  # Read input at native frame rate
            '-i', str(self.video_path),
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-f', 'mpegts',
            udp_url
        ]
        
        logger.info(f"Starting UDP stream: {udp_url}")
        logger.info(f"Command: {' '.join(cmd)}")
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.is_running = True
        
        # Start error reader thread
        threading.Thread(target=self._read_stderr, daemon=True).start()
        
        return udp_url
    
    def start_rtsp_rtp(self) -> str:
        """
        Start streaming directly via RTP (can be used as pseudo RTSP).
        
        This creates an SDP file that can be opened by media players.
        """
        ffmpeg_path = self._find_ffmpeg()
        
        rtp_port = self.port
        
        # Create SDP file for stream information
        sdp_content = f"""v=0
o=- 0 0 IN IP4 127.0.0.1
s=STEAD Test Stream
c=IN IP4 127.0.0.1
m=video {rtp_port} RTP/AVP 96
a=rtpmap:96 H264/90000
"""
        sdp_path = Path(self.video_path).parent / "stream.sdp"
        with open(sdp_path, 'w') as f:
            f.write(sdp_content)
        
        loop_args = ['-stream_loop', '-1'] if self.loop else []
        
        cmd = [
            ffmpeg_path,
            *loop_args,
            '-re',
            '-i', str(self.video_path),
            '-an',  # No audio
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-profile:v', 'baseline',
            '-pix_fmt', 'yuv420p',
            '-f', 'rtp',
            f'rtp://127.0.0.1:{rtp_port}'
        ]
        
        logger.info(f"Starting RTP stream on port: {rtp_port}")
        logger.info(f"SDP file: {sdp_path}")
        logger.info(f"Use OpenCV: cv2.VideoCapture('{sdp_path}')")
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.is_running = True
        threading.Thread(target=self._read_stderr, daemon=True).start()
        
        return str(sdp_path)
    
    def start_tcp_stream(self) -> str:
        """
        Start a TCP stream that can be read directly by OpenCV.
        
        This is the simplest method and works with:
        cv2.VideoCapture('tcp://localhost:port')
        """
        ffmpeg_path = self._find_ffmpeg()
        
        loop_args = ['-stream_loop', '-1'] if self.loop else []
        
        # Stream directly over TCP using MPEG-TS format
        tcp_url = f"tcp://localhost:{self.port}?listen=1"
        
        cmd = [
            ffmpeg_path,
            *loop_args,
            '-re',  # Real-time input
            '-i', str(self.video_path),
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-profile:v', 'baseline',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-f', 'mpegts',
            tcp_url
        ]
        
        logger.info(f"Starting TCP stream server on port: {self.port}")
        logger.info(f"Client URL: tcp://localhost:{self.port}")
        logger.info(f"Command: {' '.join(cmd)}")
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.is_running = True
        threading.Thread(target=self._read_stderr, daemon=True).start()
        
        # Return the client URL (without ?listen=1)
        return f"tcp://localhost:{self.port}"
    
    def start_file_stream(self) -> str:
        """
        The simplest approach - just return the file path.
        OpenCV can read video files directly.
        
        This is useful for testing without any network streaming.
        """
        logger.info(f"Using direct file access: {self.video_path}")
        return str(self.video_path)
    
    def _read_stderr(self):
        """Read stderr from FFmpeg process for logging."""
        if self.process and self.process.stderr:
            for line in iter(self.process.stderr.readline, b''):
                if line:
                    logger.debug(f"FFmpeg: {line.decode().strip()}")
    
    def stop(self):
        """Stop the streaming server."""
        self.is_running = False
        
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logger.info("Stopped FFmpeg stream")
        
        if self.mediamtx_process:
            self.mediamtx_process.terminate()
            try:
                self.mediamtx_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.mediamtx_process.kill()
            logger.info("Stopped MediaMTX server")
    
    def is_active(self) -> bool:
        """Check if the stream is active."""
        if self.process:
            return self.process.poll() is None
        return False
    
    def get_video_info(self) -> dict:
        """Get information about the source video."""
        import shutil
        ffprobe = shutil.which('ffprobe')
        
        if not ffprobe:
            return {'error': 'ffprobe not found'}
        
        try:
            cmd = [
                ffprobe,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(self.video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            return json.loads(result.stdout)
        except Exception as e:
            return {'error': str(e)}


def create_test_stream(video_path: str, method: str = 'file') -> tuple:
    """
    Convenience function to create a test stream.
    
    Args:
        video_path: Path to the video file
        method: Streaming method - 'file', 'tcp', 'udp', or 'rtp'
        
    Returns:
        tuple: (simulator instance, stream URL)
    """
    simulator = RTSPServerSimulator(video_path)
    
    if method == 'file':
        url = simulator.start_file_stream()
    elif method == 'tcp':
        url = simulator.start_tcp_stream()
    elif method == 'udp':
        url = simulator.start_simple()
    elif method == 'rtp':
        url = simulator.start_rtsp_rtp()
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return simulator, url


def main():
    parser = argparse.ArgumentParser(description='RTSP Server Simulator for Testing')
    parser.add_argument('--video', required=True, help='Path to input video file')
    parser.add_argument('--port', type=int, default=8554, help='Stream port (default: 8554)')
    parser.add_argument('--stream_name', default='live', help='Stream name (default: live)')
    parser.add_argument('--method', choices=['file', 'tcp', 'udp', 'rtp'], default='tcp',
                       help='Streaming method (default: tcp)')
    parser.add_argument('--no-loop', action='store_true', help='Do not loop the video')
    
    args = parser.parse_args()
    
    simulator = RTSPServerSimulator(
        video_path=args.video,
        port=args.port,
        stream_name=args.stream_name,
        loop=not args.no_loop
    )
    
    # Print video info
    info = simulator.get_video_info()
    if 'format' in info:
        logger.info(f"Video duration: {info['format'].get('duration', 'unknown')}s")
        logger.info(f"Video size: {info['format'].get('size', 'unknown')} bytes")
    
    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        simulator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the stream
    if args.method == 'file':
        url = simulator.start_file_stream()
    elif args.method == 'tcp':
        url = simulator.start_tcp_stream()
    elif args.method == 'udp':
        url = simulator.start_simple()
    elif args.method == 'rtp':
        url = simulator.start_rtsp_rtp()
    
    logger.info("=" * 50)
    logger.info(f"Stream URL: {url}")
    logger.info(f"Use this URL in your RTSP processing API")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 50)
    
    # Keep running until interrupted
    while simulator.is_active():
        time.sleep(1)
    
    logger.info("Stream ended")


if __name__ == '__main__':
    main()
