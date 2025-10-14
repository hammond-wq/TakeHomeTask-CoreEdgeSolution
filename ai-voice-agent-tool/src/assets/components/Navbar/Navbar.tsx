// src/assets/components/Navbar/Navbar.tsx

import React from 'react';
import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <nav className="bg-vite-green p-4 text-white">
      <div className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-2xl font-semibold">AI Call Agent</Link> {/* Brand Name */}
        <div>
          <Link to="/dashboard" className="px-4">Dashboard</Link>
          <Link to="/agent-config" className="px-4">Agent Config</Link>
          <Link to="/call-trigger" className="px-4">Call Trigger</Link>
          <Link to="/analytics" className="px-4">Analytics</Link>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
