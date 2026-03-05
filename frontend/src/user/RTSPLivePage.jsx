/**
 * RTSP Live Processing Page
 */

import React from 'react';
import Navbar from '../components/Navbar';
import RTSPLiveProcessor from '../components/stead/RTSPLiveProcessor';

const RTSPLivePage = () => {
  return (
    <>
      <Navbar />
      <RTSPLiveProcessor />
    </>
  );
};

export default RTSPLivePage;
