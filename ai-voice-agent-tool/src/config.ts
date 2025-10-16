export const API_BASE = (import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000").replace(/\/+$/, "");
export const NGROK_HEADERS = { "ngrok-skip-browser-warning": "true" as const };
