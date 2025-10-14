

import React from 'react';

const Analytics = () => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-lg mb-6">
      <h2 className="text-2xl font-semibold mb-4 text-vite-green">Analytics Overview</h2>
      <div className="grid grid-cols-2 gap-6">
       
        <div className="p-4 bg-gray-100 rounded shadow">
          <h3 className="font-semibold">Total Calls</h3>
          <p className="text-3xl">2,345</p>
        </div>
        <div className="p-4 bg-gray-100 rounded shadow">
          <h3 className="font-semibold">Successful Calls</h3>
          <p className="text-3xl">2,000</p>
        </div>
        <div className="p-4 bg-gray-100 rounded shadow">
          <h3 className="font-semibold">Failed Calls</h3>
          <p className="text-3xl">345</p>
        </div>
        <div className="p-4 bg-gray-100 rounded shadow">
          <h3 className="font-semibold">Pending Calls</h3>
          <p className="text-3xl">100</p>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
