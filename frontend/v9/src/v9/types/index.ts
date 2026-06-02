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

export type TradeOutcome = 'WIN' | 'LOSS' | 'BE' | 'SCRATCH' | 'OPEN';

export interface ContractPnlLeg {
  id: string;
  status: string;
  exit_price?: number;
  pnl_usd: number;
  pnl_r?: number | null;
}

export interface SystemAgreement {
  id: number;
  name: string;
  agree: boolean | null;
  is_firing: boolean;
  hint?: string | null;
}

// ── Trade types (GET /api/v9/trades) ──

export interface Trade {
  id: number;
  mode: string;
  system: number;
  direction: string;
  state?: string | null;
  entry_ts: string | null;
  entry_price: number | null;
  stop?: number | null;
  stop_initial?: number | null;
  /** initial | BE@entry — Smart BE overwrites stop column */
  stop_note?: string | null;
  /** T1_NO_BE when T1 hit but stop never moved to entry */
  stop_issue?: string | null;
  systems_agreement?: SystemAgreement[];
  t1?: number | null;
  t2?: number | null;
  t3?: number | null;
  t1_hit?: boolean;
  t2_hit?: boolean;
  t3_hit?: boolean;
  exit_ts: string | null;
  exit_price: number | null;
  exit_reason: string | null;
  pnl_usd: number | null;
  pnl_r: number | null;
  /** closed | partial (realized C1/C2) | open */
  pnl_mode?: string | null;
  contracts_pnl?: ContractPnlLeg[] | null;
  /** From v9_bars_5min between entry and exit (5m resolution). */
  price_high?: number | null;
  price_low?: number | null;
  mfe_pts?: number | null;
  mae_pts?: number | null;
  /** Closest approach to T1 in points (0 = touched). */
  t1_closest_pts?: number | null;
  /** Distance to T1 at MFE peak price. */
  t1_at_mfe_pts?: number | null;
  t1_reached?: boolean | null;
  bars_count?: number | null;
  outcome: string | null;
  sierra_bracket_id: string | null;
  is_synthetic?: boolean;
  pattern_id?: string | null;
  trigger?: string | null;
  classification?: string | null;
  day_type?: string | null;
  confidence?: number | null;
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
  1: '#3B82F6',
  2: '#10B981',
  3: '#8B5CF6',
  4: '#F97316',
  5: '#06B6D4',
  6: '#6B7280',
};

export const SYSTEM_NAMES: Record<SystemId, string> = {
  1: 'Day Type',
  2: '5-Min Patterns',
  3: 'Footprint',
  4: 'Woodies CCI',
  5: 'TPO Profile',
  6: 'Killzone',
};

// Source of truth: D-089 (S3 Footprint = FIRING, locked 2026-05-23 by Michael)
// which SUPERSEDES D-082 (S3 Observer-only per V3 spec) and D-086 (S3 SHADOW
// firing tolerated, "revisit before LIVE"). Restores Master Matrix V1.0
// designation in `backend/v9/systems/wrappers.py:8-14`. The 3 firing
// systems are canonical: S2, S3, S4. S1 stays Observer per Master Matrix.
// Decision doc: docs/decisions/D-089_S3_FIRING_LOCKED.md
// Registry doc: docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md
export const SYSTEM_ROLES: Record<SystemId, 'firing' | 'observer' | 'gate'> = {
  1: 'observer',
  2: 'firing',
  3: 'firing',
  4: 'firing',
  5: 'observer',
  6: 'gate',
};

export const SYSTEM_BORDER_STYLE: Record<TradeMode, string> = {
  LIVE: 'solid',
  SHADOW: 'dashed',
  SIM: 'none',
};
