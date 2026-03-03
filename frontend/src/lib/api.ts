/**
 * API utility — makes authenticated requests to the FastAPI backend.
 */

const API_BASE = "http://localhost:8000";

export async function apiFetch(
  path: string,
  options: RequestInit = {},
  token?: string | null,
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API request failed");
  }

  if (res.status === 204) return null;
  return res.json();
}
