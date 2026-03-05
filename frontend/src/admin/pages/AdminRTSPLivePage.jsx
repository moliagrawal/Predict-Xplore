/**
 * Admin RTSP Live Processing Page
 * 
 * Page wrapper for RTSP live anomaly detection (Admin).
 */

import React from 'react';
import AdminNavbar from '../../components/AdminNavbar';
import AdminRTSPLiveProcessor from '../../components/stead/AdminRTSPLiveProcessor';

const AdminRTSPLivePage = () => {
  return (
    <>
      <AdminNavbar />
      <AdminRTSPLiveProcessor />
    </>
  );
};

export default AdminRTSPLivePage;
