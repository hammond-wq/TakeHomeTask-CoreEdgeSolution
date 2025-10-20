import React, { useEffect, useRef, useState } from "react";
import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

export default function PipecatCallPanel() {
  const [driver_name, setDriverName] = useState("John Doe");
  const [load_number, setLoadNumber] = useState("7891-B");
  const [status, setStatus] = useState<"idle" | "connecting" | "connected" | "ended" | "error">("idle");
  const [err, setErr] = useState<string | null>(null);
  const clientRef = useRef<PipecatClient | null>(null);

  const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

  const connect = async () => {
    try {
      setStatus("connecting");

      const res = await fetch(`${API_BASE}/api/v1/voice/start?vendor=pipecat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          driver_name,
          load_number,
          call_type: "web_call",
        }),
      });

      if (!res.ok) throw new Error(await res.text());
      const { connect_url } = await res.json();

      window.open(connect_url, "_blank");
      setStatus("connected");
    } catch (e: any) {
      setErr(e?.message || "Failed to start Pipecat call");
      setStatus("error");
    }
  };

  const end = async () => {
    try {
      await clientRef.current?.disconnect();
    } catch {}
  };

  useEffect(() => {
    return () => {
      try {
        clientRef.current?.disconnect();
      } catch {}
    };
  }, []);

  return (
    <div className="panel p-4 text-left">
      <div className="font-semibold mb-2">Pipecat Web Call</div>

    
      <div className="mb-3 flex flex-col gap-2">
        <input
          value={driver_name}
          onChange={(e) => setDriverName(e.target.value)}
          placeholder="Driver Name"
          className="input"
        />
        <input
          value={load_number}
          onChange={(e) => setLoadNumber(e.target.value)}
          placeholder="Load Number"
          className="input"
        />
      </div>

      <div className="text-sm mb-3">
        Status: <b>{status}</b>
        {err && (
          <>
            {" "}
            • <span className="text-red-600">{err}</span>
          </>
        )}
      </div>

      <div className="flex gap-2">
        <button
          className="btn"
          onClick={connect}
          disabled={status === "connected" || status === "connecting"}
        >
          Join
        </button>
        <button className="btn ghost" onClick={end} disabled={status !== "connected"}>
          End
        </button>
      </div>
    </div>
  );
}
