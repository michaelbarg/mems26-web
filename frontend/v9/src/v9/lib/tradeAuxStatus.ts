/**
 * Per-trade auxiliary status derived from the set of trades.
 *
 * 3 axes Michael wants to filter on the /trades page:
 *  - overlap:       was another trade live at the same time? (SHADOW reality)
 *  - liveEligible:  would this trade have been taken if we'd been running LIVE
 *                   (sequential gating: at most one open trade at any time)?
 *  - confluence:    did at least one system disagree with the entry direction
 *                   at fire-time? (uses backend systems_agreement field)
 *
 * Kept in sync with tests/v9/frontend/test_trade_aux_status.py
 * (same algorithm, Python mirror).
 */
import type { Trade } from '../types';

export type ConfluenceClass = 'agree' | 'disagree' | 'neutral';

export interface TradeAuxStatus {
  isParallel: boolean;
  liveEligible: boolean;
  confluence: ConfluenceClass;
  /** Trade id whose lifetime forced this row into "skipped" (gating winner). */
  blockedBy: number | null;
}

const NOW_FALLBACK_SKEW_S = 5; // be conservative for still-open trades
// Cap open/partial trade windows at 30 min from entry.
// Without this, PARTIAL trades with no exit_ts extend to "now" and
// incorrectly mark every subsequent trade as parallel.
const MAX_OPEN_WINDOW_S = 30 * 60;

function parseIso(ts: string | null | undefined): number | null {
  if (!ts) return null;
  const ms = Date.parse(ts);
  if (Number.isNaN(ms)) return null;
  return ms / 1000;
}

function nowUnix(): number {
  return Math.floor(Date.now() / 1000) + NOW_FALLBACK_SKEW_S;
}

interface Window {
  id: number;
  start: number;
  end: number;
}

function buildWindows(trades: Trade[], now: number): Window[] {
  const out: Window[] = [];
  for (const t of trades) {
    const start = parseIso(t.entry_ts);
    if (start === null) continue;
    const exit = parseIso(t.exit_ts);
    // PARTIAL/PENDING with no exit_ts are "stuck" trades whose real close
    // time is unknown; cap their window at 30 min so they don't mark every
    // later trade as parallel. OPEN/FILLED with no exit_ts are genuinely
    // active → extend to now (current behaviour).
    const isStuck = !t.exit_ts && (t.state === 'PARTIAL' || t.state === 'PENDING');
    const end = exit !== null
      ? Math.max(exit, start)
      : isStuck ? Math.min(start + MAX_OPEN_WINDOW_S, now) : now;
    out.push({ id: t.id, start, end });
  }
  return out;
}

function classifyConfluence(t: Trade): ConfluenceClass {
  const sys = t.systems_agreement ?? [];
  if (sys.length === 0) return 'neutral';
  let agrees = 0;
  let disagrees = 0;
  for (const s of sys) {
    if (s.agree === true) agrees += 1;
    else if (s.agree === false) disagrees += 1;
  }
  if (disagrees > 0) return 'disagree';
  if (agrees > 0) return 'agree';
  return 'neutral';
}

/**
 * Compute aux status for every trade.
 *
 * Overlap is O(n^2) but n ≤ 200 in practice (single API page), so this stays
 * well under 1ms. Live-eligibility is O(n log n) via sorted walk.
 *
 * Passing `nowOverride` keeps the test deterministic; production callers omit
 * it and pick up Date.now().
 */
export function computeAuxStatus(
  trades: Trade[],
  nowOverride?: number,
): Map<number, TradeAuxStatus> {
  const out = new Map<number, TradeAuxStatus>();
  const now = nowOverride ?? nowUnix();
  const windows = buildWindows(trades, now);
  const winById = new Map<number, Window>();
  for (const w of windows) winById.set(w.id, w);

  // Overlap: two windows overlap iff a.start < b.end AND a.end > b.start.
  // Strict inequality so identical timestamps don't accidentally mark every
  // burst-fired pair as parallel — we only call it parallel if there's real
  // time intersection.
  for (const t of trades) {
    const wA = winById.get(t.id);
    let isParallel = false;
    if (wA) {
      for (const wB of windows) {
        if (wB.id === wA.id) continue;
        if (wA.start < wB.end && wA.end > wB.start) {
          isParallel = true;
          break;
        }
      }
    }
    out.set(t.id, {
      isParallel,
      liveEligible: false, // filled in below
      blockedBy: null,
      confluence: classifyConfluence(t),
    });
  }

  // Live-eligibility: walk windows in start order; accept iff no active live
  // window covers the candidate's start. Closed live windows free the slot.
  const sortedWindows = [...windows].sort((a, b) => a.start - b.start || a.id - b.id);
  let activeEnd = -Infinity;
  let activeId: number | null = null;
  for (const w of sortedWindows) {
    const aux = out.get(w.id);
    if (!aux) continue;
    if (w.start >= activeEnd) {
      aux.liveEligible = true;
      aux.blockedBy = null;
      activeEnd = w.end;
      activeId = w.id;
    } else {
      aux.liveEligible = false;
      aux.blockedBy = activeId;
    }
  }
  return out;
}
