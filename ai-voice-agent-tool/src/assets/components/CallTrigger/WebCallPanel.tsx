
import React, { useEffect, useRef, useState } from "react";
import { RetellWebClient } from "retell-client-js-sdk";

type Props = { callId: string; accessToken: string };

const WebCallPanel: React.FC<Props> = ({ callId, accessToken }) => {
  const clientRef = useRef<RetellWebClient | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "joining" | "connected" | "ended" | "error">("loading");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    try {
      const client = new RetellWebClient();

  
      const log = (...args: any[]) => console.log("[RetellWebClient]", ...args);

      client.on?.("room_joined", () => { log("room_joined"); setStatus("connected"); });
      client.on?.("call_started", () => { log("call_started"); setStatus("connected"); });
      client.on?.("conversation_started", () => log("conversation_started"));
      client.on?.("agent_response", (d: any) => log("agent_response", d));
      client.on?.("user_speech", (d: any) => log("user_speech", d));
      client.on?.("ice_connection_state_change", (s: any) => log("ice_state", s));
      client.on?.("media_device_error", (e: any) => { log("media_device_error", e); setErr("Mic/Audio device error"); setStatus("error"); });
      client.on?.("error", (e: any) => { log("error", e); setErr(e?.message || "Unknown error"); setStatus("error"); });
      client.on?.("call_ended", () => { log("call_ended"); setStatus("ended"); });

      clientRef.current = client;
      setStatus("ready");
    } catch (e: any) {
      setStatus("error");
      setErr(e?.message || "Client init failed");
    }

    return () => {
      try { clientRef.current?.stopCall?.(); } catch {}
      clientRef.current = null;
    };
  }, []);

  const join = async () => {
    if (!clientRef.current) {
      setErr("Client not initialized");
      setStatus("error");
      return;
    }
    if (!accessToken) {
      setErr("Missing access token");
      setStatus("error");
      return;
    }

    try {
      setStatus("joining");

 
      await clientRef.current.startCall({ accessToken });


     
    } catch (e: any) {
      console.error("startCall failed", e);
      setStatus("error");
      setErr(e?.message || "Failed to start call");
    }
  };

  const end = async () => {
    try { await clientRef.current?.stopCall?.(); } catch {}
  };

  return (
    <div className="panel p-4 text-left">
      <div className="font-semibold mb-2">Web Call</div>
      <div className="text-sm mb-3">
        <div>Call ID: <code>{callId}</code></div>
        <div>Status: <b>{status}</b></div>
        {err && <div className="text-red-600 mt-1">{err}</div>}
      </div>

      <div className="flex gap-2">
        <button
          onClick={join}
          className="px-4 py-2 rounded bg-green-600 text-white disabled:opacity-60"
          disabled={status !== "ready" && status !== "error"}
        >
          {status === "joining" ? "Connecting..." : "Join Call"}
        </button>
        <button
          onClick={end}
          className="px-4 py-2 rounded border"
          disabled={status !== "connected"}
        >
          End
        </button>
      </div>
    </div>
  );
};

export default WebCallPanel;
