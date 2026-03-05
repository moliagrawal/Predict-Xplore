/**
 * Video Upload Component
 * 
 * Upload video files for STEAD anomaly detection.
 */

import React, { useState, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { toast } from 'react-toastify';
import {
  uploadVideo,
  getVideoHistory,
  deleteVideo,
  getVideoStreamUrl,
  checkModelStatus,
  checkFFmpegStatus
} from '../../services/steadApi';
import {
  setModelStatus,
  setFFmpegStatus,
  setLoading,
  setProgress,
  addVideoUpload,
  setVideoUploads,
  removeVideoUpload,
  setCurrentUpload
} from '../../redux/reducers/steadSlice';

const VideoUpload = () => {
  const dispatch = useDispatch();
  const user = useSelector((state) => state.user.users[state.user.users.length - 1]);
  const { modelStatus, ffmpegStatus, videoUploads, currentUpload, loading, processingProgress } = useSelector((state) => state.stead);
  
  const [selectedFile, setSelectedFile] = useState(null);
  const [threshold, setThreshold] = useState(0.7);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  
  const fileInputRef = useRef(null);
  
  // Fetch history on mount
  React.useEffect(() => {
    if (user?.token) {
      fetchHistory();
      fetchStatuses();
    }
  }, [user?.token]);
  
  const fetchStatuses = async () => {
    try {
      const [modelRes, ffmpegRes] = await Promise.all([
        checkModelStatus(user.token),
        checkFFmpegStatus(user.token)
      ]);
      dispatch(setModelStatus(modelRes));
      dispatch(setFFmpegStatus(ffmpegRes));
    } catch (err) {
      console.error('Error fetching statuses:', err);
    }
  };
  
  const fetchHistory = async () => {
    try {
      const history = await getVideoHistory(user.token);
      dispatch(setVideoUploads(history));
    } catch (err) {
      console.error('Error fetching history:', err);
    }
  };
  
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('video/')) {
        toast.error('Please select a video file');
        return;
      }
      setSelectedFile(file);
    }
  };
  
  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      if (!file.type.startsWith('video/')) {
        toast.error('Please select a video file');
        return;
      }
      setSelectedFile(file);
    }
  };
  
  const handleDragOver = (e) => {
    e.preventDefault();
  };
  
  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error('Please select a video file');
      return;
    }
    
    if (!user?.token) {
      toast.error('Please login first');
      return;
    }
    
    setIsUploading(true);
    setUploadProgress(0);
    dispatch(setLoading(true));
    
    try {
      const result = await uploadVideo(
        user.token,
        selectedFile,
        threshold,
        (progress) => {
          setUploadProgress(progress);
          dispatch(setProgress(progress));
        }
      );
      
      if (result.success) {
        dispatch(addVideoUpload(result));
        dispatch(setCurrentUpload(result));
        toast.success('Video processed successfully!');
        setSelectedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        fetchHistory();
      } else {
        toast.error(result.error || 'Upload failed');
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.message;
      toast.error(errorMsg);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      dispatch(setLoading(false));
      dispatch(setProgress(0));
    }
  };
  
  const handleDelete = async (uploadId) => {
    if (!window.confirm('Are you sure you want to delete this video?')) {
      return;
    }
    
    try {
      await deleteVideo(user.token, uploadId);
      dispatch(removeVideoUpload(uploadId));
      toast.success('Video deleted');
    } catch (err) {
      toast.error(err.response?.data?.error || err.message);
    }
  };
  
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="min-h-screen bg-[#EAECFF] p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#123087] mb-2">
            Video Anomaly Detection
          </h1>
          <p className="text-gray-600">
            Upload video files to detect anomalies using STEAD model
          </p>
        </div>
        
        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <div className={`bg-white rounded-xl p-4 shadow-sm border-l-4 ${
            modelStatus.status === 'ready' ? 'border-green-500' : 'border-yellow-500'
          }`}>
            <h3 className="text-sm font-medium text-gray-500 mb-1">STEAD Model</h3>
            <p className={`text-lg font-semibold ${
              modelStatus.status === 'ready' ? 'text-green-600' : 'text-yellow-600'
            }`}>
              {modelStatus.status === 'ready' ? 'Ready' : 'Loading...'}
            </p>
          </div>
          
          <div className={`bg-white rounded-xl p-4 shadow-sm border-l-4 ${
            ffmpegStatus.available ? 'border-green-500' : 'border-red-500'
          }`}>
            <h3 className="text-sm font-medium text-gray-500 mb-1">FFmpeg</h3>
            <p className={`text-lg font-semibold ${
              ffmpegStatus.available ? 'text-green-600' : 'text-red-600'
            }`}>
              {ffmpegStatus.available ? 'Available' : 'Not Found'}
            </p>
          </div>
        </div>
        
        {/* Upload Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upload Form */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-[#123087] mb-4">
              Upload Video
            </h2>
            
            {/* Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
                selectedFile
                  ? 'border-green-400 bg-green-50'
                  : 'border-gray-300 hover:border-[#6966FF] hover:bg-[#6966FF]/5'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                className="hidden"
              />
              
              {selectedFile ? (
                <div>
                  <div className="w-12 h-12 mx-auto bg-green-100 rounded-full flex items-center justify-center mb-2">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="font-medium text-gray-800">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">{formatFileSize(selectedFile.size)}</p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                    className="mt-2 text-red-500 text-sm hover:underline"
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div>
                  <div className="w-12 h-12 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-2">
                    <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <p className="text-gray-600">
                    Drop video here or click to browse
                  </p>
                  <p className="text-sm text-gray-400 mt-1">
                    Supports MP4, AVI, MOV, MKV
                  </p>
                </div>
              )}
            </div>
            
            {/* Threshold Slider */}
            <div className="mt-6">
              <div className="flex justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">
                  Anomaly Threshold
                </label>
                <span className="text-sm font-mono text-[#6966FF]">{threshold}</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#6966FF]"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Sensitive</span>
                <span>Strict</span>
              </div>
            </div>
            
            {/* Upload Progress */}
            {isUploading && (
              <div className="mt-6">
                <div className="flex justify-between text-sm text-gray-600 mb-1">
                  <span>Processing...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#6966FF] transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}
            
            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
              className={`mt-6 w-full py-3 rounded-xl font-semibold text-white transition ${
                !selectedFile || isUploading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-[#6966FF] hover:bg-[#5855DD]'
              }`}
            >
              {isUploading ? 'Processing...' : 'Analyze Video'}
            </button>
          </div>
          
          {/* Current Result */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-[#123087] mb-4">
              Analysis Result
            </h2>
            
            {currentUpload ? (
              <div className="space-y-4">
                {/* Result Summary */}
                <div className={`p-4 rounded-lg ${
                  currentUpload.result?.has_anomaly
                    ? 'bg-red-50 border border-red-200'
                    : 'bg-green-50 border border-green-200'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className={`text-lg font-semibold ${
                      currentUpload.result?.has_anomaly ? 'text-red-600' : 'text-green-600'
                    }`}>
                      {currentUpload.result?.has_anomaly
                        ? 'Anomaly Detected'
                        : 'No Anomaly'
                      }
                    </span>
                    <span className="text-sm text-gray-500">
                      {currentUpload.filename}
                    </span>
                  </div>
                </div>
                
                {/* Stats */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500">Max Score</p>
                    <p className="text-xl font-bold text-[#123087]">
                      {((currentUpload.result?.max_anomaly_score || 0) * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500">Anomaly Count</p>
                    <p className="text-xl font-bold text-red-600">
                      {currentUpload.result?.anomaly_count || 0}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500">Total Frames</p>
                    <p className="text-xl font-bold text-[#123087]">
                      {currentUpload.result?.total_frames || 0}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500">FPS</p>
                    <p className="text-xl font-bold text-[#123087]">
                      {currentUpload.result?.fps?.toFixed(1) || 'N/A'}
                    </p>
                  </div>
                </div>
                
                {/* Output Video */}
                {currentUpload.upload_id && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Output Video</h3>
                    <video
                      controls
                      className="w-full rounded-lg bg-black"
                      src={`${getVideoStreamUrl(currentUpload.upload_id)}?token=${user.token}`}
                    >
                      Your browser does not support video playback.
                    </video>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <p className="text-gray-500">
                  Upload a video to see analysis results
                </p>
              </div>
            )}
          </div>
        </div>
        
        {/* Upload History */}
        {videoUploads.length > 0 && (
          <div className="mt-8 bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-[#123087] mb-4">
              Upload History
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-sm text-gray-500 border-b">
                    <th className="pb-3 pr-4">Filename</th>
                    <th className="pb-3 pr-4">Status</th>
                    <th className="pb-3 pr-4">Anomaly</th>
                    <th className="pb-3 pr-4">Score</th>
                    <th className="pb-3 pr-4">Date</th>
                    <th className="pb-3 pr-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {videoUploads.map((upload) => (
                    <tr key={upload.id} className="border-b last:border-0">
                      <td className="py-3 pr-4 text-sm font-medium">
                        {upload.original_filename}
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          upload.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : upload.status === 'error'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {upload.status}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        {upload.has_anomaly ? (
                          <span className="text-red-600">Yes ({upload.anomaly_count})</span>
                        ) : (
                          <span className="text-green-600">No</span>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-sm">
                        {((upload.max_anomaly_score || 0) * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 pr-4 text-sm text-gray-500">
                        {new Date(upload.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex gap-2">
                          <button
                            onClick={() => dispatch(setCurrentUpload(upload))}
                            className="text-[#6966FF] text-sm hover:underline"
                          >
                            View
                          </button>
                          <button
                            onClick={() => handleDelete(upload.id)}
                            className="text-red-500 text-sm hover:underline"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoUpload;
