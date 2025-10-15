// src/pages/CallTriggerPage.tsx
import React from "react";
import CallTrigger from "../components/CallTrigger/CallTrigger"; // <-- fix path

const CallTriggerPage: React.FC = () => (
  <div className="max-w-2xl mx-auto">
    <h2 className="text-2xl font-semibold mb-4">Trigger Test Call</h2>
    <CallTrigger />
  </div>
);

export default CallTriggerPage;
