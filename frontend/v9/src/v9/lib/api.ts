/** Local V9 backend — never empty string (breaks fetch → relative /api on :3000). */
export function getApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!raw) return 'http://localhost:8000';
  return raw.replace(/\/$/, '');
}

const API_BASE = getApiBase();
const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';

export type ApiPostResult<T> = {
  ok: boolean;
  status: number;
  data: T | null;
  error: string | null;
};

/** POST with bridge token — cockpit mutations (exit, etc.). */
export async function apiPost<T = Record<string, unknown>>(
  path: string,
  body: Record<string, unknown> = {},
): Promise<ApiPostResult<T>> {
  const url = `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${TOKEN}`,
      },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    let data: T | null = null;
    if (text) {
      try {
        data = JSON.parse(text) as T;
      } catch {
        data = null;
      }
    }
    if (!res.ok) {
      const detail =
        data && typeof data === 'object' && 'detail' in (data as object)
          ? String((data as { detail: unknown }).detail)
          : text.slice(0, 200);
      return { ok: false, status: res.status, data, error: detail || res.statusText };
    }
    return { ok: true, status: res.status, data, error: null };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.warn(`apiPost failed ${url}`, e);
    return { ok: false, status: 0, data: null, error: msg };
  }
}

export async function exitTrade(
  tradeId: number,
  body: { exit_price?: number; reason?: string } = {},
): Promise<ApiPostResult<Record<string, unknown>>> {
  return apiPost(`/api/v9/trades/${tradeId}/exit`, body);
}

/** Journal page + /trades/log — local V9 backend only. */
export const JOURNAL_API = API_BASE;

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

/** Public read endpoints — longer timeout when backend is busy. */
export async function publicApiFetch<T>(path: string, timeoutMs = 45_000): Promise<T | null> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, { signal: ctrl.signal });
    if (!res.ok) {
      console.warn(`API ${res.status} on ${path}`);
      return null;
    }
    return (await res.json()) as T;
  } catch (e) {
    console.warn(`API unreachable for ${path}`, e);
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export function normalizeTradesPayload(data: unknown): any[] {
  if (Array.isArray(data)) return data;
  if (data && typeof data === 'object' && Array.isArray((data as { trades?: unknown }).trades)) {
    return (data as { trades: any[] }).trades;
  }
  return [];
}

export function mapTradeRow(t: Record<string, unknown>) {
  const pnl = (t.pnl_usd ?? t.pnl ?? null) as number | null;
  const state = (t.state as string | undefined) ?? null;
  let outcome = (t.outcome as string | null) ?? null;
  if (!outcome) {
    if (state === 'CLOSED' || t.exit_ts) {
      if (pnl != null) outcome = pnl > 0 ? 'WIN' : pnl < 0 ? 'LOSS' : 'SCRATCH';
      else outcome = 'SCRATCH';
    } else if (
      state === 'OPEN' ||
      state === 'FILLED' ||
      state === 'PARTIAL' ||
      state === 'PENDING'
    ) {
      outcome = 'OPEN';
    }
  }
  const system = (t.system ?? t.firing_system ?? null) as number | null;
  const rawMode = String(t.mode ?? '').toLowerCase();
  const mode =
    rawMode === 'shadow'
      ? 'SHADOW'
      : rawMode === 'demo'
        ? 'SIM'
        : rawMode === 'live'
          ? 'LIVE'
          : (t.mode as string | undefined);
  return { ...t, pnl_usd: pnl, outcome, system, mode };
}

export const fetchTrades = async (mode?: string, limit = 500) => {
  const qs = new URLSearchParams();
  if (mode) qs.set('mode', mode.toLowerCase());
  qs.set('limit', String(limit));
  const data = await apiFetch<unknown>(`/api/v9/trades?${qs}`);
  return normalizeTradesPayload(data).map((t) => mapTradeRow(t));
};

export const fetchRecentTrades = async (limit = 20) => {
  const data = await publicApiFetch<unknown[]>(`/api/v9/trades/recent?limit=${limit}`);
  if (!Array.isArray(data)) return [];
  return data.map((t) => mapTradeRow(t as Record<string, unknown>));
};

export const fetchActiveTrade = () =>
  publicApiFetch<Record<string, unknown>>('/api/v9/trades/active');

export type TradeDetailResponse = {
  trade?: Record<string, unknown>;
  insight?: {
    fire?: Record<string, unknown>;
    recognition?: Array<{
      id: number;
      name: string;
      role: string;
      is_firing: boolean;
      agree: boolean | null;
      lines: string[];
    }>;
    lifecycle?: unknown[];
  };
  management_log?: unknown[];
};

/** Entry insight for expanded trade row (requires bridge token on live backend). */
export const fetchTradeById = async (id: number): Promise<TradeDetailResponse | null> => {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 15_000);
  try {
    const res = await fetch(`${API_BASE}/api/v9/trades/${id}`, {
      signal: ctrl.signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${TOKEN}`,
      },
    });
    if (!res.ok) {
      console.warn(`API ${res.status} on /api/v9/trades/${id}`);
      return null;
    }
    const data = (await res.json()) as TradeDetailResponse;
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      return null;
    }
    return data;
  } catch (e) {
    console.warn(`API unreachable for /api/v9/trades/${id}`, e);
    return null;
  } finally {
    clearTimeout(timer);
  }
};

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
