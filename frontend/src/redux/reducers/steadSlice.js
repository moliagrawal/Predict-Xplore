/**
 * STEAD Redux Slice
 * 
 * Manages state for STEAD anomaly detection features.
 */

import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  // Model status
  modelStatus: {
    loaded: false,
    status: 'unknown',
    device: null,
    cudaAvailable: false,
    threshold: 0.7,
    framesRequired: 16
  },
  
  // FFmpeg status
  ffmpegStatus: {
    available: false,
    path: null
  },
  
  // RTSP Live Jobs
  liveJobs: [],
  currentJob: null,
  
  // Video uploads
  videoUploads: [],
  currentUpload: null,
  
  // Anomalies
  anomalies: [],
  
  // UI state
  loading: false,
  error: null,
  processingProgress: 0
};

export const steadSlice = createSlice({
  name: "stead",
  initialState,
  reducers: {
    // Model Status
    setModelStatus: (state, action) => {
      state.modelStatus = {
        loaded: action.payload.model_loaded,
        status: action.payload.status,
        device: action.payload.device,
        cudaAvailable: action.payload.cuda_available,
        cudaDeviceName: action.payload.cuda_device_name,
        threshold: action.payload.threshold,
        framesRequired: action.payload.frames_required,
        frameSize: action.payload.frame_size
      };
    },
    
    // FFmpeg Status
    setFFmpegStatus: (state, action) => {
      state.ffmpegStatus = {
        available: action.payload.ffmpeg_available,
        path: action.payload.ffmpeg_path,
        ffprobePath: action.payload.ffprobe_path
      };
    },
    
    // Loading state
    setLoading: (state, action) => {
      state.loading = action.payload;
    },
    
    // Error state
    setError: (state, action) => {
      state.error = action.payload;
    },
    
    clearError: (state) => {
      state.error = null;
    },
    
    // Progress
    setProgress: (state, action) => {
      state.processingProgress = action.payload;
    },
    
    // RTSP Live Jobs
    setLiveJobs: (state, action) => {
      state.liveJobs = action.payload.jobs || [];
    },
    
    addLiveJob: (state, action) => {
      state.liveJobs.push(action.payload);
      state.currentJob = action.payload;
    },
    
    updateLiveJob: (state, action) => {
      const { jobId, data } = action.payload;
      const index = state.liveJobs.findIndex(job => job.job_id === jobId);
      if (index !== -1) {
        state.liveJobs[index] = { ...state.liveJobs[index], ...data };
      }
      if (state.currentJob && state.currentJob.job_id === jobId) {
        state.currentJob = { ...state.currentJob, ...data };
      }
    },
    
    setCurrentJob: (state, action) => {
      state.currentJob = action.payload;
    },
    
    clearCurrentJob: (state) => {
      state.currentJob = null;
    },
    
    removeLiveJob: (state, action) => {
      const jobId = action.payload;
      state.liveJobs = state.liveJobs.filter(job => job.job_id !== jobId);
      if (state.currentJob && state.currentJob.job_id === jobId) {
        state.currentJob = null;
      }
    },
    
    // Video Uploads
    setVideoUploads: (state, action) => {
      state.videoUploads = action.payload;
    },
    
    addVideoUpload: (state, action) => {
      state.videoUploads.unshift(action.payload);
      state.currentUpload = action.payload;
    },
    
    setCurrentUpload: (state, action) => {
      state.currentUpload = action.payload;
    },
    
    clearCurrentUpload: (state) => {
      state.currentUpload = null;
    },
    
    removeVideoUpload: (state, action) => {
      const uploadId = action.payload;
      state.videoUploads = state.videoUploads.filter(upload => upload.upload_id !== uploadId);
      if (state.currentUpload && state.currentUpload.upload_id === uploadId) {
        state.currentUpload = null;
      }
    },
    
    // Anomalies
    setAnomalies: (state, action) => {
      state.anomalies = action.payload;
    },
    
    addAnomaly: (state, action) => {
      state.anomalies.unshift(action.payload);
    },
    
    removeAnomaly: (state, action) => {
      state.anomalies = state.anomalies.filter(a => a.id !== action.payload);
    },
    
    // Reset state
    resetState: () => initialState
  }
});

export const {
  setModelStatus,
  setFFmpegStatus,
  setLoading,
  setError,
  clearError,
  setProgress,
  setLiveJobs,
  addLiveJob,
  updateLiveJob,
  setCurrentJob,
  clearCurrentJob,
  removeLiveJob,
  setVideoUploads,
  addVideoUpload,
  setCurrentUpload,
  clearCurrentUpload,
  removeVideoUpload,
  setAnomalies,
  addAnomaly,
  removeAnomaly,
  resetState
} = steadSlice.actions;

export default steadSlice.reducer;
