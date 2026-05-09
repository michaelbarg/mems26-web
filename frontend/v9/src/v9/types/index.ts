// MEMS26 V9 Types

// Bar types
export interface Bar5Min {
  id: number;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  tick_count: number;
  vwap: number;
  delta: number;
  poc_price: number;
  vah_price: number;
  val_price: number;
}

export interface TickReversalBar {
  id: number;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  tick_count: number;
  up_ticks: number;
  down_ticks: number;
  delta: number;
  bid_volume: number;
  ask_volume: number;
  footprint_json: Record<string, { bid: number; ask: number }>;
}

export interface WoodiesBar {
  id: number;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  cci_14: number;
  cci_6: number;
  tcci: number;
  cci_34: number;
  cci_50: number;
  cci_128: number;
  cci_200: number;
  lsma_25: number;
  ema_34_cci: number;
  turbo_cci_5: number;
  turbo_cci_8: number;
  zlr_pattern: string | null;
}

export interface TPOBar {
  id: number;
  timestamp: string;
  price_level: number;
  tpo_letter: string;
  period_label: string;
  is_poc: boolean;
  is_vah: boolean;
  is_val: boolean;
}

// System types
export type SystemId = 1 | 2 | 3 | 4 | 5 | 6;
export type TradeMode = 'SHADOW' | 'SIM' | 'LIVE';
export type MarkerType = 'ENTRY' | 'EXIT_WIN' | 'EXIT_STOP' | 'ALERT' | 'LEVEL';

export interface SystemSignal {
  id: number;
  system_id: SystemId;
  timestamp: string;
  signal_type: string;
  direction: 'LONG' | 'SHORT' | null;
  confidence: number;
  mode: TradeMode;
  metadata_json: Record<string, unknown>;
}

export interface SystemMarker {
  id: number;
  system_id: SystemId;
  timestamp: string;
  bar_timestamp: string;
  marker_type: MarkerType;
  price: number;
  direction: 'LONG' | 'SHORT';
  mode: TradeMode;
  label: string;
  metadata_json: Record<string, unknown>;
}

// Trade types
export type TradeOutcome = 'WIN' | 'LOSS' | 'SCRATCH' | 'OPEN';

export interface Trade {
  id: number;
  system_id: SystemId;
  mode: TradeMode;
  direction: 'LONG' | 'SHORT';
  entry_time: string;
  entry_price: number;
  exit_time: string | null;
  exit_price: number | null;
  stop_price: number;
  target_price: number;
  quantity: number;
  pnl_ticks: number | null;
  pnl_dollars: number | null;
  outcome: TradeOutcome;
  quality_score: number | null;
  pattern_name: string;
  notes: string;
}

// Config types
export interface SystemConfig {
  system_id: SystemId;
  mode: TradeMode;
  enabled: boolean;
  params_json: Record<string, unknown>;
}

export interface AccountStatus {
  id: number;
  timestamp: string;
  daily_pnl: number;
  total_pnl: number;
  trade_count: number;
  win_rate: number;
  max_drawdown: number;
  margin_used: number;
}

// System metadata
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

export const SYSTEM_ROLES: Record<SystemId, 'firing' | 'observer' | 'data' | 'gate'> = {
  1: 'firing',
  2: 'firing',
  3: 'observer',
  4: 'firing',
  5: 'data',
  6: 'gate',
};

export const SYSTEM_BORDER_STYLE: Record<TradeMode, string> = {
  LIVE: 'solid',
  SHADOW: 'dashed',
  SIM: 'none',
};
