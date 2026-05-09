const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN}`,
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export const fetchBars5min = (limit = 300) =>
  apiFetch<any[]>(`/api/v9/bars/5min?limit=${limit}`);

export const fetchTickReversalBars = (tickCount = 15, limit = 300) =>
  apiFetch<any[]>(`/api/v9/bars/tick_reversal?tick_count=${tickCount}&limit=${limit}`);

export const fetchWoodiesBars = (limit = 100) =>
  apiFetch<any[]>(`/api/v9/bars/woodies?limit=${limit}`);

export const fetchTPOBars = () =>
  apiFetch<any[]>(`/api/v9/bars/tpo`);

export const fetchSignals = (systemId?: number) =>
  apiFetch<any[]>(`/api/v9/signals${systemId ? `?system_id=${systemId}` : ''}`);

export const fetchMarkers = (systemId?: number) =>
  apiFetch<any[]>(`/api/v9/markers${systemId ? `?system_id=${systemId}` : ''}`);

export const fetchTrades = (mode?: string) =>
  apiFetch<any[]>(`/api/v9/trades${mode ? `?mode=${mode}` : ''}`);

export const fetchTradeById = (id: number) =>
  apiFetch<any>(`/api/v9/trades/${id}`);

export const fetchConfigs = () =>
  apiFetch<any[]>(`/api/v9/configs`);

export const fetchConfig = (systemId: number, mode: string) =>
  apiFetch<any>(`/api/v9/configs/${systemId}/${mode}`);

export const updateConfig = (systemId: number, mode: string, params: Record<string, unknown>) =>
  apiFetch<any>(`/api/v9/configs/${systemId}/${mode}`, {
    method: 'PUT',
    body: JSON.stringify(params),
  });
