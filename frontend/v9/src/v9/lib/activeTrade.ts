// activeTrade.ts — SHARED types + display math for GET /api/v9/trades/active
// (UI round 2, 2026-07-02).
//
// Single source for the active-trade payload shape and the distance/progress/
// elapsed/BE display logic used by BOTH the side-panel ActiveTradeCard and the
// floating DemoMonitor — imported, not duplicated (round-2 requirement: "reuse
// the exact logic/stores from the round-1 ActiveTradeCard").
//
// Payload evidence (backend/v9/api/v9/trades.py::get_active_trade):
//   response keys            trades.py:279-294  (trade_id — NOT id)
//   contracts rows           trades.py:247-271  (id/target_price/status/pnl/r/exit_ts/smart_be)
//   display fields spread    trades.py:292      (**extract_trade_display → pattern_id/day_type/...)
//   no-active-trade response trades.py:237-238  (JSON null)
// BE convention |stop − entry| < 0.5 mirrors trades.py::_stop_note (:81-87).
//
// Display-only helpers; no trading logic, no requests.

export interface ActiveContract {
  id: string; // "C1" | "C2" | "C3" (trades.py:257)
  target_price: number | null; // t1/t2/t3 — null when trail-only (trades.py:258)
  status: 'OPEN' | 'HIT_TARGET' | 'HIT_STOP' | 'BE'; // trades.py:248
  pnl: number; // trades.py:260
  r: number; // trades.py:261
  exit_ts?: string | null; // trades.py:262
  smart_be: boolean; // trades.py:263
}

export interface TradeSystemChip {
  id: number;
  name: string;
  role: string;
  involved: boolean;
  is_firing: boolean;
  hint?: string | null;
  entry_price?: number | null;
}

export interface ActiveTrade {
  trade_id: number; // trades.py:280
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  entry_ts: string | null;
  stop_price: number;
  state?: string | null; // FILLED / PARTIAL / OPEN (trades.py:285)
  firing_system?: number;
  systems?: TradeSystemChip[];
  contracts: ActiveContract[];
  hits: number;
  total_pnl: number;
  total_r: number;
  summary: string; // "N/3 hit"
  /** Contracts actually in the market = this trade's legs + any scale-in child.
   *  `contracts` above is only this trade's own legs, so on a reinforced
   *  position the two differ — that difference is what Michael was missing
   *  on 17.08 (trades.py). */
  position_contracts?: number;
  /** Present while a reinforcement is open. `added` is the child's size. */
  scale_in?: {
    child_id: number;
    added: number;
    at: string | null;
    child_entry?: number | null;
  } | null;
  // extract_trade_display spread (trades.py:292)
  pattern_id?: string | null;
  trigger?: string | null;
  classification?: string | null;
  day_type?: string | null;
}

/** Contract-status → color (round-1 ActiveTradeCard convention). */
export const CONTRACT_STATUS_COLORS: Record<string, string> = {
  OPEN: '#737373',
  HIT_TARGET: '#16a34a',
  HIT_STOP: '#dc2626',
  BE: '#eab308',
};

/** /active returns JSON null when there is no active trade (trades.py:237-238)
 *  and `trade_id` (not `id`) when there is one — the single correct guard. */
export function parseActiveTrade(d: unknown): ActiveTrade | null {
  const t = d as { trade_id?: unknown } | null;
  return t && typeof t.trade_id === 'number' ? (d as ActiveTrade) : null;
}

/** "17m" / "1h 23m" from entry_ts to now; null when not computable. */
export function elapsedLabel(entryTs: string | null | undefined, nowMs: number): string | null {
  if (!entryTs) return null;
  const t0 = new Date(entryTs).getTime();
  if (!Number.isFinite(t0)) return null;
  const min = Math.floor((nowMs - t0) / 60000);
  if (min < 0) return null;
  if (min < 60) return `${min}m`;
  return `${Math.floor(min / 60)}h ${min % 60}m`;
}

/** Favorable points remaining from live price to target (negative = beyond). */
export function ptsToTarget(target: number, price: number, isLong: boolean): number {
  return (target - price) * (isLong ? 1 : -1);
}

/** % of the entry→target span already covered, clamped 0–100. Null when the
 *  span is not positive (bad/absent levels) — honest missing, no synthesis. */
export function progressPct(target: number, entry: number, price: number, isLong: boolean): number | null {
  const mul = isLong ? 1 : -1;
  const span = (target - entry) * mul;
  if (!(span > 0)) return null;
  const done = (price - entry) * mul;
  return Math.max(0, Math.min(100, (done / span) * 100));
}

/** Stop parked at entry (Break-Even). Backend convention: |stop − entry| < 0.5
 *  (trades.py::_stop_note:85). */
export function isStopAtBE(
  entryPrice: number | null | undefined,
  stopPrice: number | null | undefined,
): boolean {
  return entryPrice != null && stopPrice != null && Math.abs(stopPrice - entryPrice) < 0.5;
}
