const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${TOKEN}`,
        ...options?.headers,
      },
    });
    if (!res.ok) {
      console.warn(`API ${res.status} on ${path}`);
      return [] as unknown as T;
    }
    return res.json();
  } catch {
    console.warn(`API unreachable for ${path}`);
    return [] as unknown as T;
  }
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

// V9 Day Type classification (3a-S4 endpoint)
export interface DayTypeV9Response {
  classified: boolean;
  session_date: string;
  data: {
    session_date: string;
    day_type: string;
    probability: number | null;
    directional_certainty: string | null;
    trading_confidence: string | null;
    ib_h: number | null;
    ib_l: number | null;
    ib_width: number | null;
    ib_width_class: string | null;
    opening_type: string | null;
    last_updated_at: string | null;
    reasoning_notes: string | null;
    active_zohar_rules: string[];
  } | null;
}

export const fetchDayTypeV9 = () =>
  apiFetch<DayTypeV9Response>(`/api/v9/day_type/v9/current`);

export const fetchConfig = (systemId: number, mode: string) =>
  apiFetch<any>(`/api/v9/configs/${systemId}/${mode}`);

export const updateConfig = (systemId: number, mode: string, params: Record<string, unknown>) =>
  apiFetch<any>(`/api/v9/configs/${systemId}/${mode}`, {
    method: 'PUT',
    body: JSON.stringify(params),
  });
