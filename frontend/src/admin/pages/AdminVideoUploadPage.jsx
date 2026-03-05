/**
 * Admin Video Upload Page
 * 
 * Page wrapper for video upload anomaly detection (Admin).
 */

import React from 'react';
import AdminNavbar from '../../components/AdminNavbar';
import AdminVideoUpload from '../../components/stead/AdminVideoUpload';

const AdminVideoUploadPage = () => {
  return (
    <>
      <AdminNavbar />
      <AdminVideoUpload />
    </>
  );
};

export default AdminVideoUploadPage;
