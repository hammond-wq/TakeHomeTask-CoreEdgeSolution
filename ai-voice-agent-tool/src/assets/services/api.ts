
export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export type StartWebCallResponse = {
  provider_call_id: string;
  retell: {
    call_id: string;
    access_token: string;
    
  };
};

export async function startWebCall(payload: {
  driver_name: string;
  load_number: string;
}) {
  const res = await fetch(`${API_BASE}/api/v1/calls/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, call_type: "web" }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  return (await res.json()) as StartWebCallResponse;
}

export type ResultItem = Record<string, unknown>;

export async function listResults(load_number?: string) {
  const qs = load_number ? `?load_number=${encodeURIComponent(load_number)}` : "";
  const res = await fetch(`${API_BASE}/api/v1/results${qs}`);
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as ResultItem[];
}
