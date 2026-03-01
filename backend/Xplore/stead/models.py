from django.db import models
from django.conf import settings
import uuid


class RTSPJob(models.Model):
    """Model to track RTSP stream processing jobs."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rtsp_jobs'
    )
    name = models.CharField(max_length=255, help_text="Camera/Stream name")
    rtsp_url = models.CharField(max_length=500, help_text="RTSP URL or camera index (0 for webcam)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Processing settings
    fps = models.IntegerField(default=15, help_text="Frames per second to capture")
    buffer_size = models.IntegerField(default=16, help_text="Frames to buffer before processing (STEAD requires 16)")
    threshold = models.FloatField(default=0.7, help_text="Anomaly detection threshold (0-1)")
    
    # Statistics
    total_frames_processed = models.BigIntegerField(default=0)
    total_anomalies_detected = models.IntegerField(default=0)
    last_anomaly_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'RTSP Job'
        verbose_name_plural = 'RTSP Jobs'
    
    def __str__(self):
        return f"{self.name} - {self.status}"


class AnomalyDetection(models.Model):
    """Model to store detected anomalies."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        RTSPJob,
        on_delete=models.CASCADE,
        related_name='anomalies'
    )
    
    # Anomaly details
    anomaly_score = models.FloatField()
    label = models.CharField(max_length=50, default='Suspicious')
    frame_start = models.IntegerField(null=True, blank=True)
    frame_end = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Video chunk that triggered the anomaly (optional)
    video_chunk = models.FileField(upload_to='anomaly_videos/', null=True, blank=True)
    
    # Model output details
    model_output = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Anomaly Detection'
        verbose_name_plural = 'Anomaly Detections'
    
    def __str__(self):
        return f"Anomaly in {self.job.name} - Score: {self.anomaly_score:.2f}"


class VideoUpload(models.Model):
    """Model to track video upload processing jobs."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video_uploads'
    )
    video_file = models.FileField(upload_to='stead_uploads/')
    original_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Output video files
    output_video = models.FileField(upload_to='stead_outputs/', null=True, blank=True)
    output_video_web = models.CharField(max_length=500, null=True, blank=True, help_text="Web-ready MP4 path")
    hls_playlist = models.CharField(max_length=500, null=True, blank=True, help_text="HLS playlist path")
    thumbnail = models.CharField(max_length=500, null=True, blank=True, help_text="Thumbnail image path")
    
    # Results
    has_anomaly = models.BooleanField(null=True)
    max_anomaly_score = models.FloatField(null=True)
    avg_anomaly_score = models.FloatField(null=True)
    total_clips = models.IntegerField(null=True)
    anomaly_count = models.IntegerField(null=True)
    total_frames = models.IntegerField(null=True)
    fps = models.FloatField(null=True)
    resolution = models.CharField(max_length=50, null=True, blank=True)
    result_details = models.JSONField(default=dict)
    
    # Error tracking
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Video Upload'
        verbose_name_plural = 'Video Uploads'
    
    def __str__(self):
        return f"{self.original_filename} - {self.status}"
    
    def get_stream_urls(self, request=None):
        """Get all streaming URLs for this video."""
        from django.conf import settings
        
        urls = {
            'original': None,
            'output': None,
            'web_ready': None,
            'hls': None,
            'thumbnail': None,
        }
        
        base_url = ''
        if request:
            base_url = request.build_absolute_uri(settings.MEDIA_URL)
        else:
            base_url = settings.MEDIA_URL
        
        if self.video_file:
            urls['original'] = f"{base_url}{self.video_file.name}"
        
        if self.output_video:
            urls['output'] = f"{base_url}{self.output_video.name}"
        
        if self.output_video_web:
            urls['web_ready'] = f"{base_url}{self.output_video_web}"
        
        if self.hls_playlist:
            urls['hls'] = f"{base_url}{self.hls_playlist}"
        
        if self.thumbnail:
            urls['thumbnail'] = f"{base_url}{self.thumbnail}"
        
        return urls
