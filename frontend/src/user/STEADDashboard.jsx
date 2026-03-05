/**
 * STEAD Dashboard Page
 * 
 * Main dashboard for STEAD anomaly detection features.
 * Provides navigation to RTSP Live Processing and Video Upload.
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import Navbar from '../components/Navbar';
import {
  checkModelStatus,
  checkFFmpegStatus,
  listRTSPLiveJobs,
  getVideoHistory
} from '../services/steadApi';
import {
  setModelStatus,
  setFFmpegStatus,
  setLiveJobs,
  setVideoUploads
} from '../redux/reducers/steadSlice';

const STEADDashboard = () => {
  const dispatch = useDispatch();
  const user = useSelector((state) => state.user.users[state.user.users.length - 1]);
  const { modelStatus, ffmpegStatus, liveJobs, videoUploads } = useSelector((state) => state.stead);
  
  const [stats, setStats] = useState({
    totalJobs: 0,
    activeJobs: 0,
    totalUploads: 0,
    totalAnomalies: 0
  });
  
  useEffect(() => {
    if (user?.token) {
      fetchAllData();
    }
  }, [user?.token]);
  
  const fetchAllData = async () => {
    try {
      // Fetch statuses
      const [modelRes, ffmpegRes] = await Promise.all([
        checkModelStatus(user.token),
        checkFFmpegStatus(user.token)
      ]);
      dispatch(setModelStatus(modelRes));
      dispatch(setFFmpegStatus(ffmpegRes));
      
      // Fetch jobs and uploads
      const [jobsRes, uploadsRes] = await Promise.all([
        listRTSPLiveJobs(user.token),
        getVideoHistory(user.token)
      ]);
      
      dispatch(setLiveJobs(jobsRes));
      dispatch(setVideoUploads(uploadsRes));
      
      // Calculate stats
      const jobs = jobsRes.jobs || [];
      const uploads = uploadsRes || [];
      
      setStats({
        totalJobs: jobs.length,
        activeJobs: jobs.filter(j => j.is_running).length,
        totalUploads: uploads.length,
        totalAnomalies: jobs.reduce((sum, j) => sum + (j.stats?.anomalies_detected || 0), 0) +
                        uploads.reduce((sum, u) => sum + (u.anomaly_count || 0), 0)
      });
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  };

  return (
    <>
      <Navbar />
      <div className="min-h-screen bg-[#EAECFF] p-6">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-[#123087] mb-2">
              STEAD Anomaly Detection
            </h1>
            <p className="text-gray-600 text-lg">
              Real-time video anomaly detection powered by STEAD model
            </p>
          </div>
          
          {/* System Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            {/* Model Status */}
            <div className={`bg-white rounded-xl p-5 shadow-sm border-l-4 ${
              modelStatus.status === 'ready' ? 'border-green-500' : 'border-yellow-500'
            }`}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">STEAD Model</h3>
                  <p className={`text-2xl font-bold mt-1 ${
                    modelStatus.status === 'ready' ? 'text-green-600' : 'text-yellow-600'
                  }`}>
                    {modelStatus.status === 'ready' ? 'Ready' : 'Loading'}
                  </p>
                </div>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  modelStatus.status === 'ready' ? 'bg-green-100' : 'bg-yellow-100'
                }`}>
                  <span className={`text-lg font-bold ${
                    modelStatus.status === 'ready' ? 'text-green-600' : 'text-yellow-600'
                  }`}>
                    {modelStatus.status === 'ready' ? 'OK' : '...'}
                  </span>
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                {modelStatus.cudaAvailable ? `GPU: ${modelStatus.cudaDeviceName}` : 'CPU Mode'}
              </p>
            </div>
            
            {/* FFmpeg Status */}
            <div className={`bg-white rounded-xl p-5 shadow-sm border-l-4 ${
              ffmpegStatus.available ? 'border-green-500' : 'border-red-500'
            }`}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">FFmpeg</h3>
                  <p className={`text-2xl font-bold mt-1 ${
                    ffmpegStatus.available ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {ffmpegStatus.available ? 'Available' : 'Missing'}
                  </p>
                </div>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  ffmpegStatus.available ? 'bg-green-100' : 'bg-red-100'
                }`}>
                  <span className={`text-lg font-bold ${
                    ffmpegStatus.available ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {ffmpegStatus.available ? 'OK' : 'X'}
                  </span>
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Video processing & streaming
              </p>
            </div>
            
            {/* Active Jobs */}
            <div className="bg-white rounded-xl p-5 shadow-sm border-l-4 border-blue-500">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Active Jobs</h3>
                  <p className="text-2xl font-bold mt-1 text-blue-600">
                    {stats.activeJobs}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                  <span className="text-lg font-bold text-blue-600">#</span>
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Total: {stats.totalJobs} jobs
              </p>
            </div>
            
            {/* Total Anomalies */}
            <div className="bg-white rounded-xl p-5 shadow-sm border-l-4 border-red-500">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Anomalies</h3>
                  <p className="text-2xl font-bold mt-1 text-red-600">
                    {stats.totalAnomalies}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                  <span className="text-lg font-bold text-red-600">!</span>
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Total detected anomalies
              </p>
            </div>
          </div>
          
          {/* Feature Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* RTSP Live Processing */}
            <Link to="/stead/rtsp-live" className="block group">
              <div className="bg-white rounded-xl p-6 shadow-sm hover:shadow-lg transition-all duration-300 border-2 border-transparent hover:border-[#6966FF]">
                <div className="flex items-start gap-4">
                  <div className="w-16 h-16 bg-gradient-to-br from-[#6966FF] to-[#8B5CF6] rounded-xl flex items-center justify-center">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-[#123087] group-hover:text-[#6966FF] transition">
                      RTSP Live Processing
                    </h3>
                    <p className="text-gray-600 mt-2">
                      Process RTSP streams or video files in real-time. 
                      Detect anomalies as they happen with instant output.
                    </p>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full">
                        Real-time
                      </span>
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                        RTSP/TCP/UDP
                      </span>
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                        HLS Streaming
                      </span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-[#6966FF] font-medium group-hover:translate-x-2 transition-transform">
                  Start Processing &rarr;
                </div>
              </div>
            </Link>
            
            {/* Video Upload */}
            <Link to="/stead/video-upload" className="block group">
              <div className="bg-white rounded-xl p-6 shadow-sm hover:shadow-lg transition-all duration-300 border-2 border-transparent hover:border-[#6966FF]">
                <div className="flex items-start gap-4">
                  <div className="w-16 h-16 bg-gradient-to-br from-[#10B981] to-[#059669] rounded-xl flex items-center justify-center">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-[#123087] group-hover:text-[#6966FF] transition">
                      Video Upload
                    </h3>
                    <p className="text-gray-600 mt-2">
                      Upload video files for complete anomaly analysis. 
                      Get detailed reports and annotated output videos.
                    </p>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                        File Upload
                      </span>
                      <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-full">
                        MP4/AVI/MOV
                      </span>
                      <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full">
                        Anomaly Report
                      </span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-[#6966FF] font-medium group-hover:translate-x-2 transition-transform">
                  Upload Video &rarr;
                </div>
              </div>
            </Link>
          </div>
          
          {/* Recent Activity */}
          {(liveJobs.length > 0 || videoUploads.length > 0) && (
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h2 className="text-xl font-semibold text-[#123087] mb-4">
                Recent Activity
              </h2>
              <div className="space-y-3">
                {liveJobs.slice(0, 3).map((job) => (
                  <div key={job.job_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-100 rounded flex items-center justify-center">
                        <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">RTSP Job</p>
                        <p className="text-xs text-gray-500">{job.job_id?.slice(0, 12)}...</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        job.is_running ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {job.is_running ? 'Running' : 'Stopped'}
                      </span>
                      <span className="text-sm text-red-600 font-medium">
                        {job.stats?.anomalies_detected || 0} anomalies
                      </span>
                    </div>
                  </div>
                ))}
                
                {videoUploads.slice(0, 3).map((upload) => (
                  <div key={upload.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-green-100 rounded flex items-center justify-center">
                        <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">{upload.original_filename}</p>
                        <p className="text-xs text-gray-500">{new Date(upload.created_at).toLocaleDateString()}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        upload.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {upload.status}
                      </span>
                      <span className="text-sm text-red-600 font-medium">
                        {upload.anomaly_count || 0} anomalies
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default STEADDashboard;
