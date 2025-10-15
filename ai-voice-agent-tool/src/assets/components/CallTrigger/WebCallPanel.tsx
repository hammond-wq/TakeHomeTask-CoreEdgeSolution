// src/assets/components/CallTrigger/WebCallPanel.tsx
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

      client.on("call_started", () => setStatus("connected"));
      client.on("call_ended", () => setStatus("ended"));
      client.on("error", (error) => {
        console.error("Call error:", error);
        setErr(error?.message || "Unknown error");
        setStatus("error");
        client.stopCall();
      });

      clientRef.current = client;
      setStatus("ready");
    } catch (e: any) {
      setStatus("error");
      setErr(e?.message || "Client init failed");
    }

    return () => {
      try {
        clientRef.current?.stopCall();
      } catch {}
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
      // call_started event will handle setting "connected"
    } catch (e: any) {
      setStatus("error");
      setErr(e?.message || "Failed to start call");
    }
  };

  const end = async () => {
    try {
      await clientRef.current?.stopCall();
    } catch {}
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
