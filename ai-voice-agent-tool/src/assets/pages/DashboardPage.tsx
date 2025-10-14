import React from "react";

const StatCard: React.FC<{ title: string; value: string; sub?: string }> = ({ title, value, sub }) => (
  <div className="panel p-5">
    <div className="text-sm text-[var(--muted)]">{title}</div>
    <div className="mt-2 text-3xl font-bold">{value}</div>
    {sub && <div className="mt-1 text-xs text-[var(--muted)]">{sub}</div>}
  </div>
);

const DashboardPage = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="text-sm text-[var(--muted)]">Overview of AI call activity and performance.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard title="Total Calls" value="2,345" sub="+4.1% this week" />
        <StatCard title="Successful Calls" value="2,010" sub="85.7% success" />
        <StatCard title="Avg. Call Time" value="2m 18s" sub="-12s vs last week" />
        <StatCard title="Escalations" value="34" sub="1.5% of calls" />
      </div>

      <div className="panel p-6">
        <h3 className="text-lg font-semibold mb-3">Recent Activity</h3>
        <ul className="space-y-2 text-sm">
          <li>• Call queued for Ahmed (+9665•••) — Normal check-in</li>
          <li>• Delay/ETA captured for Load LDN-10492 — ETA 08:00</li>
          <li>• Breakdown escalated for Riyadh ring road — SMS sent to dispatcher</li>
        </ul>
      </div>
    </div>
  );
};

export default DashboardPage;
