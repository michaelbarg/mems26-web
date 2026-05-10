// MEMS26 V9 Types — aligned with backend API response shapes (2026-05-10)

// ── Bar types (GET /api/v9/bars/*) ──

export interface Bar5Min {
  id: number;
  ts: string;
  o: number;
  h: number;
  l: number;
  c: number;
  vol: number;
  poc_vol: number | null;
  vah: number | null;
  val: number | null;
  cumulative_delta: number | null;
}

export interface TickReversalBar {
  id: number;
  ts: string;
  tick_size: number;
  o: number;
  h: number;
  l: number;
  c: number;
  vol: number;
  ask_vol: number | null;
  bid_vol: number | null;
  delta: number | null;
  direction: number | null;
  footprint: Record<string, any> | null;
  cluster: Record<string, any> | null;
}

export interface WoodiesBar {
  id: number;
  ts: string;
  o: number;
  h: number;
  l: number;
  c: number;
  vol: number;
  cci_14: number | null;
  cci_6_tcci: number | null;
  lsma_value: number | null;
  swi_value: number | null;
  czi_value: number | null;
  ema_34: number | null;
  trend_state: string | null;
  predictor_next_cci: number | null;
  zlr_detected: boolean;
  zlr_direction: string | null;
}

export interface TPOBar {
  id: number;
  ts: string;
  letter: string;
  price: number;
  level: number;
  period_id: number;
}

// ── System types ──

export type SystemId = 1 | 2 | 3 | 4 | 5 | 6;
export type TradeMode = 'SHADOW' | 'SIM' | 'LIVE';

export interface SystemSignal {
  id: number;
  ts: string;
  system_id: number;
  classification: string | null;
  direction: string | null;
  confidence: number | null;
  payload: Record<string, unknown> | null;
}

export interface SystemMarker {
  id: number;
  ts: string;
  system_id: number;
  type: string;
  price: number | null;
  color: string | null;
  label: string | null;
  border_style: string | null;
  payload: Record<string, unknown> | null;
}

export type TradeOutcome = 'WIN' | 'LOSS' | 'SCRATCH' | 'OPEN';

// ── Trade types (GET /api/v9/trades) ──

export interface Trade {
  id: number;
  mode: string;
  system: number;
  direction: string;
  entry_ts: string | null;
  entry_price: number | null;
  exit_ts: string | null;
  exit_price: number | null;
  exit_reason: string | null;
  pnl_usd: number | null;
  pnl_r: number | null;
  outcome: string | null;
  sierra_bracket_id: string | null;
}

export interface TradeDetailed extends Trade {
  stop_initial: number | null;
  stop_final: number | null;
  t1_price: number | null;
  t1_filled_at: string | null;
  t2_price: number | null;
  t2_filled_at: string | null;
  t3_price: number | null;
  quality_review: Record<string, unknown> | null;
  context_json: Record<string, unknown> | null;
}

export interface TradeLogEntry {
  id: number;
  ts: string;
  action: string;
  value: Record<string, unknown> | null;
}

// ── Config types (GET /api/v9/configs) ──

export interface SystemConfig {
  id: number;
  system_id: number;
  mode: string;
  params: Record<string, unknown>;
  locked_at: string | null;
  locked_by: string | null;
}

// ── Account status (WS-only, no REST endpoint) ──

export interface AccountStatus {
  daily_pnl: number;
  total_pnl: number;
  trade_count: number;
  win_rate: number;
  max_drawdown: number;
  margin_used: number;
}

// ── System metadata ──

export const SYSTEM_COLORS: Record<SystemId, string> = {
  1: '#58a6ff',
  2: '#56d364',
  3: '#d2a8ff',
  4: '#fb950b',
  5: '#79c0ff',
  6: '#8b949e',
};

export const SYSTEM_NAMES: Record<SystemId, string> = {
  1: 'Day Type',
  2: '5-Min Patterns',
  3: 'Footprint',
  4: 'Woodies CCI',
  5: 'TPO Profile',
  6: 'Killzone',
};

export const SYSTEM_ROLES: Record<SystemId, 'firing' | 'observer' | 'gate'> = {
  1: 'firing',
  2: 'firing',
  3: 'observer',
  4: 'firing',
  5: 'observer',
  6: 'gate',
};

export const SYSTEM_BORDER_STYLE: Record<TradeMode, string> = {
  LIVE: 'solid',
  SHADOW: 'dashed',
  SIM: 'none',
};
