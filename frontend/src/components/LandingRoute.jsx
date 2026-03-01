import React from 'react';
import { Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';

const LandingRoute = ({ children }) => {
    const users = useSelector((state) => state.user.users);
    const user = users.length > 0 ? users[users.length - 1] : null;

    // If user is already logged in, redirect to dashboard based on role
    if (user && user.token) {
        if (user.role === 'admin') {
            return <Navigate to="/admin/dashboard" replace />;
        } else {
            return <Navigate to="/home" replace />;
        }
    }

    return children;
};

export default LandingRoute;
