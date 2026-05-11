// Auto-generated from registry.yaml — do not edit manually
// Run: python scripts/generate_ts_types.py

export interface BaseEvent {
  event_type: string;
  correlation_id: string;
  ts_ms: number;
  source: string;
  version: string;
}

/** Live price tick from Sierra Chart DLL (every ~200ms) */
export interface PriceTickEvent extends BaseEvent {
  event_type: "price.tick";
  price: number;
  ts_ms: number;
  bid?: number;
  ask?: number;
  last_size?: number;
  spread?: number;
}

/** Periodic price snapshot with derived fields (every 1s) */
export interface PriceSnapshotEvent extends BaseEvent {
  event_type: "price.snapshot";
  price: number;
  ts_ms: number;
  bid?: number;
  ask?: number;
  vwap?: number;
  session_high?: number;
  session_low?: number;
}

/** 5-minute OHLCV bar */
export interface Bar5minEvent extends BaseEvent {
  event_type: "bar.5min";
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  delta?: number;
}

/** Tick reversal bar (15-tick or 12-tick) */
export interface BarTick_reversalEvent extends BaseEvent {
  event_type: "bar.tick_reversal";
  tick_size: number;
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  delta?: number;
  direction?: number;
}

/** A trading system fired a signal */
export interface SignalFiredEvent extends BaseEvent {
  event_type: "signal.fired";
  system_id: number;
  direction: string;
  classification: string;
  confidence: number;
  entry_price?: number;
  stop?: number;
  targets?: unknown[];
}

/** System health heartbeat */
export interface SystemHealthEvent extends BaseEvent {
  event_type: "system.health";
  component: string;
  status: string;
  ts_ms: number;
  details?: Record<string, unknown>;
}

export type MemsEvent = PriceTickEvent | PriceSnapshotEvent | Bar5minEvent | BarTick_reversalEvent | SignalFiredEvent | SystemHealthEvent;

export const EVENT_CHANNELS = {
  PRICE_TICK: "mems26:events:price.tick",
  PRICE_SNAPSHOT: "mems26:events:price.snapshot",
  BAR_5MIN: "mems26:events:bar.5min",
  BAR_TICK_REVERSAL: "mems26:events:bar.tick_reversal",
  SIGNAL_FIRED: "mems26:events:signal.fired",
  SYSTEM_HEALTH: "mems26:events:system.health",
} as const;
