"""
FFmpeg Video Streaming Utility for STEAD.

Provides functionality to:
- Convert videos to web-compatible formats (H.264/AAC)
- Generate HLS (HTTP Live Streaming) segments for adaptive streaming
- Stream videos with proper frontend compatibility
"""

import subprocess
import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


class FFmpegProcessor:
    """
    FFmpeg-based video processing for streaming.
    """
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
    
    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable."""
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            return ffmpeg
        
        # Common paths
        common_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/homebrew/bin/ffmpeg',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
    
    def _find_ffprobe(self) -> str:
        """Find FFprobe executable."""
        ffprobe = shutil.which('ffprobe')
        if ffprobe:
            return ffprobe
        
        common_paths = [
            '/usr/bin/ffprobe',
            '/usr/local/bin/ffprobe',
            '/opt/homebrew/bin/ffprobe',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def is_available(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_video_info(self, video_path: str) -> dict:
        """Get video metadata using FFprobe."""
        if not self.ffprobe_path:
            return {}
        
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"FFprobe error: {e}")
            return {}
    
    def convert_to_web_format(
        self,
        input_path: str,
        output_path: str,
        codec: str = 'libx264',
        audio_codec: str = 'aac',
        crf: int = 23,
        preset: str = 'medium'
    ) -> bool:
        """
        Convert video to web-compatible format (H.264 + AAC in MP4).
        
        Args:
            input_path: Input video path
            output_path: Output video path
            codec: Video codec (default: libx264)
            audio_codec: Audio codec (default: aac)
            crf: Constant Rate Factor for quality (lower = better, 18-28 typical)
            preset: Encoding speed preset (ultrafast, fast, medium, slow)
            
        Returns:
            bool: Success status
        """
        try:
            cmd = [
                self.ffmpeg_path,
                '-y',  # Overwrite output
                '-i', input_path,
                '-c:v', codec,
                '-preset', preset,
                '-crf', str(crf),
                '-c:a', audio_codec,
                '-b:a', '128k',
                '-movflags', '+faststart',  # Enable fast start for web streaming
                '-pix_fmt', 'yuv420p',  # Ensure compatibility
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Converted video to web format: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion error: {e.stderr}")
            return False
    
    def generate_hls_stream(
        self,
        input_path: str,
        output_dir: str,
        segment_duration: int = 4,
        playlist_name: str = 'playlist.m3u8'
    ) -> Optional[str]:
        """
        Generate HLS (HTTP Live Streaming) segments for adaptive streaming.
        
        Args:
            input_path: Input video path
            output_dir: Output directory for HLS segments
            segment_duration: Duration of each segment in seconds
            playlist_name: Name of the master playlist file
            
        Returns:
            str: Path to the playlist file, or None on failure
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            playlist_path = os.path.join(output_dir, playlist_name)
            segment_pattern = os.path.join(output_dir, 'segment_%03d.ts')
            
            cmd = [
                self.ffmpeg_path,
                '-y',
                '-i', input_path,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-hls_time', str(segment_duration),
                '-hls_list_size', '0',  # Keep all segments in playlist
                '-hls_segment_filename', segment_pattern,
                '-f', 'hls',
                playlist_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Generated HLS stream: {playlist_path}")
            return playlist_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"HLS generation error: {e.stderr}")
            return None
    
    def generate_thumbnail(
        self,
        input_path: str,
        output_path: str,
        timestamp: str = '00:00:01'
    ) -> bool:
        """
        Generate a thumbnail from the video.
        
        Args:
            input_path: Input video path
            output_path: Output image path (jpg/png)
            timestamp: Timestamp to capture (format: HH:MM:SS)
            
        Returns:
            bool: Success status
        """
        try:
            cmd = [
                self.ffmpeg_path,
                '-y',
                '-i', input_path,
                '-ss', timestamp,
                '-vframes', '1',
                '-q:v', '2',
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"Generated thumbnail: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Thumbnail generation error: {e}")
            return False
    
    def extract_anomaly_clip(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        duration: float = 5.0
    ) -> bool:
        """
        Extract a clip around the anomaly detection point.
        
        Args:
            input_path: Input video path
            output_path: Output clip path
            start_time: Start time in seconds
            duration: Clip duration in seconds
            
        Returns:
            bool: Success status
        """
        try:
            cmd = [
                self.ffmpeg_path,
                '-y',
                '-ss', str(max(0, start_time - 2)),  # Start 2 seconds before
                '-i', input_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-movflags', '+faststart',
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"Extracted anomaly clip: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Clip extraction error: {e}")
            return False


