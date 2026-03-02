import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import Homepage from './user/Homepage';
import Modeltestpage from './user/Modeltestpage';
import Modeltestrunpage from './user/Modeltestrunpage';
import Reportpage from './user/Reportpage';
import Login from './components/Login';
import OTP from './components/OTP';
import Register from './components/Register';
import CreateModel from './admin/pages/CreateModel';
import AdminModelTest from './admin/pages/AdminModelTest';
import CreatePipeline from './admin/pages/CreatePipeline';
import ModelProceed from './admin/pages/ModelProceed';
import AdminDashboard from './admin/pages/AdminDashboard';
import AdminReport from './admin/pages/AdminReport';
import AdminModelList from './admin/pages/AdminModelList';
import { ToastContainer, Slide } from 'react-toastify';
import ManageUser from './admin/pages/ManageUser';
import ContainerTestRun from './components/ContainerTestRun';
import Tasks from './admin/pages/Tasks';
import TaskLog from './admin/pages/TaskLog';
import ProtectedRoute from './components/ProtectedRoute';
import LandingRoute from './components/LandingRoute';

function App() {
  return (
    <div>
      <ToastContainer position="top-left" transition={Slide} className="mt-10" />
      <Router>
        <Routes>
          <Route path='/' element={<LandingRoute><Register role="user" /></LandingRoute>} />
          {/* login part */}
          <Route path="/login" element={<LandingRoute><Login /></LandingRoute>} />
          <Route path="/otp" element={<LandingRoute><OTP /></LandingRoute>} />
          <Route path="/user/register" element={<LandingRoute><Register role="user" /></LandingRoute>} />
          <Route path="/admin/register" element={<LandingRoute><Register role="admin" /></LandingRoute>} />
          {/* login part end */}
          <Route path="/home" element={<ProtectedRoute><Homepage /></ProtectedRoute>} />
          <Route path="/model-test" element={<ProtectedRoute><Modeltestpage /></ProtectedRoute>} />
          <Route path="/model-test-run" element={<ProtectedRoute><Modeltestrunpage /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><Reportpage /></ProtectedRoute>} />
          <Route path="/container-test-run" element={<ProtectedRoute><ContainerTestRun /></ProtectedRoute>} />

          {/* Admin Pages */}
          <Route path="/admin/dashboard" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
          <Route path="/admin/models" element={<ProtectedRoute><AdminModelList /></ProtectedRoute>} />
          <Route path="/admin/create-model" element={<ProtectedRoute><CreateModel /></ProtectedRoute>} />
          <Route path="/admin/create-pipeline" element={<ProtectedRoute><CreatePipeline /></ProtectedRoute>} />
          <Route path="/admin/reports" element={<ProtectedRoute><AdminReport /></ProtectedRoute>} />
          <Route path="/admin/tasks" element={<ProtectedRoute><Tasks /></ProtectedRoute>} />
          <Route path="/admin/tasks/:taskId/logs" element={<ProtectedRoute><TaskLog /></ProtectedRoute>} />

          <Route path="/admin/manage-user" element={<ProtectedRoute><ManageUser /></ProtectedRoute>} />
          <Route path="/admin/model-proceed" element={<ProtectedRoute><ModelProceed /></ProtectedRoute>} />
          <Route path="/admin/model-test" element={<ProtectedRoute><AdminModelTest /></ProtectedRoute>} />
        </Routes>
      </Router>
    </div>
  );
}

export default App;