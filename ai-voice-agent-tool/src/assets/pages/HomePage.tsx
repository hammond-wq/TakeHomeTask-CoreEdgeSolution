

import React, { useState } from 'react';
import { Navigate } from 'react-router-dom'; 
import LoginModal from '../components/LoginModal/LoginModal';

const HomePage = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleLogin = () => {
    setIsLoggedIn(true); 
  };

  if (isLoggedIn) {
    return <Navigate to="/dashboard" />; 
  }

  return <LoginModal onLogin={handleLogin} />; 
};

export default HomePage;
