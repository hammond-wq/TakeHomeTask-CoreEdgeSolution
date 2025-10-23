import React, { useEffect, useMemo, useState } from "react";
import { listConversations, getConversationsCSVUrl, Conversation } from "../services/api";
import { downloadUrl } from "../../utils/download";

const statuses = ["Driving", "Delayed", "Arrived", "Unloading"] as const;
type Status = typeof statuses[number];

const ConversationsPage: React.FC = () => {
  const [q, setQ] = useState("");
  const [driver, setDriver] = useState("");
  const [loadNumber, setLoadNumber] = useState("");
  const [status, setStatus] = useState<Status | "">("");
  const [from, setFrom] = useState<string>("");
  const [to, setTo] = useState<string>("");

  const [page, setPage] = useState(1);
  const [limit] = useState(20);

  const [data, setData] = useState<Conversation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      const res = await listConversations({
        q: q.trim() || undefined,
        driver_name: driver.trim() || undefined,
        load_number: loadNumber.trim() || undefined,

        status: (status || undefined) as Status | undefined,
        date_from: from || undefined,
        date_to: to || undefined,
        page,
        limit,
      });
      setData(res.items);
      setTotal(res.total);
    } catch (e: any) {
      setErr(e?.message || "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();

  }, [page, limit]);

  const pages = useMemo(() => Math.max(1, Math.ceil(total / limit)), [total, limit]);

  const exportCsv = () => {
    const url = getConversationsCSVUrl({
      q, driver_name: driver, load_number: loadNumber, status: status || "", date_from: from, date_to: to, limit: 5000,
    });
    downloadUrl(url, "conversations.csv");
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold">Conversations</h2>
        <p className="text-sm text-gray-500">Search, filter and export call transcripts.</p>
      </div>


      <div className="panel p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
        <input className="input" placeholder="Search transcript…" value={q} onChange={(e) => setQ(e.target.value)} />
        <input className="input" placeholder="Driver name…" value={driver} onChange={(e) => setDriver(e.target.value)} />
        <input className="input" placeholder="Load #" value={loadNumber} onChange={(e) => setLoadNumber(e.target.value)} />
        <select className="input" value={status} onChange={(e) => setStatus((e.target.value || "") as Status | "")}>
          <option value="">Any status</option>
          {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input className="input" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        <input className="input" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        <div className="col-span-1 sm:col-span-2 lg:col-span-6 flex gap-2">
          <button className="btn" onClick={() => { setPage(1); load(); }}>Apply</button>
          <button className="btn ghost" onClick={() => { setQ(""); setDriver(""); setLoadNumber(""); setStatus(""); setFrom(""); setTo(""); setPage(1); load(); }}>
            Reset
          </button>
          <div className="flex-1" />
          <button
            className="btn"
            onClick={() =>
              exportConversationsCSV({
                q,
                driver_name: driver,
                load_number: loadNumber,
                status: status === "" ? undefined : status,
                date_from: from,
                date_to: to,
                limit: 5000,
              })

            }
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="panel p-0 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="th">Date</th>
              <th className="th">Driver</th>
              <th className="th">Phone</th>
              <th className="th">Load #</th>
              <th className="th">Status</th>
              <th className="th">Scenario</th>
              <th className="th">Transcript</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className="td" colSpan={7}>Loading…</td></tr>
            ) : err ? (
              <tr><td className="td text-red-600" colSpan={7}>⚠ {err}</td></tr>
            ) : data.length === 0 ? (
              <tr><td className="td" colSpan={7}>No conversations</td></tr>
            ) : (
              data.map((row) => {
                const sp = row.structured_payload || {};
                const dname = row.driver?.name || "—";
                const phone = row.driver?.phone_number || "—";
                const rowStatus = sp.driver_status || row.status || "—";
                const snippet = (row.transcript || "").split("\n").join(" ").slice(0, 140);
                return (
                  <tr key={row.id} className="border-t">
                    <td className="td">{new Date(row.created_at).toLocaleString()}</td>
                    <td className="td">{dname}</td>
                    <td className="td">{phone}</td>
                    <td className="td">{row.load_number || "—"}</td>
                    <td className="td">{rowStatus}</td>
                    <td className="td">{row.scenario || "—"}</td>
                    <td className="td">{snippet}{row.transcript && row.transcript.length > 140 ? "…" : ""}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>


      <div className="flex items-center gap-2">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
        <div className="text-sm text-gray-500">Page {page} / {pages} (Total {total})</div>
        <button className="btn" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
      </div>
    </div>
  );
};

export default ConversationsPage;
