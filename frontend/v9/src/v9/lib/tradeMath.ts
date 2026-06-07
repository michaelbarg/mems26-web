import type { Trade } from '../types';

/**
 * Pure trade-math helpers for the Trades journal.
 *
 * Source-of-truth (CLAUDE.md Rule 1): every value here is derived from existing
 * Trade fields. When a required field is null we return null / '—' — never a
 * synthesised value.
 *
 * The cumulative functions order by the *correct* timestamp:
 *   - cumulativeByClose → exit_ts  (realised running balance; equity curve, max-DD)
 *   - cumulativeByOpen  → entry_ts (exposure sequence)
 * Ordering by entry_ts for the realised curve is a bug: a trade entered earlier
 * can close later (e.g. an overnight scalp held to next session), which mis-orders
 * the equity curve and max drawdown.
 */

/** Accounting money format: gain "+$5.00", loss "($33.75)", zero "$0.00". */
export function formatUsdAccounting(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—';
  if (v > 0) return `+$${v.toFixed(2)}`;
  if (v < 0) return `($${Math.abs(v).toFixed(2)})`;
  return '$0.00';
}

export interface RLevels {
  /** |entry - stop_initial| in price points; 0 when not computable. */
  risk: number;
  /** Stop is -1R by definition of risk. */
  stopR: number;
  t1R: number | null;
  t2R: number | null;
  t3R: number | null;
  /** Realised exit in R (= pnl_r). */
  exitR: number | null;
  /** Where the stop moved to, in R (null if it never moved). */
  movedR: number | null;
}

/** Map a trade's levels to R-multiples relative to entry (0) and risk (1R). */
export function rLevels(t: Trade): RLevels {
  const entry = t.entry_price;
  const stopInit = t.stop_initial ?? t.stop ?? null;
  const risk = entry != null && stopInit != null ? Math.abs(entry - stopInit) : 0;
  // lvl<=0 means "no target" (legacy 0.0 sentinel) → treat as null, not a real price.
  const fav = (lvl: number | null | undefined): number | null => {
    if (lvl == null || lvl <= 0 || entry == null || risk <= 0) return null;
    return (t.direction === 'LONG' ? lvl - entry : entry - lvl) / risk;
  };
  const moved =
    t.stop != null && stopInit != null && Math.abs(stopInit - t.stop) >= 0.01 ? t.stop : null;
  return {
    risk,
    stopR: -1,
    t1R: fav(t.t1),
    t2R: fav(t.t2),
    t3R: fav(t.t3),
    exitR: t.pnl_r ?? null,
    movedR: moved != null ? fav(moved) : null,
  };
}

/** Planned risk/reward in R: { t1, t2 } or null when there is no T1. */
export function riskReward(t: Trade): { t1: number | null; t2: number | null } | null {
  if (t.t1 == null) return null;
  const l = rLevels(t);
  return { t1: l.t1R, t2: l.t2R };
}

export type StopMovement = 'moved' | 't1_no_be' | 'static';

/**
 * Did the stop move per the characterization?
 *  - 'moved'    → stop_initial != stop (SMART_BE moved it to BE after T1)
 *  - 't1_no_be' → T1 hit but stop never moved (stop_issue flag)
 *  - 'static'   → stopped/exited at the initial stop
 */
export function stopMovement(t: Trade): StopMovement {
  const stopInit = t.stop_initial ?? null;
  if (stopInit != null && t.stop != null && Math.abs(stopInit - t.stop) >= 0.01) return 'moved';
  if (t.stop_issue === 'T1_NO_BE') return 't1_no_be';
  return 'static';
}

/** Hold duration in minutes (entry→exit). null while open. */
export function durationMinutes(t: Trade): number | null {
  if (!t.entry_ts || !t.exit_ts) return null;
  const a = Date.parse(t.entry_ts);
  const b = Date.parse(t.exit_ts);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.round(((b - a) / 60000) * 10) / 10;
}

/** Human duration: "48m" / "12h 29m" / "—". */
export function formatDuration(min: number | null): string {
  if (min == null) return '—';
  if (min < 60) return `${Math.floor(min)}m`;
  return `${Math.floor(min / 60)}h ${Math.round(min % 60)}m`;
}

const tsKey = (s: string | null | undefined): string => s ?? '';

function realised(list: Trade[]): Trade[] {
  return list.filter((t) => !t.is_synthetic && t.pnl_usd != null);
}

/** Running cumulative P&L keyed by trade id, ordered by exit_ts (realised). */
export function cumulativeByClose(list: Trade[]): Map<number, number> {
  const closed = realised(list)
    .filter((t) => t.exit_ts)
    .slice()
    .sort((a, b) => {
      const ka = tsKey(a.exit_ts), kb = tsKey(b.exit_ts);
      return ka < kb ? -1 : ka > kb ? 1 : a.id - b.id;
    });
  const m = new Map<number, number>();
  let run = 0;
  for (const t of closed) {
    run += t.pnl_usd ?? 0;
    m.set(t.id, Math.round(run * 100) / 100);
  }
  return m;
}

/** Running cumulative P&L keyed by trade id, ordered by entry_ts (exposure). */
export function cumulativeByOpen(list: Trade[]): Map<number, number> {
  const arr = realised(list)
    .slice()
    .sort((a, b) => {
      const ka = tsKey(a.entry_ts), kb = tsKey(b.entry_ts);
      return ka < kb ? -1 : ka > kb ? 1 : a.id - b.id;
    });
  const m = new Map<number, number>();
  let run = 0;
  for (const t of arr) {
    run += t.pnl_usd ?? 0;
    m.set(t.id, Math.round(run * 100) / 100);
  }
  return m;
}

export interface EquityPoint {
  id: number;
  label: string;
  cum: number;
  pnl: number;
  outcome: string;
  system: number;
}

/** Ordered equity-curve points (by exit_ts) for charting. */
export function equityCurveByClose(list: Trade[]): { points: EquityPoint[]; maxDd: number } {
  const closed = realised(list)
    .filter((t) => t.exit_ts)
    .slice()
    .sort((a, b) => {
      const ka = tsKey(a.exit_ts), kb = tsKey(b.exit_ts);
      return ka < kb ? -1 : ka > kb ? 1 : a.id - b.id;
    });
  const points: EquityPoint[] = [];
  let run = 0, peak = 0, maxDd = 0;
  for (const t of closed) {
    run += t.pnl_usd ?? 0;
    if (run > peak) peak = run;
    if (peak - run > maxDd) maxDd = peak - run;
    const label = t.exit_ts ? t.exit_ts.slice(5, 16).replace('T', ' ') : `#${t.id}`;
    points.push({
      id: t.id,
      label,
      cum: Math.round(run * 100) / 100,
      pnl: t.pnl_usd ?? 0,
      outcome: t.outcome ?? '',
      system: t.system,
    });
  }
  return { points, maxDd: Math.round(maxDd * 100) / 100 };
}
