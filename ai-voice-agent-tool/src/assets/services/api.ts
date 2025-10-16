import { getJSON } from "./http";
import { API_BASE } from "../../config";

export type StartWebCallResponse = {
  provider_call_id: string;
  retell: { call_id: string; access_token: string };
};

export async function startWebCall(payload: { driver_name: string; load_number: string }) {
  return getJSON<StartWebCallResponse>("/api/v1/calls/start", {
    method: "POST",
    body: JSON.stringify({ ...payload, call_type: "web" }),
  });
}

export type ResultItem = Record<string, unknown>;

export async function listResults(load_number?: string) {
  const qs = load_number ? `?load_number=${encodeURIComponent(load_number)}` : "";
  return getJSON<ResultItem[]>(`/api/v1/results${qs}`, { cache: "no-store" });
}

export async function getMetrics() {
  return getJSON<any>("/api/v1/metrics", { cache: "no-store" });
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
  return getJSON<{ items: Conversation[]; page: number; limit: number; total: number }>(
    `/api/v1/conversations?${usp.toString()}`,
    { cache: "no-store" },
  );
}

/** Build CSV URL (UI triggers download; no DOM in service) */
export function getConversationsCSVUrl(params: {
  q?: string;
  driver_name?: string;
  load_number?: string;
  status?: "Driving" | "Delayed" | "Arrived" | "Unloading" | "";
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  const usp = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") usp.set(k, String(v));
  });
  return `${API_BASE}/api/v1/conversations/export.csv?${usp.toString()}`;
}
