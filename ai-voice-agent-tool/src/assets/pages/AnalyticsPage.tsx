import React, { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";

const API_BASE = (import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000").replace(/\/+$/, "");

export default function AnalyticsPage() {
  const [view, setView] = useState<"retell" | "pipecat">("retell");
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (view === "retell") fetchRetellMetrics();
    else fetchPipecatMetrics();
  }, [view]);


  const fetchRetellMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics`);
      const json = await res.json();
      setMetrics(json || {});
    } catch (err) {
      console.error(err);
      setError("Failed to load Retell metrics");
    }
    setLoading(false);
  };


  const fetchPipecatMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/pipecat/metrics`);
      const json = await res.json();
      setMetrics(Array.isArray(json.items) ? json.items : []);
    } catch (err) {
      console.error(err);
      setError("Failed to load Pipecat metrics");
    }
    setLoading(false);
  };


  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold flex justify-between items-center">
        Analytics Dashboard
        <div className="flex gap-2">
          <button
            onClick={() => setView("retell")}
            className={`px-3 py-1 rounded ${view === "retell" ? "bg-blue-600 text-white" : "bg-gray-200"}`}
          >
            Retell
          </button>
          <button
            onClick={() => setView("pipecat")}
            className={`px-3 py-1 rounded ${view === "pipecat" ? "bg-green-600 text-white" : "bg-gray-200"}`}
          >
            Pipecat
          </button>
        </div>
      </h2>

      <div className="panel p-6">
        {loading && <p className="text-gray-500">Loading {view} analytics…</p>}
        {error && <p className="text-red-500">{error}</p>}

        {!loading && !error && (
          <>
            {view === "retell" ? (
              <RetellCharts data={metrics} />
            ) : (
              <PipecatCharts data={metrics} />
            )}
          </>
        )}
      </div>
    </div>
  );
}


function RetellCharts({ data }: { data: any }) {
  if (!data) return <p className="text-gray-500">No Retell data found.</p>;

  const cards = [
    { title: "Total Calls", value: data.total_calls || 0 },
    { title: "Arrivals", value: data.arrivals || 0 },
    { title: "Delays", value: data.delays || 0 },
    { title: "Emergencies", value: data.emergencies || 0 },
  ];

  const avgDelay = (data.avg_delay_minutes || 0).toFixed(1);

  const pieData = [
    { name: "Arrivals", value: data.arrivals || 0 },
    { name: "Delays", value: data.delays || 0 },
    { name: "Emergencies", value: data.emergencies || 0 },
  ];

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {cards.map((c, i) => (
          <StatCard key={i} title={c.title} value={c.value} />
        ))}
        <StatCard title="Avg Delay (min)" value={avgDelay} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-2xl shadow">
          <h3 className="font-semibold mb-3">Event Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label
              >
                {pieData.map((_, i) => (
                  <Cell key={i} fill={["#2563eb", "#f59e0b", "#ef4444"][i % 3]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white p-4 rounded-2xl shadow">
          <h3 className="font-semibold mb-3">Delay vs Emergencies</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={[data]}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="total_calls" hide />
              <YAxis />
              <Tooltip />
              <Bar dataKey="delays" fill="#f59e0b" name="Delays" />
              <Bar dataKey="emergencies" fill="#ef4444" name="Emergencies" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}


function PipecatCharts({ data }: { data: any[] }) {
  if (!Array.isArray(data) || !data.length)
    return <p className="text-gray-500">No Pipecat data found.</p>;

  const avgDur = (data.reduce((a, x) => a + (x.duration_secs || 0), 0) / (data.length || 1)).toFixed(1);
  const totalEmergencies = data.reduce(
    (a, x) => a + ((x.keyword_hits?.emergency || 0) as number),
    0
  );

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <StatCard title="Total Calls" value={data.length} />
        <StatCard title="Average Duration (s)" value={avgDur} />
        <StatCard title="Total Emergencies" value={totalEmergencies} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-2xl shadow">
          <h3 className="font-semibold mb-3">Duration by Load</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={data.map((x) => ({
                load: x.load_number || "N/A",
                duration: x.duration_secs || 0,
              }))}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="load" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="duration" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white p-4 rounded-2xl shadow">
          <h3 className="font-semibold mb-3">Keyword Hits Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={Object.entries(
                  data.reduce((acc, row) => {
                    const hits = row.keyword_hits || {};
                    Object.entries(hits).forEach(([k, v]) => {
                      acc[k] = (acc[k] || 0) + (v as number);
                    });
                    return acc;
                  }, {} as Record<string, number>)
                ).map(([k, v]) => ({ name: k, value: v }))}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label
              >
                {["#22c55e", "#f97316", "#3b82f6", "#ef4444"].map((color, i) => (
                  <Cell key={i} fill={color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}

function StatCard({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="bg-white p-4 rounded-2xl shadow flex flex-col items-center justify-center">
      <p className="text-gray-600 text-sm">{title}</p>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </div>
  );
}
