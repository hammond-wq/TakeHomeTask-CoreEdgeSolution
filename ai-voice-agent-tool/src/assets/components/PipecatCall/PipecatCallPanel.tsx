import React, { useEffect, useRef, useState } from "react";
import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

export default function PipecatCallPanel() {
  const [status, setStatus] = useState<"idle"|"connecting"|"connected"|"ended"|"error">("idle");
  const [err, setErr] = useState<string | null>(null);
  const clientRef = useRef<PipecatClient | null>(null);

  const connect = async () => {
    try {
      setStatus("connecting");
      const res = await fetch("/api/v1/pipecat/start"); // our adapter
      if (!res.ok) throw new Error(await res.text());
      const { endpoint } = await res.json();

      const transport = new SmallWebRTCTransport();
      const client = new PipecatClient({ transport });

      client.on("connected", () => setStatus("connected"));
      client.on("disconnected", () => setStatus("ended"));
      client.on("error", (e: any) => { setErr(e?.message || "error"); setStatus("error"); });

      await client.connect({ endpoint });  // Pipecat’s /start
      clientRef.current = client;
    } catch (e: any) {
      setErr(e?.message || "Failed to connect");
      setStatus("error");
    }
  };

  const end = async () => { try { await clientRef.current?.disconnect(); } catch {} };

  useEffect(() => () => { try { clientRef.current?.disconnect(); } catch {} }, []);

  return (
    <div className="panel p-4 text-left">
      <div className="font-semibold mb-2">Pipecat Web Call</div>
      <div className="text-sm mb-3">Status: <b>{status}</b>{err && <> • <span className="text-red-600">{err}</span></>}</div>
      <div className="flex gap-2">
        <button className="btn" onClick={connect} disabled={status==="connected" || status==="connecting"}>Join</button>
        <button className="btn ghost" onClick={end} disabled={status!=="connected"}>End</button>
      </div>
    </div>
  );
}
