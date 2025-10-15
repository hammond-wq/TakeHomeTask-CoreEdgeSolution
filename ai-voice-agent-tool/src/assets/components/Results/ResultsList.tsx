
import React, { useEffect, useState } from "react";
import { listResults, ResultItem } from "../../services/api";

const ResultsList: React.FC = () => {
  const [items, setItems] = useState<ResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const load = async () => {
    try {
      setErr(null); setLoading(true);
      const rows = await listResults(filter || undefined);
      setItems(rows);
    } catch (e: any) {
      setErr(e?.message || "Failed to load results");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []); 

  return (
    <section className="w-full max-w-4xl mx-auto">
      <header className="flex items-center gap-2 mb-3">
        <input
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="Filter by load number (e.g., LDN-09)"
          className="flex-1 p-2 rounded border"
        />
        <button onClick={load} className="px-4 py-2 rounded bg-green-600 text-white">Refresh</button>
      </header>

      {loading && <div>Loading…</div>}
      {err && <div className="text-red-600">{err}</div>}

      <div className="space-y-4">
        {items.map((it: any) => (
          <div key={it.id} className="border rounded-lg p-4 bg-white">
            <div className="flex justify-between mb-2">
              <div className="font-semibold">{it.load_number}</div>
              <div className="text-sm text-gray-500">{it.created_at}</div>
            </div>
            <div className="text-sm text-gray-700 mb-2">
              <b>Outcome:</b> {it.structured_payload?.call_outcome ?? "—"} &nbsp;|&nbsp;
              <b>Status:</b> {it.structured_payload?.driver_status ?? it.scenario ?? "—"}
            </div>
            <details className="mb-2">
              <summary className="cursor-pointer">Structured Summary</summary>
              <pre className="bg-gray-50 p-3 rounded text-xs overflow-auto">
                {JSON.stringify(it.structured_payload, null, 2)}
              </pre>
            </details>
            <details>
              <summary className="cursor-pointer">Transcript</summary>
              <pre className="bg-gray-50 p-3 rounded text-xs overflow-auto whitespace-pre-wrap">
                {it.transcript || "—"}
              </pre>
            </details>
          </div>
        ))}
      </div>
    </section>
  );
};

export default ResultsList;
