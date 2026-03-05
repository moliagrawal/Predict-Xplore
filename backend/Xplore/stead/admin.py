from django.contrib import admin
from .models import RTSPJob, AnomalyDetection, VideoUpload


@admin.register(RTSPJob)
class RTSPJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user', 'status', 'total_anomalies_detected', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'rtsp_url', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'started_at', 'stopped_at', 'total_frames_processed', 'total_anomalies_detected']
    ordering = ['-created_at']


@admin.register(AnomalyDetection)
class AnomalyDetectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'anomaly_score', 'label', 'timestamp']
    list_filter = ['label', 'timestamp']
    search_fields = ['job__name']
    readonly_fields = ['id', 'timestamp']
    ordering = ['-timestamp']


@admin.register(VideoUpload)
class VideoUploadAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_filename', 'user', 'status', 'has_anomaly', 'max_anomaly_score', 'created_at']
    list_filter = ['status', 'has_anomaly', 'created_at']
    search_fields = ['original_filename', 'user__email']
    readonly_fields = ['id', 'created_at', 'processed_at']
    ordering = ['-created_at']
