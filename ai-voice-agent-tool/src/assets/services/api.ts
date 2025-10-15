export const API_BASE = (import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000").replace(/\/+$/, "");
const NGROK_HEADERS = { "ngrok-skip-browser-warning": "true" as const };



export type StartWebCallResponse = {
  provider_call_id: string;
  retell: { call_id: string; access_token: string };
};

export async function startWebCall(payload: { driver_name: string; load_number: string }) {
  const res = await fetch(`${API_BASE}/api/v1/calls/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...NGROK_HEADERS },
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
  const res = await fetch(`${API_BASE}/api/v1/results${qs}`, {
    headers: { ...NGROK_HEADERS },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as ResultItem[];
}



export async function getMetrics() {
  const res = await fetch(`${API_BASE}/api/v1/metrics`, {
    headers: { ...NGROK_HEADERS },
    cache: "no-store",
  });

  const ct = res.headers.get("content-type") || "";
  const text = await res.text();
  if (!res.ok) throw new Error(text || "Failed to fetch metrics");
  if (!ct.includes("application/json") && text.trim().startsWith("<!DOCTYPE")) {
    throw new Error("Ngrok warning page intercepted. Header added, but check VITE_API_BASE and restart dev server.");
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error("Invalid JSON received from /metrics");
  }
}



export type Conversation = {
  id: number;
  created_at: string;
  load_number: string | null;
  status: string | null;
  scenario: string | null;
  transcript: string | null;
  structured_payload: Record<string, any> | null;
  driver?: { name?: string; phone_number?: string } | null;
};

export async function listConversations(params: {
  q?: string;
  driver_name?: string;
  load_number?: string;
  status?: string;   
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
}) {
  const usp = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") usp.set(k, String(v));
  });

  const res = await fetch(`${API_BASE}/api/v1/conversations?${usp.toString()}`, {
    headers: { ...NGROK_HEADERS },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as { items: Conversation[]; page: number; limit: number; total: number };
}

export function exportConversationsCSV(params: {
  q?: string;
  driver_name?: string;
  load_number?: string;
  status?: "Driving" | "Delayed" | "Arrived" | "Unloading";
  date_from?: string;
  date_to?: string;
  limit?: number; 
}) {
  const usp = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") usp.set(k, String(v));
  });

  const url = `${API_BASE}/api/v1/conversations/export.csv?${usp.toString()}`;
  const a = document.createElement("a");
  a.href = url;
  a.download = "conversations.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
}
