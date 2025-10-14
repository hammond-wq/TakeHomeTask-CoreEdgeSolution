import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./assets/components/Layout/Layout";

import HomePage from "./assets/pages/HomePage";
import DashboardPage from "./assets/pages/DashboardPage";
import AgentConfigPage from "./assets/pages/AgentConfigPage"
import CallTriggerPage from "./assets/pages/CallTriggerPage";
import AnalyticsPage from "./assets/pages/AnalyticsPage";

const AppRoutes = () => (
  <Router>
    <Routes>
     
      <Route path="/" element={<HomePage />} />

    
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/agent-config" element={<AgentConfigPage />} />
        <Route path="/call-trigger" element={<CallTriggerPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
       
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  </Router>
);

export default AppRoutes;
