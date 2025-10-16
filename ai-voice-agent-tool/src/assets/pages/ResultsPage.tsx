import React, { useState } from "react";
import { listResults } from "../services/api";

const pretty = (v: unknown) => (typeof v === "object" ? JSON.stringify(v, null, 2) : String(v ?? ""));

const ResultsPage: React.FC = () => {
  const [load, setLoad] = useState("");
  const [items, setItems] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setBusy(true); setErr(null);
    try {
      const res = await listResults(load.trim() || undefined);
      setItems(res);
    } catch (e: any) {
      setErr(e?.message || "Failed to fetch results");
    } finally {
      setBusy(false);
    }
  };

  const latest = items?.[0];

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <h2 className="text-2xl font-semibold">Results</h2>
      <div className="panel p-4 grid gap-3">
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="Filter by load number (optional)"
            value={load}
            onChange={(e) => setLoad(e.target.value)}
          />
          <button onClick={run} disabled={busy} className="btn">
            {busy ? "Loading..." : "Fetch"}
          </button>
        </div>
        {err && <div className="text-red-600 text-sm">{err}</div>}
      </div>

      {latest ? (
        <div className="panel p-4 text-left">
          <div className="font-semibold mb-2">Latest Record</div>
          <pre className="text-sm whitespace-pre-wrap">{pretty(latest)}</pre>
        </div>
      ) : (
        <div className="text-sm text-[var(--muted)]">No items yet.</div>
      )}
    </div>
  );
};

export default ResultsPage;
