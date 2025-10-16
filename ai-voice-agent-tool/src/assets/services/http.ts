import { API_BASE, NGROK_HEADERS } from "../../config";

function withBase(path: string) {
  return `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}

export async function http(path: string, init?: RequestInit): Promise<Response> {
  const headers = {
    "Content-Type": "application/json",
    ...NGROK_HEADERS,
    ...(init?.headers || {}),
  };
  return fetch(withBase(path), { ...init, headers });
}

export async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await http(path, init);
  const text = await res.text();
  if (!res.ok) throw new Error(text || `HTTP ${res.status}`);

  const ct = (res.headers.get("content-type") || "").toLowerCase();
  if (!ct.includes("application/json") && text.trim().startsWith("<!doctype")) {
    throw new Error("Ngrok warning page intercepted. Check VITE_API_BASE or dev proxy.");
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error("Invalid JSON from server");
  }
}