class VideoStreamManager:
    """
    Manages video storage and streaming preparation.
    """
    
    def __init__(self, base_dir: str):
        """
        Args:
            base_dir: Base directory for video storage
        """
        self.base_dir = Path(base_dir)
        self.uploads_dir = self.base_dir / 'stead_uploads'
        self.outputs_dir = self.base_dir / 'stead_outputs'
        self.hls_dir = self.base_dir / 'stead_hls'
        self.thumbnails_dir = self.base_dir / 'stead_thumbnails'
        self.clips_dir = self.base_dir / 'stead_clips'
        
        # Create directories
        for dir_path in [self.uploads_dir, self.outputs_dir, self.hls_dir, 
                         self.thumbnails_dir, self.clips_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.ffmpeg = FFmpegProcessor()
    
    def process_output_video(
        self,
        video_id: str,
        input_video_path: str,
        annotated_video_path: str
    ) -> dict:
        """
        Process and prepare video for streaming.
        
        Args:
            video_id: Unique identifier for this video
            input_video_path: Path to original uploaded video
            annotated_video_path: Path to annotated output video
            
        Returns:
            dict with paths to all generated assets
        """
        result = {
            'video_id': video_id,
            'original': input_video_path,
            'annotated': annotated_video_path,
            'web_ready': None,
            'hls_playlist': None,
            'thumbnail': None,
            'success': False
        }
        
        try:
            # 1. Convert annotated video to web-ready format
            web_ready_path = str(self.outputs_dir / f"{video_id}_web.mp4")
            if self.ffmpeg.convert_to_web_format(annotated_video_path, web_ready_path):
                result['web_ready'] = web_ready_path
            
            # 2. Generate HLS stream for adaptive playback
            hls_output_dir = str(self.hls_dir / video_id)
            hls_playlist = self.ffmpeg.generate_hls_stream(
                web_ready_path or annotated_video_path,
                hls_output_dir
            )
            if hls_playlist:
                result['hls_playlist'] = hls_playlist
            
            # 3. Generate thumbnail
            thumbnail_path = str(self.thumbnails_dir / f"{video_id}.jpg")
            if self.ffmpeg.generate_thumbnail(annotated_video_path, thumbnail_path):
                result['thumbnail'] = thumbnail_path
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"Video processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def extract_anomaly_clips(
        self,
        video_id: str,
        input_video_path: str,
        anomaly_clips: list,
        fps: float
    ) -> list:
        """
        Extract individual clips for each detected anomaly.
        
        Args:
            video_id: Video identifier
            input_video_path: Path to the input video
            anomaly_clips: List of anomaly detection results with frame info
            fps: Video frame rate
            
        Returns:
            List of extracted clip paths
        """
        extracted_clips = []
        
        for i, clip in enumerate(anomaly_clips):
            start_frame = clip.get('start_frame', 0)
            start_time = start_frame / fps if fps > 0 else 0
            
            clip_filename = f"{video_id}_anomaly_{i+1}.mp4"
            clip_path = str(self.clips_dir / clip_filename)
            
            if self.ffmpeg.extract_anomaly_clip(input_video_path, clip_path, start_time):
                extracted_clips.append({
                    'clip_index': i + 1,
                    'path': clip_path,
                    'start_time': start_time,
                    'anomaly_score': clip.get('anomaly_score', 0)
                })
        
        return extracted_clips
    
    def cleanup_video(self, video_id: str):
        """Remove all assets associated with a video."""
        patterns = [
            self.uploads_dir / f"*{video_id}*",
            self.outputs_dir / f"*{video_id}*",
            self.hls_dir / video_id,
            self.thumbnails_dir / f"{video_id}*",
            self.clips_dir / f"{video_id}*",
        ]
        
        import glob
        for pattern in patterns:
            for path in glob.glob(str(pattern)):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")


# Global instance
_stream_manager = None


def get_stream_manager() -> VideoStreamManager:
    """Get the global VideoStreamManager instance."""
    global _stream_manager
    if _stream_manager is None:
        from django.conf import settings
        _stream_manager = VideoStreamManager(settings.MEDIA_ROOT)
    return _stream_manager
