from rest_framework import serializers
from .models import RTSPJob, AnomalyDetection, VideoUpload


class RTSPJobSerializer(serializers.ModelSerializer):
    """Serializer for RTSP Job model."""
    
    anomaly_count = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = RTSPJob
        fields = [
            'id', 'name', 'rtsp_url', 'status',
            'fps', 'buffer_size', 'threshold',
            'total_frames_processed', 'total_anomalies_detected',
            'last_anomaly_at', 'created_at', 'updated_at',
            'started_at', 'stopped_at', 'anomaly_count', 'user_email'
        ]
        read_only_fields = [
            'id', 'status', 'total_frames_processed',
            'total_anomalies_detected', 'last_anomaly_at',
            'created_at', 'updated_at', 'started_at', 'stopped_at', 'user_email'
        ]
    
    def get_anomaly_count(self, obj):
        return obj.anomalies.count()


class RTSPJobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating RTSP Jobs."""
    
    class Meta:
        model = RTSPJob
        fields = ['name', 'rtsp_url', 'fps', 'buffer_size', 'threshold']
    
    def validate_rtsp_url(self, value):
        """Validate RTSP URL or camera index."""
        # Allow camera index (integer)
        if value.isdigit():
            return value
        
        # Basic RTSP URL validation
        if not (value.startswith('rtsp://') or value.startswith('http://') or value.startswith('https://')):
            raise serializers.ValidationError(
                "URL must start with rtsp://, http://, or https:// (or be a camera index like 0)"
            )
        return value
    
    def validate_threshold(self, value):
        """Ensure threshold is between 0 and 1."""
        if not 0 <= value <= 1:
            raise serializers.ValidationError("Threshold must be between 0 and 1")
        return value


class AnomalyDetectionSerializer(serializers.ModelSerializer):
    """Serializer for Anomaly Detection model."""
    
    job_name = serializers.CharField(source='job.name', read_only=True)
    
    class Meta:
        model = AnomalyDetection
        fields = [
            'id', 'job', 'job_name', 'anomaly_score', 'label',
            'frame_start', 'frame_end', 'timestamp',
            'video_chunk', 'model_output'
        ]
        read_only_fields = ['id', 'timestamp', 'job_name']


class VideoUploadSerializer(serializers.ModelSerializer):
    """Serializer for Video Upload model."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    streaming_urls = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoUpload
        fields = [
            'id', 'original_filename', 'status',
            'has_anomaly', 'max_anomaly_score', 'avg_anomaly_score',
            'total_clips', 'anomaly_count', 'total_frames',
            'fps', 'resolution', 'result_details',
            'error_message', 'created_at', 'processed_at', 'user_email',
            'streaming_urls'
        ]
        read_only_fields = [
            'id', 'original_filename', 'status', 'has_anomaly',
            'max_anomaly_score', 'avg_anomaly_score', 'total_clips', 
            'anomaly_count', 'total_frames', 'fps', 'resolution',
            'result_details', 'error_message', 'created_at', 'processed_at',
            'streaming_urls'
        ]
    
    def get_streaming_urls(self, obj):
        """Get streaming URLs for this video."""
        request = self.context.get('request')
        return obj.get_stream_urls(request)


class VideoUploadRequestSerializer(serializers.Serializer):
    """Serializer for video upload request."""
    
    video = serializers.FileField()
    
    def validate_video(self, value):
        """Validate video file."""
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        import os
        ext = os.path.splitext(value.name)[1].lower()
        
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Max file size: 500MB
        max_size = 500 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size must be less than 500MB")
        
        return value
