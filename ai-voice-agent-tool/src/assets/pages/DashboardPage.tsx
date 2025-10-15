import React, { useEffect, useState } from "react";
import { getMetrics } from "../services/api";

const StatCard: React.FC<{ title: string; value: string | number; sub?: string }> = ({ title, value, sub }) => (
  <div className="panel p-5 rounded-xl shadow-sm bg-white">
    <div className="text-sm text-gray-500">{title}</div>
    <div className="mt-2 text-3xl font-bold text-gray-800">{value}</div>
    {sub && <div className="mt-1 text-xs text-gray-400">{sub}</div>}
  </div>
);

const DashboardPage = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const data = await getMetrics();
        setMetrics(data);
      } catch (err: any) {
        setError(err.message || "Error loading metrics");
      } finally {
        setLoading(false);
      }
    }
    fetchMetrics();
  }, []);

  if (loading) return <div className="p-6 text-gray-500">Loading dashboard...</div>;
  if (error) return <div className="p-6 text-red-500">⚠️ {error}</div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-800">Dashboard</h2>
        <p className="text-sm text-gray-500">Overview of AI call activity and performance.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard title="Total Calls" value={metrics.total_calls} />
        <StatCard title="Arrivals" value={metrics.arrivals} sub={`${((metrics.arrivals / metrics.total_calls) * 100).toFixed(1)}%`} />
        <StatCard title="Delays" value={metrics.delays} sub={`${metrics.avg_delay_minutes} min avg delay`} />
        <StatCard title="Emergencies" value={metrics.emergencies} sub="Critical incidents" />
      </div>

      <div className="panel p-6 mt-6 bg-white rounded-xl shadow-sm">
        <h3 className="text-lg font-semibold mb-3 text-gray-800">Recent Activity</h3>
        <ul className="space-y-2 text-sm text-gray-600">
          <li>• Latest delay reported: {metrics.delays} drivers</li>
          <li>• Average ETA delay: {metrics.avg_delay_minutes} min</li>
          <li>• Emergencies logged: {metrics.emergencies}</li>
        </ul>
      </div>
    </div>
  );
};

export default DashboardPage;
