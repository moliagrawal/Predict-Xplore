"""
STEAD Anomaly Detection Inference Module.

This module provides the STEADInference class for running anomaly detection
on video frames and video files using the STEAD model.
"""

import torch
import cv2
import numpy as np
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Get the directory where this file is located
STEAD_DIR = Path(__file__).resolve().parent
MODEL_PATH = STEAD_DIR / 'model.pth'

# Import the STEAD model architecture
from .model import Model


class STEADInference:
    """
    STEAD Anomaly Detection Inference Class.
    
    Processes video frames and returns anomaly scores.
    Uses singleton pattern to load model only once.
    """
    
    # Configuration - STEAD model requirements
    T = 16  # Number of frames per clip
    FRAME_SIZE = (32, 32)  # Resize frames to this size
    CHANNELS_REQUIRED = 192  # Required channels for model
    DEFAULT_THRESHOLD = 0.7  # Anomaly threshold
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern - load model only once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.threshold = self.DEFAULT_THRESHOLD
        self._load_model()
        self._initialized = True
    
    def _load_model(self):
        """Load the STEAD model."""
        logger.info(f"Loading STEAD model on device: {self.device}")
        
        try:
            self.model = Model()
            
            if MODEL_PATH.exists():
                state_dict = torch.load(MODEL_PATH, map_location=self.device, weights_only=True)
                self.model.load_state_dict(state_dict)
                logger.info(f"Loaded model weights from {MODEL_PATH}")
            else:
                logger.error(f"Model weights not found at {MODEL_PATH}")
                raise FileNotFoundError(f"Model weights not found at {MODEL_PATH}")
            
            self.model.to(self.device)
            self.model.eval()
            logger.info("STEAD model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load STEAD model: {e}")
            raise
    
    def set_threshold(self, threshold: float):
        """Set the anomaly detection threshold."""
        if not 0 <= threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")
        self.threshold = threshold
    
    def preprocess_frame(self, frame: np.ndarray) -> torch.Tensor:
        """
        Preprocess a single frame for the model.
        
        Args:
            frame: BGR frame from OpenCV (H, W, 3)
            
        Returns:
            Tensor of shape (3, 32, 32)
        """
        frame_resized = cv2.resize(frame, self.FRAME_SIZE)
        frame_tensor = torch.tensor(frame_resized, dtype=torch.float32).permute(2, 0, 1) / 255.0
        return frame_tensor
    
    def preprocess_frames(self, frames: list) -> torch.Tensor:
        """
        Preprocess a list of frames into model input.
        
        Args:
            frames: List of 16 BGR frames from OpenCV
            
        Returns:
            Tensor ready for model input (1, 192, 16, 32, 32)
        """
        if len(frames) != self.T:
            raise ValueError(f"Expected {self.T} frames, got {len(frames)}")
        
        # Preprocess each frame
        frame_tensors = [self.preprocess_frame(f) for f in frames]
        
        # Stack into (T, 3, H, W) = (16, 3, 32, 32)
        frames_tensor = torch.stack(frame_tensors)
        
        # Rearrange to (1, 3, 16, 32, 32)
        frames_tensor = frames_tensor.permute(1, 0, 2, 3).unsqueeze(0)
        
        # Repeat channels to get (1, 192, 16, 32, 32)
        sequence = frames_tensor.repeat(1, self.CHANNELS_REQUIRED // 3, 1, 1, 1)
        
        return sequence
    
    def predict_frames(self, frames: list, threshold: float = None) -> dict:
        """
        Run anomaly detection on a list of frames.
        
        Args:
            frames: List of exactly 16 BGR frames from OpenCV
            threshold: Optional custom threshold (uses default if not provided)
            
        Returns:
            dict with:
                - has_anomaly: bool
                - anomaly_score: float (0-1)
                - label: str ('Normal' or 'Suspicious')
        """
        if len(frames) != self.T:
            raise ValueError(f"Expected {self.T} frames, got {len(frames)}")
        
        threshold = threshold or self.threshold
        
        # Preprocess
        sequence = self.preprocess_frames(frames).to(self.device)
        
        # Inference
        with torch.no_grad():
            logits, features = self.model(sequence)
            prediction = torch.sigmoid(logits).item()
        
        has_anomaly = prediction > threshold
        label = 'Suspicious' if has_anomaly else 'Normal'
        
        return {
            'has_anomaly': has_anomaly,
            'anomaly_score': round(prediction, 4),
            'label': label,
            'threshold': threshold
        }
    
    def draw_annotation(
        self,
        frame: np.ndarray,
        anomaly_score: float,
        clip_index: int,
        has_anomaly: bool,
        threshold: float
    ) -> np.ndarray:
        """
        Draw anomaly detection annotations on a frame.
        
        Args:
            frame: BGR frame from OpenCV
            anomaly_score: Current anomaly score (0-1)
            clip_index: Current clip number
            has_anomaly: Whether anomaly was detected
            threshold: Detection threshold
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        
        # Colors
        if has_anomaly:
            status_color = (0, 0, 200)  # Red background
            border_color = (0, 0, 255)  # Red border
            text_color = (255, 255, 255)
        else:
            status_color = (0, 120, 0)  # Green background
            border_color = (0, 255, 0)  # Green border
            text_color = (255, 255, 255)
        
        # Draw status bar at top
        cv2.rectangle(annotated, (0, 0), (w, 70), status_color, -1)
        
        # Status text
        status_text = "⚠ ANOMALY DETECTED" if has_anomaly else "✓ Normal"
        cv2.putText(
            annotated, status_text, (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, text_color, 2
        )
        
        # Score text
        score_text = f"Score: {anomaly_score:.4f} | Threshold: {threshold}"
        cv2.putText(
            annotated, score_text, (15, 55),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1
        )
        
        # Clip info on right
        clip_text = f"Clip #{clip_index}"
        text_size = cv2.getTextSize(clip_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        cv2.putText(
            annotated, clip_text, (w - text_size[0] - 15, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1
        )
        
        # Draw progress bar at bottom
        bar_height = 25
        bar_y = h - bar_height - 10
        bar_margin = 15
        bar_width = w - (2 * bar_margin)
        
        # Background
        cv2.rectangle(
            annotated,
            (bar_margin, bar_y),
            (bar_margin + bar_width, bar_y + bar_height),
            (60, 60, 60), -1
        )
        
        # Score fill
        score_width = int(bar_width * anomaly_score)
        fill_color = (0, 0, 255) if has_anomaly else (0, 200, 0)
        cv2.rectangle(
            annotated,
            (bar_margin, bar_y),
            (bar_margin + score_width, bar_y + bar_height),
            fill_color, -1
        )
        
        # Threshold line
        threshold_x = bar_margin + int(bar_width * threshold)
        cv2.line(
            annotated,
            (threshold_x, bar_y - 5),
            (threshold_x, bar_y + bar_height + 5),
            (0, 255, 255), 2
        )
        
        # Border
        cv2.rectangle(
            annotated,
            (bar_margin, bar_y),
            (bar_margin + bar_width, bar_y + bar_height),
            (200, 200, 200), 1
        )
        
        # Anomaly border around entire frame
        if has_anomaly:
            cv2.rectangle(annotated, (0, 0), (w-1, h-1), border_color, 4)
        
        return annotated

    def predict_video(
        self,
        video_path: str,
        output_path: str = None,
        stride: int = 16,
        threshold: float = None,
        save_output: bool = True
    ) -> dict:
        """
        Run anomaly detection on a video file and generate annotated output.
        
        Args:
            video_path: Path to the video file
            output_path: Path for output video (auto-generated if None)
            stride: Number of frames to skip between clips (default: 16 = non-overlapping)
            threshold: Optional custom threshold
            save_output: Whether to save annotated output video
            
        Returns:
            dict with:
                - has_anomaly: bool (True if any clip has anomaly)
                - max_anomaly_score: float
                - anomaly_clips: list of clip results with anomalies
                - output_video: path to annotated output video
                - all_clips: list of all clip results
                - total_frames: int
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        threshold = threshold or self.threshold
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video info
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Setup output video writer
        out = None
        if save_output:
            if output_path is None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = Path(video_path).parent
                output_path = str(output_dir / f"output_{timestamp}.mp4")
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frames = []
        all_clips = []
        anomaly_clips = []
        frame_counter = 0
        clip_index = 0
        current_score = 0.0
        current_anomaly = False
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_counter += 1
                frames.append(frame.copy())
                
                if len(frames) == self.T:
                    clip_index += 1
                    start_idx = frame_counter - self.T + 1
                    end_idx = frame_counter
                    
                    result = self.predict_frames(frames, threshold)
                    result['clip_index'] = clip_index
                    result['clip'] = f"{start_idx}-{end_idx}"
                    result['start_frame'] = start_idx
                    result['end_frame'] = end_idx
                    
                    current_score = result['anomaly_score']
                    current_anomaly = result['has_anomaly']
                    
                    all_clips.append(result)
                    
                    if result['has_anomaly']:
                        anomaly_clips.append(result)
                    
                    # Write annotated frames
                    if out:
                        for f in frames:
                            annotated = self.draw_annotation(
                                f, current_score, clip_index, current_anomaly, threshold
                            )
                            out.write(annotated)
                    
                    # Use stride to determine overlap
                    if stride >= self.T:
                        frames = []  # Non-overlapping
                    else:
                        frames = frames[stride:]  # Overlapping window
            
            # Handle remaining frames
            if out and frames:
                for f in frames:
                    annotated = self.draw_annotation(
                        f, current_score, clip_index, current_anomaly, threshold
                    )
                    out.write(annotated)
        
        finally:
            cap.release()
            if out:
                out.release()
        
        # Calculate summary
        max_score = max([c['anomaly_score'] for c in all_clips]) if all_clips else 0.0
        avg_score = sum([c['anomaly_score'] for c in all_clips]) / len(all_clips) if all_clips else 0.0
        has_anomaly = len(anomaly_clips) > 0
        
        return {
            'has_anomaly': has_anomaly,
            'max_anomaly_score': max_score,
            'avg_anomaly_score': round(avg_score, 4),
            'anomaly_clips': anomaly_clips,
            'total_clips': len(all_clips),
            'anomaly_count': len(anomaly_clips),
            'total_frames': frame_counter,
            'video_fps': fps,
            'resolution': f"{width}x{height}",
            'threshold_used': threshold,
            'output_video': output_path if save_output else None,
            'all_clips': all_clips
        }


def get_stead_model() -> STEADInference:
    """Get the singleton STEAD model instance."""
    return STEADInference()


def run_anomaly_detection(
    video_path: str,
    output_path: str = None,
    threshold: float = None,
    save_output: bool = True
) -> dict:
    """
    Convenience function to run anomaly detection on a video.
    
    Args:
        video_path: Path to video file
        output_path: Path for annotated output video
        threshold: Optional custom threshold (0-1)
        save_output: Whether to save annotated output video
        
    Returns:
        Anomaly detection results with output video path
    """
    model = get_stead_model()
    return model.predict_video(
        video_path,
        output_path=output_path,
        threshold=threshold,
        save_output=save_output
    )
