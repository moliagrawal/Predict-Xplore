import React from 'react';
import { Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';

const ProtectedRoute = ({ children }) => {
    const users = useSelector((state) => state.user.users);
    const user = users.length > 0 ? users[users.length - 1] : null;

    // If user does not exist or has no token, redirect to landing page
    if (!user || !user.token) {
        return <Navigate to="/login" replace />;
    }

    return children;
};

export default ProtectedRoute;
