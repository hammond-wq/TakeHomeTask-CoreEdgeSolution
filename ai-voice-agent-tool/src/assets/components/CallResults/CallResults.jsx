

import React from 'react';

const CallResults = ({ results }) => {
  return (
    <div className="container mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Call Results</h2>
      <div className="space-y-4">
        <div>
          <strong>Driver Status:</strong> {results.driverStatus}
        </div>
        <div>
          <strong>Location:</strong> {results.currentLocation}
        </div>
        <div>
          <strong>ETA:</strong> {results.eta}
        </div>
        <div>
          <strong>Delay Reason:</strong> {results.delayReason}
        </div>
        <div>
          <strong>Call Outcome:</strong> {results.callOutcome}
        </div>
      </div>
    </div>
  );
};

export default CallResults;
