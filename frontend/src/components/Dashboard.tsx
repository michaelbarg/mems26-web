'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import LightweightChart from './LightweightChart';
import PreEntryChecklist, { type ChecklistSetup } from './PreEntryChecklist';
import AnalyticsTab from './AnalyticsTab';

const API_URL = 'https://mems26-web.onrender.com';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Bar { o:number; h:number; l:number; c:number; vol:number; buy:number; sell:number; delta:number; }
interface Signal { direction:'LONG'|'SHORT'|'NO_TRADE'; score:number; confidence:string|number; entry:number; stop:number; target1:number; target2:number; target3:number; risk_pts:number; rationale:string; tl_color:string; setup?:string; setup_name?:string; win_rate?:number; t1_win_rate?:number; t2_win_rate?:number; t3_win_rate?:number; wait_reason?:string; rr?:string; the_box?:string; anchor_line?:number; order_block?:string; invalidation?:number; geometric_notes?:string; warning?:string; time_estimate?:string; }
interface MarketData {
  ts:number; price:number; bar:Bar;
  mtf:{ m3:Bar; m15:Bar; m30:Bar; m60:Bar };
  cvd:{ total:number; d20:number; d5:number; trend:string; buy_vol:number; sell_vol:number; delta:number };
  vwap:{ value:number; distance:number; above:boolean; pullback:boolean };
  session:{ phase:string; min:number; sh:number; sl:number; ibh:number; ibl:number; ib_locked:boolean };
  profile:{ poc:number; vah:number; val:number; tpo_poc:number; prev_day_poc:number; in_va:boolean; above_poc:boolean };
  woodi:{ pp:number; r1:number; r2:number; s1:number; s2:number; above_pp:boolean };
  levels:{ prev_high:number; prev_low:number; prev_close:number; daily_open:number; overnight_high:number; overnight_low:number };
  order_flow:{ absorption_bull:boolean; liq_sweep:boolean; liq_sweep_long:boolean; liq_sweep_short:boolean; imbalance_bull:number; imbalance_bear:number };
  reversal:{ ib_high:number; ib_low:number; rev15_type:string; rev15_price:number };
  order_fills?:{ price:number; qty:number; side:string; ts:number; pos:number }[];
  footprint?:any[];
  current_candle?:{ ts:number; o:number; h:number; l:number; c:number; buy:number; sell:number; vol:number; delta:number };
  signal?:Signal;
}
interface Candle { ts:number; o:number; h:number; l:number; c:number; buy:number; sell:number; delta:number; }

// ── Normalize candle — single source of truth ────────────────────────────────
function normalizeCandle(c: any): Candle | null {
  const o = c.o ?? c.open ?? 0;
  const h = c.h ?? c.high ?? 0;
  const l = c.l ?? c.low ?? 0;
  const cl = c.c ?? c.close ?? 0;
  const ts = c.ts ?? c.time ?? 0;
  if (!o || !h || !l || !cl || ts < 1577836800) return null;
  if (!isFinite(o) || !isFinite(h) || !isFinite(l) || !isFinite(cl)) return null;
  return {
    ts, o, h, l, c: cl,
    buy: c.buy ?? 0, sell: c.sell ?? 0,
    delta: c.delta ?? ((c.buy ?? 0) - (c.sell ?? 0)),
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const G = '#22c55e', Y = '#f59e0b', R = '#ef5350';
const scoreCol = (s:number) => s >= 7 ? G : s >= 5 ? Y : R;
const CANDLE_SEC = 180; // 3 minute candles

// ── Detected Setup — סטאפ שזוהה ונשמר ─────────────────────────────────────
interface DetectedSetup {
  id: string;
  detectedAt: number;       // ts of detection
  type: string;             // sweep/rejection/momentum/bounce/breakout/approaching
  dir: 'long' | 'short';
  levelName: string;
  level: number;
  score: number;
  entry: number;
  stop: number;
  c1: number;
  c2: number;
  c3: number;
  riskPts: number;
  delta: number;
  // Bar timestamps for chart markers
  detectionBarTs: number;   // נר הזיהוי
  entryBarTs: number;       // נר הכניסה
  // Lifecycle
  status: 'detected' | 'confirmed' | 'entered' | 'c1_hit' | 'c2_hit' | 'stopped' | 'expired';
  result?: string;
  pnlPts?: number;
}

// ── Active Setup — סטאפ שנבחר ונשאר על הגרף ─────────────────────────────────
interface ActiveSetup {
  sweep: SweepEvent;
  activatedAt: number;      // ts of activation
  status: 'ACTIVE' | 'T1_HIT' | 'T2_HIT' | 'T3_HIT' | 'STOPPED';
  result?: string;
  resultBars?: number;      // כמה נרות עד לתוצאה
  // Future bar timestamps (estimated)
  entryBarTs: number;
  stopBarTs: number;
  t1BarTs: number;
  t2BarTs: number;
  t3BarTs: number;
  // Time estimates
  t1EstBars: number;
  t2EstBars: number;
  t3EstBars: number;
}

// ── Time Estimation — הערכת נרות עד למחיר יעד ────────────────────────────────
function estimateBarReach(candles: Candle[], targetDist: number): { bars: number; minBars: number; maxBars: number } {
  if (!candles || candles.length < 5) return { bars: 5, minBars: 3, maxBars: 10 };
  // Sort oldest → newest, take last 20
  const sorted = [...candles].sort((a, b) => a.ts - b.ts);
  const recent = sorted.slice(-20);
  // Average |close - open| per bar
  let sumMove = 0;
  for (const c of recent) sumMove += Math.abs(c.c - c.o);
  const avgMove = sumMove / recent.length;
  if (avgMove < 0.01) return { bars: 10, minBars: 5, maxBars: 20 };
  const bars = Math.round(targetDist / avgMove);
  return {
    bars: Math.max(1, bars),
    minBars: Math.max(1, Math.round(bars * 0.5)),
    maxBars: Math.max(2, Math.round(bars * 1.8)),
  };
}

function buildActiveSetup(sweep: SweepEvent, candles: Candle[]): ActiveSetup {
  const now = Math.floor(Date.now() / 1000);
  const entryTs = sweep.reversalBarTs || now;
  const risk = Math.abs(sweep.entry - sweep.stop);
  const t1dist = Math.abs(sweep.c1 - sweep.entry);
  const t2dist = Math.abs(sweep.c2 - sweep.entry);
  const t3dist = Math.abs(sweep.c3 - sweep.entry);

  const t1Est = estimateBarReach(candles, t1dist);
  const t2Est = estimateBarReach(candles, t2dist);
  const t3Est = estimateBarReach(candles, t3dist);
  const stopEst = estimateBarReach(candles, risk);

  return {
    sweep,
    activatedAt: now,
    status: 'ACTIVE',
    entryBarTs: entryTs,
    stopBarTs: entryTs + stopEst.bars * CANDLE_SEC,
    t1BarTs: entryTs + t1Est.bars * CANDLE_SEC,
    t2BarTs: entryTs + t2Est.bars * CANDLE_SEC,
    t3BarTs: entryTs + t3Est.bars * CANDLE_SEC,
    t1EstBars: t1Est.bars,
    t2EstBars: t2Est.bars,
    t3EstBars: t3Est.bars,
  };
}

// ── Setup Potential Calculator ────────────────────────────────────────────────
function calcPotential(entry:number, stop:number, dir:'long'|'short', woodi:any, levels:any) {
  if (!entry || !stop) return null;
  const risk = Math.abs(entry - stop);
  if (risk <= 0) return null;
  const L = dir === 'long';
  const t1 = L ? entry + risk     : entry - risk;
  const t2 = L ? entry + risk * 2 : entry - risk * 2;
  // T3 = Woodi R1/S1 או PDH/PDL
  const t3 = L
    ? Math.max(woodi?.r1||0, levels?.prev_high||0) || (entry + risk * 3)
    : Math.min(woodi?.s1||9999, levels?.prev_low||9999) || (entry - risk * 3);
  const t1pts  = Math.abs(t1 - entry);
  const t2pts  = Math.abs(t2 - entry);
  const t3pts  = Math.abs(t3 - entry);
  const valid  = t1pts >= 10; // פילטר מינימום 10 נקודות
  return {
    risk_pts: Math.round(risk * 4) / 4,
    t1, t2, t3,
    t1_pts: Math.round(t1pts * 4) / 4,
    t2_pts: Math.round(t2pts * 4) / 4,
    t3_pts: Math.round(t3pts * 4) / 4,
    t1_usd: Math.round(t1pts * 5),
    t2_usd: Math.round(t2pts * 5),
    t3_usd: Math.round(t3pts * 5),
    rr1:    Math.round(t1pts / risk * 10) / 10,
    rr2:    Math.round(t2pts / risk * 10) / 10,
    valid,
    reason: !valid ? `T1 = ${t1pts.toFixed(1)}pt — פחות מ-10` : '',
  };
}

// ── Liq Sweep Scanner — סורק 960 נרות ───────────────────────────────────────
interface SweepEvent {
  id: string;
  ts: number;
  dir: 'long' | 'short';
  level: number;
  levelName: string;
  levelTouches: number;       // כמה נגיעות ברמה לפני ה-sweep
  sweepBarIndex: number;
  reversalBarIndex: number;
  confirmBarIndex: number;    // נר האישור
  confirmed: boolean;         // האם נר האישור עבר
  confirmDelta: number;       // delta של נר האישור
  confirmCCI6?: number;       // CCI6 אם זמין
  sweepWick: number;          // עומק ה-sweep מתחת/מעל לרמה
  entry: number;
  stop: number;
  c1: number;                 // R:R 1:1 — 50% exit, סטופ ל-BE
  c2: number;                 // R:R 1:2 — 25% exit
  c3: number;                 // runner — Woodi R1/S1 or R:R 1:3
  riskPts: number;
  delta: number;
  volume: number;
  relVol: number;
  score: number;
  sweepBarTs: number;
  reversalBarTs: number;
  confirmBarTs: number;
  setupBarTs: number[];
}

// Level touch data for chart markers
interface LevelTouch {
  price: number;
  name: string;
  touches: number;
  touchBarTs: number[];       // timestamps of bars that touched the level
}

function scanHistoricalSweeps(
  candles: Candle[],
  levels: { prev_high:number; prev_low:number; overnight_high:number; overnight_low:number },
  woodi?: { pp:number; r1:number; r2:number; s1:number; s2:number },
  live?: MarketData | null,
): { events: SweepEvent[]; levelTouches: LevelTouch[] } {
  if (!candles || candles.length < 10) return { events: [], levelTouches: [] };

  const bars = [...candles].sort((a, b) => a.ts - b.ts);
  const sess = live?.session || {} as any;
  const prof = live?.profile || {} as any;
  const vwap = live?.vwap || {} as any;

  // ── שלב א: כל הרמות — קבועות + דינמיות ────────────────────
  const keyLevels: { price: number; name: string }[] = [];
  if (levels.prev_high > 0)      keyLevels.push({ price: levels.prev_high,      name: 'PDH' });
  if (levels.prev_low > 0)       keyLevels.push({ price: levels.prev_low,       name: 'PDL' });
  if (levels.overnight_high > 0) keyLevels.push({ price: levels.overnight_high, name: 'ONH' });
  if (levels.overnight_low > 0)  keyLevels.push({ price: levels.overnight_low,  name: 'ONL' });
  if (sess.ibh > 0 && sess.ib_locked) keyLevels.push({ price: sess.ibh, name: 'IBH' });
  if (sess.ibl > 0 && sess.ib_locked) keyLevels.push({ price: sess.ibl, name: 'IBL' });
  if (vwap.value > 0)           keyLevels.push({ price: vwap.value,           name: 'VWAP' });
  if (prof.poc > 0)             keyLevels.push({ price: prof.poc,             name: 'POC' });
  if (prof.vah > 0)             keyLevels.push({ price: prof.vah,             name: 'VAH' });
  if (prof.val > 0)             keyLevels.push({ price: prof.val,             name: 'VAL' });
  if (sess.sh > 0)              keyLevels.push({ price: sess.sh,              name: 'SH' });
  if (sess.sl > 0)              keyLevels.push({ price: sess.sl,              name: 'SL' });

  // רמות דינמיות — מחירים שנגעו 3+ פעמים
  const touchCount: Record<number, number> = {};
  for (const c of bars.slice(-50)) {
    const rh = Math.round(c.h * 2) / 2;
    const rl = Math.round(c.l * 2) / 2;
    touchCount[rh] = (touchCount[rh] || 0) + 1;
    touchCount[rl] = (touchCount[rl] || 0) + 1;
  }
  for (const [p, count] of Object.entries(touchCount)) {
    const pf = parseFloat(p);
    if (count >= 3 && !keyLevels.some(l => Math.abs(l.price - pf) < 1.5)) {
      keyLevels.push({ price: pf, name: `T${count}x` });
    }
  }

  if (keyLevels.length === 0) return { events: [], levelTouches: [] };

  // ── ספירת נגיעות ────────────────────────────────────────────
  const TOUCH_DIST = 0.75;
  const levelTouches: LevelTouch[] = keyLevels.map(lev => {
    const touchBars: number[] = [];
    for (let i = 0; i < bars.length; i++) {
      const b = bars[i];
      if (Math.abs(b.h - lev.price) <= TOUCH_DIST || Math.abs(b.l - lev.price) <= TOUCH_DIST ||
          (b.l <= lev.price && b.h >= lev.price)) {
        if (touchBars.length === 0 || i - bars.findIndex(bb => bb.ts === touchBars[touchBars.length-1]) >= 3) {
          touchBars.push(b.ts);
        }
      }
    }
    return { price: lev.price, name: lev.name, touches: touchBars.length, touchBarTs: touchBars };
  });

  // ── שלב ב+ג: זיהוי sweep + rejection + אישור ───────────────
  const avgVol = (idx: number): number => {
    const start = Math.max(0, idx - 20);
    let sum = 0, count = 0;
    for (let j = start; j < idx; j++) {
      sum += (bars[j].buy || 0) + (bars[j].sell || 0);
      count++;
    }
    return count > 0 ? sum / count : 1;
  };

  const events: SweepEvent[] = [];
  const MIN_GAP = 4;

  for (let i = 1; i < bars.length - 2; i++) {
    const bar = bars[i];
    const nextBar = bars[i + 1];
    const vol = (bar.buy || 0) + (bar.sell || 0);
    const avg = avgVol(i);
    const relVol = avg > 0 ? vol / avg : 1;
    const barDelta = bar.delta || ((bar.buy || 0) - (bar.sell || 0));
    const body = Math.abs(bar.c - bar.o);
    const lowerWick = Math.min(bar.o, bar.c) - bar.l;
    const upperWick = bar.h - Math.max(bar.o, bar.c);

    for (const lev of keyLevels) {
      const recentSame = events.find(e => Math.abs(e.level - lev.price) < 2 && i - e.sweepBarIndex < MIN_GAP);
      if (recentSame) continue;

      const confirmDelta = nextBar.delta || ((nextBar.buy||0) - (nextBar.sell||0));
      const confirmCCI6 = (nextBar as any).cci6;
      const lt = levelTouches.find(l => l.name === lev.name);
      const touches = lt?.touches || 0;

      // ═══ LONG patterns ═══════════════════════════════════════
      let longType: 'sweep' | 'rejection' | null = null;
      let longScore = 0;

      // Sweep: wick שבר רמה ב-0.5+, סגר מעל
      if (bar.l < lev.price - 0.5 && bar.c > lev.price) {
        longType = 'sweep';
        longScore += 25; // שבירה
        longScore += 20; // חזרה מעל
        if (relVol >= 1.2) longScore += 15;
        if (lev.price - bar.l >= 1.0) longScore += 10;
        if (confirmDelta > 100) longScore += 20;
        if (confirmDelta > 50) longScore += 5;
        if (touches >= 2) longScore += 5;
      }
      // Rejection: נגע ברמה + wick ארוך למטה + סגר ירוק
      else if (Math.abs(bar.l - lev.price) < 1.0 && bar.c > lev.price && bar.c > bar.o) {
        if (lowerWick > body * 1.5) {
          longType = 'rejection';
          longScore += 20; // נגיעה ברמה
          longScore += 15; // wick ארוך
          if (bar.c > bar.o) longScore += 10; // נר ירוק
          if (relVol >= 1.2) longScore += 15;
          if (confirmDelta > 50) longScore += 15;
          if (touches >= 2) longScore += 5;
        }
      }

      if (longType && longScore >= 55) {
        const entry = nextBar.c;
        const stop = bar.l - 0.25;
        const risk = Math.abs(entry - stop);
        if (risk > 0.5 && risk < 15) {
          const c1 = entry + risk;
          const c2 = entry + risk * 2;
          const c3 = (woodi?.r1 && woodi.r1 > entry + risk * 2) ? woodi.r1 : entry + risk * 3;
          events.push({
            id: `${longType}-long-${bar.ts}-${lev.name}`,
            ts: bar.ts, dir: 'long',
            level: lev.price, levelName: lev.name, levelTouches: touches,
            sweepBarIndex: i, reversalBarIndex: i, confirmBarIndex: i + 1,
            confirmed: confirmDelta > 100, confirmDelta, confirmCCI6,
            sweepWick: lev.price - bar.l, entry, stop, c1, c2, c3,
            riskPts: Math.round(risk * 4) / 4,
            delta: barDelta, volume: vol,
            relVol: Math.round(relVol * 10) / 10, score: Math.min(longScore, 100),
            sweepBarTs: bar.ts, reversalBarTs: bar.ts, confirmBarTs: nextBar.ts,
            setupBarTs: bars.slice(Math.max(0, i - 3), i).map(b => b.ts),
          });
        }
      }

      // ═══ SHORT patterns ══════════════════════════════════════
      let shortType: 'sweep' | 'rejection' | null = null;
      let shortScore = 0;

      if (bar.h > lev.price + 0.5 && bar.c < lev.price) {
        shortType = 'sweep';
        shortScore += 25;
        shortScore += 20;
        if (relVol >= 1.2) shortScore += 15;
        if (bar.h - lev.price >= 1.0) shortScore += 10;
        if (confirmDelta < -100) shortScore += 20;
        if (confirmDelta < -50) shortScore += 5;
        if (touches >= 2) shortScore += 5;
      }
      else if (Math.abs(bar.h - lev.price) < 1.0 && bar.c < lev.price && bar.c < bar.o) {
        if (upperWick > body * 1.5) {
          shortType = 'rejection';
          shortScore += 20;
          shortScore += 15;
          if (bar.c < bar.o) shortScore += 10;
          if (relVol >= 1.2) shortScore += 15;
          if (confirmDelta < -50) shortScore += 15;
          if (touches >= 2) shortScore += 5;
        }
      }

      if (shortType && shortScore >= 55) {
        const entry = nextBar.c;
        const stop = bar.h + 0.25;
        const risk = Math.abs(entry - stop);
        if (risk > 0.5 && risk < 15) {
          const c1 = entry - risk;
          const c2 = entry - risk * 2;
          const c3 = (woodi?.s1 && woodi.s1 < entry - risk * 2) ? woodi.s1 : entry - risk * 3;
          events.push({
            id: `${shortType}-short-${bar.ts}-${lev.name}`,
            ts: bar.ts, dir: 'short',
            level: lev.price, levelName: lev.name, levelTouches: touches,
            sweepBarIndex: i, reversalBarIndex: i, confirmBarIndex: i + 1,
            confirmed: confirmDelta < -100, confirmDelta: Math.abs(confirmDelta), confirmCCI6,
            sweepWick: bar.h - lev.price, entry, stop, c1, c2, c3,
            riskPts: Math.round(risk * 4) / 4,
            delta: Math.abs(barDelta), volume: vol,
            relVol: Math.round(relVol * 10) / 10, score: Math.min(shortScore, 100),
            sweepBarTs: bar.ts, reversalBarTs: bar.ts, confirmBarTs: nextBar.ts,
            setupBarTs: bars.slice(Math.max(0, i - 3), i).map(b => b.ts),
          });
        }
      }
    }
  }

  events.sort((a, b) => b.ts - a.ts);
  return { events, levelTouches };
}

// ── Forked Setup Evaluation — RANGE vs TREND ─────────────────────────────────
// Binary Pass/Fail — does NOT change the 8-check scoring model.
// Returns { pass: boolean, reason: string, eval_type: string }

interface SetupEvalResult {
  pass: boolean;
  reason: string;
  eval_type: 'range' | 'trend';
}

function evaluate_range_setup(
  hit: { level: number; levelName: string; bar: Candle; relVol: number; type: string } | null,
  dir: 'long' | 'short',
  live: MarketData | null,
  candles: Candle[],
): SetupEvalResult {
  // 3-Pillar evaluation for NORMAL / VOLATILE days (V6.1)
  // All 3 pillars must PASS. Binary Pass/Fail.
  if (!hit || !live) return { pass: false, reason: 'No setup hit', eval_type: 'range' };

  const of2 = (live as any).order_flow || {} as any;
  const fp = (live as any).footprint_bools || {} as any;
  const L = dir === 'long';

  // ── PILLAR 1: ZONE — Macro Sweep of key level ──────────────────────
  // Must be sweep with wick >= 1.5pt at macro level (PDH/PDL/ONH/ONL/IBH/IBL)
  const macroLevels = ['PDH', 'PDL', 'ONH', 'ONL', 'IBH', 'IBL'];
  if (hit.type !== 'sweep') {
    return { pass: false, reason: 'P1 ZONE: Range requires sweep (not ' + hit.type + ')', eval_type: 'range' };
  }
  // Wick must be >= 1.5pt
  const sweepWick = L
    ? (Math.min(hit.bar.o, hit.bar.c) - hit.bar.l)
    : (hit.bar.h - Math.max(hit.bar.o, hit.bar.c));
  if (sweepWick < 1.5) {
    return { pass: false, reason: `P1 ZONE: Sweep wick ${sweepWick.toFixed(1)}pt < 1.5pt min`, eval_type: 'range' };
  }
  // Middle of Nowhere reject — must be near a named level (not just dynamic)
  if (!macroLevels.includes(hit.levelName) && !['VWAP', 'POC', 'VAH', 'VAL', 'SH', 'SL'].includes(hit.levelName)) {
    return { pass: false, reason: 'P1 ZONE: Middle of Nowhere — no macro level', eval_type: 'range' };
  }

  // ── PILLAR 2: PATTERN — MSS + FVG + RelVol + Stacked Imbalance ────
  // MSS: swing break with volume
  const recent20 = candles.slice(0, 20);
  let hasMSS = false;
  const price = live.price || 0;
  if (L) {
    const swingHighs = recent20.slice(2, 10).map(c => c.h);
    const swingH = swingHighs.length > 0 ? Math.max(...swingHighs) : 0;
    hasMSS = price > swingH && swingH > 0;
  } else {
    const swingLows = recent20.slice(2, 10).map(c => c.l);
    const swingL = swingLows.length > 0 ? Math.min(...swingLows) : 999999;
    hasMSS = price < swingL && swingL < 999999;
  }
  if (!hasMSS) return { pass: false, reason: 'P2 PATTERN: No MSS (swing break)', eval_type: 'range' };

  // FVG: 0.5-4.0pt gap in last 10 candles
  const recent10 = candles.slice(0, 10);
  let hasFVG = false;
  for (let i = 0; i < recent10.length - 2; i++) {
    const c1 = recent10[i], c3 = recent10[i + 2];
    if (L) {
      if (c1.l > c3.h && (c1.l - c3.h) >= 0.5 && (c1.l - c3.h) <= 4.0) { hasFVG = true; break; }
    } else {
      if (c1.h < c3.l && (c3.l - c1.h) >= 0.5 && (c3.l - c1.h) <= 4.0) { hasFVG = true; break; }
    }
  }
  if (!hasFVG) return { pass: false, reason: 'P2 PATTERN: No FVG (0.5-4pt)', eval_type: 'range' };

  // RelVol > 1.2 on MSS bar
  if (hit.relVol <= 1.2) {
    return { pass: false, reason: `P2 PATTERN: RelVol ${hit.relVol.toFixed(2)} <= 1.2`, eval_type: 'range' };
  }

  // Stacked Imbalance — 2+ levels at 250% (from C++ bools)
  const stackedCount = fp.stacked_imbalance_count ?? (of2.imbalance_bull ?? 0) + (of2.imbalance_bear ?? 0);
  if (stackedCount < 2) {
    return { pass: false, reason: `P2 PATTERN: Stacked imbalance ${stackedCount} < 2`, eval_type: 'range' };
  }

  // ── PILLAR 3: FLOW — absorption_at_fvg + delta_confirmed_1m ───────
  // Both are booleans from C++ via footprint_bools
  const absorptionOk = fp.absorption_at_fvg ?? (L ? of2.absorption_bull : of2.absorption_bear) ?? false;
  if (!absorptionOk) return { pass: false, reason: 'P3 FLOW: No absorption at FVG', eval_type: 'range' };

  const deltaConfirmed = fp.delta_confirmed_1m ?? false;
  if (!deltaConfirmed) return { pass: false, reason: 'P3 FLOW: No delta confirmation (1m)', eval_type: 'range' };

  return { pass: true, reason: 'All 3 pillars PASS: ZONE + PATTERN + FLOW', eval_type: 'range' };
}

function evaluate_trend_setup(
  hit: { level: number; levelName: string; bar: Candle; relVol: number; type: string } | null,
  dir: 'long' | 'short',
  live: MarketData | null,
  candles: Candle[],
): SetupEvalResult {
  // 3-Pillar evaluation for TREND days (V6.1)
  // All 3 pillars must PASS. No sweep required.
  if (!hit || !live) return { pass: false, reason: 'No setup hit', eval_type: 'trend' };

  const vwap = live.vwap || {} as any;
  const fp = (live as any).footprint_bools || {} as any;
  const price = live.price || 0;
  const L = dir === 'long';

  // ── PILLAR 1: ZONE — Pullback to VWAP or FVG ─────────────────────
  const vwapDist = Math.abs(price - (vwap.value || 0));
  let hasPullback = vwapDist <= 3.0;

  if (!hasPullback) {
    const recent = candles.slice(0, 10);
    for (let i = 0; i < recent.length - 2; i++) {
      const c1 = recent[i], c3 = recent[i + 2];
      if (L) {
        if (c1.l > c3.h && (c1.l - c3.h) >= 0.5 && Math.abs(price - (c1.l + c3.h) / 2) <= 2.0) { hasPullback = true; break; }
      } else {
        if (c1.h < c3.l && (c3.l - c1.h) >= 0.5 && Math.abs(price - (c1.h + c3.l) / 2) <= 2.0) { hasPullback = true; break; }
      }
    }
  }
  if (!hasPullback) return { pass: false, reason: 'P1 ZONE: No pullback to VWAP/FVG', eval_type: 'trend' };

  // ── PILLAR 2: PATTERN — Continuation MSS + FVG + RelVol > 1.2 ────
  const recent20 = candles.slice(0, 20);
  let hasMSS = false;
  if (L) {
    const swingHighs = recent20.slice(2, 10).map(c => c.h);
    const swingH = swingHighs.length > 0 ? Math.max(...swingHighs) : 0;
    hasMSS = price > swingH && swingH > 0;
  } else {
    const swingLows = recent20.slice(2, 10).map(c => c.l);
    const swingL = swingLows.length > 0 ? Math.min(...swingLows) : 999999;
    hasMSS = price < swingL && swingL < 999999;
  }
  if (!hasMSS) return { pass: false, reason: 'P2 PATTERN: No continuation MSS', eval_type: 'trend' };

  // FVG check
  const recent10 = candles.slice(0, 10);
  let hasFVG = false;
  for (let i = 0; i < recent10.length - 2; i++) {
    const c1 = recent10[i], c3 = recent10[i + 2];
    if (L) {
      if (c1.l > c3.h && (c1.l - c3.h) >= 0.5 && (c1.l - c3.h) <= 4.0) { hasFVG = true; break; }
    } else {
      if (c1.h < c3.l && (c3.l - c1.h) >= 0.5 && (c3.l - c1.h) <= 4.0) { hasFVG = true; break; }
    }
  }
  if (!hasFVG) return { pass: false, reason: 'P2 PATTERN: No FVG (0.5-4pt)', eval_type: 'trend' };

  // RelVol > 1.2
  if (hit.relVol <= 1.2) {
    return { pass: false, reason: `P2 PATTERN: RelVol ${hit.relVol.toFixed(2)} <= 1.2`, eval_type: 'trend' };
  }

  // ── PILLAR 3: FLOW — Declining delta on pullback + delta_confirmed_1m ──
  const recent5 = candles.slice(0, 5);
  if (recent5.length >= 3) {
    const deltas = recent5.map(c => Math.abs(c.delta));
    const declining = deltas[0] < deltas[1] || deltas[1] < deltas[2];
    if (!declining) return { pass: false, reason: 'P3 FLOW: Delta not declining on pullback', eval_type: 'trend' };
  }

  const deltaConfirmed = fp.delta_confirmed_1m ?? false;
  if (!deltaConfirmed) return { pass: false, reason: 'P3 FLOW: No delta confirmation (1m)', eval_type: 'trend' };

  return { pass: true, reason: 'All 3 pillars PASS: ZONE + PATTERN + FLOW', eval_type: 'trend' };
}

// ── Real-time Setup Scanner ───────────────────────────────────────────────────
function calcSetups(live: MarketData | null, candles: Candle[] = []) {
  if (!live) return null;
  const bar  = live.bar        || {} as any;
  const sess = live.session    || {} as any;
  const lev  = live.levels     || {} as any;
  const prof = live.profile    || {} as any;
  const vwap = live.vwap       || {} as any;
  const cp   = (live as any).candle_patterns || {};
  const vol  = (live as any).volume_context  || {};
  const price = live.price || 0;
  const relVol = vol.rel_vol || 1;

  // ── רמות קבועות ──────────────────────────────────────────────────
  const allLevels: { price: number; name: string }[] = [];
  if (lev.prev_high > 0)      allLevels.push({ price: lev.prev_high,      name: 'PDH' });
  if (lev.prev_low > 0)       allLevels.push({ price: lev.prev_low,       name: 'PDL' });
  if (lev.overnight_high > 0) allLevels.push({ price: lev.overnight_high, name: 'ONH' });
  if (lev.overnight_low > 0)  allLevels.push({ price: lev.overnight_low,  name: 'ONL' });
  if (sess.ibh > 0 && sess.ib_locked) allLevels.push({ price: sess.ibh, name: 'IBH' });
  if (sess.ibl > 0 && sess.ib_locked) allLevels.push({ price: sess.ibl, name: 'IBL' });
  if (vwap.value > 0)         allLevels.push({ price: vwap.value,         name: 'VWAP' });
  if (prof.poc > 0)           allLevels.push({ price: prof.poc,           name: 'POC' });
  if (prof.vah > 0)           allLevels.push({ price: prof.vah,           name: 'VAH' });
  if (prof.val > 0)           allLevels.push({ price: prof.val,           name: 'VAL' });
  if (sess.sh > 0)            allLevels.push({ price: sess.sh,            name: 'SH' });
  if (sess.sl > 0)            allLevels.push({ price: sess.sl,            name: 'SL' });

  // ── רמות מנרות — session low/high snapshot מ-10 נרות אחרונים ──────
  // זה תופס רמות שהמחיר כבר עבר (ONL ישן שהתעדכן)
  const sortedAll = [...candles].sort((a, b) => b.ts - a.ts);
  if (sortedAll.length >= 10) {
    const r30 = sortedAll.slice(0, 30);
    const r30Low = Math.min(...r30.map(c => c.l));
    const r30High = Math.max(...r30.map(c => c.h));
    // Add recent swing low/high if not too close to existing levels
    if (r30Low > 0 && !allLevels.some(l => Math.abs(l.price - r30Low) < 1.5)) {
      allLevels.push({ price: r30Low, name: 'SwL' });
    }
    if (r30High > 0 && !allLevels.some(l => Math.abs(l.price - r30High) < 1.5)) {
      allLevels.push({ price: r30High, name: 'SwH' });
    }
  }

  // ── רמות דינמיות — מחירים שנגעו 3+ פעמים ─────────────────────────
  const sorted = sortedAll;
  const recent50 = sorted.slice(0, 50);
  if (recent50.length >= 10) {
    const touchCount: Record<number, number> = {};
    for (const c of recent50) {
      // Round to 0.5 pt precision
      const rh = Math.round(c.h * 2) / 2;
      const rl = Math.round(c.l * 2) / 2;
      touchCount[rh] = (touchCount[rh] || 0) + 1;
      touchCount[rl] = (touchCount[rl] || 0) + 1;
    }
    for (const [p, count] of Object.entries(touchCount)) {
      const pf = parseFloat(p);
      if (count >= 3 && Math.abs(pf - price) < 30) {
        // Don't add if too close to existing level
        const tooClose = allLevels.some(l => Math.abs(l.price - pf) < 1.5);
        if (!tooClose) allLevels.push({ price: pf, name: `T${count}x` });
      }
    }
  }

  // ── נתוני בסיס — כולל נר חי בראש ────────────────────────────────
  const liveCandle: Candle = { ts: 0, o: bar.o||0, h: bar.h||0, l: bar.l||0, c: bar.c||price, buy: bar.buy||0, sell: bar.sell||0, delta: bar.delta||0 };
  const recent10 = [liveCandle, ...sorted.slice(0, 9)];
  const recent20 = sorted.slice(0, 20);
  const avgVol20 = recent20.length > 0
    ? recent20.reduce((s, c) => s + (c.buy || 0) + (c.sell || 0), 0) / recent20.length : 1;
  const avgRange20 = recent20.length > 0
    ? recent20.reduce((s, c) => s + Math.abs(c.h - c.l), 0) / recent20.length : 1;

  type SetupHit = { level: number; levelName: string; bar: Candle; relVol: number; type: 'sweep' | 'rejection' | 'momentum' | 'bounce' | 'breakout' | 'approaching' };
  let longHit: SetupHit | null = null;
  let shortHit: SetupHit | null = null;

  // ── Pattern 1+2: Sweep + Rejection (level-based) ──────────────────
  // Sweep: check same bar close OR next bar close (delayed reversal)
  for (let ri = 0; ri < recent10.length; ri++) {
    const rb = recent10[ri];
    const nextRb = ri > 0 ? recent10[ri - 1] : null; // ri=0 is newest, ri-1 doesn't exist for newest
    // For candles (not live), the "next" bar is the one with smaller index (newer)
    const rbVol = (rb.buy || 0) + (rb.sell || 0);
    const rbRelVol = avgVol20 > 0 ? rbVol / avgVol20 : 1;
    const rbDelta = rb.delta || ((rb.buy || 0) - (rb.sell || 0));
    const lowerWick = Math.min(rb.o, rb.c) - rb.l;
    const upperWick = rb.h - Math.max(rb.o, rb.c);
    const body = Math.abs(rb.c - rb.o);
    const totalRange = rb.h - rb.l;

    for (const lv of allLevels) {
      // LONG Sweep: wick שבר רמה מלמטה
      if (!longHit && rb.l < lv.price - 0.5) {
        // Wick ratio: lower wick must be ≥40% of total range
        const wickRatio = totalRange > 0 ? lowerWick / totalRange : 0;
        if (wickRatio >= 0.4) {
          // Same bar closed above?
          if (rb.c > lv.price) {
            longHit = { level: lv.price, levelName: lv.name, bar: rb, relVol: rbRelVol, type: 'sweep' };
          }
          // Or next bar closed above? (delayed reversal)
          else if (nextRb && nextRb.c > lv.price) {
            longHit = { level: lv.price, levelName: lv.name, bar: nextRb, relVol: rbRelVol, type: 'sweep' };
          }
          // Or current price is above? (live reversal in progress)
          else if (ri > 0 && price > lv.price) {
            longHit = { level: lv.price, levelName: lv.name, bar: rb, relVol: rbRelVol, type: 'sweep' };
          }
        }
      }
      // LONG Rejection: נגע ברמה + hammer
      if (!longHit && Math.abs(rb.l - lv.price) < 1.0 && rb.c > lv.price && rb.c > rb.o && lowerWick > body * 1.5) {
        longHit = { level: lv.price, levelName: lv.name, bar: rb, relVol: rbRelVol, type: 'rejection' };
      }
      // SHORT Sweep: wick שבר רמה מלמעלה
      if (!shortHit && rb.h > lv.price + 0.5) {
        // Wick ratio: upper wick must be ≥40% of total range
        const wickRatio = totalRange > 0 ? upperWick / totalRange : 0;
        if (wickRatio >= 0.4) {
          if (rb.c < lv.price) {
            shortHit = { level: lv.price, levelName: lv.name, bar: rb, relVol: rbRelVol, type: 'sweep' };
          }
          else if (nextRb && nextRb.c < lv.price) {
            shortHit = { level: lv.price, levelName: lv.name, bar: nextRb, relVol: rbRelVol, type: 'sweep' };
          }
          else if (ri > 0 && price < lv.price) {
            shortHit = { level: lv.price, levelName: lv.name, bar: rb, relVol: rbRelVol, type: 'sweep' };
          }
        }
      }
      // SHORT Rejection: נגע ברמה + shooting star
      if (!shortHit && Math.abs(rb.h - lv.price) < 1.0 && rb.c < lv.price && rb.c < rb.o && upperWick > body * 1.5) {
        shortHit = { level: lv.price, levelName: lv.name, bar: rb, relVol: rbRelVol, type: 'rejection' };
      }
    }
    if (longHit && shortHit) break;
  }

  // ── Pattern 3: Momentum Reversal — 3+ נרות בכיוון אחד ואז היפוך ──
  if ((!longHit || !shortHit) && recent10.length >= 4) {
    const r = recent10; // newest first
    const curBar = r[0];
    const curDelta = curBar.delta || ((curBar.buy||0) - (curBar.sell||0));
    const curVol = (curBar.buy||0) + (curBar.sell||0);
    const curRelVol = avgVol20 > 0 ? curVol / avgVol20 : 1;

    // LONG momentum: 1+ red bars then green bar with positive delta > 50
    const prevRed = r.slice(1, 4).filter(c => c.c < c.o);
    if (!longHit && prevRed.length >= 1 && curBar.c > curBar.o && curDelta > 50) {
      const avgLow = prevRed.reduce((s, c) => s + c.l, 0) / prevRed.length;
      const nearLevel = allLevels.find(l => Math.abs(avgLow - l.price) < 5);
      longHit = {
        level: nearLevel?.price || curBar.l,
        levelName: nearLevel?.name || 'REV',
        bar: curBar, relVol: curRelVol, type: 'momentum',
      };
    }

    // SHORT momentum: 1+ green bars then red bar with negative delta < -50
    const prevGreen = r.slice(1, 4).filter(c => c.c > c.o);
    if (!shortHit && prevGreen.length >= 1 && curBar.c < curBar.o && curDelta < -50) {
      const avgHigh = prevGreen.reduce((s, c) => s + c.h, 0) / prevGreen.length;
      const nearLevel = allLevels.find(l => Math.abs(avgHigh - l.price) < 5);
      shortHit = {
        level: nearLevel?.price || curBar.h,
        levelName: nearLevel?.name || 'REV',
        bar: curBar, relVol: curRelVol, type: 'momentum',
      };
    }
  }

  // ── Pattern 4: Support/Resistance Bounce — מתקרב לרמה + מאט + היפוך ──
  if ((!longHit || !shortHit) && recent10.length >= 3) {
    const r = recent10;
    const curBar = r[0];
    const curDelta = curBar.delta || ((curBar.buy||0) - (curBar.sell||0));
    const curVol = (curBar.buy||0) + (curBar.sell||0);
    const curRelVol = avgVol20 > 0 ? curVol / avgVol20 : 1;
    const prevBar = r[1];
    const prevDelta = prevBar.delta || ((prevBar.buy||0) - (prevBar.sell||0));

    for (const lv of allLevels) {
      // LONG bounce: price near level from above, slowing down, then green
      if (!longHit && Math.abs(curBar.l - lv.price) < 5.0 && curBar.c > curBar.o && curDelta > 0) {
        // Previous bar was bearish or small — slowing
        if (prevBar.c <= prevBar.o || Math.abs(prevDelta) < 200) {
          longHit = { level: lv.price, levelName: lv.name, bar: curBar, relVol: curRelVol, type: 'bounce' };
        }
      }
      // SHORT bounce: price near level from below, slowing, then red
      if (!shortHit && Math.abs(curBar.h - lv.price) < 5.0 && curBar.c < curBar.o && curDelta < 0) {
        if (prevBar.c >= prevBar.o || Math.abs(prevDelta) < 200) {
          shortHit = { level: lv.price, levelName: lv.name, bar: curBar, relVol: curRelVol, type: 'bounce' };
        }
      }
    }
  }

  // ── Pattern 5: Breakout — פריצת רמה עם volume + המשך ──────────────
  if ((!longHit || !shortHit) && recent10.length >= 2) {
    const r = recent10;
    const curBar = r[0];
    const curDelta = curBar.delta || ((curBar.buy||0) - (curBar.sell||0));
    const curVol = (curBar.buy||0) + (curBar.sell||0);
    const curRelVol = avgVol20 > 0 ? curVol / avgVol20 : 1;
    const prevBar = r[1];

    for (const lv of allLevels) {
      // LONG breakout: prev bar was below level, current bar breaks above with volume
      if (!longHit && prevBar.c < lv.price && curBar.c > lv.price + 0.5 && curRelVol > 1.3 && curDelta > 50) {
        longHit = { level: lv.price, levelName: lv.name, bar: curBar, relVol: curRelVol, type: 'breakout' };
      }
      // SHORT breakout: prev bar was above level, current bar breaks below
      if (!shortHit && prevBar.c > lv.price && curBar.c < lv.price - 0.5 && curRelVol > 1.3 && curDelta < -50) {
        shortHit = { level: lv.price, levelName: lv.name, bar: curBar, relVol: curRelVol, type: 'breakout' };
      }
    }
  }

  // ── Pattern 6: Approaching Level — מתקרב לרמה, התראה מוקדמת ────
  if (!longHit || !shortHit) {
    // Find closest level below price (potential long) and above (potential short)
    const levelsBelow = allLevels.filter(l => l.price < price).sort((a, b) => b.price - a.price);
    const levelsAbove = allLevels.filter(l => l.price > price).sort((a, b) => a.price - b.price);

    if (!longHit && levelsBelow.length > 0) {
      const closest = levelsBelow[0];
      const dist = price - closest.price;
      // Within 8pt, price moving toward it (bar is red or delta negative)
      if (dist <= 8 && dist > 0.5) {
        const approaching = (bar.delta || 0) < 0 || (bar.c || price) < (bar.o || price);
        if (approaching) {
          longHit = {
            level: closest.price, levelName: closest.name,
            bar: { ts: 0, o: bar.o, h: bar.h, l: bar.l, c: bar.c || price, buy: bar.buy, sell: bar.sell, delta: bar.delta } as Candle,
            relVol, type: 'approaching' as any,
          };
        }
      }
    }
    if (!shortHit && levelsAbove.length > 0) {
      const closest = levelsAbove[0];
      const dist = closest.price - price;
      if (dist <= 8 && dist > 0.5) {
        const approaching = (bar.delta || 0) > 0 || (bar.c || price) > (bar.o || price);
        if (approaching) {
          shortHit = {
            level: closest.price, levelName: closest.name,
            bar: { ts: 0, o: bar.o, h: bar.h, l: bar.l, c: bar.c || price, buy: bar.buy, sell: bar.sell, delta: bar.delta } as Candle,
            relVol, type: 'approaching' as any,
          };
        }
      }
    }
  }

  // ── Type labels ────────────────────────────────────────────────────
  const typeLabel = (t: string) => {
    if (t === 'sweep') return 'Sweep';
    if (t === 'rejection') return 'Rejection';
    if (t === 'momentum') return 'Momentum';
    if (t === 'bounce') return 'Bounce';
    if (t === 'breakout') return 'Breakout';
    if (t === 'approaching') return 'Approaching';
    return t;
  };

  // ── Sweep-specific checks: wick ratio + CVD divergence ───────────
  const cvd = live.cvd || {} as any;
  // LONG: wick ratio of sweep candle
  const longSweepRange = longHit?.bar ? longHit.bar.h - longHit.bar.l : 0;
  const longSweepWick = longHit?.bar ? (Math.min(longHit.bar.o, longHit.bar.c) - longHit.bar.l) : 0;
  const longWickRatio = longSweepRange > 0 ? longSweepWick / longSweepRange : 0;
  // LONG CVD divergence: price made new low but CVD didn't collapse
  const longCvdDiv = longHit?.type === 'sweep' && (cvd.d5 || 0) > -50;
  // SHORT: wick ratio of sweep candle
  const shortSweepRange = shortHit?.bar ? shortHit.bar.h - shortHit.bar.l : 0;
  const shortSweepWick = shortHit?.bar ? (shortHit.bar.h - Math.max(shortHit.bar.o, shortHit.bar.c)) : 0;
  const shortWickRatio = shortSweepRange > 0 ? shortSweepWick / shortSweepRange : 0;
  // SHORT CVD divergence: price made new high but CVD didn't surge
  const shortCvdDiv = shortHit?.type === 'sweep' && (cvd.d5 || 0) < 50;

  // ── Checks ─────────────────────────────────────────────────────────
  const liqLong = [
    { label: `${typeLabel(longHit?.type||'')} ${longHit?.levelName||''}`, ok: !!longHit, critical: true },
    { label: longHit?.type==='breakout' ? 'פריצה מעלה' : longHit?.type==='approaching' ? 'מתקרב לרמה' : 'מחיר מעל רמה', ok: !!longHit && (longHit.type==='breakout' ? price > longHit.level + 0.5 : longHit.type==='approaching' ? price > longHit.level && price - longHit.level <= 8 : price > longHit.level), critical: true },
    { label: 'Delta > +50',  ok: (bar.delta || 0) > 50, critical: true },
    ...(longHit?.type === 'sweep' ? [
      { label: 'Wick ≥ 40%', ok: longWickRatio >= 0.4, critical: true },
      { label: 'CVD Divergence', ok: longCvdDiv, critical: true },
    ] : []),
    { label: 'Vol > 1.1x',   ok: longHit ? longHit.relVol > 1.1 : relVol > 1.1, critical: false },
    { label: 'נר היפוך',     ok: cp.bull_engulf || cp.bar0 === 'HAMMER' || cp.bar0 === 'BULL_STRONG', critical: false },
  ];
  const liqShort = [
    { label: `${typeLabel(shortHit?.type||'')} ${shortHit?.levelName||''}`, ok: !!shortHit, critical: true },
    { label: shortHit?.type==='breakout' ? 'פריצה מטה' : shortHit?.type==='approaching' ? 'מתקרב לרמה' : 'מחיר מתחת רמה', ok: !!shortHit && (shortHit.type==='breakout' ? price < shortHit.level - 0.5 : shortHit.type==='approaching' ? price < shortHit.level && shortHit.level - price <= 8 : price < shortHit.level), critical: true },
    { label: 'Delta < -50',   ok: (bar.delta || 0) < -50, critical: true },
    ...(shortHit?.type === 'sweep' ? [
      { label: 'Wick ≥ 40%', ok: shortWickRatio >= 0.4, critical: true },
      { label: 'CVD Divergence', ok: shortCvdDiv, critical: true },
    ] : []),
    { label: 'Vol > 1.1x',    ok: shortHit ? shortHit.relVol > 1.1 : relVol > 1.1, critical: false },
    { label: 'נר היפוך',      ok: cp.bear_engulf || cp.bar0 === 'SHOOTING_STAR' || cp.bar0 === 'BEAR_STRONG', critical: false },
  ];

  // ── Score ──────────────────────────────────────────────────────────
  const score = (checks: { ok: boolean; critical: boolean }[]) => {
    const criticalAll = checks.filter(c => c.critical);
    const criticalOk = criticalAll.filter(c => c.ok).length;
    const allOk = checks.filter(c => c.ok).length;
    if (criticalOk < criticalAll.length) return Math.round(criticalOk / criticalAll.length * 40);
    return Math.round(45 + (allOk / checks.length) * 55);
  };

  const longScore = score(liqLong);
  const shortScore = score(liqShort);

  // ── Entry/Stop/C1/C2/C3 ──────────────────────────────────────────
  const MAX_STOP_PTS = 8;
  const MIN_STOP_PTS = 3;
  const calcLevels = (dir: 'long' | 'short', hit: SetupHit | null) => {
    if (!hit) return { entry: 0, stop: 0, c1: 0, c2: 0, c3: 0, riskPts: 0, stopTooWide: false };
    const L = dir === 'long';
    const entry = hit.type === 'sweep'
      ? (L ? hit.bar.h + 0.25 : hit.bar.l - 0.25)
      : price;
    let stop = L ? hit.bar.l - 0.25 : hit.bar.h + 0.25;
    let risk = Math.abs(entry - stop);
    // Auto-expand stop if too narrow
    if (risk < MIN_STOP_PTS) {
      stop = L ? entry - MIN_STOP_PTS : entry + MIN_STOP_PTS;
      risk = MIN_STOP_PTS;
    }
    const stopTooWide = risk > MAX_STOP_PTS;
    const c1 = L ? entry + risk : entry - risk;
    const c2 = L ? entry + risk * 2 : entry - risk * 2;
    const woodi = live.woodi || {} as any;
    const c3 = L
      ? (woodi.r1 && woodi.r1 > entry + risk * 2 ? woodi.r1 : entry + risk * 3)
      : (woodi.s1 && woodi.s1 < entry - risk * 2 ? woodi.s1 : entry - risk * 3);
    return { entry, stop, c1, c2, c3, riskPts: Math.round(risk * 4) / 4, stopTooWide };
  };

  // ── Opportunity ────────────────────────────────────────────────────
  // ── Stop validation at setup level — reject if risk > MAX_STOP_PTS ──
  const longLevels = longHit ? calcLevels('long', longHit) : null;
  const shortLevels = shortHit ? calcLevels('short', shortHit) : null;
  const longValid = longLevels && !longLevels.stopTooWide;
  const shortValid = shortLevels && !shortLevels.stopTooWide;

  const bestDir: 'long' | 'short' | 'none' =
    (longScore >= 80 && longValid) ? 'long' :
    (shortScore >= 80 && shortValid) ? 'short' :
    (longScore >= 60 && longValid) ? 'long' :
    (shortScore >= 60 && shortValid) ? 'short' : 'none';

  const bestHit = bestDir === 'long' ? longHit : bestDir === 'short' ? shortHit : null;
  const bestLevels = bestDir === 'long' ? longLevels : bestDir === 'short' ? shortLevels : null;
  const bestScore = bestDir === 'long' ? longScore : bestDir === 'short' ? shortScore : 0;

  // ── Forked Evaluation — day-type-aware pass/fail ──────────────────
  const dayType = ((live as any)?.day?.type || '').toUpperCase();
  const isTrend = dayType === 'TREND' || dayType === 'TREND_DAY';
  const sortedForEval = [...candles].sort((a, b) => b.ts - a.ts);

  let setupEval: SetupEvalResult | null = null;
  if (bestDir !== 'none' && bestHit) {
    setupEval = isTrend
      ? evaluate_trend_setup(bestHit, bestDir, live, sortedForEval)
      : evaluate_range_setup(bestHit, bestDir, live, sortedForEval);
  }

  // ── Building setups — expose raw hits for "BUILDING NOW" tracker ──
  const buildingCandidates: { dir: 'long'|'short'; hit: SetupHit; score: number; levels: any; eval: SetupEvalResult | null }[] = [];
  for (const side of ['long', 'short'] as const) {
    const hit = side === 'long' ? longHit : shortHit;
    const sc = side === 'long' ? longScore : shortScore;
    const lv = side === 'long' ? longLevels : shortLevels;
    if (hit && hit.type === 'sweep') {
      let ev: SetupEvalResult | null = null;
      try {
        ev = isTrend
          ? evaluate_trend_setup(hit, side, live, sortedForEval)
          : evaluate_range_setup(hit, side, live, sortedForEval);
      } catch {}
      buildingCandidates.push({ dir: side, hit, score: sc, levels: lv, eval: ev });
    }
  }

  return {
    long: { checks: liqLong, score: longScore, sweep: longHit },
    short: { checks: liqShort, score: shortScore, sweep: shortHit },
    opportunity: bestDir,
    opportunityScore: bestScore,
    opportunitySweep: bestHit,
    opportunityLevels: bestLevels,
    setupEval,
    dayType,
    buildingCandidates,
  };
}

// ── Setup Entry Card — כרטיס כניסה ראשי ─────────────────────────────────────
function SetupEntryCard({ setup, dir, levels, live }: {
  setup: any; dir: 'long'|'short'; levels: any; live: MarketData|null;
}) {
  if (!setup || !levels) return null;
  const L       = dir === 'long';
  const col     = setup.col;
  const price   = live?.price || 0;
  const pot     = levels.potential;
  const checks  = L ? setup.long.checks : setup.short.checks;
  const score   = L ? setup.long.score  : setup.short.score;
  const criticalFail = checks.filter((c:any) => c.critical && !c.ok);

  // החלטה: כנס / חכה / דלג
  let decision: 'ENTER' | 'WAIT' | 'SKIP';
  let decisionText: string;
  let decisionSub: string;
  let decisionCol: string;

  if (criticalFail.length > 0) {
    decision = 'SKIP';
    decisionText = 'דלג';
    decisionSub  = `חסר: ${criticalFail[0].label}`;
    decisionCol  = '#ef5350';
  } else if (!pot?.valid) {
    decision = 'SKIP';
    decisionText = 'פוטנציאל נמוך';
    decisionSub  = pot?.reason || 'T1 < 10 נקודות';
    decisionCol  = '#ef5350';
  } else if (score >= 80) {
    decision = 'ENTER';
    decisionText = 'כנס עכשיו';
    decisionSub  = `${score}% תנאים עברו`;
    decisionCol  = '#22c55e';
  } else if (score >= 60) {
    decision = 'WAIT';
    decisionText = 'חכה לאישור';
    decisionSub  = `${score}% — צריך עוד אישור`;
    decisionCol  = '#f59e0b';
  } else {
    decision = 'SKIP';
    decisionText = 'דלג';
    decisionSub  = `רק ${score}% תנאים`;
    decisionCol  = '#ef5350';
  }

  return (
    <div style={{ background:'#0a0e1a', border:`2px solid ${decisionCol}44`, borderRadius:10, overflow:'hidden' }}>

      {/* Header — החלטה + win rate */}
      <div style={{ background:`${decisionCol}18`, padding:'10px 14px', borderBottom:`1px solid ${decisionCol}33` }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
          <div>
            <div style={{ fontSize:14, color:`${col}`, fontWeight:700, marginBottom:2 }}>
              {setup.name} {L ? '▲ LONG' : '▼ SHORT'}
            </div>
            <div style={{ fontSize:14, color:'#6b7280' }}>{decisionSub}</div>
          </div>
          <div style={{ fontSize:20, fontWeight:900, color:decisionCol, letterSpacing:-0.5 }}>
            {decisionText}
          </div>
        </div>
        {/* Win Rate + Delta + Volume */}
        <div style={{ display:'flex', gap:8, marginTop:8 }}>
          <div style={{ background:'#0a0e1a', borderRadius:5, padding:'4px 8px', textAlign:'center', flex:1 }}>
            <div style={{ fontSize:14, color:'#4a5568' }}>Win Rate</div>
            <div style={{ fontSize:14, fontWeight:800, color:col }}>{setup.base}%</div>
          </div>
          <div style={{ background:'#0a0e1a', borderRadius:5, padding:'4px 8px', textAlign:'center', flex:1 }}>
            <div style={{ fontSize:14, color:'#4a5568' }}>Delta</div>
            <div style={{ fontSize:14, fontWeight:800, color:(live?.bar?.delta||0)>=0?'#22c55e':'#ef5350', fontFamily:'monospace' }}>
              {(live?.bar?.delta||0)>0?'+':''}{live?.bar?.delta||0}
            </div>
          </div>
          <div style={{ background:'#0a0e1a', borderRadius:5, padding:'4px 8px', textAlign:'center', flex:1 }}>
            <div style={{ fontSize:14, color:'#4a5568' }}>Vol</div>
            <div style={{ fontSize:14, fontWeight:800, color:((live as any)?.volume_context?.rel_vol||1)>1.2?'#22c55e':'#4a5568', fontFamily:'monospace' }}>
              {((live as any)?.volume_context?.rel_vol||1).toFixed(1)}x
            </div>
          </div>
        </div>
      </div>

      {/* רמות כניסה */}
      {decision !== 'SKIP' && levels.entry > 0 && (
        <div style={{ padding:'10px 14px', borderBottom:`1px solid #1e2738` }}>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:8 }}>
            <div style={{ background:'#1e2738', borderRadius:6, padding:'6px 10px' }}>
              <div style={{ fontSize:14, color:'#4a5568', marginBottom:2 }}>כניסה</div>
              <div style={{ fontSize:14, fontWeight:800, color:'#f0f6fc', fontFamily:'monospace' }}>{(levels.entry||0).toFixed(2)}</div>
            </div>
            <div style={{ background:'#1e2738', borderRadius:6, padding:'6px 10px' }}>
              <div style={{ fontSize:14, color:'#ef5350', marginBottom:2 }}>✕ סטופ</div>
              <div style={{ fontSize:14, fontWeight:800, color:'#ef5350', fontFamily:'monospace' }}>{(levels.stop||0).toFixed(2)}</div>
              <div style={{ fontSize:14, color:'#4a5568' }}>−{pot?.risk_pts}pt / −${(pot?.risk_pts||0)*5}</div>
            </div>
          </div>

          {/* פוטנציאל */}
          {pot?.valid && (
            <div style={{ display:'grid', gridTemplateColumns:'repeat(3, minmax(0, 1fr))', gap:6 }}>
              {[
                { label:'T1 · C1', pts:pot.t1_pts, usd:pot.t1_usd, rr:pot.rr1, col:'#22c55e', price:levels.t1 },
                { label:'T2 · C2', pts:pot.t2_pts, usd:pot.t2_usd, rr:pot.rr2, col:'#16a34a', price:levels.t2 },
                { label:'T3 · Run', pts:pot.t3_pts, usd:pot.t3_usd, rr:null, col:'#86efac', price:levels.t3stop },
              ].map(t => (
                <div key={t.label} style={{ background:`${t.col}11`, border:`1px solid ${t.col}33`, borderRadius:6, padding:'5px 6px', textAlign:'center' }}>
                  <div style={{ fontSize:14, color:t.col, fontWeight:700 }}>{t.label}</div>
                  <div style={{ fontSize:14, fontWeight:800, color:t.col, fontFamily:'monospace' }}>{(t.price||0).toFixed(2)}</div>
                  <div style={{ fontSize:14, color:'#4a5568' }}>+{t.pts}pt</div>
                  <div style={{ fontSize:14, fontWeight:700, color:t.col }}>+${t.usd}</div>
                  {t.rr && <div style={{ fontSize:14, color:'#4a5568' }}>R:R 1:{t.rr}</div>}
                </div>
              ))}
            </div>
          )}

          {/* אזהרת פוטנציאל נמוך */}
          {!pot?.valid && pot?.reason && (
            <div style={{ background:'#ef535011', border:'1px solid #ef535033', borderRadius:6, padding:'6px 10px', fontSize:14, color:'#ef5350', textAlign:'center' }}>
              ⚠ {pot.reason}
            </div>
          )}
        </div>
      )}

      {/* תנאים */}
      <div style={{ padding:'8px 14px' }}>
        <div style={{ display:'flex', flexWrap:'wrap', gap:'4px 8px' }}>
          {checks.map((c:any) => (
            <span key={c.label} style={{
              fontSize:14, padding:'2px 6px', borderRadius:4, fontWeight:700,
              background: c.ok ? (c.critical?'#22c55e22':'#22c55e11') : (c.critical?'#ef535022':'#1e2738'),
              color: c.ok ? '#22c55e' : (c.critical ? '#ef5350' : '#4a5568'),
              border: `1px solid ${c.ok?(c.critical?'#22c55e44':'#22c55e22'):(c.critical?'#ef535044':'#1e2738')}`,
            }}>
              {c.ok ? '✓' : c.critical ? '✗' : '○'} {c.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}


// ── Pattern Detection — זיהוי תבניות גרף על 50 נרות ─────────────────────────
interface PatternResult {
  id: string;
  name: string;
  nameHeb: string;
  direction: 'long' | 'short' | 'neutral';
  confidence: number;        // 0-100
  keyLevel: number;          // רמת פריצה/תמיכה
  breakoutLevel?: number;    // נקודת כניסה
  stopLevel?: number;        // סטופ מומלץ
  description: string;       // הסבר קצר
  col: string;
  barIndex?: number;         // איפה התבנית התחילה
}

function detectPatterns(candles: Candle[]): PatternResult[] {
  const results: PatternResult[] = [];
  if (!candles || candles.length < 10) return results;

  const c = [...candles].reverse(); // חדש → ישן → הופך לישן → חדש
  const n = c.length;

  // ── עזרים ────────────────────────────────────────────────────────────────
  const highs  = c.map(x => x.h);
  const lows   = c.map(x => x.l);
  const closes = c.map(x => x.c);
  const deltas = c.map(x => x.delta || 0);

  // מוצא שיא/שפל מקומי בחלון
  const isLocalHigh = (i:number, w=3) => {
    const start = Math.max(0,i-w), end = Math.min(n-1,i+w);
    for(let j=start;j<=end;j++) if(j!==i && highs[j]>highs[i]) return false;
    return true;
  };
  const isLocalLow = (i:number, w=3) => {
    const start = Math.max(0,i-w), end = Math.min(n-1,i+w);
    for(let j=start;j<=end;j++) if(j!==i && lows[j]<lows[i]) return false;
    return true;
  };

  // אוסף שיאים/שפלים מקומיים
  const localHighs: number[] = [];
  const localLows:  number[] = [];
  for(let i=3;i<n-3;i++){
    if(isLocalHigh(i)) localHighs.push(i);
    if(isLocalLow(i))  localLows.push(i);
  }

  const price = closes[n-1];
  const tolerance = price * 0.001; // 0.1% tolerance לרמות

  // ── 1. DOUBLE BOTTOM — רצפה כפולה ─────────────────────────────────────────
  if(localLows.length >= 2){
    const recent = localLows.slice(-4);
    for(let a=0;a<recent.length-1;a++){
      for(let b=a+1;b<recent.length;b++){
        const i1=recent[a], i2=recent[b];
        const l1=lows[i1], l2=lows[i2];
        if(Math.abs(l1-l2) < tolerance*3 && i2-i1 >= 5){
          // בדוק שיש שיא בין השניים
          const midHigh = Math.max(...highs.slice(i1,i2));
          const neckline = midHigh;
          const depth = neckline - Math.min(l1,l2);
          const conf = Math.min(95, 60 + (depth/price)*500 + (i2-i1)*1.5);
          // בדוק נפח — buy delta צריך לגדול בשפל השני
          const vol2 = deltas.slice(Math.max(0,i2-2),i2+2).reduce((a,b)=>a+b,0);
          const confAdj = vol2 > 0 ? conf + 10 : conf - 5;
          results.push({
            id:'double_bottom', name:'Double Bottom', nameHeb:'רצפה כפולה',
            direction:'long', confidence:Math.min(95,Math.round(confAdj)),
            keyLevel:Math.min(l1,l2), breakoutLevel:neckline+0.25,
            stopLevel:Math.min(l1,l2)-0.5,
            description:`שני שפלים ב-${Math.min(l1,l2).toFixed(2)} | פריצה מעל ${neckline.toFixed(2)}`,
            col:'#22c55e', barIndex:i1,
          });
        }
      }
    }
  }

  // ── 2. DOUBLE TOP — קורת גג כפולה ─────────────────────────────────────────
  if(localHighs.length >= 2){
    const recent = localHighs.slice(-4);
    for(let a=0;a<recent.length-1;a++){
      for(let b=a+1;b<recent.length;b++){
        const i1=recent[a], i2=recent[b];
        const h1=highs[i1], h2=highs[i2];
        if(Math.abs(h1-h2) < tolerance*3 && i2-i1 >= 5){
          const midLow = Math.min(...lows.slice(i1,i2));
          const neckline = midLow;
          const depth = Math.max(h1,h2) - neckline;
          const conf = Math.min(95, 60 + (depth/price)*500 + (i2-i1)*1.5);
          const vol2 = deltas.slice(Math.max(0,i2-2),i2+2).reduce((a,b)=>a+b,0);
          const confAdj = vol2 < 0 ? conf + 10 : conf - 5;
          results.push({
            id:'double_top', name:'Double Top', nameHeb:'קורת גג כפולה',
            direction:'short', confidence:Math.min(95,Math.round(confAdj)),
            keyLevel:Math.max(h1,h2), breakoutLevel:neckline-0.25,
            stopLevel:Math.max(h1,h2)+0.5,
            description:`שני שיאים ב-${Math.max(h1,h2).toFixed(2)} | שבירה מתחת ${neckline.toFixed(2)}`,
            col:'#ef5350', barIndex:i1,
          });
        }
      }
    }
  }

  // ── 3. BULL FLAG — דגל שורי ──────────────────────────────────────────────
  if(n >= 15){
    // חפש עמוד: 5+ נרות עולים חזק
    for(let start=n-25;start<n-10;start++){
      if(start<0) continue;
      const poleEnd = start+5;
      const poleGain = closes[poleEnd]-closes[start];
      const poleRange = Math.max(...highs.slice(start,poleEnd)) - Math.min(...lows.slice(start,poleEnd));
      if(poleGain < price*0.003) continue; // עמוד קטן מ-0.3%

      // חפש קונסולידציה אחרי העמוד
      const flagBars = closes.slice(poleEnd, Math.min(poleEnd+10, n));
      if(flagBars.length < 4) continue;
      const flagHigh = Math.max(...highs.slice(poleEnd,poleEnd+10));
      const flagLow  = Math.min(...lows.slice(poleEnd,poleEnd+10));
      const flagRange = flagHigh - flagLow;

      if(flagRange < poleRange*0.5 && flagRange > 0){
        // דגל — קונסולידציה צרה אחרי עמוד
        const lastClose = closes[n-1];
        const breakout = flagHigh;
        const isNearBreakout = lastClose > flagHigh*0.998;
        const conf = Math.min(90, 55 + (poleGain/poleRange)*20 + (isNearBreakout?15:0));
        results.push({
          id:'bull_flag', name:'Bull Flag', nameHeb:'דגל שורי',
          direction:'long', confidence:Math.round(conf),
          keyLevel:flagHigh, breakoutLevel:flagHigh+0.25,
          stopLevel:flagLow-0.25,
          description:`עמוד +${poleGain.toFixed(1)}pts | דגל ${flagRange.toFixed(1)}pts | פריצה מעל ${flagHigh.toFixed(2)}`,
          col:'#22c55e', barIndex:start,
        });
        break;
      }
    }
  }

  // ── 4. BEAR FLAG — דגל דובי ──────────────────────────────────────────────
  if(n >= 15){
    for(let start=n-25;start<n-10;start++){
      if(start<0) continue;
      const poleEnd = start+5;
      const poleDrop = closes[start]-closes[poleEnd];
      const poleRange = Math.max(...highs.slice(start,poleEnd)) - Math.min(...lows.slice(start,poleEnd));
      if(poleDrop < price*0.003) continue;

      const flagBars = closes.slice(poleEnd, Math.min(poleEnd+10, n));
      if(flagBars.length < 4) continue;
      const flagHigh = Math.max(...highs.slice(poleEnd,poleEnd+10));
      const flagLow  = Math.min(...lows.slice(poleEnd,poleEnd+10));
      const flagRange = flagHigh - flagLow;

      if(flagRange < poleRange*0.5 && flagRange > 0){
        const lastClose = closes[n-1];
        const breakout = flagLow;
        const isNearBreakout = lastClose < flagLow*1.002;
        const conf = Math.min(90, 55 + (poleDrop/poleRange)*20 + (isNearBreakout?15:0));
        results.push({
          id:'bear_flag', name:'Bear Flag', nameHeb:'דגל דובי',
          direction:'short', confidence:Math.round(conf),
          keyLevel:flagLow, breakoutLevel:flagLow-0.25,
          stopLevel:flagHigh+0.25,
          description:`עמוד -${poleDrop.toFixed(1)}pts | דגל ${flagRange.toFixed(1)}pts | שבירה מתחת ${flagLow.toFixed(2)}`,
          col:'#ef5350', barIndex:start,
        });
        break;
      }
    }
  }

  // ── 5. HEAD AND SHOULDERS ─────────────────────────────────────────────────
  if(localHighs.length >= 3){
    const h = localHighs.slice(-5);
    for(let i=0;i<h.length-2;i++){
      const [iL,iH,iR] = [h[i],h[i+1],h[i+2]];
      const [hL,hH,hR] = [highs[iL],highs[iH],highs[iR]];
      if(hH > hL && hH > hR && Math.abs(hL-hR) < tolerance*4 && iH-iL>=4 && iR-iH>=4){
        const neckL = Math.min(...lows.slice(iL,iH));
        const neckR = Math.min(...lows.slice(iH,iR));
        const neckline = (neckL+neckR)/2;
        const depth = hH - neckline;
        const target = neckline - depth;
        const conf = Math.min(88, 65 + (depth/price)*400);
        results.push({
          id:'head_shoulders', name:'Head & Shoulders', nameHeb:'ראש וכתפיים',
          direction:'short', confidence:Math.round(conf),
          keyLevel:neckline, breakoutLevel:neckline-0.25,
          stopLevel:hR+0.5,
          description:`ראש ${hH.toFixed(2)} | Neckline ${neckline.toFixed(2)} | Target ${target.toFixed(2)}`,
          col:'#f59e0b', barIndex:iL,
        });
      }
    }
  }

  // ── 6. CUP AND HANDLE ────────────────────────────────────────────────────
  if(n >= 20 && localLows.length >= 1){
    const cupStart = Math.max(0, n-30);
    const cupHigh  = Math.max(...highs.slice(cupStart, cupStart+5));
    const cupLow   = Math.min(...lows.slice(cupStart+3, n-5));
    const cupRight = Math.max(...highs.slice(n-8, n-2));
    const depth    = cupHigh - cupLow;

    if(depth > price*0.002 && Math.abs(cupRight-cupHigh) < tolerance*5){
      // ידית — ירידה קטנה מהשפה הימנית
      const handleLow  = Math.min(...lows.slice(n-5,n));
      const handleDrop = cupRight - handleLow;
      if(handleDrop > 0 && handleDrop < depth*0.4){
        const conf = Math.min(88, 60 + (depth/price)*300);
        results.push({
          id:'cup_handle', name:'Cup & Handle', nameHeb:'כוס וידית',
          direction:'long', confidence:Math.round(conf),
          keyLevel:cupRight, breakoutLevel:cupRight+0.25,
          stopLevel:handleLow-0.25,
          description:`עומק ${depth.toFixed(1)}pts | שפה ${cupRight.toFixed(2)} | ידית ${handleDrop.toFixed(1)}pts`,
          col:'#60a5fa', barIndex:cupStart,
        });
      }
    }
  }

  // ── 7. HIGHER HIGHS / LOWER LOWS — מבנה מגמה ────────────────────────────
  if(localHighs.length >= 3 && localLows.length >= 3){
    const recentH = localHighs.slice(-3).map(i=>highs[i]);
    const recentL = localLows.slice(-3).map(i=>lows[i]);
    const hhhl = recentH[0]<recentH[1] && recentH[1]<recentH[2] && recentL[0]<recentL[1] && recentL[1]<recentL[2];
    const lhll = recentH[0]>recentH[1] && recentH[1]>recentH[2] && recentL[0]>recentL[1] && recentL[1]>recentL[2];
    if(hhhl){
      results.push({
        id:'hh_hl', name:'HH/HL Structure', nameHeb:'מבנה עולה HH/HL',
        direction:'long', confidence:78,
        keyLevel:recentL[2], breakoutLevel:recentH[2]+0.25,
        stopLevel:recentL[2]-0.5,
        description:`שיאים ושפלים עולים — מגמת עלייה מבנית`,
        col:'#22c55e',
      });
    } else if(lhll){
      results.push({
        id:'lh_ll', name:'LH/LL Structure', nameHeb:'מבנה יורד LH/LL',
        direction:'short', confidence:78,
        keyLevel:recentH[2], breakoutLevel:recentL[2]-0.25,
        stopLevel:recentH[2]+0.5,
        description:`שיאים ושפלים יורדים — מגמת ירידה מבנית`,
        col:'#ef5350',
      });
    }
  }

  // מיין לפי confidence
  return results.sort((a,b)=>b.confidence-a.confidence).slice(0,4);
}

// ── חישוב רמות סטאפ ────────────────────────────────────────────────────────
function calcSetupLevels(id:string, live:MarketData|null, dir:'long'|'short') {
  if(!live) return null;
  const p    = live.price||0;
  const bar  = live.bar||{} as any;
  const vwap = live.vwap||{} as any;
  const sess = live.session||{} as any;
  const prof = live.profile||{} as any;
  const woodi= live.woodi||{} as any;
  const lev  = live.levels||{} as any;
  const L    = dir==='long';

  let detect=0, verify=0, entry=0, stop=0, t1=0, t2=0, t3stop=0;

  if(id==='Liq Sweep'){
    // מצא את הרמה הקרובה ביותר שנשברה
    const candidates = [lev.prev_high, lev.prev_low, lev.overnight_high, lev.overnight_low]
      .filter(v=>v&&v>0);
    const swept = candidates.find(l => L ? (bar.l||p)<l-0.5 : (bar.h||p)>l+0.5) || (L?p-2:p+2);
    detect = swept;
    verify = L ? swept + 0.5 : swept - 0.5;  // חזרה מעל/מתחת
    entry  = L ? swept + 1.0 : swept - 1.0;  // כניסה אחרי אישור
    stop   = L ? (bar.l||swept) - 0.5 : (bar.h||swept) + 0.5;
    const risk = Math.abs(entry-stop);
    t1     = L ? entry+risk   : entry-risk;
    t2     = L ? entry+risk*2 : entry-risk*2;
    t3stop = L ? (woodi.r1||lev.prev_high||entry+risk*3) : (woodi.s1||lev.prev_low||entry-risk*3);

  } else if(id==='VWAP Pullback'){
    const vwapV = vwap.value||p;
    detect = vwapV;
    verify = L ? vwapV+0.25 : vwapV-0.25;
    entry  = L ? vwapV+0.5  : vwapV-0.5;
    stop   = L ? vwapV-1.5  : vwapV+1.5;
    const risk = Math.abs(entry-stop);
    t1     = L ? entry+risk   : entry-risk;
    t2     = L ? entry+risk*2 : entry-risk*2;
    t3stop = L ? (woodi.r1||entry+risk*3) : (woodi.s1||entry-risk*3);

  } else if(id==='IB Breakout'){
    const ib = L ? (sess.ibh||p+2) : (sess.ibl||p-2);
    detect = ib;
    verify = L ? ib-0.5 : ib+0.5;    // חזרה לבדוק
    entry  = L ? ib+0.25 : ib-0.25;  // כניסה על הבדיקה
    stop   = L ? ib-1.5  : ib+1.5;
    const risk = Math.abs(entry-stop);
    t1     = L ? entry+risk   : entry-risk;
    t2     = L ? entry+risk*2 : entry-risk*2;
    t3stop = L ? (woodi.r1||lev.prev_high||t2) : (woodi.s1||lev.prev_low||t2);

  } else if(id==='CCI Turbo'){
    const poc = prof.poc||p;
    detect = poc;
    verify = L ? poc+0.5 : poc-0.5;
    entry  = L ? poc+1.0 : poc-1.0;
    stop   = L ? (bar.l||poc-3)-0.25 : (bar.h||poc+3)+0.25;
    const risk = Math.abs(entry-stop);
    t1     = L ? entry+risk   : entry-risk;
    t2     = L ? entry+risk*2 : entry-risk*2;
    t3stop = L ? (woodi.r1||t2) : (woodi.s1||t2);
  }

  const potential = calcPotential(entry, stop, dir, woodi, lev);
  // עדכן T1/T2 מהpotential (מחושב נכון)
  if(potential){ t1 = potential.t1; t2 = potential.t2; t3stop = potential.t3; }

  return {detect, verify, entry, stop, t1, t2, t3stop, potential};
}

// ── Live LONG/SHORT probability ───────────────────────────────────────────────
function calcProbability(live: MarketData | null): { long: number; short: number } {
  if (!live) return { long: 50, short: 50 };

  const cvd    = live.cvd    || {} as any;
  const vwap   = live.vwap   || {} as any;
  const prof   = live.profile|| {} as any;
  const woodi  = live.woodi  || {} as any;
  const of2    = live.order_flow || {} as any;
  const bar    = live.bar    || {} as any;
  const sess   = live.session|| {} as any;

  let longScore  = 0;
  let shortScore = 0;

  // CVD Trend (משקל גבוה)
  if (cvd.trend === 'BULLISH')  longScore  += 20;
  if (cvd.trend === 'BEARISH')  shortScore += 20;
  if ((cvd.d20 || 0) > 200)    longScore  += 10;
  if ((cvd.d20 || 0) < -200)   shortScore += 10;
  if ((cvd.d5  || 0) > 50)     longScore  += 8;
  if ((cvd.d5  || 0) < -50)    shortScore += 8;
  if ((bar.delta || 0) > 100)   longScore  += 6;
  if ((bar.delta || 0) < -100)  shortScore += 6;

  // VWAP
  if (vwap.above)             longScore  += 12;
  else                        shortScore += 12;
  if (vwap.pullback)          longScore  += 8;

  // Profile
  if (prof.above_poc)         longScore  += 8;
  else                        shortScore += 8;
  if (prof.in_va) { longScore += 3; shortScore += 3; }

  // Woodi PP
  if (woodi.above_pp)         longScore  += 6;
  else                        shortScore += 6;

  // Order Flow
  if (of2.absorption_bull)    longScore  += 10;
  if (of2.liq_sweep || of2.liq_sweep_long) longScore += 8;
  if (of2.liq_sweep_short)    shortScore += 8;
  if ((of2.imbalance_bull||0) > 0) longScore  += 5;
  if ((of2.imbalance_bear||0) > 0) shortScore += 5;

  // Session
  if (sess.phase === 'RTH' || sess.phase === 'AM_SESSION') {
    longScore += 2; shortScore += 2;
  }

  const total = longScore + shortScore || 1;
  const longPct  = Math.round((longScore  / total) * 100);
  const shortPct = 100 - longPct;
  return { long: longPct, short: shortPct };
}

// ── Traffic Light — רמזור קלאסי אנכי ─────────────────────────────────────────
function TrafficLight({ score, live }: { score: number; live: MarketData | null }) {
  const isGreen  = score >= 7;
  const isYellow = score >= 5 && score < 7;
  const isRed    = score < 5;
  const { long, short } = calcProbability(live);
  const bias = long > short ? 'LONG' : short > long ? 'SHORT' : 'NEUTRAL';
  const biasCol = bias === 'LONG' ? G : bias === 'SHORT' ? R : Y;

  const light = (on: boolean, color: string) => ({
    width: 28, height: 28, borderRadius: '50%',
    background: on ? color : '#1a1a2e',
    border: `2px solid ${on ? color : '#2d3a4a'}`,
    boxShadow: on ? `0 0 14px ${color}, 0 0 4px ${color}` : 'none',
    transition: 'all .4s',
  });

  const biasWR = bias==='LONG' ? long : bias==='SHORT' ? short : 50;

  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:5, flexShrink:0 }}>
      {/* Traffic light */}
      <div style={{ background:'#111827', border:'2px solid #2d3a4a', borderRadius:14, padding:'8px 7px', display:'flex', flexDirection:'column', gap:7, alignItems:'center', width:46 }}>
        <div style={light(isRed,    R)} />
        <div style={light(isYellow, Y)} />
        <div style={light(isGreen,  G)} />
      </div>

      {/* הצגת המלצה + אחוזי הצלחה */}
      <div style={{ width:46, background:'#111827', border:`1px solid ${biasCol}44`, borderRadius:8, padding:'6px 4px', display:'flex', flexDirection:'column', gap:3, alignItems:'center' }}>
        {/* Bias */}
        <div style={{ fontSize:14, fontWeight:800, color:biasCol }}>{bias}</div>
        {/* אחוז הצלחה */}
        <div style={{ fontSize:16, fontWeight:800, color:biasCol, fontFamily:'monospace', lineHeight:1 }}>{biasWR}%</div>
        {/* Bar */}
        <div style={{ width:'100%', height:4, background:'#1e2738', borderRadius:2, overflow:'hidden' }}>
          <div style={{ width:`${biasWR}%`, height:'100%', background:biasCol, borderRadius:2, transition:'width .5s' }} />
        </div>
        {/* L / S mini */}
        <div style={{ display:'flex', justifyContent:'space-between', width:'100%', fontSize:14, marginTop:1 }}>
          <span style={{ color:G, fontWeight:700 }}>L {long}%</span>
          <span style={{ color:R, fontWeight:700 }}>S {short}%</span>
        </div>
      </div>
    </div>
  );
}

// ── Mini Traffic Light — 3 נקודות קטנות לאינדיקטור ───────────────────────────
function MiniLight({ col }: { col: string }) {
  const isG = col === G;
  const isY = col === Y;
  const isR = col === R;
  const dot = (on: boolean, color: string) => ({
    width: 8, height: 8, borderRadius: '50%',
    background: on ? color : '#1e2738',
    boxShadow: on ? `0 0 5px ${color}` : 'none',
    transition: 'all .3s',
    flexShrink: 0 as const,
  });
  return (
    <div style={{ display:'flex', gap:3, alignItems:'center', flexShrink:0 }}>
      <div style={dot(isR, R)} />
      <div style={dot(isY, Y)} />
      <div style={dot(isG, G)} />
    </div>
  );
}

// ── Zone A: Top Bar ───────────────────────────────────────────────────────────
function TopBar({ live, connected, onAskAI, aiLoading, systemOn, onToggleSystem, newsGuard, entryMode }:{ live:MarketData|null; connected:boolean; onAskAI:()=>void; aiLoading:boolean; systemOn:boolean; onToggleSystem:()=>void; newsGuard?:{ state:string; available:boolean; active_event:any; events_today:number; events:any[] }; entryMode?:{mode:string;gates?:any}|null }) {
  const [time, setTime] = useState('');
  useEffect(() => {
    const t = setInterval(() => {
      setTime(new Date().toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false, timeZone:'America/New_York' }));
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const price = live?.price ?? 0;
  const phase = live?.session?.phase ?? '—';
  const phaseCol = phase === 'RTH' ? G : phase === 'OVERNIGHT' ? Y : '#60a5fa';

  return (
    <div style={{ display:'flex', alignItems:'center', gap:16, padding:'10px 16px', background:'#111827', borderRadius:8, border:'1px solid #1e2738', flexWrap:'wrap' }}>
      <span style={{ fontSize:16, fontWeight:800, letterSpacing:2, color:'#f0f6fc', flexShrink:0 }}>MES<span style={{ color:'#f6c90e' }}>26</span></span>
      <span style={{ fontSize:28, fontWeight:800, fontFamily:'monospace', color:'#f0f6fc', flexShrink:0 }}>{price ? price.toFixed(2) : '—'}</span>
      <span style={{ fontSize:14, padding:'3px 10px', borderRadius:12, fontWeight:700, background:phaseCol+'22', color:phaseCol, border:`1px solid ${phaseCol}44` }}>{phase}</span>

      {/* MODE badge — SIM/LIVE */}
      {(() => {
        const mode = (live as any)?.mode || 'SIM';
        const isSim = mode === 'SIM';
        return <span style={{ fontSize:14, padding:'3px 10px', borderRadius:12, fontWeight:800,
          background: isSim ? '#22c55e22' : '#ef535022',
          color: isSim ? '#22c55e' : '#ef5350',
          border: `1px solid ${isSim ? '#22c55e44' : '#ef535044'}`,
        }}>{isSim ? '🟢 SIM' : '🔴 LIVE'}</span>;
      })()}

      {/* V6.5.2: Entry Mode badge */}
      {entryMode && (() => {
        const m = entryMode.mode;
        const isDemo = m === 'DEMO';
        return <span style={{ fontSize:12, padding:'2px 8px', borderRadius:10, fontWeight:700,
          background: isDemo ? '#f59e0b22' : '#4a556822',
          color: isDemo ? '#f59e0b' : '#6b7280',
          border: `1px solid ${isDemo ? '#f59e0b44' : '#4a556844'}`,
        }}>{isDemo ? '🧪 DEMO' : 'STRICT'}</span>;
      })()}

      {/* News Guard indicator */}
      {(() => {
        if (!newsGuard) return <span style={{ fontSize:14, padding:'3px 10px', borderRadius:12, fontWeight:700, background:'#22c55e22', color:'#22c55e', border:'1px solid #22c55e44' }}>News: OK</span>;
        if (newsGuard.state === 'PRE_NEWS_FREEZE') {
          const ev = newsGuard.active_event;
          return <span className="live-blink" style={{ fontSize:14, padding:'3px 10px', borderRadius:12, fontWeight:800, background:'#ef535022', color:'#ef5350', border:'1px solid #ef535044' }}>NEWS FREEZE{ev ? ` — ${ev.title}` : ''}</span>;
        }
        if (!newsGuard.available) {
          return <span style={{ fontSize:14, padding:'3px 10px', borderRadius:12, fontWeight:700, background:'#f59e0b22', color:'#f59e0b', border:'1px solid #f59e0b44' }}>News: N/A</span>;
        }
        // Find next event within 60min
        const nextEv = newsGuard.events?.find((ev: any) => {
          try {
            const etStr = new Date().toLocaleString('en-US', { timeZone: 'America/New_York' });
            const now = new Date(etStr);
            const [h, m] = ev.time_et.split(':').map(Number);
            const evTime = new Date(now);
            evTime.setHours(h, m, 0, 0);
            const diffMin = (evTime.getTime() - now.getTime()) / 60000;
            return diffMin > 0 && diffMin <= 60;
          } catch { return false; }
        });
        if (nextEv) {
          const etStr = new Date().toLocaleString('en-US', { timeZone: 'America/New_York' });
          const now = new Date(etStr);
          const [h, m] = nextEv.time_et.split(':').map(Number);
          const evTime = new Date(now);
          evTime.setHours(h, m, 0, 0);
          const minsUntil = Math.round((evTime.getTime() - now.getTime()) / 60000);
          return <span style={{ fontSize:14, padding:'3px 10px', borderRadius:12, fontWeight:700, background:'#f59e0b22', color:'#f59e0b', border:'1px solid #f59e0b44' }}>Next: {nextEv.title} in {minsUntil}m</span>;
        }
        return <span style={{ fontSize:14, padding:'3px 10px', borderRadius:12, fontWeight:700, background:'#22c55e22', color:'#22c55e', border:'1px solid #22c55e44' }}>News: OK</span>;
      })()}

      {/* כפתור AI on-demand */}
      <button onClick={onAskAI} disabled={aiLoading} style={{
        display:'flex', alignItems:'center', gap:6,
        padding:'6px 14px', borderRadius:8, fontSize:14, fontWeight:700,
        background: aiLoading ? '#1e2738' : '#7f77dd22',
        color: aiLoading ? '#4a5568' : '#7f77dd',
        border:`1px solid ${aiLoading ? '#2d3a4a' : '#7f77dd44'}`,
        cursor: aiLoading ? 'not-allowed' : 'pointer',
        fontFamily:'inherit', transition:'all .2s',
      }}>
        {aiLoading ? (
          <>
            <span style={{ display:'inline-block', width:10, height:10, borderRadius:'50%', border:'2px solid #4a5568', borderTopColor:'#7f77dd', animation:'spin 0.8s linear infinite' }} />
            מנתח...
          </>
        ) : (
          <>⚡ שאל AI עכשיו</>
        )}
      </button>

      <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:16 }}>
        <span style={{ fontSize:18, fontWeight:700, fontFamily:'monospace', color:'#f0f6fc' }}>{time}</span>
        <span style={{ fontSize:14, color:'#4a5568' }}>EST</span>
        <div style={{ display:'flex', alignItems:'center', gap:6 }}>
          <div style={{ width:8, height:8, borderRadius:'50%', background:connected&&systemOn?G:R, boxShadow:connected&&systemOn?`0 0 6px ${G}`:'none' }} className={connected&&systemOn?'live-blink':''} />
          <span style={{ fontSize:14, fontWeight:700, color:connected&&systemOn?G:R }}>{systemOn?(connected?'LIVE':'OFFLINE'):'OFF'}</span>
        </div>
        <button onClick={onToggleSystem} style={{
          padding:'4px 12px', borderRadius:6, fontSize:14, fontWeight:800,
          background: systemOn ? '#ef535022' : '#22c55e22',
          color: systemOn ? '#ef5350' : '#22c55e',
          border: `1px solid ${systemOn ? '#ef535044' : '#22c55e44'}`,
          cursor:'pointer', fontFamily:'inherit',
        }}>
          {systemOn ? '⏸ OFF' : '▶ ON'}
        </button>
      </div>
    </div>
  );
}

// ── Zone B: Main Score + Signal Panel ────────────────────────────────────────
function MainScore({ live, liveSetup, onAccept, onReject, accepted, newsGuard }:{ live:MarketData|null; liveSetup:any; onAccept:()=>void; onReject:()=>void; accepted:boolean; newsGuard?:{ state:string; available:boolean; active_event:any; events_today:number; events:any[] } }) {
  // Primary source: real-time calcSetups opportunity
  const opp = liveSetup?.opportunity || 'none';
  const oppScore = liveSetup?.opportunityScore || 0;
  const oppSweep = liveSetup?.opportunitySweep;
  const oppLevels = liveSetup?.opportunityLevels;

  // Map 0-100 score to 1-10 for display
  const score10 = Math.round(oppScore / 10);
  const { long: longPct, short: shortPct } = calcProbability(live);

  // AI signal as secondary
  const sig = live?.signal;

  // Determine direction and color
  const dir = opp === 'long' ? 'LONG' : opp === 'short' ? 'SHORT' : (sig?.direction === 'LONG' || sig?.direction === 'SHORT') ? sig.direction : 'NO_TRADE';
  const isActive = opp !== 'none' || (dir !== 'NO_TRADE' && (sig?.score ?? 0) >= 5);
  const col = dir === 'LONG' ? G : dir === 'SHORT' ? R : Y;
  const displayScore = opp !== 'none' ? score10 : (sig?.score ?? 0);

  return (
    <div style={{ background: isActive ? (dir==='LONG'?'#0d1f1a':'#1f0d0d') : '#111827', border:`1.5px solid ${isActive ? col+'44' : '#1e2738'}`, borderRadius:8, padding:14, minHeight:120 }}>
      <div style={{ display:'flex', alignItems:'center', gap:14 }}>
        <TrafficLight score={displayScore} live={live} />
        <div style={{ width:44, height:44, borderRadius:'50%', background:col+'18', border:`2px solid ${col}44`, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
          <span style={{ fontSize:20, fontWeight:800, color:col, fontFamily:'monospace' }}>{displayScore}</span>
        </div>
        <div style={{ flex:1 }}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:4 }}>
            <span style={{ fontSize:20, fontWeight:800, color:col }}>{dir === 'NO_TRADE' ? 'המתן' : dir}</span>
            {oppSweep && <span style={{ fontSize:14, padding:'2px 8px', borderRadius:10, background:col+'22', color:col }}>{oppSweep.levelName}</span>}
            {!oppSweep && sig?.setup && <span style={{ fontSize:14, padding:'2px 8px', borderRadius:10, background:col+'22', color:col }}>{sig.setup}</span>}
          </div>
          <div style={{ fontSize:14, color:'#4a5568', marginBottom:6 }}>
            {opp !== 'none' ? `${oppScore}% תנאים | L ${longPct}% S ${shortPct}%` : `L ${longPct}% · S ${shortPct}%`}
          </div>
          <div style={{ height:4, background:'#1e2738', borderRadius:2, overflow:'hidden' }}>
            <div style={{ width:`${opp!=='none' ? oppScore : Math.max(longPct,shortPct)}%`, height:'100%', background:col, borderRadius:2 }} />
          </div>
          {/* Forked eval result */}
          {liveSetup?.setupEval && (
            <div style={{ marginTop:4, fontSize:14, fontWeight:700, color: liveSetup.setupEval.pass ? G : '#f59e0b' }}>
              {liveSetup.setupEval.pass ? '✓' : '✗'} {liveSetup.setupEval.eval_type === 'trend' ? 'TREND' : 'RANGE'}: {liveSetup.setupEval.reason}
            </div>
          )}
          {/* News guard */}
          {newsGuard && newsGuard.state !== 'CLEAR' && (
            <div style={{ marginTop:4, padding:'4px 8px', borderRadius:4, fontSize:14, fontWeight:700,
              background: newsGuard.state === 'PRE_NEWS_FREEZE' ? '#ef535022' : '#f59e0b22',
              color: newsGuard.state === 'PRE_NEWS_FREEZE' ? R : Y,
              border: `1px solid ${newsGuard.state === 'PRE_NEWS_FREEZE' ? '#ef535044' : '#f59e0b44'}` }}>
              {newsGuard.state === 'PRE_NEWS_FREEZE' ? '⛔' : '⚡'} {newsGuard.state.replace(/_/g, ' ')}
              {newsGuard.active_event && ` — ${newsGuard.active_event.title} @ ${newsGuard.active_event.time_et}`}
            </div>
          )}
          {newsGuard && !newsGuard.available && (
            <div style={{ marginTop:4, fontSize:14, color:'#f59e0b', fontWeight:700 }}>
              ⚠ News guard unavailable
            </div>
          )}
        </div>
        {isActive && oppLevels && (
          <div style={{ textAlign:'right', flexShrink:0 }}>
            <div style={{ fontSize:14, color:'#4a5568', marginBottom:2 }}>כניסה / סטופ</div>
            <div style={{ fontSize:14, fontWeight:800, color:'#f0f6fc', fontFamily:'monospace' }}>{(oppLevels.entry||0).toFixed(2)}</div>
            <div style={{ fontSize:14, fontWeight:700, color:R, fontFamily:'monospace' }}>{(oppLevels.stop||0).toFixed(2)}</div>
          </div>
        )}
      </div>

      {/* Signal detail — כשיש סטאפ */}
      {isActive && sig && (
        <>
          {/* Per-target win rates */}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(3, minmax(0, 1fr))', gap:6, marginTop:10 }}>
            {[
              { label:'T1 · C1', val:sig.target1, pct:sig.t1_win_rate??0, note:'R:R 1:1' },
              { label:'T2 · C2', val:sig.target2, pct:sig.t2_win_rate??0, note:'R:R 1:2' },
              { label:'T3 · Runner', val:sig.target3, pct:sig.t3_win_rate??0, note:'Woodi R1' },
            ].map(({ label, val, pct, note }) => (
              <div key={label} style={{ background:'#0d1117', borderRadius:6, padding:'6px 8px', textAlign:'center', border:`1px solid ${col}22` }}>
                <div style={{ fontSize:14, color:'#4a5568', marginBottom:2 }}>{label}</div>
                <div style={{ fontSize:14, fontWeight:700, color:col, fontFamily:'monospace' }}>{(val??0).toFixed(2)}</div>
                <div style={{ fontSize:14, color:col, fontWeight:700 }}>{pct}%</div>
                <div style={{ height:3, background:'#1e2738', borderRadius:2, marginTop:3, overflow:'hidden' }}>
                  <div style={{ width:`${pct}%`, height:'100%', background:col, borderRadius:2 }} />
                </div>
                <div style={{ fontSize:14, color:'#4a5568', marginTop:2 }}>{note}</div>
              </div>
            ))}
          </div>

          {/* כפתור ביטול בלבד — קבלה אוטומטית */}
          {accepted && (
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginTop:10, padding:'6px 10px', background:'#22c55e18', borderRadius:6, border:'1px solid #22c55e44' }}>
              <span style={{ fontSize:14, color:G, fontWeight:700 }}>✓ סטאפ מקובע אוטומטית</span>
              <button onClick={onReject} style={{ fontSize:14, padding:'3px 12px', borderRadius:4, background:'#ef535022', color:'#ef5350', border:'1px solid #ef535044', cursor:'pointer', fontFamily:'inherit', fontWeight:700 }}>לא מעניין ✗</button>
            </div>
          )}
          {!accepted && isActive && displayScore >= 7 && (
            <div style={{ marginTop:10, padding:'6px 10px', background:'#f59e0b18', borderRadius:6, border:'1px solid #f59e0b44', fontSize:14, color:'#f59e0b', direction:'rtl' }}>
              ⏳ ממתין לאישור אוטומטי...
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Zone C: Entry Zone ────────────────────────────────────────────────────────
function EntryZone({ live, signal }:{ live:MarketData|null; signal?:any }) {
  const sig = signal || live?.signal;
  const [c1, setC1] = useState<'open'|'hit'|'closed'>('open');
  const [c2, setC2] = useState<'open'|'hit'|'closed'>('open');
  const [c3, setC3] = useState<'open'|'hit'|'closed'>('open');
  const [entered, setEntered] = useState(false);
  const price = live?.price ?? 0;

  useEffect(() => {
    if (!sig || !entered || sig.direction === 'NO_TRADE') return;
    const long = sig.direction === 'LONG';
    if (long ? price >= sig.target1 : price <= sig.target1) setC1(v => v === 'open' ? 'hit' : v);
    if (long ? price >= sig.target2 : price <= sig.target2) setC2(v => v === 'open' ? 'hit' : v);
    if (long ? price >= sig.target3 : price <= sig.target3) setC3(v => v === 'open' ? 'hit' : v);
  }, [price, sig, entered]);

  const hasSignal = sig && sig.direction !== 'NO_TRADE' && (sig.entry ?? 0) > 0;
  const isLong = sig?.direction === 'LONG';
  const acol = isLong ? G : R;
  const sCol = (s:string) => s==='hit'?G:s==='closed'?'#4a5568':Y;
  const sTxt = (s:string) => s==='hit'?'✓ הגיע':s==='closed'?'✗ סגור':'◌ פתוח';

  // תמיד מוצג — אם אין signal, מציג מחיר נוכחי + VWAP
  if (!hasSignal) {
    return (
      <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, overflow:'hidden' }}>
        <div style={{ padding:'8px 12px', borderBottom:'1px solid #1e2738', display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:14, color:'#4a5568', letterSpacing:1 }}>אזור כניסה</span>
          <span style={{ fontSize:14, fontWeight:800, color:'#f0f6fc', marginLeft:'auto', fontFamily:'monospace' }}>{(live?.price??0).toFixed(2)}</span>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:0 }}>
          {[
            { l:'VWAP', v:(live?.vwap?.value??0).toFixed(2), c:'#f6c90e', note:live?.vwap?.above?'מעל ▲':'מתחת ▼' },
            { l:'CVD', v:live?.cvd?.trend??'—', c:live?.cvd?.trend==='BULLISH'?G:live?.cvd?.trend==='BEARISH'?R:Y, note:'' },
          ].map(({l,v,c,note})=>(
            <div key={l} style={{ padding:'6px 8px', textAlign:'center', borderRight:'1px solid #1e2738' }}>
              <div style={{ fontSize:14, color:'#4a5568', marginBottom:2 }}>{l}</div>
              <div style={{ fontSize:14, fontWeight:700, color:c, fontFamily:'monospace' }}>{v} <span style={{fontSize:14,color:'#4a5568'}}>{note}</span></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ background:'#0d1f1a', border:`1px solid ${acol}33`, borderRadius:8, overflow:'hidden' }}>
      {/* Stop / Entry / T1 / T2 / T3 */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)' }}>
        {[
          { label:'STOP', val:sig.stop, color:R },
          { label:'ENTRY', val:sig.entry, color:'#ffffff' },
          { label:'T1·C1', val:sig.target1, color:G, diff:true },
          { label:'T2·C2', val:sig.target2, color:'#16a34a', diff:true },
          { label:'T3·Runner', val:sig.target3, color:'#86efac', diff:true },
        ].map(({ label, val, color, diff }, i) => (
          <div key={label} style={{ padding:'8px 6px', textAlign:'center', borderRight:i<4?`1px solid ${acol}22`:'none', background: label==='ENTRY'?acol+'0f':'transparent' }}>
            <div style={{ fontSize:14, color, marginBottom:3 }}>{label}</div>
            <div style={{ fontSize:14, fontWeight:800, color, fontFamily:'monospace' }}>{val?.toFixed(2)??'—'}</div>
            {diff && val && <div style={{ fontSize:14, color:'#4a5568' }}>+{(val-sig.entry).toFixed(2)}</div>}
          </div>
        ))}
      </div>
      {/* C1/C2/C3 tracker */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr 120px', borderTop:`1px solid ${acol}22` }}>
        {[
          { label:'C1', status:c1, desc:'R:R 1:1 → BE', setter:setC1 },
          { label:'C2', status:c2, desc:'R:R 1:2', setter:setC2 },
          { label:'C3', status:c3, desc:'Runner', setter:setC3 },
        ].map(({ label, status, desc, setter }) => (
          <div key={label} onClick={() => entered && setter(s => s==='open'?'hit':s==='hit'?'closed':'open')}
            style={{ padding:'6px 8px', textAlign:'center', borderRight:`1px solid ${acol}22`, cursor:entered?'pointer':'default' }}>
            <div style={{ fontSize:14, fontWeight:700, color:entered?sCol(status):'#4a5568' }}>{label}</div>
            <div style={{ fontSize:14, color:'#4a5568', marginBottom:2 }}>{desc}</div>
            {entered && <div style={{ fontSize:14, fontWeight:700, color:sCol(status) }}>{sTxt(status)}</div>}
          </div>
        ))}
        <div style={{ display:'flex', alignItems:'center', justifyContent:'center', padding:6 }}>
          {!entered
            ? <button onClick={() => setEntered(true)} style={{ padding:'4px 12px', borderRadius:6, fontSize:14, fontWeight:700, background:G, color:'#0d1117', border:'none', cursor:'pointer', fontFamily:'inherit' }}>נכנסתי ✓</button>
            : <button onClick={() => { setEntered(false); setC1('open'); setC2('open'); setC3('open'); }} style={{ padding:'4px 10px', borderRadius:6, fontSize:14, background:'#1e2738', color:'#6b7280', border:'none', cursor:'pointer', fontFamily:'inherit' }}>אפס</button>
          }
        </div>
      </div>
    </div>
  );
}

// ── AI Canvas Chart ───────────────────────────────────────────────────────────
function AIChart({ candles, live, tf }:{ candles:Candle[]; live:MarketData|null; tf:string }) {
  const cvs = useRef<HTMLCanvasElement>(null);
  const meta = useRef<{ px:(i:number)=>number; py:(p:number)=>number; cW:number; data:Candle[] }>({ px:()=>0, py:()=>0, cW:8, data:[] });
  const [hov, setHov] = useState<Candle|null>(null);

  const draw = useCallback(() => {
    const canvas = cvs.current; if (!canvas) return;
    const W = canvas.width = canvas.parentElement!.clientWidth;
    const H = canvas.height;
    const ctx = canvas.getContext('2d')!;
    const PL=8, PR=72, PT=18, PB=26;
    ctx.fillStyle='#0d1117'; ctx.fillRect(0,0,W,H);

    const data = [...candles].reverse().slice(-80);
    if (live?.bar) {
      const lb:Candle = { ts:live.ts, o:live.bar.o, h:live.bar.h, l:live.bar.l, c:live.bar.c, buy:live.bar.buy, sell:live.bar.sell, delta:live.bar.delta };
      if (data.length===0 || data[data.length-1].ts!==lb.ts) data.push(lb);
    }
    if (data.length===0) {
      ctx.fillStyle='#4a5568'; ctx.font='12px monospace'; ctx.textAlign='center';
      ctx.fillText('ממתין לנתונים...', W/2, H/2); return;
    }

    const prices = data.flatMap(c=>[c.h,c.l]);
    const sig = live?.signal;
    if (sig && sig.direction!=='NO_TRADE') [sig.entry,sig.stop,sig.target1,sig.target2,sig.target3].forEach(p=>p&&prices.push(p));
    if (live?.vwap?.value) prices.push(live.vwap.value);
    if (live?.profile) prices.push(live.profile.vah,live.profile.val,live.profile.poc);
    if ((live?.session?.ibh??0)>0) prices.push(live?.session?.ibh??0,live?.session?.ibl??0);
    if (live?.levels) prices.push(live.levels.prev_high,live.levels.prev_low,live.levels.daily_open);

    let minP=Math.min(...prices.filter(Boolean)), maxP=Math.max(...prices.filter(Boolean));
    const rng=maxP-minP||1; minP-=rng*.07; maxP+=rng*.07;

    const chartW=W-PL-PR, chartH=H-PT-PB;
    const cW=Math.max(3,Math.floor(chartW/data.length));
    const barW=Math.max(2,cW-2);
    const px=(i:number)=>PL+i*cW+cW/2;
    const py=(p:number)=>PT+chartH*(1-(p-minP)/(maxP-minP));
    meta.current={px,py,cW,data};

    // Grid
    for(let i=0;i<=6;i++){
      const p=minP+(maxP-minP)*(i/6), y=py(p);
      ctx.strokeStyle='#161d2a'; ctx.lineWidth=1; ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(PL,y); ctx.lineTo(W-PR,y); ctx.stroke();
      ctx.fillStyle='#3d4a5e'; ctx.font='9px monospace'; ctx.textAlign='left';
      ctx.fillText(p.toFixed(2),W-PR+3,y+3);
    }

    // Level helper
    const lvl=(price:number,color:string,label:string,dash=[4,3],lw=1)=>{
      if(!price||price<minP||price>maxP)return;
      const y=py(price);
      ctx.strokeStyle=color; ctx.lineWidth=lw; ctx.setLineDash(dash);
      ctx.beginPath(); ctx.moveTo(PL,y); ctx.lineTo(W-PR,y); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle=color; ctx.font='bold 8px monospace'; ctx.textAlign='left';
      ctx.fillText(label,W-PR+3,y-1);
    };

    if(live){
      const lv=live.levels||{}, pr=live.profile||{}, se=live.session||{};
      lvl(lv.prev_high,'#ef4444','PDH',[3,3]);
      lvl(lv.prev_low,'#ef4444','PDL',[3,3]);
      lvl(lv.daily_open,'#60a5fa','DO',[3,3]);
      lvl(lv.overnight_high,'#a78bfa','ONH',[2,4]);
      lvl(lv.overnight_low,'#a78bfa','ONL',[2,4]);
      lvl(pr.vah,'#22c55e','VAH',[4,2]);
      lvl(pr.val,'#22c55e','VAL',[4,2]);
      lvl(pr.poc,'#f97316','POC',[6,2]);
      lvl(pr.tpo_poc,'#fb923c','tPOC',[3,3]);
      if(se.ibh>0){lvl(se.ibh,'#38bdf8','IBH',[4,2]); lvl(se.ibl,'#38bdf8','IBL',[4,2]);}
      const vv=live.vwap?.value;
      if(vv&&vv>minP&&vv<maxP){
        const y=py(vv);
        ctx.strokeStyle='#f6c90e'; ctx.lineWidth=1.5; ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(PL,y); ctx.lineTo(W-PR,y); ctx.stroke();
        ctx.fillStyle='#f6c90e'; ctx.font='bold 8px monospace';
        ctx.fillText('VWAP',W-PR+3,y-1);
      }
    }

    // Signal overlays
    if(sig&&sig.direction!=='NO_TRADE'&&sig.entry){
      const acol=sig.direction==='LONG'?'#26a69a':'#ef5350';
      const eyT=py(Math.max(sig.entry,sig.stop)), eyB=py(Math.min(sig.entry,sig.stop));
      ctx.fillStyle=acol+'15'; ctx.fillRect(PL,eyT,W-PL-PR,eyB-eyT);
      lvl(sig.stop,'#ef5350','✕ STOP',[3,2],1.5);
      lvl(sig.entry,'#ffffff','→ ENTRY',[],1.5);
      lvl(sig.target1,'#22c55e','⊕ T1·C1',[5,2],1.2);
      lvl(sig.target2,'#16a34a','⊕ T2·C2',[5,2],1.2);
      lvl(sig.target3,'#86efac','★ T3·Runner',[5,2],1.2);
    }

    // Candles
    data.forEach((c,i)=>{
      const x=px(i), up=c.c>=c.o;
      ctx.strokeStyle=up?'#1a756d':'#a33535'; ctx.lineWidth=1; ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(x,py(c.h)); ctx.lineTo(x,py(c.l)); ctx.stroke();
      const bt=py(Math.max(c.o,c.c)), bb=py(Math.min(c.o,c.c));
      ctx.fillStyle=up?'#26a69a':'#ef5350';
      ctx.fillRect(x-barW/2,bt,barW,Math.max(1,bb-bt));
    });

    // Live price
    if(live){
      const price=live.price||live.bar?.c||0, y=py(price);
      if(y>PT&&y<H-PB){
        ctx.strokeStyle='#ffffff66'; ctx.lineWidth=1; ctx.setLineDash([2,2]);
        ctx.beginPath(); ctx.moveTo(PL,y); ctx.lineTo(W-PR,y); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle='#e2e8f0'; ctx.fillRect(W-PR+1,y-8,66,16);
        ctx.fillStyle='#0d1117'; ctx.font='bold 10px monospace'; ctx.textAlign='left';
        ctx.fillText(price.toFixed(2),W-PR+4,y+4);
      }
    }

    // Time labels
    ctx.fillStyle='#3d4a5e'; ctx.font='8px monospace'; ctx.textAlign='center';
    const step=Math.max(1,Math.floor(data.length/8));
    data.forEach((c,i)=>{
      if(i%step===0&&c.ts){
        const d=new Date(c.ts*1000);
        ctx.fillText(`${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`,px(i),H-8);
      }
    });
  },[candles,live,tf]);

  useEffect(()=>{draw();},[draw]);
  useEffect(()=>{window.addEventListener('resize',draw);return()=>window.removeEventListener('resize',draw);},[draw]);

  const onMove=(e:React.MouseEvent<HTMLCanvasElement>)=>{
    const canvas=cvs.current; if(!canvas)return;
    const rect=canvas.getBoundingClientRect();
    const mx=(e.clientX-rect.left)*(canvas.width/rect.width);
    const {px,cW,data}=meta.current;
    const idx=Math.round((mx-8-cW/2)/cW);
    setHov(idx>=0&&idx<data.length?data[idx]:null);
  };

  return (
    <div style={{ position:'relative' }}>
      <canvas ref={cvs} height={400} style={{ width:'100%', display:'block', cursor:'crosshair' }}
        onMouseMove={onMove} onMouseLeave={()=>setHov(null)} />
      {hov&&(
        <div style={{ position:'absolute', top:8, left:12, background:'#1a2233ee', border:'1px solid #2d3a4a', borderRadius:6, padding:'4px 10px', fontSize:14, color:'#94a3b8', fontFamily:'monospace', pointerEvents:'none' }}>
          <span style={{color:'#60a5fa'}}>O</span> {(hov.o??0).toFixed(2)}&nbsp;
          <span style={{color:'#22c55e'}}>H</span> {(hov.h??0).toFixed(2)}&nbsp;
          <span style={{color:'#ef5350'}}>L</span> {(hov.l??0).toFixed(2)}&nbsp;
          <span style={{color:'#e2e8f0'}}>C</span> {(hov.c??0).toFixed(2)}&nbsp;
          <span style={{color:hov.delta>=0?'#26a69a':'#ef5350'}}>Δ {hov.delta>=0?'+':''}{Math.round(hov.delta)}</span>
        </div>
      )}
    </div>
  );
}

// ── Volume + Timer ────────────────────────────────────────────────────────────
function VolumeTimer({ bar }:{ bar:Bar|null }) {
  const [secs,setSecs]=useState(0);
  useEffect(()=>{
    const tick=()=>setSecs(180-(Math.floor(Date.now()/1000)%180));
    tick(); const t=setInterval(tick,1000); return()=>clearInterval(t);
  },[]);
  const pct=((180-secs)/180)*100, urgent=secs<=30;
  const mm=Math.floor(secs/60), ss=secs%60;
  const buy=bar?.buy??0, sell=bar?.sell??0, total=buy+sell||1;
  const buyPct=Math.round((buy/total)*100);
  const delta=bar?.delta??0, isPos=delta>=0;
  const deltaLbl=Math.abs(delta)>300?(isPos?'קונים חזקים':'מוכרים חזקים'):Math.abs(delta)>100?(isPos?'לחץ קנייה':'לחץ מכירה'):'נייטרלי';

  return (
    <div style={{ borderTop:'1px solid #1e2738', padding:'8px 12px', display:'flex', flexDirection:'column', gap:6 }}>
      {/* Volume */}
      <div>
        <div style={{ display:'flex', justifyContent:'space-between', fontSize:14, marginBottom:3 }}>
          <span style={{color:'#26a69a'}}>B {Math.round(buy).toLocaleString()}</span>
          <span style={{color:'#4a5568'}}>נפח</span>
          <span style={{color:'#ef5350'}}>S {Math.round(sell).toLocaleString()}</span>
        </div>
        <div style={{ height:8, borderRadius:4, overflow:'hidden', display:'flex', background:'#ef5350' }}>
          <div style={{ width:`${buyPct}%`, background:'#26a69a', transition:'width .4s', borderRadius:'4px 0 0 4px' }} />
        </div>
        <div style={{ display:'flex', justifyContent:'space-between', fontSize:14, marginTop:3 }}>
          <span style={{color:'#4a5568'}}>Delta</span>
          <span style={{ color:isPos?'#26a69a':'#ef5350', fontFamily:'monospace', fontWeight:700 }}>
            {isPos?'+':''}{Math.round(delta).toLocaleString()} · {deltaLbl}
          </span>
        </div>
      </div>
      {/* Timer */}
      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
        <span style={{ fontSize:14, color:'#4a5568' }}>נר הבא</span>
        <div style={{ flex:1, height:3, background:'#1e2738', borderRadius:2, overflow:'hidden' }}>
          <div style={{ width:`${pct}%`, height:'100%', background:urgent?R:G, transition:'width 1s linear', borderRadius:2 }} />
        </div>
        <span style={{ fontSize:14, fontFamily:'monospace', fontWeight:700, color:urgent?R:'#6b7280' }}>{mm}:{ss.toString().padStart(2,'0')}</span>
      </div>
    </div>
  );
}

// ── Zone E: Indicators ────────────────────────────────────────────────────────
const TOOLTIPS:Record<string,string> = {
  'CVD מגמה':'Cumulative Volume Delta — סכום הפרש קונים/מוכרים מתחילת היום',
  'CVD 15m':'דלתא של 15 דקות האחרונות — מומנטום קצר',
  'CVD 60m':'דלתא של 60 דקות האחרונות — מומנטום ארוך',
  'VWAP':'ממוצע משוקלל נפח — הרמה שמפרידה קונים ומוכרים',
  'Value Area':'70% מהמסחר נמצא בין VAH ל-VAL',
  'POC':'המחיר עם הכי הרבה נפח היום',
  'Woodi PP':'ציר Woodi — מרכז המסחר לפי נוסחת יאנגן',
  'Absorption':'קונים בולעים מכירות — רמזור להיפוך',
  'Liq Sweep':'שבירה מתחת לרמה עם חזרה מהירה',
  'Imbalance':'חוסר איזון בספר פקודות — 3:1 לפחות',
  'Session':'שלב המסחר הנוכחי',
  'IB':'Initial Balance — טווח השעה הראשונה',
  'MTF':'יישור Multi-Timeframe — כל הטווחים באותו כיוון',
};

function Indicators({ live }:{ live:MarketData|null }) {
  const [tip,setTip]=useState('');
  if(!live) return null;

  const cvd=live.cvd||{}, vwap=live.vwap||{}, prof=live.profile||{}, woodi=live.woodi||{};
  const sess=live.session||{}, of2=live.order_flow||{}, bar=live.bar||{}, mtf=live.mtf||{};
  const fp=(live as any).footprint_bools||{};
  const price=live.price||0;

  const rows=[
    // מגמה
    { cat:'מגמה', name:'CVD מגמה', col:cvd.trend==='BULLISH'?G:cvd.trend==='BEARISH'?R:Y, val:cvd.trend||'—', note:cvd.trend==='BULLISH'?'עולה':cvd.trend==='BEARISH'?'יורדת':'נייטרלי' },
    { cat:'', name:'CVD 15m', col:(cvd.d5||0)>50?G:(cvd.d5||0)<-50?R:Y, val:((cvd.d5||0)>=0?'+':'')+Math.round(cvd.d5||0), note:Math.abs(cvd.d5||0)>200?'חזק':Math.abs(cvd.d5||0)>50?'בינוני':'חלש' },
    { cat:'', name:'CVD 60m', col:(cvd.d20||0)>200?G:(cvd.d20||0)<-200?R:Y, val:((cvd.d20||0)>=0?'+':'')+Math.round(cvd.d20||0), note:Math.abs(cvd.d20||0)>500?'מומנטום חזק':'מומנטום' },
    // מיקום
    { cat:'מיקום', name:'VWAP', col:vwap.pullback?G:vwap.above?G:R, val:vwap.value?.toFixed(2)||'—', note:vwap.pullback?'⚡ Pullback':vwap.above?'מעל':'מתחת' },
    { cat:'', name:'Value Area', col:prof.in_va?Y:prof.above_poc?G:R, val:prof.in_va?'בתוך VA':prof.above_poc?'מעל VAH':'מתחת VAL', note:prof.in_va?'בטווח ערך':prof.above_poc?'שבירה מעלה':'שבירה מטה' },
    { cat:'', name:'POC', col:'#f97316', val:prof.poc?.toFixed(2)||'—', note:((price-(prof.poc||price))>=0?'+':'')+((price-(prof.poc||price)).toFixed(2))+' pts' },
    { cat:'', name:'Woodi PP', col:woodi.above_pp?G:R, val:woodi.pp?.toFixed(2)||'—', note:woodi.above_pp?'מעל ▲':'מתחת ▼' },
    // Order Flow
    { cat:'Order Flow', name:'Absorption', col:(of2.absorption_bull||fp.absorption_detected)?G:'#2d3a4a', val:(of2.absorption_bull||fp.absorption_detected)?'פעיל ✓':'לא זוהה', note:of2.absorption_bull?'קונים בולעים':fp.absorption_detected?'זוהה (footprint)':'—' },
    { cat:'', name:'Liq Sweep', col:of2.liq_sweep?G:'#2d3a4a', val:of2.liq_sweep?'זוהה ✓':'לא זוהה', note:of2.liq_sweep?'Sweep + חזרה':'—' },
    { cat:'', name:'Imbalance', col:(of2.imbalance_bull||0)>0?G:(of2.imbalance_bear||0)>0?R:'#2d3a4a', val:`B×${of2.imbalance_bull||0} S×${of2.imbalance_bear||0}`, note:(of2.imbalance_bull||0)>0?'עולה':(of2.imbalance_bear||0)>0?'יורד':'—' },
    // מבנה
    { cat:'מבנה', name:'Session', col:sess.phase==='RTH'?G:sess.phase==='OVERNIGHT'?Y:R, val:sess.phase||'—', note:sess.phase==='RTH'?'שעות מסחר':'לילי' },
    { cat:'', name:'IB', col:sess.ibh>0?(sess.ib_locked?G:Y):'#2d3a4a', val:sess.ibh>0?`H${sess.ibh?.toFixed(0)} L${sess.ibl?.toFixed(0)}`:'בניית IB', note:sess.ib_locked?'נעול ✓':sess.ibh>0?'מתגבש':'—' },
    { cat:'', name:'MTF', col:(()=>{ const m3=bar.delta||0, m15=mtf.m15?.delta||0, m30=mtf.m30?.delta||0; return (m3>0&&m15>0&&m30>0)||(m3<0&&m15<0&&m30<0)?G:Y; })(), val:(()=>{ const m3=bar.delta||0, m15=mtf.m15?.delta||0, m30=mtf.m30?.delta||0; return `3m${m3>=0?'▲':'▼'} 15m${m15>=0?'▲':'▼'} 30m${m30>=0?'▲':'▼'}`; })(), note:'יישור timeframes' },
  ];

  return (
    <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, overflow:'hidden', position:'relative' }}>
      {/* Tooltip */}
      {tip && (
        <div style={{ position:'absolute', top:0, left:0, right:0, background:'#1a2233', borderBottom:'1px solid #2d3a4a', padding:'6px 10px', fontSize:14, color:'#94a3b8', lineHeight:1.5, direction:'rtl', textAlign:'right', zIndex:10 }}>
          {TOOLTIPS[tip] || tip}
          <button onClick={()=>setTip('')} style={{ float:'left', background:'none', border:'none', color:'#4a5568', cursor:'pointer', fontSize:14 }}>×</button>
        </div>
      )}
      <div style={{ padding:'8px 10px', borderBottom:'1px solid #1e2738' }}>
        <span style={{ fontSize:14, color:'#4a5568', letterSpacing:2 }}>אינדיקטורים ({rows.filter(r=>r.col===G).length}/{rows.length} ✓)</span>
      </div>
      <div style={{ padding:'4px 0' }}>
        {rows.map((r,i)=>(
          <div key={i}>
            {r.cat && <div style={{ fontSize:14, color:'#2d3a4a', letterSpacing:1, padding:'4px 10px 2px' }}>{r.cat}</div>}
            <div style={{ display:'flex', alignItems:'center', gap:6, padding:'4px 10px', borderBottom:'1px solid #0d1117' }}>
              <MiniLight col={r.col} />
              <span style={{ fontSize:14, color:'#6b7280', width:72, flexShrink:0 }}>{r.name}</span>
              <span style={{ fontSize:14, color:r.col, fontFamily:'monospace', flex:1, fontWeight:600 }}>{r.val}</span>
              <span style={{ fontSize:14, color:'#4a5568', direction:'rtl' }}>{r.note}</span>
              <button onClick={()=>setTip(tip===r.name?'':r.name)} style={{ width:14, height:14, borderRadius:'50%', background:'#1e2738', border:'none', color:'#4a5568', fontSize:14, cursor:'pointer', flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center' }}>?</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


// ── AI Analysis Panel ─────────────────────────────────────────────────────────
// ── 3-Pillar Badges — glanceable P1/P2/P3 status ──────────────────────────
function PillarBadges({ live, liveSetup }:{ live:MarketData|null; liveSetup:any }) {
  if (!live) return null;
  const of2 = live.order_flow || {} as any;
  const fp = (live as any)?.footprint_bools || {} as any;
  const vol = (live as any)?.volume_context || {} as any;
  const price = live.price || 0;

  const opp = liveSetup?.opportunity || 'none';
  const oppSweep = liveSetup?.opportunitySweep;
  const evalResult = liveSetup?.setupEval;

  // ── P1 ZONE: Sweep at macro level ──
  const hasSweep = oppSweep?.type === 'sweep';
  const sweepLevel = oppSweep?.levelName || '—';
  const macroLevels = ['PDH','PDL','ONH','ONL','IBH','IBL','VWAP','POC','VAH','VAL','SH','SL'];
  const atMacro = macroLevels.includes(sweepLevel);
  const p1Pass = hasSweep && atMacro;

  // ── P2 PATTERN: MSS + FVG + RelVol + Stacked ──
  const relVol = oppSweep?.relVol ?? vol.rel_vol ?? 0;
  const relVolOk = relVol > 1.2;
  const stackedCount = fp.stacked_imbalance_count ?? 0;
  const stackedDir = fp.stacked_imbalance_dir ?? '';
  const stackedOk = stackedCount >= 2;
  // MSS/FVG derived from evalResult reason
  const evalReason = evalResult?.reason || '';
  const hasMSS = evalResult ? !evalReason.includes('No MSS') : false;
  const hasFVG = evalResult ? !evalReason.includes('No FVG') : false;
  const p2Pass = hasMSS && hasFVG && relVolOk && stackedOk;

  // ── P3 FLOW: Absorption + Delta 1m ──
  const absorptionOk = fp.absorption_at_fvg ?? of2.absorption_bull ?? false;
  const deltaConfirmed = fp.delta_confirmed_1m ?? false;
  const p3Pass = absorptionOk && deltaConfirmed;

  const allPass = p1Pass && p2Pass && p3Pass;
  const evalType = evalResult?.eval_type === 'trend' ? 'TREND' : 'RANGE';

  const row = (label:string, pass:boolean|null, subs:{label:string;ok:boolean;val?:string}[]) => {
    const bg = pass === null ? '#1e273822' : pass ? '#22c55e11' : '#ef535011';
    const borderCol = pass === null ? '#2d3a4a' : pass ? '#22c55e44' : '#ef535044';
    const icon = pass === null ? '⬜' : pass ? '✅' : '❌';
    return (
      <div key={label} style={{ background:bg, border:`1px solid ${borderCol}`, borderRadius:6, padding:'6px 10px', marginBottom:3 }}>
        <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:3 }}>
          <span style={{ fontSize:13 }}>{icon}</span>
          <span style={{ fontSize:13, fontWeight:800, color: pass===null?'#4a5568': pass?G:R }}>{label}</span>
        </div>
        <div style={{ display:'flex', flexWrap:'wrap', gap:'2px 10px', fontSize:12, color:'#94a3b8' }}>
          {subs.map(s => (
            <span key={s.label}>
              {s.label}: <span style={{ color:s.ok?G:R, fontWeight:700 }}>{s.ok?'✓':'✗'}{s.val ? ` ${s.val}` : ''}</span>
            </span>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div style={{ background:'#0a0e1a', border:'1px solid #1e2738', borderRadius:8, padding:8 }}>
      <div style={{ fontSize:12, color:'#4a5568', letterSpacing:1.5, marginBottom:5, fontWeight:700 }}>3-PILLAR GATE — {evalType}</div>
      {row('P1 ZONE', opp==='none'?null:p1Pass, [
        { label:'Sweep', ok:hasSweep },
        { label:'Level', ok:atMacro, val:sweepLevel },
      ])}
      {row('P2 PATTERN', opp==='none'?null:p2Pass, [
        { label:'MSS', ok:hasMSS },
        { label:'FVG', ok:hasFVG },
        { label:'RelVol', ok:relVolOk, val:`${relVol.toFixed(2)}` },
        { label:'Stacked', ok:stackedOk, val:stackedOk?`${stackedCount}×250% ${stackedDir}`:`${stackedCount}` },
      ])}
      {row('P3 FLOW', opp==='none'?null:p3Pass, [
        { label:'Absorption', ok:absorptionOk },
        { label:'Delta 1m', ok:deltaConfirmed },
      ])}
      {allPass && opp !== 'none' && (
        <div style={{ marginTop:4, padding:'6px 10px', borderRadius:6, background:'#22c55e18', border:'1px solid #22c55e44', textAlign:'center' }}>
          <span style={{ fontSize:13, fontWeight:800, color:G }}>✅ SETUP VALID — ready to execute</span>
        </div>
      )}
    </div>
  );
}

function AIAnalysisPanel({signal, signalTime, aiLoading, aiError, onAskAI, live}: {
  signal?: Signal | null; signalTime?: string; aiLoading: boolean; aiError?: boolean; onAskAI: () => void; live?: any;
}) {
  if (aiLoading) return (
    <div style={{ padding:20, textAlign:'center', color:'#7f77dd' }}>
      <div style={{ fontSize:14, marginBottom:8 }}>⚡ Claude מנתח...</div>
      <div style={{ fontSize:14, color:'#4a5568' }}>בודק נפח, מבנה ורמות</div>
    </div>
  );
  if (aiError && !signal) return (
    <div style={{ padding:16, textAlign:'center' }}>
      <div style={{ fontSize:14, color:'#64748b', marginBottom:4 }}>AI לא זמין</div>
      <div style={{ fontSize:14, color:'#4a5568', marginBottom:12 }}>המערכת ממשיכה לעבוד — ניתן לסחור ללא AI</div>
      <button onClick={onAskAI} style={{
        padding:'6px 16px', borderRadius:8, fontSize:14, fontWeight:700,
        background:'#1e2738', color:'#7f77dd', border:'1px solid #7f77dd44',
        cursor:'pointer', fontFamily:'inherit',
      }}>🔄 רענן</button>
    </div>
  );
  if (!signal) return (
    <div style={{ padding:16, textAlign:'center' }}>
      <div style={{ fontSize:14, color:'#4a5568', marginBottom:12 }}>לחץ לניתוח AI מלא</div>
      <button onClick={onAskAI} style={{
        padding:'8px 20px', borderRadius:8, fontSize:14, fontWeight:700,
        background:'#7f77dd22', color:'#7f77dd', border:'1px solid #7f77dd44',
        cursor:'pointer', fontFamily:'inherit',
      }}>⚡ נתח</button>
    </div>
  );

  const dirColors: Record<string, string> = { LONG:'#10b981', SHORT:'#ef4444', NO_TRADE:'#64748b' };
  const dirLabels: Record<string, string> = { LONG:'▲ LONG', SHORT:'▼ SHORT', NO_TRADE:'— NO TRADE' };
  const col = dirColors[signal.direction] || '#64748b';
  const dirLabel = dirLabels[signal.direction] || signal.direction;
  const biasColor = signal.score >= 7 ? '#10b981' : signal.score >= 4 ? '#f59e0b' : '#ef4444';
  const profile = (live as any)?.profile || {};
  const vwap = (live as any)?.vwap?.value || 0;

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:1 }}>

      {/* HEADER */}
      <div style={{
        background:'#0f172a', borderRadius:'10px 10px 0 0', padding:'10px 12px',
        display:'flex', alignItems:'center', justifyContent:'space-between',
        borderBottom:'1px solid #1e2738',
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:14, color:'#7f77dd', fontWeight:700 }}>⚡ CLAUDE AI</span>
          <span style={{
            fontSize:14, fontWeight:800, color:col,
            background:`${col}22`, padding:'2px 8px', borderRadius:6, border:`1px solid ${col}44`,
          }}>{dirLabel}</span>
          {signal.setup_name && (
            <span style={{ fontSize:14, color:'#94a3b8', background:'#1e2738', padding:'2px 7px', borderRadius:5 }}>{signal.setup_name}</span>
          )}
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:6 }}>
          {signalTime && <span style={{ fontSize:14, color:'#4a5568' }}>{signalTime}</span>}
          <button onClick={onAskAI} style={{
            padding:'2px 8px', borderRadius:5, fontSize:14, fontWeight:700,
            background:'#1e2738', color:'#6b7280', border:'1px solid #2d3a4a',
            cursor:'pointer', fontFamily:'inherit',
          }}>🔄</button>
        </div>
      </div>

      {/* BIAS + SCORE */}
      <div style={{
        background:'#0a0f1a', padding:'8px 12px', display:'flex', alignItems:'center', gap:10,
        borderBottom:'1px solid #1e2738',
      }}>
        <div style={{
          fontSize:14, fontWeight:700, color:biasColor,
          background:`${biasColor}22`, padding:'3px 10px', borderRadius:20, border:`1px solid ${biasColor}44`,
        }}>
          {signal.score >= 7 ? '🟢 Bias חיובי' : signal.score >= 4 ? '🟡 Bias ניטרלי' : '🔴 Bias שלילי'}
        </div>
        <div style={{ fontSize:14, color:'#64748b', cursor:'help' }} title="Setup quality 0-10: combines Bias alignment, pillar pass count, volume context, and killzone.">ציון: <span style={{ color:biasColor, fontWeight:700 }}>{signal.score}/10</span></div>
        <div style={{ fontSize:14, color:'#64748b' }}>ביטחון: <span style={{ color:'#94a3b8', fontWeight:700 }}>{signal.direction === 'NO_TRADE' ? 'N/A (אין סטאפ לנתח)' : `${signal.confidence}%`}</span></div>
        {signal.win_rate && <div style={{ fontSize:14, color:'#64748b' }}>Win: <span style={{ color:'#94a3b8', fontWeight:700 }}>{signal.win_rate}%</span></div>}
      </div>

      {/* RATIONALE */}
      {signal.rationale && (
        <div style={{ background:'#0a0f1a', padding:'10px 12px', borderBottom:'1px solid #1e2738' }}>
          <div style={{ fontSize:14, color:'#475569', marginBottom:6, fontWeight:600 }}>📋 ניתוח</div>
          <div style={{ fontSize:14, color:'#cbd5e1', lineHeight:1.7, direction:'rtl' as const, textAlign:'right' }}>{signal.rationale}</div>
        </div>
      )}

      {/* ENTRY GRID */}
      {signal.direction !== 'NO_TRADE' && (
        <div style={{ background:'#0a0f1a', padding:'10px 12px', borderBottom:'1px solid #1e2738' }}>
          <div style={{ fontSize:14, color:'#475569', marginBottom:8, fontWeight:600 }}>🎯 פרמטרי כניסה</div>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:6 }}>
            {[
              { label:'כניסה', value:signal.entry?.toFixed(2), color:col },
              { label:'סטופ', value:signal.stop?.toFixed(2), color:'#ef4444' },
              { label:'T1', value:signal.target1?.toFixed(2), color:'#10b981' },
              { label:'T2', value:signal.target2?.toFixed(2), color:'#10b981' },
              { label:'R:R', value:signal.rr, color:'#f59e0b' },
              { label:'זמן T1', value:signal.time_estimate || '—', color:'#94a3b8' },
            ].map(item => (
              <div key={item.label} style={{ background:'#1e2738', borderRadius:6, padding:'6px 8px', minWidth:0 }}>
                <div style={{ fontSize:14, color:'#475569', marginBottom:2 }}>{item.label}</div>
                <div style={{ fontSize:14, fontWeight:700, color:item.color, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' as const }}>{item.value || '—'}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* LEVELS */}
      {(profile.vah || profile.val || profile.poc || vwap) ? (
        <div style={{ background:'#0a0f1a', padding:'10px 12px', borderBottom:'1px solid #1e2738' }}>
          <div style={{ fontSize:14, color:'#475569', marginBottom:8, fontWeight:600 }}>📊 רמות קריטיות</div>
          <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
            {[
              { label:'VAH', value:profile.vah, color:'#3b82f6' },
              { label:'POC', value:profile.poc, color:'#7c3aed' },
              { label:'VAL', value:profile.val, color:'#3b82f6' },
              { label:'VWAP', value:vwap, color:'#f59e0b' },
            ].filter(l => l.value).map(level => (
              <div key={level.label} style={{
                background:`${level.color}11`, border:`1px solid ${level.color}33`,
                borderRadius:6, padding:'4px 10px', display:'flex', alignItems:'center', gap:6,
              }}>
                <span style={{ fontSize:14, color:level.color, fontWeight:700 }}>{level.label}</span>
                <span style={{ fontSize:14, color:'#e2e8f0', fontWeight:600 }}>{level.value?.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* WARNING */}
      {signal.warning && (
        <div style={{ background:'#1c110a', padding:'8px 12px', borderBottom:'1px solid #1e2738', borderLeft:'3px solid #f59e0b' }}>
          <div style={{ fontSize:14, color:'#f59e0b', fontWeight:600, marginBottom:4 }}>⚠️ אזהרה</div>
          <div style={{ fontSize:14, color:'#fbbf24', direction:'rtl' as const, lineHeight:1.6 }}>{signal.warning}</div>
        </div>
      )}

      {/* WAIT REASON */}
      {signal.wait_reason && (
        <div style={{ background:'#0a0f1a', padding:'8px 12px', borderRadius:'0 0 10px 10px' }}>
          <div style={{ fontSize:14, color:'#475569', fontWeight:600, marginBottom:4 }}>⏳ מה חסר</div>
          <div style={{ fontSize:14, color:'#64748b', direction:'rtl' as const, lineHeight:1.6 }}>{signal.wait_reason}</div>
        </div>
      )}

    </div>
  );
}



// ── Pattern Scanner Component ────────────────────────────────────────────────
function PatternScanner({ candles, onSelect, selectedId }:{ candles:Candle[]; onSelect?:(p:PatternResult)=>void; selectedId?:string }) {
  const patterns = detectPatterns(candles);
  if(!patterns.length) return (
    <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:'10px 14px' }}>
      <div style={{ fontSize:14, color:'#4a5568', letterSpacing:2, marginBottom:4 }}>זיהוי תבניות גרף</div>
      <div style={{ fontSize:14, color:'#2d3a4a', direction:'rtl' }}>לא זוהו תבניות משמעותיות</div>
    </div>
  );
  return (
    <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:10 }}>
      <div style={{ fontSize:14, color:'#4a5568', letterSpacing:2, marginBottom:8 }}>זיהוי תבניות — {patterns.length} נמצאו</div>
      <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
        {patterns.map(p=>{
          const isSelected = selectedId===p.id;
          const dirCol = p.direction==='long'?'#22c55e':p.direction==='short'?'#ef5350':'#f59e0b';
          return (
            <div key={p.id} onClick={()=>onSelect?.(p)}
              style={{ border:`1px solid ${isSelected?p.col:'#1e2738'}`, borderRadius:7, padding:'7px 10px',
                background:isSelected?p.col+'12':'transparent', cursor:'pointer', transition:'all .2s' }}>
              <div style={{ display:'flex', alignItems:'center', gap:7, marginBottom:4 }}>
                <div style={{ width:7, height:7, borderRadius:'50%', background:p.col, boxShadow:isSelected?`0 0 6px ${p.col}`:'none' }} />
                <span style={{ fontSize:14, fontWeight:700, color:p.col, flex:1 }}>{p.nameHeb}</span>
                <span style={{ fontSize:14, fontWeight:700, color:dirCol }}>{p.direction==='long'?'▲ LONG':p.direction==='short'?'▼ SHORT':'↔'}</span>
                <span style={{ fontSize:14, fontWeight:800, color:p.confidence>=70?p.col:'#f59e0b', fontFamily:'monospace' }}>{p.confidence}%</span>
              </div>
              <div style={{ height:3, background:'#1e2738', borderRadius:2, marginBottom:5, overflow:'hidden' }}>
                <div style={{ width:`${p.confidence}%`, height:'100%', background:p.col, borderRadius:2 }} />
              </div>
              <div style={{ fontSize:14, color:'#6b7280', direction:'rtl', textAlign:'right' }}>{p.description}</div>
              {isSelected && p.breakoutLevel && (
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:4, marginTop:6 }}>
                  {[
                    {l:'כניסה', v:(p.breakoutLevel||0).toFixed(2), c:'#a78bfa'},
                    {l:'סטופ',  v:(p.stopLevel||0).toFixed(2), c:'#ef5350'},
                    {l:'רמה',  v:(p.keyLevel||0).toFixed(2), c:p.col},
                  ].map(({l,v,c})=>(
                    <div key={l} style={{ background:'#0d1117', borderRadius:5, padding:'4px 6px', textAlign:'center' }}>
                      <div style={{ fontSize:14, color:'#4a5568' }}>{l}</div>
                      <div style={{ fontSize:14, fontWeight:700, color:c, fontFamily:'monospace' }}>{v}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Trade Journal — יומן מסחר ────────────────────────────────────────────────
function TradeJournal({ live }:{ live:MarketData|null }) {
  const [trades, setTrades]       = useState<any[]>([]);
  const [analysis, setAnalysis]   = useState<Record<string,any>>({});
  const [loading, setLoading]     = useState<Record<string,boolean>>({});
  const [showForm, setShowForm]   = useState(false);
  const [showFills, setShowFills] = useState(true);
  const [form, setForm]           = useState({ side:'LONG', entry:'', stop:'', t1:'', t2:'', setup:'', notes:'' });

  const price    = live?.price || 0;
  const sierraFills = live?.order_fills || [];

  // טעינת עסקאות
  const fetchTrades = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/trades`, { cache:'no-store' });
      if (r.ok) setTrades(await r.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchTrades();
    const t = setInterval(fetchTrades, 5000);
    return () => clearInterval(t);
  }, [fetchTrades]);

  // שמירת עסקה חדשה
  const saveTrade = async () => {
    if (!form.entry) return;
    const entry = parseFloat(form.entry);
    const stop  = parseFloat(form.stop) || 0;
    const t1    = parseFloat(form.t1) || 0;
    const t2    = parseFloat(form.t2) || 0;
    const rr    = stop > 0 ? Math.abs((t1 - entry) / (entry - stop)) : 0;
    const trade = {
      id:           Date.now().toString(),
      ts_open:      Math.floor(Date.now() / 1000),
      side:         form.side,
      entry_price:  entry,
      stop,
      t1, t2,
      setup:        form.setup,
      notes:        form.notes,
      status:       'OPEN',
      exit_price:   null,
      pnl_pts:      null,
      pnl_usd:      null,
      rr_planned:   Math.round(rr * 10) / 10,
      // הוסף הקשר שוק בכניסה
      ctx: {
        day_type:   (live as any)?.day?.type || '',
        phase:      live?.session?.phase || '',
        vwap_above: live?.vwap?.above || false,
        cci14:      (live as any)?.woodies_cci?.cci14 || 0,
        cvd_trend:  live?.cvd?.trend || '',
      }
    };
    await fetch(`${API_URL}/trades`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(trade)
    });
    setShowForm(false);
    setForm({ side:'LONG', entry:'', stop:'', t1:'', t2:'', setup:'', notes:'' });
    fetchTrades();
  };

  // סגירת עסקה
  const closeTrade = async (trade: any) => {
    const exit    = price;
    const pnlPts  = trade.side === 'LONG' ? exit - trade.entry_price : trade.entry_price - exit;
    const updated = { ...trade, status:'CLOSED', exit_price:exit, pnl_pts:Math.round(pnlPts*4)/4, pnl_usd:Math.round(pnlPts*5*100)/100, ts_close:Math.floor(Date.now()/1000) };
    await fetch(`${API_URL}/trades/${trade.id}`, { method: 'DELETE' });
    await fetch(`${API_URL}/trades`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(updated)
    });
    fetchTrades();
  };

  // ניתוח AI
  const analyzeTradeAI = async (tradeId: string) => {
    setLoading(p => ({ ...p, [tradeId]: true }));
    try {
      const r = await fetch(`${API_URL}/trades/analyze/${tradeId}`);
      if (r.ok) {
        const data = await r.json();
        setAnalysis(p => ({ ...p, [tradeId]: data }));
      }
    } catch {}
    setLoading(p => ({ ...p, [tradeId]: false }));
  };

  const openTrades  = trades.filter(t => t.status === 'OPEN');
  const closedTrades = trades.filter(t => t.status === 'CLOSED');
  const totalPnl    = closedTrades.reduce((s, t) => s + (t.pnl_usd || 0), 0);
  const wins        = closedTrades.filter(t => (t.pnl_pts || 0) > 0).length;
  const wr          = closedTrades.length > 0 ? Math.round(wins / closedTrades.length * 100) : 0;

  const actionCol: Record<string,string> = { HOLD:'#22c55e', EXIT:'#ef5350', MOVE_BE:'#f59e0b', PARTIAL:'#60a5fa' };
  const actionHeb: Record<string,string> = { HOLD:'המשך', EXIT:'צא עכשיו', MOVE_BE:'הזז ל-BE', PARTIAL:'קח חלקי' };

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:8 }}>

      {/* Stats bar */}
      {closedTrades.length > 0 && (
        <div style={{ display:'flex', gap:6 }}>
          {[
            { label:'עסקאות', val:closedTrades.length, col:'#94a3b8' },
            { label:'WR', val:`${wr}%`, col:wr>=55?G:wr>=45?Y:R },
            { label:'PnL', val:`${totalPnl>=0?'+':''}$${totalPnl.toFixed(0)}`, col:totalPnl>=0?G:R },
          ].map(s => (
            <div key={s.label} style={{ flex:1, background:'#111827', border:'1px solid #1e2738', borderRadius:7, padding:'6px 8px', textAlign:'center' }}>
              <div style={{ fontSize:14, color:'#4a5568', marginBottom:2 }}>{s.label}</div>
              <div style={{ fontSize:14, fontWeight:800, color:s.col, fontFamily:'monospace' }}>{s.val}</div>
            </div>
          ))}
        </div>
      )}

      {/* כפתור עסקה חדשה */}
      <button onClick={() => setShowForm(!showForm)} style={{ background:showForm?'#1e2738':'#7f77dd22', border:'1px solid #7f77dd44', borderRadius:7, padding:'7px', color:'#a78bfa', fontSize:14, fontWeight:700, cursor:'pointer', fontFamily:'inherit' }}>
        {showForm ? '✕ סגור' : '+ עסקה חדשה'}
      </button>

      {/* טופס עסקה חדשה */}
      {showForm && (
        <div style={{ background:'#0d1117', border:'1px solid #7f77dd44', borderRadius:8, padding:10, display:'flex', flexDirection:'column', gap:6 }}>
          {/* Side */}
          <div style={{ display:'flex', gap:4 }}>
            {['LONG','SHORT'].map(s => (
              <button key={s} onClick={() => setForm(p => ({...p, side:s}))}
                style={{ flex:1, padding:'5px', borderRadius:6, border:'none', cursor:'pointer', fontWeight:800, fontSize:14,
                  background: form.side===s ? (s==='LONG'?'#22c55e':'#ef5350') : '#1e2738',
                  color: form.side===s ? '#fff' : '#4a5568' }}>
                {s==='LONG'?'▲ LONG':'▼ SHORT'}
              </button>
            ))}
          </div>
          {/* Fields */}
          {[
            { key:'entry', label:'כניסה', placeholder:price.toFixed(2) },
            { key:'stop',  label:'סטופ',  placeholder:'' },
            { key:'t1',    label:'T1',    placeholder:'' },
            { key:'t2',    label:'T2',    placeholder:'' },
          ].map(f => (
            <div key={f.key} style={{ display:'flex', alignItems:'center', gap:6 }}>
              <span style={{ fontSize:14, color:'#6b7280', minWidth:36, textAlign:'right' }}>{f.label}</span>
              <input value={(form as any)[f.key]} onChange={e => setForm(p => ({...p,[f.key]:e.target.value}))}
                placeholder={f.placeholder}
                style={{ flex:1, background:'#1e2738', border:'1px solid #2d3a4a', borderRadius:5, padding:'4px 8px', color:'#e2e8f0', fontSize:14, fontFamily:'monospace', outline:'none' }} />
            </div>
          ))}
          {/* Setup */}
          <select value={form.setup} onChange={e => setForm(p => ({...p,setup:e.target.value}))}
            style={{ background:'#1e2738', border:'1px solid #2d3a4a', borderRadius:5, padding:'4px 8px', color:'#e2e8f0', fontSize:14, fontFamily:'inherit' }}>
            <option value=''>בחר סטאפ</option>
            {['Liq Sweep','VWAP Pullback','IB Breakout','CCI Turbo','אחר'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <button onClick={saveTrade}
            style={{ background:'#7f77dd', border:'none', borderRadius:6, padding:'7px', color:'#fff', fontSize:14, fontWeight:700, cursor:'pointer', fontFamily:'inherit' }}>
            ✓ שמור עסקה
          </button>
        </div>
      )}

      {/* עסקאות פתוחות */}
      {openTrades.map(trade => {
        const pnlPts = trade.side === 'LONG' ? price - trade.entry_price : trade.entry_price - price;
        const pnlUsd = pnlPts * 5 * (trade.qty || 1);
        const col    = trade.side === 'LONG' ? G : R;
        const ai     = analysis[trade.id];
        const aiCol  = ai ? (actionCol[ai.action] || '#94a3b8') : '#4a5568';
        const entry  = trade.entry_price || 0;
        const stop   = trade.stop || 0;
        const t1     = trade.t1 || 0;
        const t2     = trade.t2 || 0;
        const risk   = stop ? Math.abs(entry - stop) : 0;
        const rr     = risk > 0 ? (pnlPts / risk) : 0;

        // האם מחיר קרוב לסטופ (25% מהריסק)
        const stopNear = stop && risk > 0 && Math.abs(price - stop) < risk * 0.25;

        return (
          <div key={trade.id} style={{ background:'#0d1117', border:`1.5px solid ${stopNear?'#ef5350':col}44`, borderRadius:8, overflow:'hidden' }}>

            {/* Header — PnL */}
            <div style={{ background:`${col}12`, padding:'8px 10px', borderBottom:`1px solid ${col}22` }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <span style={{ fontSize:14, fontWeight:800, color:col }}>
                  {trade.side==='LONG'?'▲':'▼'} {trade.side} {trade.qty>1?`×${trade.qty}`:''} — {trade.setup||'Sierra'}
                </span>
                <span style={{ fontSize:14, fontWeight:800, color:pnlPts>=0?G:R, fontFamily:'monospace' }}>
                  {pnlPts>=0?'+':''}{pnlPts.toFixed(2)}pt
                </span>
              </div>
              <div style={{ display:'flex', justifyContent:'space-between', marginTop:2 }}>
                <span style={{ fontSize:14, color:'#6b7280', fontFamily:'monospace' }}>
                  כניסה {entry.toFixed(2)} → {price.toFixed(2)}
                </span>
                <span style={{ fontSize:14, fontWeight:700, color:pnlUsd>=0?G:R, fontFamily:'monospace' }}>
                  {pnlUsd>=0?'+':''}${pnlUsd.toFixed(0)}
                  {risk>0 && <span style={{color:'#6b7280',fontSize:14}}> ({rr>=0?'+':''}{rr.toFixed(1)}R)</span>}
                </span>
              </div>
            </div>

            {/* תוכנית יציאה */}
            <div style={{ padding:'8px 10px', borderBottom:'1px solid #1e2738' }}>
              <div style={{ fontSize:14, color:'#4a5568', marginBottom:5 }}>תוכנית יציאה</div>
              <div style={{ display:'flex', flexDirection:'column', gap:3 }}>

                {/* סטופ */}
                {stop > 0 ? (
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
                    background: stopNear ? '#ef535018' : '#0a0a0f',
                    border: `1px solid ${stopNear?'#ef5350':'#1e2738'}`, borderRadius:5, padding:'4px 8px' }}>
                    <span style={{ fontSize:14, color:'#ef5350', fontWeight:700 }}>
                      {stopNear ? '⚠ סטופ קרוב!' : '✕ סטופ'}
                    </span>
                    <span style={{ fontSize:14, fontFamily:'monospace', color:'#ef5350', fontWeight:700 }}>{stop.toFixed(2)}</span>
                    {risk > 0 && <span style={{ fontSize:14, color:'#4a5568' }}>−{risk.toFixed(2)}pt / −${(risk*5).toFixed(0)}</span>}
                  </div>
                ) : (
                  <div style={{ background:'#ef535011', border:'1px solid #ef535033', borderRadius:5, padding:'4px 8px', fontSize:14, color:'#ef5350' }}>
                    ⚠ אין סטופ מוגדר!
                  </div>
                )}

                {/* T1 */}
                {t1 > 0 && (
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
                    background: price >= t1 && trade.side==='LONG' || price <= t1 && trade.side==='SHORT' ? '#22c55e18' : '#0a0a0f',
                    border:'1px solid #22c55e22', borderRadius:5, padding:'4px 8px' }}>
                    <span style={{ fontSize:14, color:G, fontWeight:700 }}>⊕ T1 · C1</span>
                    <span style={{ fontSize:14, fontFamily:'monospace', color:G, fontWeight:700 }}>{t1.toFixed(2)}</span>
                    {risk > 0 && <span style={{ fontSize:14, color:'#4a5568' }}>+{risk.toFixed(2)}pt / +${(risk*5).toFixed(0)}</span>}
                  </div>
                )}

                {/* T2 */}
                {t2 > 0 && (
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
                    background:'#0a0a0f', border:'1px solid #16a34a22', borderRadius:5, padding:'4px 8px' }}>
                    <span style={{ fontSize:14, color:'#16a34a', fontWeight:700 }}>⊕ T2 · C2</span>
                    <span style={{ fontSize:14, fontFamily:'monospace', color:'#16a34a', fontWeight:700 }}>{t2.toFixed(2)}</span>
                    {risk > 0 && <span style={{ fontSize:14, color:'#4a5568' }}>+{(risk*2).toFixed(2)}pt / +${(risk*10).toFixed(0)}</span>}
                  </div>
                )}

                {/* אם אין T1/T2 */}
                {!t1 && !t2 && (
                  <div style={{ background:'#f59e0b11', border:'1px solid #f59e0b33', borderRadius:5, padding:'4px 8px', fontSize:14, color:Y }}>
                    ⚠ הגדר T1/T2 לניהול פוזיציה
                  </div>
                )}
              </div>
            </div>

            {/* AI Analysis */}
            {ai && (
              <div style={{ padding:'7px 10px', background:`${aiCol}11`, borderBottom:`1px solid ${aiCol}22` }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:3 }}>
                  <span style={{ fontSize:14, fontWeight:800, color:aiCol }}>{actionHeb[ai.action] || ai.action}</span>
                  <span style={{ fontSize:14, color:'#6b7280' }}>ביטחון {ai.confidence}%</span>
                </div>
                <div style={{ fontSize:14, color:'#94a3b8', direction:'rtl', textAlign:'right', lineHeight:1.5 }}>{ai.reason}</div>
                {ai.urgency === 'HIGH' && <div style={{ marginTop:4, fontSize:14, color:'#ef5350', fontWeight:700 }}>⚠ דחוף</div>}
              </div>
            )}

            {/* Actions */}
            <div style={{ display:'flex', gap:4, padding:'7px 10px' }}>
              <button onClick={() => analyzeTradeAI(trade.id)} disabled={loading[trade.id]}
                style={{ flex:1, background:'#7f77dd22', border:'1px solid #7f77dd44', borderRadius:5, padding:'5px', color:'#a78bfa', fontSize:14, cursor:'pointer', fontFamily:'inherit', fontWeight:700 }}>
                {loading[trade.id] ? '...' : '🤖 AI'}
              </button>
              <button onClick={() => closeTrade(trade)}
                style={{ flex:2, background:'#ef535022', border:'1px solid #ef535044', borderRadius:5, padding:'5px', color:'#ef5350', fontSize:14, cursor:'pointer', fontFamily:'inherit', fontWeight:700 }}>
                סגור @ {price.toFixed(2)}
              </button>
            </div>
          </div>
        );
      })}

      {/* עסקאות סגורות */}
      {closedTrades.length > 0 && (
        <>
          <div style={{ fontSize:14, color:'#4a5568', padding:'4px 2px', borderTop:'1px solid #1e2738', marginTop:2 }}>היסטוריה</div>
          {closedTrades.slice(0, 10).map(trade => {
            const won = (trade.pnl_pts || 0) > 0;
            const col = won ? G : R;
            return (
              <div key={trade.id} style={{ background:'#0d1117', border:`1px solid ${col}22`, borderRadius:7, padding:'8px 10px' }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                    <span style={{ fontSize:14, color:trade.side==='LONG'?G:R, fontWeight:700 }}>{trade.side==='LONG'?'▲':'▼'}</span>
                    <span style={{ fontSize:14, color:'#6b7280' }}>{trade.setup||'—'}</span>
                    {trade.ctx?.day_type && <span style={{ fontSize:14, color:'#4a5568' }}>{trade.ctx.day_type}</span>}
                  </div>
                  <div style={{ textAlign:'right' }}>
                    <span style={{ fontSize:14, fontWeight:800, color:col, fontFamily:'monospace' }}>
                      {(trade.pnl_pts||0)>=0?'+':''}{(trade.pnl_pts||0).toFixed(2)}pt
                    </span>
                    <span style={{ fontSize:14, color:col, fontFamily:'monospace', marginLeft:6 }}>
                      {(trade.pnl_usd||0)>=0?'+':''}${(trade.pnl_usd||0).toFixed(0)}
                    </span>
                  </div>
                </div>
                <div style={{ display:'flex', gap:8, marginTop:3, fontSize:14, color:'#4a5568', fontFamily:'monospace' }}>
                  <span>{trade.entry_price} → {trade.exit_price}</span>
                  {trade.rr_planned>0 && <span>R:R {trade.rr_planned}</span>}
                </div>
              </div>
            );
          })}
        </>
      )}

      {trades.length === 0 && !showForm && sierraFills.length === 0 && (
        <div style={{ padding:'20px 12px', textAlign:'center', color:'#4a5568', fontSize:14, direction:'rtl' }}>
          <div style={{ fontSize:24, marginBottom:8 }}>📒</div>
          <div>יומן מסחר ריק</div>
          <div style={{ fontSize:14, marginTop:4, color:'#2d3a4a' }}>לחץ + לפתוח עסקה חדשה</div>
        </div>
      )}

      {/* פקודות Sierra Chart — בזמן אמת */}
      {sierraFills.length > 0 && (
        <>
          <div
            onClick={() => setShowFills(p => !p)}
            style={{ fontSize:14, color:'#60a5fa', padding:'4px 2px', borderTop:'1px solid #1e2738', marginTop:2, cursor:'pointer', display:'flex', justifyContent:'space-between' }}>
            <span>📡 פקודות Sierra ({sierraFills.length})</span>
            <span>{showFills ? '▲' : '▼'}</span>
          </div>
          {showFills && sierraFills.map((f, i) => {
            const isBuy = f.side === 'BUY';
            const col   = isBuy ? G : R;
            const pnl   = (price - f.price) * (isBuy ? 1 : -1) * Math.abs(f.qty);
            const ts    = new Date(f.ts * 1000).toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false, timeZone:'America/New_York' });
            return (
              <div key={i} style={{ background:'#0d1117', border:`1px solid ${col}33`, borderRadius:7, padding:'7px 10px', borderLeft:`3px solid ${col}` }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <span style={{ fontSize:14, fontWeight:800, color:col }}>{isBuy?'▲ BUY':'▼ SELL'} {Math.abs(f.qty)}</span>
                  <span style={{ fontSize:14, color:'#4a5568', fontFamily:'monospace' }}>{ts} ET</span>
                </div>
                <div style={{ display:'flex', justifyContent:'space-between', marginTop:3 }}>
                  <span style={{ fontSize:14, fontFamily:'monospace', color:'#e2e8f0', fontWeight:700 }}>{f.price.toFixed(2)}</span>
                  <span style={{ fontSize:14, fontWeight:700, color:pnl>=0?G:R, fontFamily:'monospace' }}>
                    {pnl>=0?'+':''}{(pnl*5).toFixed(0)}$
                  </span>
                </div>
                {f.pos !== undefined && f.pos !== 0 && (
                  <div style={{ fontSize:14, color:'#4a5568', marginTop:2 }}>
                    פוז: {f.pos>0?`▲ ${f.pos}`:f.pos<0?`▼ ${Math.abs(f.pos)}`:'FLAT'}
                  </div>
                )}
              </div>
            );
          })}
        </>
      )}
      {/* ── Trade Log — עסקאות סגורות ── */}
      <TradeLogSection />
    </div>
  );
}

function TradeLogSection() {
  const [log, setLog] = useState<any[]>([]);
  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`${API_URL}/trades/log?limit=50`, { cache: 'no-store' });
        if (r.ok) setLog(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);

  const today = new Date().toISOString().slice(0, 10);
  const todayTrades = log.filter(t => {
    const d = new Date((t.exit_ts || 0) * 1000).toISOString().slice(0, 10);
    return d === today;
  });
  const prevTrades = log.filter(t => {
    const d = new Date((t.exit_ts || 0) * 1000).toISOString().slice(0, 10);
    return d !== today;
  }).slice(0, 5);

  const wins = todayTrades.filter(t => t.win);
  const totalPnl = todayTrades.reduce((s, t) => s + (t.pnl_usd || 0), 0);
  const avgPnl = todayTrades.length ? todayTrades.reduce((s, t) => s + (t.pnl_pts || 0), 0) / todayTrades.length : 0;
  const avgRR = todayTrades.filter(t => t.rr_actual).length
    ? todayTrades.filter(t => t.rr_actual).reduce((s, t) => s + t.rr_actual, 0) / todayTrades.filter(t => t.rr_actual).length : 0;
  const winRate = todayTrades.length ? Math.round(wins.length / todayTrades.length * 100) : 0;

  const TradeCard = ({ t, faded }: { t: any; faded?: boolean }) => {
    const isWin = t.win;
    const col = isWin ? '#22c55e' : '#ef4444';
    const bg = isWin ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)';
    const exitTime = new Date((t.exit_ts || 0) * 1000).toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit', hour12:false, timeZone:'America/New_York' });
    const dateStr = faded ? new Date((t.exit_ts || 0) * 1000).toLocaleDateString('he-IL', { day:'2-digit', month:'2-digit' }) + ' ' : '';
    return (
      <div style={{ padding:'6px 8px', borderRadius:6, background: faded ? '#0d111733' : bg, border:`1px solid ${faded ? '#1e273844' : col+'22'}`,
        opacity: faded ? 0.5 : 1, marginBottom:3 }}>
        <div style={{ display:'flex', gap:6, alignItems:'center', fontSize:14, marginBottom:3 }}>
          <span style={{ color:'#64748b' }}>{dateStr}{exitTime}</span>
          <span style={{ color: t.direction==='LONG'?'#22c55e':'#ef4444', fontWeight:800, padding:'1px 5px', borderRadius:3,
            background: t.direction==='LONG'?'#14532d':'#450a0a', fontSize:14 }}>
            {t.direction==='LONG'?'▲ LONG':'▼ SHORT'}
          </span>
          {t.setup_type && <span style={{ fontSize:8, color:'#7f77dd', background:'#7f77dd22', padding:'1px 4px', borderRadius:3 }}>{t.setup_type}</span>}
          {t.killzone && <span style={{ fontSize:8, color:'#f59e0b', background:'#f59e0b22', padding:'1px 4px', borderRadius:3 }}>{t.killzone}</span>}
          {t.day_type && <span style={{ fontSize:8, color:'#64748b' }}>{t.day_type}</span>}
        </div>
        <div style={{ display:'flex', gap:8, fontSize:14, color:'#94a3b8', marginBottom:2 }}>
          <span>כניסה: {t.entry_price?.toFixed(2)}</span>
          <span>→</span>
          <span>יציאה: {t.exit_price?.toFixed(2)}</span>
          {t.duration_min != null && <span style={{ color:'#4a5568' }}>| {t.duration_min < 1 ? '<1' : Math.round(t.duration_min)}מ'</span>}
          {t.close_reason && <span style={{ color:'#4a5568' }}>| {t.close_reason}</span>}
        </div>
        <div style={{ display:'flex', gap:10, fontSize:14, fontWeight:700 }}>
          <span style={{ color:col }}>{(t.pnl_pts||0)>=0?'+':''}{t.pnl_pts?.toFixed(2)}pt</span>
          <span style={{ color:col }}>{(t.pnl_usd||0)>=0?'+':''}${t.pnl_usd?.toFixed(0)}</span>
          {t.rr_actual != null && <span style={{ color:'#f59e0b', fontSize:14 }}>R:R 1:{t.rr_actual.toFixed(1)}</span>}
        </div>
      </div>
    );
  };

  return (
    <div style={{ borderTop:'1px solid #1e2738', marginTop:8, paddingTop:8 }}>
      <div style={{ fontSize:14, fontWeight:700, color:'#94a3b8', marginBottom:6, display:'flex', justifyContent:'space-between', flexWrap:'wrap', gap:4 }}>
        <span>📋 עסקאות היום</span>
        {todayTrades.length > 0 && (
          <span style={{ color: totalPnl>=0?'#22c55e':'#ef4444' }}>
            סה״כ: {totalPnl>=0?'+':''}{totalPnl.toFixed(0)}$ | {todayTrades.length} עסקאות | Win: {winRate}%
          </span>
        )}
      </div>
      {todayTrades.length === 0 ? (
        <div style={{ fontSize:14, color:'#4a5568', textAlign:'center', padding:8 }}>אין עסקאות היום עדיין</div>
      ) : (
        <>
          {todayTrades.map((t, i) => <TradeCard key={t.id||i} t={t} />)}
          <div style={{ display:'flex', gap:10, fontSize:14, color:'#64748b', padding:'4px 8px', borderTop:'1px solid #1e2738', marginTop:4 }}>
            <span>Win Rate: {wins.length}/{todayTrades.length} = {winRate}%</span>
            <span>ממוצע P&L: {avgPnl>=0?'+':''}{avgPnl.toFixed(2)}pt</span>
            {avgRR > 0 && <span>ממוצע R:R: 1:{avgRR.toFixed(1)}</span>}
          </div>
        </>
      )}
      {prevTrades.length > 0 && (
        <div style={{ marginTop:8 }}>
          <div style={{ fontSize:14, color:'#4a5568', marginBottom:4 }}>ימים קודמים</div>
          {prevTrades.map((t, i) => <TradeCard key={t.id||`p${i}`} t={t} faded />)}
        </div>
      )}
    </div>
  );
}

// ── Day Type SVG Icons ───────────────────────────────────────────────────────
function DayTypeSVG({ shape, color }: { shape: string; color: string }) {
  const s = { stroke: color, strokeWidth: 1.5, fill: 'none' };
  switch (shape) {
    case 'bell':
      return (
        <svg viewBox="0 0 40 36" width="40" height="36">
          <polyline points="2,34 8,28 12,16 20,6 28,16 32,28 38,34" {...s} />
          <line x1="2" y1="34" x2="38" y2="34" {...s} strokeWidth={1} />
        </svg>
      );
    case 'bell_tail':
      return (
        <svg viewBox="0 0 40 36" width="40" height="36">
          <polyline points="2,34 6,30 10,20 16,10 22,6 28,14 32,26 38,34" {...s} />
          <line x1="2" y1="16" x2="2" y2="34" stroke={color} strokeWidth={2.5} />
          <line x1="2" y1="34" x2="38" y2="34" {...s} strokeWidth={1} />
        </svg>
      );
    case 'trend':
      return (
        <svg viewBox="0 0 40 36" width="40" height="36">
          <rect x="14" y="4" width="12" height="30" fill={color} opacity={0.3} rx={2} />
          <rect x="14" y="4" width="12" height="30" {...s} rx={2} />
          <line x1="2" y1="34" x2="38" y2="34" {...s} strokeWidth={1} />
        </svg>
      );
    case 'double':
      return (
        <svg viewBox="0 0 40 36" width="40" height="36">
          <polyline points="2,34 5,28 8,18 12,12 16,18 19,28 22,34" {...s} />
          <polyline points="18,34 21,26 24,16 28,10 32,16 35,26 38,34" {...s} />
          <line x1="2" y1="34" x2="38" y2="34" {...s} strokeWidth={1} />
        </svg>
      );
    case 'wide':
      return (
        <svg viewBox="0 0 40 36" width="40" height="36">
          <polyline points="2,34 4,30 8,24 14,20 20,18 26,20 32,24 36,30 38,34" {...s} />
          <line x1="2" y1="34" x2="38" y2="34" {...s} strokeWidth={1} />
        </svg>
      );
    case 'narrow':
      return (
        <svg viewBox="0 0 40 36" width="40" height="36">
          <rect x="17" y="10" width="6" height="24" fill={color} opacity={0.2} rx={1} />
          <rect x="17" y="10" width="6" height="24" {...s} rx={1} />
          <line x1="2" y1="34" x2="38" y2="34" {...s} strokeWidth={1} />
        </svg>
      );
    default:
      return <svg viewBox="0 0 40 36" width="40" height="36" />;
  }
}

// ── Day Type Helpers ─────────────────────────────────────────────────────────
function getDayTypeRule(id: string): string {
  const rules: Record<string, string> = {
    NORMAL: 'מסחר דו-כיווני. קנה ב-VAL, מכור ב-VAH. IB בדרך כלל מוחזק.',
    NORMAL_VARIATION: 'מסחר בכיוון הזנב. אם זנב למעלה — Long בלבד מ-VWAP/VAL.',
    TREND_DAY: 'מסחר חד-כיווני בלבד. כניסות רק בכיוון הטרנד. אל תמכור חוזקה.',
    DOUBLE_DISTRIBUTION: 'זהירות בין שתי הדיסטריבוציות. מסחר רק בתוך כל דיסטריבוציה.',
    NEUTRAL: 'קנה בקצה התחתון, מכור בקצה העליון. הימנע מ-breakouts.',
    ROTATIONAL: 'אל תסחר — שוק ללא כיוון. המתן ליום טוב יותר.',
    DEVELOPING: 'IB לא נעול — אין סיווג סופי. המתן לשעה הראשונה לפני כניסה.',
    VOLATILE: 'תנועות חדות — הקטן גודל פוזיציה ל-50%. סטופ רחב יותר מהרגיל.',
  };
  return rules[id] || '—';
}

function getDayTypeLookFor(id: string): string {
  const lookFor: Record<string, string> = {
    NORMAL: 'Rejection מ-VAH/VAL עם נפח. Sweep של IBH/IBL ב-extension.',
    NORMAL_VARIATION: 'Pullback לאחר הזנב עם CVD חיובי. VWAP reclaim.',
    TREND_DAY: 'כל pullback קטן לרמת תמיכה — הזדמנות כניסה בכיוון הטרנד.',
    DOUBLE_DISTRIBUTION: 'Breakout ברור מהדיסטריבוציה הראשונה עם נפח גבוה.',
    NEUTRAL: 'נגיעה בקצוות הטווח עם rejection ברור + wick ארוך.',
    ROTATIONAL: 'אין — המתן ליום הבא.',
    DEVELOPING: 'המתן לנעילת ה-IB. בדוק Gap ו-day type שמתחיל להתגבש.',
    VOLATILE: 'Sweep ברור עם חזרה מהירה. המתן לאחר תנועה ראשונה לפני כניסה.',
  };
  return lookFor[id] || '—';
}

function getDayTypeAvoid(id: string): string {
  const avoid: Record<string, string> = {
    NORMAL: 'כניסות באמצע הטווח. breakouts מחוץ ל-IB בלי אישור נפח.',
    NORMAL_VARIATION: 'מסחר נגד כיוון הזנב. Fade של המגמה הראשונית.',
    TREND_DAY: 'כל כניסה נגד הטרנד. "קניית זול" בירידה חדה.',
    DOUBLE_DISTRIBUTION: 'מסחר באזור ה-gap בין שתי הדיסטריבוציות.',
    NEUTRAL: 'Breakouts — סיכוי גבוה ל-false breakout ביום ניטרלי.',
    ROTATIONAL: 'כל כניסה — יום ללא edge מובהק.',
    DEVELOPING: 'כניסות מוקדמות לפני שה-IB נעול ו-day type ברור.',
    VOLATILE: 'כניסה בתוך התנועה — המתן לסיום ה-spike ואישור כיוון.',
  };
  return avoid[id] || '—';
}

// ── D8: Active Trade Panel ────────────────────────────────────────────────
interface ActiveTrade {
  direction: 'LONG' | 'SHORT';
  setupType: string;
  entryPrice: number;
  stopPrice: number;
  t1: number;
  t2: number;
  t3: number;
  entryTs: number;
  healthScore: number;
  c1Status: 'open' | 'closed';
  c2Status: 'open' | 'closed';
  c3Status: 'open' | 'closed';
}

function getHealthColor(score: number): string {
  if (score >= 70) return '#FFD700';
  if (score >= 50) return '#B8A000';
  if (score >= 30) return '#FF8C00';
  return '#FF4500';
}

function ActiveTradePanel({ trade, currentPrice, onScaleC1, onScaleC2, onCloseAll }: {
  trade: ActiveTrade;
  currentPrice: number;
  onScaleC1: () => void;
  onScaleC2: () => void;
  onCloseAll: () => void;
}) {
  const isLong = trade.direction === 'LONG';
  const dirCol = isLong ? '#00bcd4' : '#e91e63';
  const pnlPts = isLong ? currentPrice - trade.entryPrice : trade.entryPrice - currentPrice;
  const pnlDollar = Math.round(pnlPts * 5);  // MES $5/pt
  const distStop = isLong ? currentPrice - trade.stopPrice : trade.stopPrice - currentPrice;
  const stopSize = Math.abs(trade.entryPrice - trade.stopPrice);
  const hCol = getHealthColor(trade.healthScore);
  const elapsed = Math.floor((Date.now() / 1000 - trade.entryTs) / 60);

  const targetRow = (label: string, price: number, status: string) => {
    const dist = isLong ? price - currentPrice : currentPrice - price;
    const hit = status === 'closed';
    return (
      <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, padding: '2px 0', opacity: hit ? 0.5 : 1 }}>
        <span style={{ color: '#6b7280' }}>{label}</span>
        <span style={{ color: '#fff', fontFamily: 'monospace' }}>{price.toFixed(2)}</span>
        <span style={{ color: dist > 0 ? '#22c55e' : '#ef5350', fontFamily: 'monospace' }}>{dist > 0 ? '+' : ''}{dist.toFixed(2)}</span>
        <span style={{ color: hit ? '#22c55e' : '#6b7280', fontSize: 14 }}>{hit ? 'CLOSED' : 'OPEN'}</span>
      </div>
    );
  };

  return (
    <div style={{ background: '#0d1117', borderTop: `2px solid ${dirCol}`, padding: '8px 12px', flexShrink: 0 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 800, color: dirCol }}>
            {isLong ? '▲ LONG' : '▼ SHORT'}
          </span>
          <span style={{ fontSize: 14, color: '#9ca3af' }}>{trade.setupType}</span>
        </div>
        <span style={{ fontSize: 14, color: '#6b7280', fontFamily: 'monospace' }}>{elapsed}m</span>
      </div>

      {/* Entry + Stop + P&L */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginBottom: 6, fontSize: 14 }}>
        <div>
          <div style={{ color: '#6b7280', fontSize: 14 }}>Entry</div>
          <div style={{ color: '#fff', fontFamily: 'monospace', fontWeight: 700 }}>{trade.entryPrice.toFixed(2)}</div>
        </div>
        <div>
          <div style={{ color: '#6b7280', fontSize: 14 }}>Stop ({stopSize.toFixed(1)}pt)</div>
          <div style={{ color: '#ef5350', fontFamily: 'monospace' }}>{trade.stopPrice.toFixed(2)}</div>
          <div style={{ color: distStop > 2 ? '#22c55e' : '#ef5350', fontSize: 14, fontFamily: 'monospace' }}>{distStop.toFixed(2)}pt away</div>
        </div>
        <div>
          <div style={{ color: '#6b7280', fontSize: 14 }}>P&L</div>
          <div style={{ color: pnlPts >= 0 ? '#22c55e' : '#ef5350', fontFamily: 'monospace', fontWeight: 700, fontSize: 14 }}>
            {pnlPts >= 0 ? '+' : ''}{pnlPts.toFixed(2)}pt
          </div>
          <div style={{ color: pnlDollar >= 0 ? '#22c55e' : '#ef5350', fontSize: 14, fontFamily: 'monospace' }}>
            ${pnlDollar >= 0 ? '+' : ''}{pnlDollar}
          </div>
        </div>
      </div>

      {/* Targets */}
      <div style={{ borderTop: '1px solid #1e2738', paddingTop: 4, marginBottom: 6 }}>
        {targetRow('T1/C1', trade.t1, trade.c1Status)}
        {targetRow('T2/C2', trade.t2, trade.c2Status)}
        {targetRow('T3/C3', trade.t3, trade.c3Status)}
      </div>

      {/* Health Score bar */}
      <div style={{ marginBottom: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginBottom: 2 }}>
          <span style={{ color: '#6b7280' }}>Health</span>
          <span style={{ color: hCol, fontWeight: 700 }}>{trade.healthScore}</span>
        </div>
        <div style={{ background: '#1e2738', borderRadius: 3, height: 6, overflow: 'hidden' }}>
          <div style={{ width: `${trade.healthScore}%`, height: '100%', background: hCol, borderRadius: 3, transition: 'width 0.5s, background 0.5s' }} />
        </div>
      </div>

      {/* Action buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
        <button onClick={onScaleC1} disabled={trade.c1Status === 'closed'}
          style={{ padding: '4px 0', fontSize: 14, fontWeight: 700, background: trade.c1Status === 'closed' ? '#1e2738' : '#1a3a2a', color: trade.c1Status === 'closed' ? '#4b5563' : '#22c55e', border: '1px solid #22c55e33', borderRadius: 4, cursor: trade.c1Status === 'closed' ? 'default' : 'pointer' }}>
          Scale C1
        </button>
        <button onClick={onScaleC2} disabled={trade.c2Status === 'closed'}
          style={{ padding: '4px 0', fontSize: 14, fontWeight: 700, background: trade.c2Status === 'closed' ? '#1e2738' : '#1a2a3a', color: trade.c2Status === 'closed' ? '#4b5563' : '#60a5fa', border: '1px solid #60a5fa33', borderRadius: 4, cursor: trade.c2Status === 'closed' ? 'default' : 'pointer' }}>
          Scale C2
        </button>
        <button onClick={onCloseAll}
          style={{ padding: '4px 0', fontSize: 14, fontWeight: 700, background: '#3a1a1a', color: '#ef5350', border: '1px solid #ef535033', borderRadius: 4, cursor: 'pointer' }}>
          Close All
        </button>
      </div>
    </div>
  );
}

// ── Bottom Trade Bar — persistent across all tabs ──────────────────────────
// ── Building Setup interface ──────────────────────────────────────────────
interface BuildingSetup {
  id: string;
  dir: 'long' | 'short';
  levelName: string;
  level: number;
  type: string;
  detectedAt: number;
  expiresAt: number;          // detectedAt + 10 bars * 180s
  p1Pass: boolean;
  p1Detail: string;
  p2Pass: boolean | null;     // null = not yet evaluated
  p2Detail: string;
  p3Pass: boolean | null;
  p3Detail: string;
  score: number;
  exitReason?: string;        // reason for expiry/invalidation
}

// ── Building Now Section — shows setups as they form ──────────────────────
function BuildingNowSection({ buildingSetups, expiredSetups }:{ buildingSetups: BuildingSetup[]; expiredSetups: BuildingSetup[] }) {
  const active = buildingSetups.filter(s => !s.exitReason);
  const pillarIcon = (pass: boolean | null) => pass === null ? '⏳' : pass ? '✅' : '❌';
  const pillarBg = (pass: boolean | null) => pass === null ? '#1e273822' : pass ? '#22c55e11' : '#ef535011';
  const pillarBorder = (pass: boolean | null) => pass === null ? '#2d3a4a' : pass ? '#22c55e44' : '#ef535044';

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:10 }}>
      <div style={{ fontSize:12, color:'#f6c90e', letterSpacing:2, marginBottom:6, fontWeight:700 }}>BUILDING NOW ({active.length})</div>
      {active.length === 0 ? (
        <div style={{ fontSize:12, color:'#4a5568', padding:'4px 0' }}>No sweep detected — waiting for P1 ZONE trigger</div>
      ) : (
        <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
          {active.map(s => {
            const col = s.dir === 'long' ? '#22c55e' : '#ef5350';
            const now = Date.now() / 1000;
            const alive = Math.max(0, Math.floor(now - s.detectedAt));
            const remaining = Math.max(0, Math.floor(s.expiresAt - now));
            const allPass = s.p1Pass && s.p2Pass === true && s.p3Pass === true;
            return (
              <div key={s.id} style={{ background:'#0a0e1a', border:`1px solid ${col}33`, borderRadius:6, padding:'8px 10px' }}>
                {/* Header */}
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6 }}>
                  <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                    <span style={{ fontSize:14, fontWeight:800, color:col }}>{s.dir==='long'?'▲':'▼'}</span>
                    <span style={{ fontSize:12, fontWeight:700, color:col }}>{s.type.toUpperCase()}</span>
                    <span style={{ fontSize:12, color:'#94a3b8' }}>{s.levelName} {s.level.toFixed(2)}</span>
                  </div>
                  <span style={{ fontSize:11, color: remaining < 120 ? '#ef5350' : '#4a5568', fontFamily:'monospace' }}>
                    {remaining > 0 ? `expires ${formatTime(remaining)}` : 'expired'}
                  </span>
                </div>
                {/* Pillar rows */}
                {[
                  { label: 'P1 ZONE', pass: s.p1Pass, detail: s.p1Detail },
                  { label: 'P2 PATTERN', pass: s.p2Pass, detail: s.p2Detail },
                  { label: 'P3 FLOW', pass: s.p3Pass, detail: s.p3Detail },
                ].map(p => (
                  <div key={p.label} style={{ display:'flex', alignItems:'center', gap:6, padding:'3px 6px', marginBottom:2,
                    background:pillarBg(p.pass), border:`1px solid ${pillarBorder(p.pass)}`, borderRadius:4 }}>
                    <span style={{ fontSize:11 }}>{pillarIcon(p.pass)}</span>
                    <span style={{ fontSize:11, fontWeight:700, color: p.pass===null?'#4a5568':p.pass?'#22c55e':'#ef5350', minWidth:60 }}>{p.label}</span>
                    <span style={{ fontSize:10, color:'#94a3b8', flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{p.detail}</span>
                  </div>
                ))}
                {/* Footer */}
                <div style={{ display:'flex', justifyContent:'space-between', marginTop:4, fontSize:10, color:'#4a5568' }}>
                  <span>Alive: {formatTime(alive)}</span>
                  <span>Score: {s.score}%</span>
                  {allPass && <span style={{ color:'#22c55e', fontWeight:700 }}>READY</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {/* Expired feed — last 5 */}
      {expiredSetups.length > 0 && (
        <div style={{ marginTop:8, borderTop:'1px solid #1e2738', paddingTop:6 }}>
          <div style={{ fontSize:10, color:'#4a5568', letterSpacing:1, marginBottom:4, fontWeight:700 }}>EXPIRED ({expiredSetups.length})</div>
          {expiredSetups.slice(0, 5).map(s => {
            const col = s.dir === 'long' ? '#22c55e44' : '#ef535044';
            return (
              <div key={s.id} style={{ fontSize:10, color:'#4a5568', padding:'2px 6px', marginBottom:1,
                background:'#0a0e1a', border:`1px solid ${col}`, borderRadius:3, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {s.exitReason || 'Expired'} — {s.dir==='long'?'▲':'▼'} {s.levelName} {s.level.toFixed(0)}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function BottomTradeBar({ opportunity, oppLevels, oppSweep, oppScore, liveSetup, onExecuteClick, checklistSetup }:{
  opportunity:string; oppLevels:any; oppSweep:any; oppScore:number;
  liveSetup:any; onExecuteClick:(setup:any)=>void; checklistSetup:any;
}) {
  const hasSetup = opportunity !== 'none' && oppLevels && oppLevels.entry > 0;
  const isLong = opportunity === 'long';
  const col = isLong ? '#22c55e' : '#ef5350';
  const riskPts = hasSetup ? oppLevels.riskPts : 0;
  const stopTooWide = riskPts > 8;
  const allPillarsPass = liveSetup?.setupEval?.pass === true;
  const canExecute = hasSetup && !stopTooWide && allPillarsPass;

  const cell = (label:string, value:string, color:string) => (
    <div style={{ textAlign:'center', padding:'2px 6px', minWidth:0 }}>
      <div style={{ fontSize:10, color:'#4a5568', lineHeight:1 }}>{label}</div>
      <div style={{ fontSize:13, fontWeight:700, color, fontFamily:'monospace', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{value}</div>
    </div>
  );

  if (!hasSetup) {
    return (
      <div style={{ position:'fixed', bottom:0, left:0, right:0, height:48, zIndex:9990,
        background:'#0f172a', borderTop:'1px solid #1e2738',
        display:'flex', alignItems:'center', justifyContent:'center', gap:12, padding:'0 16px' }}>
        <span style={{ fontSize:12, color:'#4a5568' }}>No valid setup — waiting for 3-pillar match</span>
        <button disabled style={{ padding:'6px 20px', borderRadius:6, fontSize:12, fontWeight:800,
          background:'#1e293b', color:'#334155', border:'none', cursor:'not-allowed', fontFamily:'inherit' }}>
          EXECUTE
        </button>
      </div>
    );
  }

  const risk = Math.abs(oppLevels.entry - oppLevels.stop);
  const rr1 = risk > 0 ? (Math.abs(oppLevels.c1 - oppLevels.entry) / risk).toFixed(1) : '—';
  const rr2 = risk > 0 ? (Math.abs(oppLevels.c2 - oppLevels.entry) / risk).toFixed(1) : '—';

  return (
    <div style={{ position:'fixed', bottom:0, left:0, right:0, height:52, zIndex:9990,
      background: stopTooWide ? '#1a0a0a' : '#0f172a',
      borderTop: `2px solid ${stopTooWide ? '#ef535066' : canExecute ? '#22c55e66' : '#1e2738'}`,
      display:'flex', alignItems:'center', gap:4, padding:'0 12px', overflow:'hidden' }}>
      {/* Setup label */}
      <div style={{ display:'flex', alignItems:'center', gap:4, flexShrink:0 }}>
        <span style={{ fontSize:14, fontWeight:800, color:col }}>{isLong?'▲':'▼'}</span>
        <span style={{ fontSize:11, fontWeight:700, color:col }}>{oppSweep?.type?.toUpperCase()?.slice(0,3) || '—'}</span>
        <span style={{ fontSize:11, color:'#94a3b8' }}>{oppSweep?.levelName || ''}</span>
      </div>
      <div style={{ width:1, height:28, background:'#1e2738', flexShrink:0 }} />
      {cell('Entry', (oppLevels.entry||0).toFixed(2), '#f0f6fc')}
      {cell('Stop', (oppLevels.stop||0).toFixed(2), '#ef5350')}
      {cell('Risk', `${riskPts}pt`, stopTooWide ? '#ef5350' : '#f59e0b')}
      <div style={{ width:1, height:28, background:'#1e2738', flexShrink:0 }} />
      {cell('T1', (oppLevels.c1||0).toFixed(2), '#22c55e')}
      {cell('T2', (oppLevels.c2||0).toFixed(2), '#16a34a')}
      {cell('T3', (oppLevels.c3||0).toFixed(2), '#86efac')}
      <div style={{ width:1, height:28, background:'#1e2738', flexShrink:0 }} />
      {cell('R:R', `1:${rr1} | 1:${rr2}`, '#94a3b8')}
      <div style={{ flex:1 }} />
      {stopTooWide && (
        <span style={{ fontSize:11, color:'#ef5350', fontWeight:700, flexShrink:0 }}>Stop too wide ({riskPts}pt &gt; 8pt)</span>
      )}
      <button
        disabled={!canExecute || !!checklistSetup}
        onClick={() => {
          if (!canExecute || !oppSweep) return;
          onExecuteClick({
            id: `${oppSweep.type}-${opportunity}-${oppSweep.levelName}`,
            dir: opportunity as 'long'|'short',
            entry: oppLevels.entry, stop: oppLevels.stop,
            t1: oppLevels.c1, t2: oppLevels.c2, t3: oppLevels.c3,
            riskPts: oppLevels.riskPts,
            levelName: oppSweep.levelName || '',
            sweepWick: 0,
            hasAbsorption: false, hasExhaustion: false,
          });
        }}
        style={{ padding:'8px 24px', borderRadius:6, fontSize:13, fontWeight:900,
          background: canExecute && !checklistSetup ? '#22c55e' : '#1e293b',
          color: canExecute && !checklistSetup ? '#0a0e1a' : '#334155',
          border:'none', cursor: canExecute && !checklistSetup ? 'pointer' : 'not-allowed',
          fontFamily:'inherit', flexShrink:0,
          boxShadow: canExecute ? '0 0 16px rgba(34,197,94,0.3)' : 'none',
          transition:'all 0.3s' }}>
        EXECUTE
      </button>
    </div>
  );
}

// ── Right Panel — טאבים חסכוניים ──────────────────────────────────────────
function RightPanel({ live, candles, accepted, lockedSignal, persistedSignal, signalTime, aiLoading, aiError, onAskAI, dayLoading, onAskDayType, dayExplanation, selectedSetup, onSelectSetup, sweepEvents, selectedSweep, setSelectedSweep, activeSetup, onActivateSweep, onDeactivateSetup, levelTouches, liveSetup, detectedSetups, selectedPattern, setSelectedPattern, onAccept, onReject, newsGuard, buildingSetups, expiredBuildingSetups }:any) {
  const [tab, setTab] = useState<'signal'|'setups'|'patterns'|'indicators'|'fills'|'daytype'|'analytics'>('signal');
  const scrollRef = useRef<HTMLDivElement>(null);
  // Reset scroll on tab change
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = 0; }, [tab]);
  // Auto-select first sweep when entering setups tab with nothing selected
  useEffect(() => {
    if (tab === 'setups' && !selectedSweep && sweepEvents?.length > 0) setSelectedSweep(sweepEvents[0]);
  }, [tab]); // eslint-disable-line react-hooks/exhaustive-deps
  const tabs = [
    { id:'signal',    label:'סיגנל', icon:'⚡' },
    { id:'setups',    label:'סטאפים', icon:'🔍' },
    { id:'patterns',  label:'תבניות', icon:'📈' },
    { id:'indicators',label:'נתונים', icon:'📊' },
    { id:'fills',     label:'פקודות', icon:'💼' },
    { id:'daytype',   label:'יום',    icon:'📅' },
    { id:'analytics', label:'אנליטיקה', icon:'📉' },
  ] as const;

  return (
    <div style={{ display:'flex', flexDirection:'column', overflow:'hidden', height:'100%', minHeight:0, borderLeft:'1px solid #1e2738', minWidth:0 }}>
      {/* Tab bar — icon + label, compact to fit 6 tabs in 260-420px */}
      <div style={{ display:'flex', borderBottom:'1px solid #1e2738', flexShrink:0 }}>
        {tabs.map(t=>(
          <button key={t.id} onClick={()=>setTab(t.id)}
            style={{ flex:'1 1 0', minWidth:0, padding:'4px 1px', border:'none', cursor:'pointer', fontFamily:'inherit',
              background: tab===t.id ? '#1e2738' : '#111827',
              borderBottom: tab===t.id ? '2px solid #7f77dd' : '2px solid transparent',
              color: tab===t.id ? '#e2e8f0' : '#4a5568', fontSize:10, fontWeight:700,
              display:'flex', flexDirection:'column', alignItems:'center', gap:0,
              overflow:'hidden' }}>
            <span style={{ fontSize:14, lineHeight:'18px' }}>{t.icon}</span>
            <span style={{ overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', maxWidth:'100%', lineHeight:'13px' }}>{t.label}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div ref={scrollRef} style={{ flex:1, minHeight:0, overflowY:'auto', padding:8, paddingBottom:60, display:'flex', flexDirection:'column', gap:7, overflowAnchor:'none' as any }}>

        {tab === 'signal' && <>
          <DayTypeBar live={live} onRequestExplanation={onAskDayType} aiLoading={dayLoading} />
          <MainScore
            live={accepted&&lockedSignal?{...live,signal:lockedSignal} as any:live}
            liveSetup={liveSetup}
            accepted={accepted}
            onAccept={onAccept}
            onReject={onReject}
            newsGuard={newsGuard}
          />
          <PillarBadges live={live} liveSetup={liveSetup} />
          <AIAnalysisPanel signal={persistedSignal} signalTime={signalTime} aiLoading={aiLoading} aiError={aiError} onAskAI={onAskAI} live={live} />
          <EntryZone live={live} signal={persistedSignal} />
        </>}

        {tab === 'setups' && <>
          {/* Selected sweep detail card */}
          {selectedSweep && (() => {
            const s = selectedSweep;
            const isLong = s.dir === 'long';
            const col = isLong ? '#22c55e' : '#ef5350';
            const isActive = activeSetup?.sweep?.id === s.id;
            return (
            <div style={{ background:'#0a0e1a', border:`2px solid ${col}44`, borderRadius:10, overflow:'hidden' }}>
              {/* Header */}
              <div style={{ background:`${col}18`, padding:'12px 16px', borderBottom:'1px solid #1e2738', borderLeft:`3px solid ${col}` }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <div>
                    <div style={{ fontSize:20, fontWeight:700, color:col }}>
                      {isLong?'▲':'▼'} SWEEP {s.levelName} @ {(s.level||0).toFixed(2)}
                    </div>
                    <div style={{ fontSize:14, color:'#6b7280' }}>
                      {(() => { const t = s.ts || s.detectedAt || 0; return t > 0 ? new Date(t*1000).toLocaleTimeString('he-IL') : '—'; })()} · {(s.levelTouches ?? 0) > 0 ? `${s.levelTouches} נגיעות` : ''} · Wick {(s.sweepWick||0).toFixed(1)}pt
                    </div>
                  </div>
                  <div style={{ textAlign:'right' }}>
                    <div style={{ fontSize:24, fontWeight:900, color:s.score>=90?'#22c55e':s.score>=75?'#f59e0b':'#4a5568' }}>{s.score}/100</div>
                    <div style={{ fontSize:14, color:s.confirmed?'#22c55e':'#f59e0b', fontWeight:700 }}>
                      {s.confirmed ? '✓ מאושר' : '⏳ ממתין'}
                    </div>
                  </div>
                </div>
                {/* Stats row */}
                <div style={{ display:'flex', gap:6, marginTop:8 }}>
                  {[
                    { label:'Delta', val: s.delta!=null ? `${s.delta>0?'+':''}${s.delta}` : '—', col: (s.delta||0)>=0?'#22c55e':'#ef5350' },
                    { label:'Vol', val: s.relVol!=null ? `${s.relVol}x` : '—', col: (s.relVol||0)>=1.3?'#22c55e':'#4a5568' },
                    { label:'Risk', val: s.riskPts!=null ? `${s.riskPts}pt` : '—', col:'#f59e0b' },
                    { label:'אישור Δ', val: s.confirmDelta!=null ? `${s.confirmDelta>0?'+':''}${s.confirmDelta}` : '—', col: s.confirmed?'#22c55e':'#ef5350' },
                  ].map(x => (
                    <div key={x.label} style={{ background:'#0a0e1a', borderRadius:4, padding:'4px 8px', textAlign:'center', flex:1, minWidth:0, overflow:'hidden' }}>
                      <div style={{ fontSize:14, color:'#4a5568' }}>{x.label}</div>
                      <div style={{ fontSize:15, fontWeight:800, color:x.col, fontFamily:'monospace' }}>{x.val}</div>
                    </div>
                  ))}
                </div>
              </div>
              {/* Entry / Stop */}
              <div style={{ padding:'12px 16px' }}>
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:8 }}>
                  <div style={{ background:'#1e2738', borderRadius:6, padding:'8px 12px' }}>
                    <div style={{ fontSize:14, color:'#94a3b8', marginBottom:2 }}>כניסה</div>
                    <div style={{ fontSize:26, fontWeight:800, color:'#f0f6fc', fontFamily:'monospace' }}>{(s.entry||0).toFixed(2)}</div>
                  </div>
                  <div style={{ background:'#1e2738', borderRadius:6, padding:'8px 12px' }}>
                    <div style={{ fontSize:14, color:'#ef5350', marginBottom:2 }}>✕ סטופ</div>
                    <div style={{ fontSize:26, fontWeight:800, color:'#ef5350', fontFamily:'monospace' }}>{(s.stop||0).toFixed(2)}</div>
                    <div style={{ fontSize:14, color:'#4a5568' }}>−{s.riskPts}pt / −${Math.round(s.riskPts*5*3)}</div>
                  </div>
                </div>
                {/* C1 / C2 / C3 */}
                <div style={{ display:'grid', gridTemplateColumns:'repeat(3, minmax(0, 1fr))', gap:6 }}>
                  {[
                    { label:'① C1 · 50%', price:s.c1, desc:'R:R 1:1 → BE', col:'#22c55e' },
                    { label:'② C2 · 25%', price:s.c2, desc:'R:R 1:2', col:'#16a34a' },
                    { label:'③ C3 · 25%', price:s.c3, desc:'Runner', col:'#86efac' },
                  ].map(t => {
                    const pts = Math.abs(t.price - s.entry);
                    return (
                      <div key={t.label} style={{ background:`${t.col}11`, border:`1px solid ${t.col}33`, borderRadius:6, padding:'4px 5px', textAlign:'center' }}>
                        <div style={{ fontSize:14, color:t.col, fontWeight:700 }}>{t.label}</div>
                        <div style={{ fontSize:14, fontWeight:800, color:t.col, fontFamily:'monospace' }}>{t.price.toFixed(2)}</div>
                        <div style={{ fontSize:14, color:'#4a5568' }}>+{pts.toFixed(1)}pt +${Math.round(pts*5)}</div>
                        <div style={{ fontSize:14, color:'#2d3a4a' }}>{t.desc}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
              {/* Time estimates */}
              {isActive && activeSetup.status === 'ACTIVE' && (
                <div style={{ padding:'8px 14px', borderTop:'1px solid #1e2738', fontSize:14, color:'#6b7280' }}>
                  <div style={{ fontWeight:700, color:'#94a3b8', marginBottom:3 }}>זמן משוער:</div>
                  <div>C1 בעוד ~{activeSetup.t1EstBars} נרות ({activeSetup.t1EstBars*3}-{activeSetup.t1EstBars*6} דק')</div>
                  <div>C2 בעוד ~{activeSetup.t2EstBars} נרות ({activeSetup.t2EstBars*3}-{activeSetup.t2EstBars*6} דק')</div>
                </div>
              )}
              {/* Status result */}
              {isActive && activeSetup.status !== 'ACTIVE' && (
                <div style={{ padding:'10px 14px', borderTop:'1px solid #1e2738', textAlign:'center' }}>
                  <div style={{ fontSize:16, fontWeight:800, color: activeSetup.status==='STOPPED'?'#ef5350':'#22c55e' }}>
                    {activeSetup.status==='STOPPED' ? '❌' : '✅'} {activeSetup.result}
                  </div>
                </div>
              )}
              {/* Buttons */}
              <div style={{ padding:'6px 14px 10px', borderTop:'1px solid #1e2738', display:'flex', gap:6 }}>
                {(!activeSetup || activeSetup.sweep?.id !== s.id) ? (
                  <button onClick={()=>onActivateSweep(s)} style={{ flex:1, padding:'6px', border:'none', borderRadius:5, background:'#22c55e', color:'#0a0e1a', fontSize:14, fontWeight:800, cursor:'pointer' }}>
                    הפעל על הגרף
                  </button>
                ) : (
                  <button onClick={()=>onDeactivateSetup()} style={{ flex:1, padding:'6px', border:'1px solid #ef535066', borderRadius:5, background:'transparent', color:'#ef5350', fontSize:14, fontWeight:700, cursor:'pointer' }}>
                    הסר מהגרף
                  </button>
                )}
                <button onClick={()=>setSelectedSweep(null)} style={{ padding:'6px 12px', border:'1px solid #1e2738', borderRadius:5, background:'transparent', color:'#6b7280', fontSize:14, cursor:'pointer' }}>✕</button>
              </div>
            </div>
            );
          })()}

          {/* Building Now — setups as they form */}
          <BuildingNowSection buildingSetups={buildingSetups || []} expiredSetups={expiredBuildingSetups || []} />

          {/* Detected setups — accumulated — always visible */}
          {(() => {
            const activeSetups = detectedSetups ? detectedSetups.filter((s:DetectedSetup)=>s.status!=='expired') : [];
            const count = activeSetups.length;

            // Build diagnosis when empty
            let diagnosis = '';
            if (count === 0 && liveSetup) {
              const parts: string[] = [];
              // Check killzone from live data
              const etStr = new Date().toLocaleString('en-US', { timeZone: 'America/New_York' });
              const etNow = new Date(etStr);
              const etMin = etNow.getHours() * 60 + etNow.getMinutes();
              const inKz = (etMin>=180&&etMin<300)||(etMin>=570&&etMin<630)||(etMin>=900&&etMin<960);
              if (!inKz) parts.push('Killzone OUTSIDE');
              if (liveSetup.setupEval) {
                const r = liveSetup.setupEval.reason;
                if (r.includes('P1')) parts.push('Pillar 1 ZONE');
                else if (r.includes('P2')) parts.push('Pillar 2 PATTERN');
                else if (r.includes('P3')) parts.push('Pillar 3 FLOW');
              } else if (liveSetup.opportunity === 'none') {
                parts.push('No pattern detected (score < 60%)');
              }
              if (parts.length > 0) diagnosis = `Blocked by: ${parts.join(' + ')}`;
            }

            return (
              <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:10 }}>
                <div style={{ fontSize:14, color:'#f6c90e', letterSpacing:2, marginBottom:6, fontWeight:700 }}>LIVE SETUPS ({count})</div>
                {count === 0 ? (
                  <div>
                    <div style={{ fontSize:13, color:Y, marginBottom:4 }}>No valid setup — waiting for 3-pillar match</div>
                    {diagnosis && <div style={{ fontSize:12, color:'#4a5568', fontFamily:'monospace' }}>{diagnosis}</div>}
                  </div>
                ) : (
                  <div style={{ display:'flex', flexDirection:'column', gap:3 }}>
                    {activeSetups.slice(0,15).map((s:DetectedSetup) => {
                      const isLong = s.dir === 'long';
                      const col = isLong ? G : R;
                      const statusCol = s.status==='stopped'?R : s.status==='c1_hit'||s.status==='c2_hit'?G : s.status==='detected'?Y : '#4a5568';
                      const statusIcon = s.status==='stopped'?'X' : s.status==='c1_hit'?'C1' : s.status==='c2_hit'?'C2' : s.status==='detected'?'!' : '?';
                      const time = new Date(s.detectedAt * 1000).toLocaleTimeString('he-IL', { hour:'2-digit', minute:'2-digit' });
                      return (
                        <div key={s.id} onClick={() => setSelectedSweep(s as any)}
                          style={{ display:'flex', alignItems:'center', gap:5, padding:'5px 8px', borderRadius:5, cursor:'pointer',
                            border:`1px solid ${col}33`, background:`${col}08` }}>
                          <span style={{ fontSize:15, color:col, fontWeight:700 }}>{isLong?'▲':'▼'}</span>
                          <span style={{ fontSize:14, color:col, fontWeight:700, minWidth:28 }}>{s.type.slice(0,3).toUpperCase()}</span>
                          <span style={{ fontSize:15, color:'#e2e8f0', fontWeight:600, minWidth:28 }}>{s.levelName}</span>
                          <span style={{ fontSize:14, color:'#4a5568' }}>{time}</span>
                          <span style={{ fontSize:14, color:'#4a5568', fontFamily:'monospace', flex:1 }}>E:{(s.entry||0).toFixed(0)}</span>
                          <span style={{ fontSize:14, fontWeight:800, color:statusCol, padding:'2px 6px', borderRadius:3, background:`${statusCol}22`, border:`1px solid ${statusCol}33` }}>
                            {statusIcon}
                          </span>
                          <span style={{ fontSize:15, fontWeight:800, color:col, fontFamily:'monospace' }}>{s.score}%</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })()}

          {/* Sweep events list */}
          <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:10 }}>
            <div style={{ fontSize:14, color:'#4a5568', letterSpacing:2, marginBottom:6, fontWeight:700 }}>SWEEP EVENTS ({sweepEvents.length})</div>
            {sweepEvents.length === 0 ? (
              <div style={{ padding:'12px', textAlign:'center', color:'#2d3a4a', fontSize:14 }}>אין sweep events בהיסטוריה</div>
            ) : (
              <div style={{ display:'flex', flexDirection:'column', gap:3 }}>
                {sweepEvents.slice(0, 20).map((ev:SweepEvent) => {
                  const sel = selectedSweep?.id === ev.id;
                  const isLong = ev.dir === 'long';
                  const time = new Date(ev.ts * 1000).toLocaleTimeString('he-IL', { hour:'2-digit', minute:'2-digit' });
                  const date = new Date(ev.ts * 1000).toLocaleDateString('he-IL', { day:'2-digit', month:'2-digit' });
                  return (
                    <div key={ev.id} onClick={() => setSelectedSweep(sel ? null : ev)}
                      style={{ display:'flex', alignItems:'center', gap:6, padding:'5px 8px', borderRadius:5, cursor:'pointer',
                        border: `1px solid ${sel ? (isLong?'#22c55e':'#ef5350')+'66' : '#1e2738'}`,
                        background: sel ? (isLong?'#22c55e':'#ef5350')+'11' : 'transparent',
                      }}>
                      <span style={{ fontSize:14, color:isLong?'#22c55e':'#ef5350', fontWeight:700 }}>{isLong?'▲':'▼'}</span>
                      <span style={{ fontSize:14, color:'#e2e8f0', fontWeight:600, minWidth:32 }}>{ev.levelName}</span>
                      <span style={{ fontSize:14, color:ev.confirmed?'#22c55e':'#f59e0b' }}>{ev.confirmed?'✓':'⏳'}</span>
                      <span style={{ fontSize:14, color:'#4a5568', flex:1 }}>{date} {time}</span>
                      <span style={{ fontSize:14, color:'#4a5568', fontFamily:'monospace' }}>{ev.relVol}x</span>
                      <span style={{ fontSize:14, fontWeight:800, color:ev.score>=90?'#22c55e':ev.score>=75?'#f59e0b':'#4a5568', fontFamily:'monospace', minWidth:28, textAlign:'right' }}>{ev.score}%</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Level touches */}
          {levelTouches.filter((lt:LevelTouch)=>lt.touches>=2).length > 0 && (
            <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:10 }}>
              <div style={{ fontSize:14, color:'#4a5568', letterSpacing:2, marginBottom:4 }}>LEVELS</div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
                {levelTouches.filter((lt:LevelTouch)=>lt.touches>=2).map((lt:LevelTouch) => (
                  <span key={lt.name} style={{ fontSize:14, padding:'2px 6px', borderRadius:4, background:'#1e2738', color:'#94a3b8', fontFamily:'monospace' }}>
                    {lt.name} {lt.price.toFixed(2)} <span style={{ color:'#f6c90e' }}>●{lt.touches}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </>}

        {tab === 'patterns' && <>
          <PatternScanner
            candles={candles||[]}
            onSelect={(p:PatternResult)=>setSelectedPattern((prev:any)=>prev?.id===p.id?null:p)}
            selectedId={selectedPattern?.id}
          />
          {selectedPattern && (
            <div style={{ padding:'8px 12px', background:'#0a1628', borderRadius:8, borderLeft:`3px solid ${selectedPattern.col}`, fontSize:14, color:'#94a3b8', direction:'rtl', textAlign:'right', lineHeight:1.7 }}>
              <div style={{ fontSize:14, color:selectedPattern.col, marginBottom:3 }}>💡 אסטרטגיה</div>
              {selectedPattern.direction==='long'
                ? 'כניסה על פריצת רמת ה-' + selectedPattern.nameHeb + '. סטופ מתחת לשפל התבנית. T1=R:R 1:1, T2=R:R 1:2.'
                : 'כניסה על שבירת רמת ה-' + selectedPattern.nameHeb + '. סטופ מעל לשיא התבנית. T1=R:R 1:1, T2=R:R 1:2.'}
            </div>
          )}
        </>}

        {tab === 'indicators' && <>
          <Indicators live={live} />
        </>}

        {tab === 'fills' && <>
          <TradeJournal live={live} />
        </>}

        {tab === 'daytype' && (
          <DayTypeTabContent live={live} />
        )}
        {tab === 'analytics' && <AnalyticsTab />}
        {false && (
          <div style={{ padding:'12px 10px', display:'flex', flexDirection:'column', gap:16 }}>
            <div style={{ fontSize:14, fontWeight:600, color:'#e2e8f0', textAlign:'center' }}>
              סוג יום — Market Profile OLD
            </div>
            {[
              { id:'NORMAL', label:'Normal', labelHe:'נורמלי', color:'#3b82f6', desc:'IB מאוזן, שני כיוונים אפשריים. מסחר בקצוות ה-IB.', shape:'bell' },
              { id:'NORMAL_VARIATION', label:'Normal Variation', labelHe:'נורמל + זנב', color:'#6366f1', desc:'כיוון ברור עם IB מורחב. כניסה בכיוון הזנב.', shape:'bell_tail' },
              { id:'TREND_DAY', label:'Trend', labelHe:'טרנד', color:'#10b981', desc:'יום חד-כיווני. תפוס breakouts, אל תמכור חוזקה.', shape:'trend' },
              { id:'DOUBLE_DISTRIBUTION', label:'Double Distribution', labelHe:'כפול', color:'#f59e0b', desc:'שני עולמות מחיר נפרדים. זהירות בין שניהם — VAH/VAL חלש.', shape:'double' },
              { id:'NEUTRAL', label:'Neutral', labelHe:'ניטרלי', color:'#64748b', desc:'שוק מהסס ורחב. קנה קצוות, מכור אמצע.', shape:'wide' },
              { id:'ROTATIONAL', label:'Non-Trend', labelHe:'ללא טרנד', color:'#ef4444', desc:'טווח צר מאוד. אל תסחר — מחכה לזרז.', shape:'narrow' },
              { id:'DEVELOPING', label:'Developing', labelHe:'מתפתח', color:'#475569', desc:'היום עדיין מתפתח — אין סיווג סופי. המתן לסגירת ה-IB.', shape:'narrow' },
              { id:'VOLATILE', label:'Volatile', labelHe:'תנודתי', color:'#f97316', desc:'תנועות חדות ומהירות לשני הכיוונים. סטופים רחבים יותר נדרשים.', shape:'bell_tail' },
            ].map((dt) => {
              const dtype = (live as any)?.day?.type || '';
              const isActive = dtype === dt.id;
              return (
                <div key={dt.id}>
                  <div style={{
                    background: isActive ? `${dt.color}22` : '#0f172a',
                    border: `1.5px solid ${isActive ? dt.color : '#1e2738'}`,
                    borderRadius:10, padding: isActive ? '10px 12px' : '8px 12px',
                    display:'flex', alignItems:'center', gap:12, transition:'all 0.2s',
                    opacity: isActive ? 1 : 0.6,
                  }}>
                    <div style={{ flexShrink:0, width:40, height:36 }}>
                      <DayTypeSVG shape={dt.shape} color={isActive ? dt.color : '#334155'} />
                    </div>
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:3 }}>
                        <span style={{ fontSize:14, fontWeight:700, color: isActive ? dt.color : '#94a3b8' }}>
                          {dt.labelHe}
                        </span>
                        {isActive && (
                          <span style={{ fontSize:14, fontWeight:700, background:dt.color, color:'#000', borderRadius:4, padding:'1px 5px' }}>
                            ✓ היום
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize:14, color:'#64748b', lineHeight:1.5, direction:'rtl' as const }}>
                        {dt.desc}
                      </div>
                    </div>
                  </div>
                  {isActive && (
                    <div style={{
                      background:'#0a0f1a', border:`1px solid ${dt.color}33`,
                      borderRadius:8, padding:'12px 14px', marginTop:-8,
                      display:'flex', flexDirection:'column', gap:10,
                    }}>
                      <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
                        {[
                          { label:'IB Range', value:`${((live as any)?.day?.ib_range || 0).toFixed(2)} pt` },
                          { label:'IB נעול', value:(live as any)?.day?.ib_locked ? '✓ כן' : '✗ לא',
                            color:(live as any)?.day?.ib_locked ? '#10b981' : '#ef4444' },
                          { label:'Gap', value:(live as any)?.day?.gap_type || 'FLAT' },
                          { label:'שלב', value:(live as any)?.session?.phase || '—' },
                        ].map(item => (
                          <div key={item.label} style={{
                            background:'#1e2738', borderRadius:6, padding:'5px 10px',
                            flex:'1 1 60px', minWidth:0, overflow:'hidden',
                          }}>
                            <div style={{ fontSize:14, color:'#64748b', marginBottom:2 }}>{item.label}</div>
                            <div style={{ fontSize:14, fontWeight:700, color:(item as any).color || '#e2e8f0', overflow:'hidden', minWidth:0 }}>
                              {item.value}
                            </div>
                          </div>
                        ))}
                      </div>
                      <div style={{ borderTop:'1px solid #1e2738', paddingTop:8 }}>
                        <div style={{ fontSize:14, color:'#94a3b8', marginBottom:6, fontWeight:600 }}>📋 כלל מסחר</div>
                        <div style={{ fontSize:14, color:'#cbd5e1', lineHeight:1.6, direction:'rtl' as const }}>{getDayTypeRule(dt.id)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize:14, color:'#94a3b8', marginBottom:6, fontWeight:600 }}>🎯 מה לחפש</div>
                        <div style={{ fontSize:14, color:'#cbd5e1', lineHeight:1.6, direction:'rtl' as const }}>{getDayTypeLookFor(dt.id)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize:14, color:'#ef444499', marginBottom:6, fontWeight:600 }}>⚠️ מה להימנע</div>
                        <div style={{ fontSize:14, color:'#94a3b8', lineHeight:1.6, direction:'rtl' as const, wordBreak:'keep-all' as const }}>{getDayTypeAvoid(dt.id)}</div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            <TradeLogSection />
          </div>
        )}

      </div>
    </div>
  );
}


// ── Day Type Bar ──────────────────────────────────────────────────────────────
const DAY_EXPLANATIONS: Record<string,{heb:string; desc:string; strategy:string; col:string}> = {
  'NORMAL': { heb:'ממשיך רגיל', col:'#22c55e', desc:'יום עם כיוון ברור — מחיר נוטה להמשיך בכיוון הפתיחה', strategy:'עקוב אחרי המגמה. IB Breakout ו-VWAP Pullback עם הכיוון.' },
  'NORMAL_VARIATION': { heb:'ווריאציה רגילה', col:'#22c55e', desc:'יום רגיל עם תנודות — אין מגמה חזקה', strategy:'Liq Sweep וVWAP Pullback מועדפים. היזהר מ-IB Breakout.' },
  'TREND_DAY':        { heb:'יום מגמה', col:'#a78bfa', desc:'מגמה חזקה חד-כיוונית — המחיר לא חוזר לIB', strategy:'כנס עם המגמה בלבד. סטופ רחוק. T3 runner — הניח לו לרוץ.' },
  'NEUTRAL':          { heb:'נייטרלי', col:'#f59e0b', desc:'מסחר בתוך הטווח — מחיר חוזר לאמצע', strategy:'מסחר קצר יותר. T1 בלבד. הימנע מ-Breakouts.' },
  'ROTATIONAL':       { heb:'רוטציה', col:'#f59e0b', desc:'רוטציה בין קונים למוכרים — אין כיוון', strategy:'ציפייה בלבד. רק Liq Sweep מובהק. WR נמוך.' },
  'DOUBLE_DISTRIBUTION':{ heb:'דיסטריביושן כפול', col:'#60a5fa', desc:'שני אזורי מסחר עיקריים — פריצה בין האזורים', strategy:'חכה לפריצה ברורה. IB Breakout Retest בלבד.' },
};

function useKillzoneCountdown() {
  const [kzText, setKzText] = useState('');
  const [kzActive, setKzActive] = useState(false);
  useEffect(() => {
    const ZONES: [string, number, number][] = [
      ['London',   180, 300],  // 03:00-05:00 ET (V6.1)
      ['NY Open',  570, 630],  // 09:30-10:30 ET (V6.1)
      ['NY Close', 900, 960],  // 15:00-16:00 ET (V6.1)
    ];
    const fmt = (totalSec: number) => {
      const h = Math.floor(totalSec / 3600);
      const m = Math.floor((totalSec % 3600) / 60);
      const s = totalSec % 60;
      return h > 0 ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
                    : `${m}:${String(s).padStart(2,'0')}`;
    };
    const tick = () => {
      const etStr = new Date().toLocaleString('en-US', { timeZone: 'America/New_York' });
      const et = new Date(etStr);
      const nowMin = et.getHours() * 60 + et.getMinutes();
      const nowSec = nowMin * 60 + et.getSeconds();
      // Check if inside a zone
      for (const [name, start, end] of ZONES) {
        if (nowMin >= start && nowMin < end) {
          const remaining = end * 60 - nowSec;
          setKzText(`${name} — ${fmt(remaining)} left`);
          setKzActive(true);
          return;
        }
      }
      // Outside — find next zone
      let bestName = '', bestSec = Infinity;
      for (const [name, start] of ZONES) {
        let diff = start * 60 - nowSec;
        if (diff <= 0) diff += 24 * 3600; // wrap to next day
        if (diff < bestSec) { bestSec = diff; bestName = name; }
      }
      setKzText(`${bestName} in ${fmt(bestSec)}`);
      setKzActive(false);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return { kzText, kzActive };
}

function DayTypeTabContent({ live }: { live: MarketData | null }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const activeRef = useRef<HTMLDivElement>(null);
  const dtype = (live as any)?.day?.type || '';

  useEffect(() => {
    if (activeRef.current) activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [dtype]);

  const DAY_TYPES = [
    { id:'NORMAL', labelHe:'נורמלי', color:'#3b82f6', desc:'IB מאוזן, שני כיוונים אפשריים. מסחר בקצוות ה-IB.', shape:'bell' },
    { id:'NORMAL_VARIATION', labelHe:'נורמל + זנב', color:'#6366f1', desc:'כיוון ברור עם IB מורחב. כניסה בכיוון הזנב.', shape:'bell_tail' },
    { id:'TREND_DAY', labelHe:'טרנד', color:'#10b981', desc:'יום חד-כיווני. תפוס breakouts, אל תמכור חוזקה.', shape:'trend' },
    { id:'DOUBLE_DISTRIBUTION', labelHe:'כפול', color:'#f59e0b', desc:'שני עולמות מחיר נפרדים. זהירות בין שניהם.', shape:'double' },
    { id:'NEUTRAL', labelHe:'ניטרלי', color:'#64748b', desc:'שוק מהסס ורחב. קנה קצוות, מכור אמצע.', shape:'narrow' },
    { id:'ROTATIONAL', labelHe:'ללא טרנד', color:'#ef4444', desc:'טווח צר מאוד. אל תסחר — מחכה לזרז.', shape:'narrow' },
    { id:'DEVELOPING', labelHe:'מתפתח', color:'#475569', desc:'היום עדיין מתפתח — אין סיווג סופי.', shape:'narrow' },
    { id:'VOLATILE', labelHe:'תנודתי', color:'#f97316', desc:'תנועות חדות ומהירות. סטופים רחבים.', shape:'bell_tail' },
  ];

  return (
    <div style={{ padding:'12px 10px', display:'flex', flexDirection:'column', gap:10 }}>
      {DAY_TYPES.map(dt => {
        const isActive = dtype === dt.id;
        const isExpanded = expandedId === dt.id;
        return (
          <div key={dt.id} ref={isActive ? activeRef : undefined}>
            <div style={{
              background: isActive ? `${dt.color}22` : '#0f172a',
              border: isActive ? `2px solid ${dt.color}` : '1px solid #1e2738',
              borderRadius:10, padding:'10px 14px', transition:'all 0.2s',
              opacity: isActive ? 1 : 0.5, position:'relative',
            }}>
              <div style={{ display:'flex', alignItems:'center', gap:12 }}>
                <div style={{ flexShrink:0, width:40, height:36 }}>
                  <DayTypeSVG shape={dt.shape} color={isActive ? dt.color : '#334155'} />
                </div>
                <div style={{ flex:1 }}>
                  <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                    <span style={{ fontSize:20, fontWeight:700, color: isActive ? dt.color : '#94a3b8' }}>{dt.labelHe}</span>
                    {isActive && <span style={{ fontSize:14, fontWeight:700, background:dt.color, color:'#000', borderRadius:5, padding:'2px 8px' }}>▶ היום</span>}
                  </div>
                  <div style={{ fontSize:14, color:'#64748b', lineHeight:1.5, direction:'rtl' as const, marginTop:2 }}>{dt.desc}</div>
                </div>
              </div>
              {/* Data grid — always visible for active */}
              {isActive && (
                <div style={{ display:'flex', gap:8, flexWrap:'wrap', marginTop:10 }}>
                  {[
                    { label:'IB Range', value:`${((live as any)?.day?.ib_range || 0).toFixed(2)} pt` },
                    { label:'IB נעול', value:(live as any)?.day?.ib_locked ? '✓ כן' : '✗ לא', color:(live as any)?.day?.ib_locked ? '#10b981' : '#ef4444' },
                    { label:'Gap', value:(live as any)?.day?.gap_type || 'FLAT' },
                    { label:'שלב', value:(live as any)?.session?.phase || '—' },
                  ].map(item => (
                    <div key={item.label} style={{ background:'#1e2738', borderRadius:6, padding:'6px 12px', flex:'1 1 70px', minWidth:0 }}>
                      <div style={{ fontSize:14, color:'#64748b', marginBottom:2 }}>{item.label}</div>
                      <div style={{ fontSize:22, fontWeight:700, color:(item as any).color || '#e2e8f0' }}>{item.value}</div>
                    </div>
                  ))}
                </div>
              )}
              {/* Toggle details */}
              {isActive && (
                <button onClick={() => setExpandedId(isExpanded ? null : dt.id)} style={{
                  marginTop:8, width:'100%', padding:'5px', border:'1px solid #1e2738', borderRadius:6,
                  background:'transparent', color:'#64748b', fontSize:14, cursor:'pointer', fontFamily:'inherit',
                }}>{isExpanded ? '▲ הסתר פרטים' : '▼ פרטים'}</button>
              )}
              {/* Expandable explanations */}
              {isActive && isExpanded && (
                <div style={{ marginTop:8, display:'flex', flexDirection:'column', gap:8, borderTop:'1px solid #1e2738', paddingTop:8 }}>
                  <div>
                    <div style={{ fontSize:14, color:'#94a3b8', marginBottom:4, fontWeight:600 }}>📋 כלל מסחר</div>
                    <div style={{ fontSize:14, color:'#cbd5e1', lineHeight:1.6, direction:'rtl' as const }}>{getDayTypeRule(dt.id)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize:14, color:'#94a3b8', marginBottom:4, fontWeight:600 }}>🎯 מה לחפש</div>
                    <div style={{ fontSize:14, color:'#cbd5e1', lineHeight:1.6, direction:'rtl' as const }}>{getDayTypeLookFor(dt.id)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize:14, color:'#ef444499', marginBottom:4, fontWeight:600 }}>⚠️ מה להימנע</div>
                    <div style={{ fontSize:14, color:'#94a3b8', lineHeight:1.6, direction:'rtl' as const }}>{getDayTypeAvoid(dt.id)}</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
      <TradeLogSection />
    </div>
  );
}

function DayTypeBar({ live, onRequestExplanation, aiLoading }:{ live:MarketData|null; onRequestExplanation:()=>void; aiLoading:boolean }) {
  const day = (live as any)?.day || {};
  const sess = live?.session || {} as any;
  const dtype = day.type || 'UNKNOWN';
  const info = DAY_EXPLANATIONS[dtype];
  const col = info?.col || '#4a5568';
  const ibRange = day.ib_range || 0;
  const ext = day.total_ext || 0;
  const gap = day.gap_type || 'FLAT';
  const min = sess.min || 0;
  const phase = sess.phase || '—';
  const { kzText, kzActive } = useKillzoneCountdown();

  return (
    <div style={{ background:'#111827', border:`1px solid ${col}44`, borderRadius:8, overflow:'hidden', flexShrink:0 }}>
      <div style={{ display:'flex', alignItems:'center', gap:8, padding:'7px 12px' }}>
        {/* Day type pill */}
        <div style={{ display:'flex', alignItems:'center', gap:6, flex:1, minWidth:0, overflow:'hidden', flexWrap:'wrap' }}>
          <div style={{ width:8, height:8, borderRadius:'50%', background:col, boxShadow:`0 0 5px ${col}` }} />
          <span style={{ fontSize:14, fontWeight:800, color:col }}>{info?.heb || dtype}</span>
          <span style={{ fontSize:14, color:'#4a5568' }}>·</span>
          <span style={{ fontSize:14, color:'#6b7280' }}>IB {ibRange.toFixed(1)}pts</span>
          <span style={{ fontSize:14, color:'#4a5568' }}>·</span>
          <span style={{ fontSize:14, color:'#6b7280' }}>Ext ×{ext}</span>
          <span style={{ fontSize:14, color:'#4a5568' }}>·</span>
          <span style={{ fontSize:14, color: gap==='FLAT'?'#4a5568':'#f59e0b' }}>Gap {gap}</span>
          <span style={{ fontSize:14, color:'#4a5568' }}>·</span>
          <span style={{ fontSize:14, fontWeight:700, color: kzActive ? '#22c55e' : '#6b7280', fontFamily:'monospace' }}>
            {kzActive ? '🟢 ' : '⏱ '}{kzText}
          </span>
        </div>
        {/* Phase + min */}
        <span style={{ fontSize:14, color:'#4a5568' }}>{phase} {min>0?`${min}m`:''}</span>
        {/* Explain button */}
        <button onClick={onRequestExplanation} disabled={aiLoading} style={{
          padding:'3px 10px', borderRadius:6, fontSize:14, fontWeight:700,
          background:'#7f77dd22', color:'#7f77dd', border:'1px solid #7f77dd44',
          cursor: aiLoading?'not-allowed':'pointer', fontFamily:'inherit'
        }}>
          {aiLoading ? '...' : '? הסבר'}
        </button>
      </div>
      {info?.desc && (
        <div style={{ padding:'4px 12px 7px', fontSize:14, color:'#6b7280', direction:'rtl', textAlign:'right', borderTop:`1px solid ${col}22` }}>
          {info.desc}
        </div>
      )}
    </div>
  );
}

// ── Root Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [live,setLive]=useState<MarketData|null>(null);
  const [candles,setCandles]=useState<Candle[]>([]);
  const [connected,setConnected]=useState(false);
  const [systemOn,setSystemOn]=useState(true);
  const [entryMode,setEntryMode]=useState<{mode:string;gates?:any}|null>(null);
  useEffect(()=>{
    try {
      fetch(API_URL+'/health',{cache:'no-store'}).then(r=>{
        if(!r.ok) return;
        return r.json();
      }).then(d=>{
        if(d&&d.entry_mode) setEntryMode({mode:d.entry_mode,gates:{relvol:d.gate_relvol_min||1.2,fvg:d.gate_fvg_max||4.0,sweep:d.gate_sweep_min||1.5,kz:d.killzone_required!==false}});
      }).catch(()=>{});
    } catch {}
  },[]);
  const [tf,setTf]=useState<'3m'|'5m'|'15m'|'30m'|'1h'>('3m');
  const [accepted,setAccepted]=useState(false);
  const [lockedSignal,setLockedSignal]=useState<any>(null);
  const [rejectedTs,setRejectedTs]=useState(0);
  const [aiLoading,setAiLoading]=useState(false);
  const [aiError,setAiError]=useState(false);
  const [persistedSignal,setPersistedSignal]=useState<Signal|null>(null);
  const [signalTime,setSignalTime]=useState<string>('');
  const [selectedSetup,setSelectedSetup]=useState<{id:string;dir:'long'|'short'}|null>(null);
  const [selectedSweep,setSelectedSweep]=useState<SweepEvent|null>(null);
  const [activeSetup,setActiveSetup]=useState<ActiveSetup|null>(null);
  const [detectedSetups,setDetectedSetups]=useState<DetectedSetup[]>([]);
  const [buildingSetups,setBuildingSetups]=useState<BuildingSetup[]>([]);
  const [expiredBuildingSetups,setExpiredBuildingSetups]=useState<BuildingSetup[]>([]);
  const [selectedPattern,setSelectedPattern]=useState<PatternResult|null>(null);
  const [dayExplanation,setDayExplanation]=useState<string>('');
  const [dayLoading,setDayLoading]=useState(false);
  const [scannedPatterns,setScannedPatterns]=useState<{pattern:string;direction:string;entry:number;stop:number;t1:number;t2:number;neckline:number;confidence:number;label:string;start_ts:number;end_ts:number}[]>([]);
  const [activeScannedPattern,setActiveScannedPattern]=useState<typeof scannedPatterns[0]|null>(null);
  const [activeTrade,setActiveTrade]=useState<ActiveTrade|null>(null);
  const [tradeToast,setTradeToast]=useState<{msg:string;color:string}|null>(null);
  const [stopWarning,setStopWarning]=useState<{dist:number;stop:number;price:number}|null>(null);
  const [checklistSetup, setChecklistSetup] = useState<ChecklistSetup | null>(null);
  const [wsCB, setWsCB] = useState<{ allowed: boolean; reason: string } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const prevSigRef=useRef<string>('');

  const askAI=useCallback(async()=>{
    if(aiLoading) return;
    setAiLoading(true);
    setAiError(false);
    try{
      const r=await fetch(`${API_URL}/market/analyze`,{cache:'no-store'});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      const sig=await r.json();
      if(!sig?.direction) throw new Error('no direction');
      setPersistedSignal(sig);
      setSignalTime(new Date().toLocaleTimeString('he-IL',{hour:'2-digit',minute:'2-digit',second:'2-digit'}));
      setLive(prev=>prev?{...prev,signal:sig}:prev);
      const isGreen=sig.tl_color==='green'||sig.tl_color==='green_bright';
      if(isGreen && sig.direction!=='NO_TRADE'){setLockedSignal(sig);setAccepted(true);}
    }catch(e){console.error('AI:',e);setAiError(true);}
    finally{ setAiLoading(false); }
  },[aiLoading]);

  const askDayType=useCallback(async()=>{
    if(dayLoading) return;
    setDayLoading(true);
    try{
      const r=await fetch(`${API_URL}/market/analyze`,{cache:'no-store'});
      if(!r.ok) throw new Error();
      const sig=await r.json();
      const day=(sig as any)?.day_analysis || sig?.rationale || '';
      // בקש ניתוח יום ספציפי
      const live2=await (await fetch(`${API_URL}/market/latest`,{cache:'no-store'})).json();
      const dtype=(live2 as any)?.day?.type||'UNKNOWN';
      const ibRange=(live2 as any)?.day?.ib_range||0;
      const ext=(live2 as any)?.day?.total_ext||0;
      const explanation = `סוג יום: ${dtype} | IB: ${ibRange.toFixed(1)}pts | Extensions: ${ext}\n${sig?.rationale||'ממתין לנתונים...'}`;
      setDayExplanation(explanation);
    }catch(e){ setDayExplanation('שגיאה בטעינת הניתוח'); }
    finally{ setDayLoading(false); }
  },[dayLoading]);

  // ── Active Setup status tracking ──────────────────────
  useEffect(() => {
    if (!activeSetup || activeSetup.status !== 'ACTIVE' || !live?.price) return;
    const p = live.price;
    const s = activeSetup.sweep;
    const isLong = s.dir === 'long';
    const barsSinceEntry = Math.round((Date.now()/1000 - activeSetup.activatedAt) / CANDLE_SEC);

    if (isLong) {
      if (p <= s.stop) {
        setActiveSetup(prev => prev ? { ...prev, status: 'STOPPED', result: `סטופ נלחץ ב-${barsSinceEntry} נרות`, resultBars: barsSinceEntry } : null);
      } else if (s.c2 && p >= s.c2) {
        setActiveSetup(prev => prev ? { ...prev, status: 'T2_HIT', result: `C2 הושג ב-${barsSinceEntry} נרות — 75% יצא`, resultBars: barsSinceEntry } : null);
      } else if (p >= s.c1) {
        setActiveSetup(prev => prev ? { ...prev, status: 'T1_HIT', result: `C1 הושג ב-${barsSinceEntry} נרות — 50% יצא, סטופ→BE`, resultBars: barsSinceEntry } : null);
      }
    } else {
      if (p >= s.stop) {
        setActiveSetup(prev => prev ? { ...prev, status: 'STOPPED', result: `סטופ נלחץ ב-${barsSinceEntry} נרות`, resultBars: barsSinceEntry } : null);
      } else if (s.c2 && p <= s.c2) {
        setActiveSetup(prev => prev ? { ...prev, status: 'T2_HIT', result: `C2 הושג ב-${barsSinceEntry} נרות — 75% יצא`, resultBars: barsSinceEntry } : null);
      } else if (p <= s.c1) {
        setActiveSetup(prev => prev ? { ...prev, status: 'T1_HIT', result: `C1 הושג ב-${barsSinceEntry} נרות — 50% יצא, סטופ→BE`, resultBars: barsSinceEntry } : null);
      }
    }
  }, [live?.price, activeSetup]);

  const systemOnRef=useRef(systemOn);
  useEffect(()=>{systemOnRef.current=systemOn;},[systemOn]);

  const fetchLive=useCallback(async()=>{
    if(!systemOnRef.current) return;
    try{
      const r=await fetch(`${API_URL}/market/latest?t=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error();
      const d:MarketData=await r.json();
      if(d?.bar){
        setLive(prev=>({...d,signal:prev?.signal??d.signal}));setConnected(true);
        // Clear stop warning when price moves away
        setStopWarning(prev => prev && Math.abs(d.price - prev.stop) > 2 ? null : prev);
      }
    }catch{setConnected(false);}
  },[]);

  const fetchAnalyze=useCallback(async()=>{
    if(accepted && lockedSignal) return; // מקובע — לא מחפש חדש
    try{
      const r=await fetch(`${API_URL}/market/analyze`,{cache:'no-store'});
      if(!r.ok)return;
      const sig=await r.json();
      if(!sig?.direction) return;
      const sigKey=`${sig.direction}-${sig.setup}-${sig.score}`;
      // אם זה אותו סטאפ שנדחה — לא מציג
      if(sigKey===prevSigRef.current && rejectedTs>0) return;
      // Auto-lock ברגע שמגיע ירוק
      const isGreen = sig.tl_color==='green'||sig.tl_color==='green_bright';
      if(isGreen && sig.direction!=='NO_TRADE' && !accepted) {
        setLockedSignal(sig);
        setAccepted(true);
      }
      setLive(prev=>prev?{...prev,signal:sig}:prev);
    }catch{}
  },[accepted,lockedSignal,rejectedTs]);

  const tfRef=useRef(tf);
  tfRef.current=tf;

  const fetchCandles=useCallback(async()=>{
    if(!systemOnRef.current) return;
    const curTf=tfRef.current;
    const tfLimits:{[k:string]:number}={'3m':960,'5m':288,'15m':96,'30m':48,'1h':168};
    const limit=tfLimits[curTf]||960;
    try{
      const r=await fetch(`${API_URL}/market/candles?tf=${curTf}&limit=${limit}`,{cache:'no-store'});
      if(!r.ok)return;
      const raw=await r.json();
      if(!Array.isArray(raw))return;
      // flatten + normalize through single normalizeCandle()
      const flat:Candle[]=[];
      for(const item of raw){
        const parse=(v:any)=>{
          try{ const c=typeof v==='string'?JSON.parse(v):v; const n=normalizeCandle(c); if(n)flat.push(n); }catch{}
        };
        if(Array.isArray(item)){ for(const sub of item) parse(sub); }
        else parse(item);
      }
      // מיין ישן→חדש (LightweightCharts דורש ascending), הסר כפולים
      flat.sort((a,b)=>a.ts-b.ts);
      const seen=new Set<number>();
      const deduped=flat.filter(c=>{if(seen.has(c.ts))return false;seen.add(c.ts);return true;});
      if(deduped.length>0)setCandles(deduped);
    }catch{}
  },[]);

  useEffect(()=>{
    // טעינה ראשונה — קודם היסטוריה, אחר כך לייב
    const init=async()=>{
      await fetchCandles();
      fetchLive();
      const lt=setInterval(fetchLive,1000);
      const ct=setInterval(fetchCandles,5000); // נרות כל 5 שניות
      const kt=setInterval(()=>fetch(API_URL+'/health',{cache:'no-store'}).catch(()=>{}),30000);
      return()=>{clearInterval(lt);clearInterval(ct);clearInterval(kt);};
    };
    const cleanup=init();
    return()=>{cleanup.then(fn=>fn?.());};
  },[fetchLive,fetchCandles,fetchAnalyze]);

  // ── Re-fetch candles when timeframe changes ──
  useEffect(()=>{
    fetchCandles();
  },[tf,fetchCandles]);

  // ── Pattern scanner polling ──
  useEffect(()=>{
    if(!systemOn) return;
    const fetchPatterns=async()=>{
      try{
        const res=await fetch(`${API_URL}/market/patterns`,{cache:'no-store'});
        const data=await res.json();
        const raw=data.patterns;
        const curPrice=live?.price||0;
        const ps=Array.isArray(raw)?raw.filter((p:any)=>{
          const r=Math.abs((p.entry||0)-(p.stop||0));
          if(r<3||r>8) return false;
          // Invalidate if price already past entry
          if(p.direction==='LONG'&&curPrice>p.entry) return false;
          if(p.direction==='SHORT'&&curPrice<p.entry) return false;
          return true;
        }):[];
        setScannedPatterns(ps);
        if(ps.length>0 && ps[0].confidence>=70 && ps[0].pattern!==activeScannedPattern?.pattern){
          setActiveScannedPattern(ps[0]);
        }
      }catch{}
    };
    fetchPatterns();
    const pt=setInterval(fetchPatterns,30000);
    return()=>clearInterval(pt);
  },[systemOn]);

  // ── Invalidate active pattern when price passes entry ──
  useEffect(() => {
    if (!activeScannedPattern || !live?.price) return;
    const p = live.price;
    if (activeScannedPattern.direction === 'LONG' && p > activeScannedPattern.entry) setActiveScannedPattern(null);
    if (activeScannedPattern.direction === 'SHORT' && p < activeScannedPattern.entry) setActiveScannedPattern(null);
  }, [live?.price, activeScannedPattern]);

  useEffect(() => {
    if (!systemOn) return;
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    const connect = () => {
      const url = API_URL.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws';
      ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          console.log('[X4] WS message received:', d.type, d.type === 'TRADE_CLOSE' ? d : '');
          if (d.type === 'EXECUTE_RESULT') {
            if (d.status === 'confirmed') {
              setTradeToast({ msg: '✅ פקודה בוצעה ב-Sierra', color: '#22c55e' });
              setTimeout(() => setTradeToast(null), 3000);
            } else {
              setTradeToast({ msg: '⚠️ לא התקבל אישור מ-Sierra — בדוק ידנית', color: '#f59e0b' });
              setTimeout(() => setTradeToast(null), 10000);
            }
          }
          if (d.type === 'STOP_NEAR') {
            setStopWarning({ dist: d.dist, stop: d.stop, price: d.price });
          }
          if (d.type === 'TRADE_CLOSE') {
            setActiveTrade(null);
            setChecklistSetup(null);
            const isWin = (d.pnl_pts || 0) > 0;
            const icon = isWin ? '✅' : '❌';
            const msg = `${icon} ${d.exit_type || 'CLOSED'} — ${d.pnl_pts>=0?'+':''}${d.pnl_pts?.toFixed(2)}pt ${d.pnl_usd>=0?'+':''}$${d.pnl_usd?.toFixed(0)}`;
            setTradeToast({ msg, color: isWin ? '#22c55e' : '#ef4444' });
            setTimeout(() => setTradeToast(null), 5000);
          }
          if (d.type === 'status_update') {
            if (d.circuit_breaker)
              setWsCB({ allowed: d.circuit_breaker.allowed, reason: d.circuit_breaker.reason ?? '' });
            // D5: Wire WS trade data to ActiveTradePanel
            const t = d.trade;
            if (t && t.status === 'OPEN') {
              setActiveTrade({
                direction: t.direction,
                setupType: t.setup_type || 'MANUAL',
                entryPrice: t.entry_price || 0,
                stopPrice: t.stop || 0,
                t1: t.t1 || 0,
                t2: t.t2 || 0,
                t3: t.t3 || 0,
                entryTs: t.entry_ts || 0,
                healthScore: d.trade_health ?? 70,
                c1Status: t.c1_status === 'closed' ? 'closed' : 'open',
                c2Status: t.c2_status === 'closed' ? 'closed' : 'open',
                c3Status: t.c3_status === 'closed' ? 'closed' : 'open',
              });
            } else if (t && (t.status === 'CLOSED' || t.status === 'NO_TRADE')) {
              setActiveTrade(null);
            }
          }
        } catch {}
      };
      ws.onclose = () => { wsRef.current = null; retryTimer = setTimeout(connect, 5000); };
      ws.onerror  = () => ws?.close();
    };
    connect();
    return () => { retryTimer && clearTimeout(retryTimer); ws?.close(); wsRef.current = null; };
  }, [systemOn]);

  const executeRetryRef = useRef(false);
  const handleExecuteTrade = useCallback(async (params: {
    direction: 'LONG' | 'SHORT'; entry_price: number; stop: number;
    t1: number; t2: number; t3: number; setup_type: string;
  }) => {
    console.log('[EXECUTE] called with params:', params);
    const url = `${API_URL}/trade/execute`;
    const body = executeRetryRef.current ? { ...params, force_clear: true } : params;
    executeRetryRef.current = false;
    console.log('[EXECUTE] fetching:', url, body.hasOwnProperty('force_clear') ? '(force_clear)' : '');
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try { const err = await res.json(); detail = err.detail || detail; } catch {}
      if (res.status === 409) {
        executeRetryRef.current = true;
        throw new Error('פקודה קיימת — לחץ שוב לביטול ושליחה מחדש');
      }
      throw new Error(detail);
    }
    setChecklistSetup(null);
    return res.json();
  }, []);

  // ── Auto-AI fallback: call every 60s when no setup detected ──
  const lastAutoAI = useRef(0);
  useEffect(() => {
    const opp = calcSetups(live, candles)?.opportunity || 'none';
    const now = Date.now();
    // Only auto-call when: no opportunity, not loading, 60s since last call, has live data
    if (systemOn && opp === 'none' && !aiLoading && live?.price && now - lastAutoAI.current > 60000 && !persistedSignal) {
      lastAutoAI.current = now;
      askAI();
    }
  }, [live?.price]); // runs on each price update (~2s)

  // ── Setup accumulator — זיהוי סטאפים חדשים ומעקב ──────
  const lastDetectRef = useRef('');
  useEffect(() => {
    if (!live?.price || !candles.length) return;
    const setup = calcSetups(live, candles);
    if (!setup || setup.opportunity === 'none') return;

    const hit = setup.opportunitySweep;
    const levels = setup.opportunityLevels;
    if (!hit || !levels || levels.entry <= 0) return;

    // Unique ID based on direction + level + approximate time
    const barTs = hit.bar?.ts || Math.floor(Date.now() / 1000 / CANDLE_SEC) * CANDLE_SEC;
    const setupId = `${hit.type}-${setup.opportunity}-${hit.levelName}-${barTs}`;

    // Skip if same as last detection or already exists
    if (setupId === lastDetectRef.current) return;
    if (detectedSetups.some(s => s.id === setupId)) return;
    lastDetectRef.current = setupId;

    const newSetup: DetectedSetup = {
      id: setupId,
      detectedAt: Date.now() / 1000,
      type: hit.type,
      dir: setup.opportunity as 'long' | 'short',
      levelName: hit.levelName,
      level: hit.level,
      score: setup.opportunityScore,
      entry: levels.entry,
      stop: levels.stop,
      c1: levels.c1,
      c2: levels.c2,
      c3: levels.c3,
      riskPts: levels.riskPts,
      delta: hit.bar?.delta || 0,
      detectionBarTs: barTs,
      entryBarTs: barTs,
      status: 'detected',
    };

    setDetectedSetups(prev => [newSetup, ...prev].slice(0, 50)); // max 50 setups
  }, [live?.price, live?.bar?.delta]);

  // ── Update setup status based on price ──────────────────
  useEffect(() => {
    if (!live?.price) return;
    const p = live.price;
    setDetectedSetups(prev => prev.map(s => {
      if (s.status === 'stopped' || s.status === 'c2_hit' || s.status === 'expired') return s;
      const isLong = s.dir === 'long';
      // Check stop
      if (isLong && p <= s.stop) return { ...s, status: 'stopped' as const, result: 'סטופ', pnlPts: s.stop - s.entry };
      if (!isLong && p >= s.stop) return { ...s, status: 'stopped' as const, result: 'סטופ', pnlPts: s.entry - s.stop };
      // Check C1
      if (s.status === 'detected' || s.status === 'confirmed') {
        if (isLong && p >= s.c1) return { ...s, status: 'c1_hit' as const, result: 'C1 הושג', pnlPts: s.c1 - s.entry };
        if (!isLong && p <= s.c1) return { ...s, status: 'c1_hit' as const, result: 'C1 הושג', pnlPts: s.entry - s.c1 };
      }
      // Check C2
      if (s.status === 'c1_hit') {
        if (isLong && p >= s.c2) return { ...s, status: 'c2_hit' as const, result: 'C2 הושג', pnlPts: s.c2 - s.entry };
        if (!isLong && p <= s.c2) return { ...s, status: 'c2_hit' as const, result: 'C2 הושג', pnlPts: s.entry - s.c2 };
      }
      // Expire after 30 bars (90 min)
      if (Date.now() / 1000 - s.detectedAt > 30 * CANDLE_SEC && s.status === 'detected') {
        return { ...s, status: 'expired' as const, result: 'פג תוקף' };
      }
      return s;
    }));
  }, [live?.price]);

  const tfToMtf:{[k:string]:string}={'3m':'m3','5m':'m3','15m':'m15','30m':'m30','1h':'m60'};
  const bar=tf==='3m'?live?.bar:(live?.mtf as any)?.[tfToMtf[tf]]??live?.bar;

  // ── Real-time opportunity detection ──────────────────
  const liveSetup = calcSetups(live, candles);
  const opportunity = liveSetup?.opportunity || 'none';
  const oppScore = liveSetup?.opportunityScore || 0;
  const oppLevels = liveSetup?.opportunityLevels;
  const oppSweep = liveSetup?.opportunitySweep;
  const newsGuard = (live as any)?.news_guard as { state: string; available: boolean; active_event: any; events_today: number; events: any[] } | undefined;

  // ── Building setup tracker — track setups as they form ──────
  useEffect(() => {
    if (!liveSetup?.buildingCandidates || !live?.price) return;
    const now = Date.now() / 1000;
    const EXPIRY_BARS = 10;
    const EXPIRY_SEC = EXPIRY_BARS * CANDLE_SEC;
    const price = live.price;

    const candidates = liveSetup.buildingCandidates;

    setBuildingSetups(prev => {
      const updated = [...prev];
      const newExpired: BuildingSetup[] = [];

      // Add new candidates that aren't already tracked
      for (const c of candidates) {
        const id = `build-${c.dir}-${c.hit.levelName}-${Math.floor(now / 300)}`;
        if (updated.some(s => s.id === id)) continue;
        // Also skip if too similar to existing
        if (updated.some(s => s.dir === c.dir && s.levelName === c.hit.levelName && Math.abs(s.level - c.hit.level) < 2)) continue;

        const evalReason = c.eval?.reason || '';
        const p1Pass = c.hit.type === 'sweep';
        const p2Pass = c.eval ? (!evalReason.includes('P2') && !evalReason.includes('No MSS') && !evalReason.includes('No FVG') && !evalReason.includes('RelVol') && !evalReason.includes('Stacked') ? true : evalReason.includes('P3') || evalReason.includes('FLOW') ? true : false) : null;
        const p3Pass = c.eval ? (c.eval.pass ? true : evalReason.includes('P3') || evalReason.includes('FLOW') ? false : null) : null;

        // Build P2 detail
        const fp = (live as any)?.footprint_bools || {};
        const of2 = live.order_flow || {} as any;
        const relVol = c.hit.relVol;
        const stackedCount = fp.stacked_imbalance_count ?? 0;
        const stackedDir = fp.stacked_imbalance_dir ?? '';
        const p2Detail = `MSS: ${!evalReason.includes('No MSS')?'✓':'waiting'} | FVG: ${!evalReason.includes('No FVG')?'ready':'waiting'} | RelVol: ${relVol.toFixed(2)}${relVol>1.2?'✓':'✗'} | Stacked: ${stackedCount}${stackedCount>=2?'✓ '+stackedDir:'✗'}`;

        const absorptionOk = fp.absorption_at_fvg ?? of2.absorption_bull ?? false;
        const deltaConfirmed = fp.delta_confirmed_1m ?? false;
        const p3Detail = `Absorption: ${absorptionOk?'✓':'✗'} | Delta 1m: ${deltaConfirmed?'✓':'✗'}`;

        updated.push({
          id,
          dir: c.dir,
          levelName: c.hit.levelName,
          level: c.hit.level,
          type: c.hit.type,
          detectedAt: now,
          expiresAt: now + EXPIRY_SEC,
          p1Pass,
          p1Detail: `Sweep @ ${c.hit.levelName} ${c.hit.level.toFixed(2)}`,
          p2Pass,
          p2Detail,
          p3Pass,
          p3Detail,
          score: c.score,
        });
      }

      // Update existing: check expiry + price invalidation
      const stillActive: BuildingSetup[] = [];
      for (const s of updated) {
        if (s.exitReason) { newExpired.push(s); continue; }
        // Expiry
        if (now > s.expiresAt) {
          newExpired.push({ ...s, exitReason: `⌛ Expired: Sweep aged out (${EXPIRY_BARS} bars)` });
          continue;
        }
        // Price passed entry — need levels from candidates
        const matchingCandidate = candidates.find(c => c.dir === s.dir && c.hit.levelName === s.levelName);
        if (matchingCandidate?.levels) {
          const entry = matchingCandidate.levels.entry;
          if (s.dir === 'long' && price > entry) {
            newExpired.push({ ...s, exitReason: '📈 Price passed entry before completion' });
            continue;
          }
          if (s.dir === 'short' && price < entry) {
            newExpired.push({ ...s, exitReason: '📉 Price passed entry before completion' });
            continue;
          }
        }
        // Promoted to LIVE — check if all 3 pillars pass
        if (s.p1Pass && s.p2Pass === true && s.p3Pass === true) {
          newExpired.push({ ...s, exitReason: '✅ Promoted to LIVE SETUPS' });
          continue;
        }

        // Update pillar status from current candidate data
        if (matchingCandidate?.eval) {
          const evalReason = matchingCandidate.eval.reason || '';
          const fp = (live as any)?.footprint_bools || {};
          const of2 = live.order_flow || {} as any;
          const relVol = matchingCandidate.hit.relVol;
          const stackedCount = fp.stacked_imbalance_count ?? 0;
          const stackedDir = fp.stacked_imbalance_dir ?? '';
          s.p2Pass = !evalReason.includes('P2') && !evalReason.includes('No MSS') && !evalReason.includes('No FVG') && !evalReason.includes('RelVol') && !evalReason.includes('Stacked') ? true : evalReason.includes('P3') || evalReason.includes('FLOW') ? true : false;
          s.p2Detail = `MSS: ${!evalReason.includes('No MSS')?'✓':'waiting'} | FVG: ${!evalReason.includes('No FVG')?'ready':'waiting'} | RelVol: ${relVol.toFixed(2)}${relVol>1.2?'✓':'✗'} | Stacked: ${stackedCount}${stackedCount>=2?'✓ '+stackedDir:'✗'}`;
          const absorptionOk = fp.absorption_at_fvg ?? of2.absorption_bull ?? false;
          const deltaConfirmed = fp.delta_confirmed_1m ?? false;
          s.p3Pass = matchingCandidate.eval.pass ? true : evalReason.includes('P3') || evalReason.includes('FLOW') ? false : null;
          s.p3Detail = `Absorption: ${absorptionOk?'✓':'✗'} | Delta 1m: ${deltaConfirmed?'✓':'✗'}`;
          s.score = matchingCandidate.score;
        }

        stillActive.push(s);
      }

      if (newExpired.length > 0) {
        setExpiredBuildingSetups(prev => [...newExpired.filter(e => e.exitReason !== '✅ Promoted to LIVE SETUPS'), ...prev].slice(0, 10));
      }

      return stillActive.slice(0, 10);
    });
  }, [live?.price, liveSetup?.buildingCandidates]);

  // Legacy compatibility
  const activeSetups = opportunity !== 'none' ? [{
    name: 'Liq Sweep', dir: opportunity as 'long'|'short', col: opportunity === 'long' ? '#22c55e' : '#ef5350',
  }] : [];
  const setupLevels = selectedSetup ? calcSetupLevels(selectedSetup.id, live, selectedSetup.dir) : null;
  const setupCol = opportunity === 'long' ? '#22c55e' : opportunity === 'short' ? '#ef5350' : '#f59e0b';

  // ── Historical sweep events ─────────────────────────
  const sweepResult = candles.length > 10 && live?.levels
    ? scanHistoricalSweeps(candles, live.levels, live.woodi, live)
    : { events: [], levelTouches: [] };
  const sweepEvents = sweepResult.events;
  const levelTouches = sweepResult.levelTouches;

  // Active or selected sweep → chart data
  const activeSweep = activeSetup?.sweep || selectedSweep;
  const sweepData = activeSweep ? {
    dir: activeSweep.dir,
    sweepBarTs: activeSweep.sweepBarTs,
    entryBarTs: activeSweep.confirmBarTs || activeSweep.reversalBarTs,
    setupBarTs: activeSweep.setupBarTs,
    entry: activeSweep.entry,
    stop: activeSweep.stop,
    t1: activeSweep.c1,
    t2: activeSweep.c2,
    t3: activeSweep.c3,
    delta: activeSweep.delta,
    relVol: activeSweep.relVol,
    score: activeSweep.score,
    confirmed: activeSweep.confirmed,
    // Future bar timestamps for markers
    stopBarTs: activeSetup?.stopBarTs || 0,
    t1BarTs: activeSetup?.t1BarTs || 0,
    t2BarTs: activeSetup?.t2BarTs || 0,
    t3BarTs: activeSetup?.t3BarTs || 0,
    status: activeSetup?.status || 'ACTIVE',
  } : undefined;
  const chartSignal:any = setupLevels ? {
    direction:selectedSetup!.dir==='long'?'LONG':'SHORT',
    entry:setupLevels.entry, stop:setupLevels.stop,
    target1:setupLevels.t1, target2:setupLevels.t2, target3:setupLevels.t3stop,
    score:8, tl_color:'green', setup:selectedSetup!.id, win_rate:70,
    risk_pts:Math.abs(setupLevels.entry-setupLevels.stop),
    _detect:setupLevels.detect, _verify:setupLevels.verify, _col:setupCol,
  } : (accepted&&lockedSignal)?lockedSignal:persistedSignal??null;

  return (
    <div style={{background:'#0a0a0f',fontFamily:'"JetBrains Mono","Fira Code",monospace',display:'flex',flexDirection:'column',height:'100vh',overflow:'hidden'}}>
      <style>{`
        @media (min-width: 3000px) {
          html { font-size: 18px; }
        }
        @media (min-width: 4000px) {
          html { font-size: 22px; }
        }
        @media (max-width: 1360px) {
          html { font-size: 13px; }
        }
        * { box-sizing: border-box; }
        html, body { overflow-x: hidden; max-width: 100vw; }
        @keyframes spin{to{transform:rotate(360deg)}}
      `}</style>

      {/* TopBar */}
      <div style={{flexShrink:0,padding:'6px 12px',borderBottom:'1px solid #1e2738'}}>
        <TopBar live={live} connected={connected} onAskAI={askAI} aiLoading={aiLoading} systemOn={systemOn} onToggleSystem={()=>setSystemOn(p=>!p)} newsGuard={newsGuard} entryMode={entryMode} />
        {entryMode?.mode === 'DEMO' && entryMode.gates && (
          <div style={{fontSize:10,color:'#f59e0b88',marginTop:3,fontFamily:'monospace'}}>
            DEMO Gates: RelVol&gt;={entryMode.gates.relvol} &middot; FVG&lt;={entryMode.gates.fvg}pt &middot; Sweep&gt;={entryMode.gates.sweep}pt &middot; Killzone=tag
          </div>
        )}
      </div>

      {/* V6.5: Sidebar left + chart right */}
      <div style={{display:'grid',gridTemplateColumns:'min(420px, max(260px, 24vw)) 1fr',flex:1,overflow:'hidden',minWidth:0,paddingBottom:52}}>

        {/* Left panel — tabs */}
        <RightPanel
          live={live}
          candles={candles}
          selectedPattern={selectedPattern}
          setSelectedPattern={setSelectedPattern}
          accepted={accepted}
          lockedSignal={lockedSignal}
          persistedSignal={persistedSignal}
          signalTime={signalTime}
          aiLoading={aiLoading}
          aiError={aiError}
          onAskAI={askAI}
          dayLoading={dayLoading}
          onAskDayType={askDayType}
          dayExplanation={dayExplanation}
          selectedSetup={selectedSetup}
          onSelectSetup={(id:string,dir:'long'|'short')=>setSelectedSetup(prev=>prev?.id===id?null:{id,dir})}
          sweepEvents={sweepEvents}
          selectedSweep={selectedSweep}
          setSelectedSweep={setSelectedSweep}
          activeSetup={activeSetup}
          onActivateSweep={(ev: SweepEvent) => {
            const fp = (live as any)?.footprint_bools || {};
            setChecklistSetup({
              id: ev.id, dir: ev.dir,
              entry: ev.entry, stop: ev.stop,
              t1: ev.c1, t2: ev.c2, t3: ev.c3,
              riskPts: Math.abs(ev.entry - ev.stop),
              levelName: ev.levelName || '',
              sweepWick: ev.sweepWick || 0,
              hasAbsorption: fp.absorption_detected ?? (ev.score >= 7),
              hasExhaustion: fp.exhaustion_detected ?? false,
            });
          }}
          onDeactivateSetup={()=>setActiveSetup(null)}
          levelTouches={levelTouches}
          liveSetup={liveSetup}
          detectedSetups={detectedSetups}
          newsGuard={newsGuard}
          buildingSetups={buildingSetups}
          expiredBuildingSetups={expiredBuildingSetups}
          onAccept={()=>{setAccepted(true);setLockedSignal(live?.signal);}}
          onReject={()=>{
            const sig=lockedSignal||live?.signal;
            if(sig) prevSigRef.current=`${sig.direction}-${sig.setup}-${sig.score}`;
            setAccepted(false);setLockedSignal(null);setRejectedTs(Date.now());
          }}
        />

        {/* Chart area */}
        <div style={{display:'flex',flexDirection:'column',overflow:'hidden',borderLeft:'1px solid #1e2738',minWidth:0}}>
          <div style={{flexShrink:0,display:'flex',alignItems:'center',gap:8,padding:'5px 12px',background:'#111827',borderBottom:'1px solid #1e2738',flexWrap:'wrap'}}>
            <span style={{fontSize:14,color:'#4a5568',letterSpacing:2}}>גרף</span>
            <div style={{display:'flex',gap:4,flex:1,flexWrap:'wrap'}}>
              {opportunity !== 'none' ? (
                <div style={{display:'flex',alignItems:'center',gap:4,padding:'2px 10px',borderRadius:10,border:`1px solid ${setupCol}66`,background:`${setupCol}15`,maxWidth:200,overflow:'hidden'}}>

                  <div style={{width:8,height:8,borderRadius:'50%',background:setupCol,boxShadow:`0 0 6px ${setupCol}`}}/>
                  <span style={{fontSize:14,fontWeight:800,color:setupCol}}>
                    {opportunity==='long'?'🟢 LONG':'🔴 SHORT'}
                  </span>
                  <span style={{fontSize:14,fontWeight:800,color:'#e2e8f0',fontFamily:'monospace'}}>{oppScore}%</span>
                  {oppSweep && <span style={{fontSize:14,color:'#6b7280'}}>{oppSweep.levelName}</span>}
                </div>
              ) : (
                <span style={{fontSize:14,color:'#2d3a4a'}}>⚫ אין הזדמנות</span>
              )}
            </div>
            <div style={{display:'flex',gap:3}}>
              {(['3m','5m','15m','30m','1h'] as const).map(t=>(
                <button key={t} onClick={()=>setTf(t)} style={{padding:'2px 7px',borderRadius:4,fontSize:14,fontWeight:700,border:tf===t?'1px solid #a855f7':'1px solid transparent',cursor:'pointer',fontFamily:'inherit',background:tf===t?'#f6c90e':'#1e2738',color:tf===t?'#0d1117':'#6b7280'}}>{t.toUpperCase()}</button>
              ))}
            </div>
          </div>
          <div style={{flex:1,position:'relative',overflow:'hidden',minHeight:0}}>
            <LightweightChart
              candles={candles}
              livePrice={live?.price}
              liveBar={live?.bar ? (()=>{
                const tfSec:{[k:string]:number}={'3m':180,'5m':300,'15m':900,'30m':1800,'1h':3600};
                const tfMtf:{[k:string]:string}={'3m':'','5m':'m5','15m':'m15','30m':'m30','1h':'m60'};
                const sec=tfSec[tf]||180;
                const cc=tf==='3m'?live.current_candle:
                          (live as any)?.[`current_candle_${tfMtf[tf]}`] ?? null;
                const raw={
                  ts:   cc?.ts ?? Math.floor(Date.now()/1000 / sec) * sec,
                  o:    cc?.o || cc?.open || live.bar.o,
                  h:    cc?.h || cc?.high || live.bar.h,
                  l:    cc?.l || cc?.low || live.bar.l,
                  c:    live.price ?? live.bar.c,
                  buy:  cc?.buy ?? live.bar.buy,
                  sell: cc?.sell ?? live.bar.sell,
                };
                return normalizeCandle(raw);
              })() : null}
              vwap={live?.vwap?.value}
              levels={live?.levels}
              profile={live?.profile}
              session={{ibh:live?.session?.ibh,ibl:live?.session?.ibl}}
              signal={chartSignal}
              activeSetups={activeSetups}
              sweepData={sweepData}
              sweepEvents={sweepEvents}
              detectedSetups={detectedSetups}
              onSweepClick={(ts:number) => {
                const ev = sweepEvents.find((e:SweepEvent) => e.sweepBarTs === ts);
                if (ev) setSelectedSweep(prev => prev?.id === ev.id ? null : ev);
              }}
              patterns={detectPatterns(candles)}
              selectedPatternId={selectedPattern?.id}
              height={undefined}
              scannedPatterns={scannedPatterns}
              dayType={(live as any)?.day?.type || ''}
              footprintBools={(live as any)?.footprint_bools}
              tradeActive={!!activeTrade}
              healthScore={activeTrade?.healthScore}
              entryTimestamp={activeTrade?.entryTs}
              zone={sweepData ? {
                entry:     sweepData.entry,
                stop:      sweepData.stop,
                t1:        sweepData.t1,
                t2:        sweepData.t2,
                t3:        sweepData.t3 ?? (sweepData.dir === 'long' ? sweepData.t2 + Math.abs(sweepData.t2 - sweepData.entry) : sweepData.t2 - Math.abs(sweepData.t2 - sweepData.entry)),
                direction: sweepData.dir === 'long' ? 'LONG' : 'SHORT',
                sweepTs:   sweepData.sweepBarTs,
                visible:   sweepData.entry > 0,
              } : activeScannedPattern ? {
                entry:     activeScannedPattern.entry,
                stop:      activeScannedPattern.stop,
                t1:        activeScannedPattern.t1,
                t2:        activeScannedPattern.t2,
                t3:        activeScannedPattern.t2 + Math.abs(activeScannedPattern.t2 - activeScannedPattern.t1),
                direction: activeScannedPattern.direction as 'LONG'|'SHORT',
                sweepTs:   activeScannedPattern.end_ts,
                start_ts:  activeScannedPattern.start_ts,
                end_ts:    activeScannedPattern.end_ts,
                visible:   true,
              } : null}
            />
            {/* Setup overlay — badges + legend */}
            {selectedSetup&&setupLevels&&(
              <div style={{position:'absolute',top:8,left:8,background:'#0d1117dd',border:`1px solid ${setupCol}`,borderRadius:8,padding:'8px 12px',zIndex:20,pointerEvents:'none',minWidth:160}}>
                <div style={{fontSize:14,fontWeight:800,color:setupCol,marginBottom:6}}>{selectedSetup.id} — {selectedSetup.dir==='long'?'▲ LONG':'▼ SHORT'}</div>
                {[
                  {n:'① הבחנה',v:setupLevels.detect,c:'#f6c90e'},
                  {n:'② בדיקה',v:setupLevels.verify,c:'#60a5fa'},
                  {n:'③ כניסה',v:setupLevels.entry,c:'#a78bfa'},
                  {n:'④ סטופ',v:setupLevels.stop,c:'#ef5350'},
                  {n:'⑤ T1·C1',v:setupLevels.t1,c:'#22c55e'},
                  {n:'⑥ T2·C2',v:setupLevels.t2,c:'#16a34a'},
                  {n:'⑦ T3·סטופ',v:setupLevels.t3stop,c:'#86efac'},
                ].map(({n,v,c})=>(
                  <div key={n} style={{display:'flex',justifyContent:'space-between',gap:12,fontSize:14,marginBottom:2}}>
                    <span style={{color:c,fontWeight:700}}>{n}</span>
                    <span style={{color:'#e2e8f0',fontFamily:'monospace'}}>{v.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}
            {opportunity!=='none'&&oppLevels&&(
              <div style={{position:'absolute',top:8,left:8,display:'flex',flexDirection:'column',gap:5,zIndex:20,pointerEvents:'none'}}>
                <div style={{display:'flex',alignItems:'center',gap:6,padding:'5px 12px',borderRadius:8,border:`2px solid ${setupCol}`,background:'#0d1117ee'}}>
                  <div style={{width:9,height:9,borderRadius:'50%',background:setupCol,boxShadow:`0 0 8px ${setupCol}`}}/>
                  <span style={{fontSize:14,fontWeight:900,color:setupCol}}>
                    {opportunity==='long'?'▲ LONG':'▼ SHORT'} {oppScore}%
                  </span>
                  <span style={{fontSize:14,color:'#94a3b8',fontFamily:'monospace'}}>
                    E:{(oppLevels.entry||0).toFixed(2)} S:{(oppLevels.stop||0).toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </div>
          {activeScannedPattern && (
            <div style={{flexShrink:0,borderTop:'1px solid #164e63',padding:'6px 10px',background:'#0a1a1f'}}>
              <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:4}}>
                <span style={{fontSize:14,fontFamily:'monospace',color:'#6b7280'}}>Pattern Scanner</span>
                <span style={{fontSize:14,fontFamily:'monospace',fontWeight:700,color:activeScannedPattern.direction==='LONG'?'#00bcd4':'#e91e63'}}>
                  {activeScannedPattern.direction==='LONG'?'▲':'▼'} {activeScannedPattern.label}
                </span>
                <span style={{fontSize:14,fontFamily:'monospace',color:'#f6c90e'}}>{activeScannedPattern.confidence}%</span>
              </div>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:4,fontSize:14,fontFamily:'monospace'}}>
                <div><span style={{color:'#6b7280'}}>Entry</span><br/><span style={{color:'#fff'}}>{activeScannedPattern.entry.toFixed(2)}</span></div>
                <div><span style={{color:'#6b7280'}}>Stop</span><br/><span style={{color:'#e91e63'}}>{activeScannedPattern.stop.toFixed(2)}</span></div>
                <div><span style={{color:'#6b7280'}}>T1</span><br/><span style={{color:'#00bcd4'}}>{activeScannedPattern.t1.toFixed(2)}</span></div>
              </div>
              <button onClick={()=>setActiveScannedPattern(null)} style={{marginTop:4,fontSize:14,color:'#4b5563',background:'none',border:'none',cursor:'pointer',fontFamily:'monospace'}}>x close</button>
            </div>
          )}
          {/* D8: Active Trade Section */}
          {activeTrade && (
            <ActiveTradePanel
              trade={activeTrade}
              currentPrice={live?.price ?? 0}
              onScaleC1={async () => {
                try {
                  await fetch(`${API_URL}/trade/scale`, { method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({contract:'c1',exit_price:0}) });
                  setActiveTrade(t => t ? { ...t, c1Status: 'closed' as const } : null);
                } catch {}
              }}
              onScaleC2={async () => {
                try {
                  await fetch(`${API_URL}/trade/scale`, { method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({contract:'c2',exit_price:0}) });
                  setActiveTrade(t => t ? { ...t, c2Status: 'closed' as const } : null);
                } catch {}
              }}
              onCloseAll={async () => {
                if (!confirm('Close all contracts?')) return;
                try {
                  await fetch(`${API_URL}/trade/close`, { method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({exit_price:0,reason:'manual'}) });
                  setActiveTrade(null);
                } catch {}
              }}
            />
          )}
          <div style={{flexShrink:0,borderTop:'1px solid #1e2738'}}>
            <VolumeTimer bar={bar??null} />
          </div>
        </div>

        {/* Left panel was moved above chart in V6.5 */}
      </div>

      {/* Bottom Trade Bar — always visible */}
      <BottomTradeBar
        opportunity={opportunity}
        oppLevels={oppLevels}
        oppSweep={oppSweep}
        oppScore={oppScore}
        liveSetup={liveSetup}
        checklistSetup={checklistSetup}
        onExecuteClick={(setup) => setChecklistSetup(setup)}
      />

      <style>{`
        @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
        .live-blink{animation:blink 2s infinite}
        ::-webkit-scrollbar{width:4px}
        ::-webkit-scrollbar-track{background:#0a0a0f}
        ::-webkit-scrollbar-thumb{background:#1e2738;border-radius:2px}
      `}</style>
      <PreEntryChecklist
        setup={checklistSetup}
        live={live}
        patterns={scannedPatterns}
        wsCircuitBreaker={wsCB}
        onExecute={handleExecuteTrade}
        onCancel={() => setChecklistSetup(null)}
      />
      {tradeToast && (
        <div style={{
          position:'fixed', top:24, left:'50%', transform:'translateX(-50%)', zIndex:10000,
          background:'#0f172a', border:`2px solid ${tradeToast.color}`,
          borderRadius:12, padding:'12px 24px', fontFamily:'monospace',
          boxShadow:`0 0 24px ${tradeToast.color}44`,
        }}>
          <span style={{ fontSize:14, fontWeight:800, color:tradeToast.color }}>{tradeToast.msg}</span>
        </div>
      )}
      {stopWarning && (
        <div style={{
          position:'fixed', top:70, left:'50%', transform:'translateX(-50%)', zIndex:10000,
          background:'#1a1500', border:'2px solid #f59e0b',
          borderRadius:10, padding:'10px 20px', fontFamily:'monospace',
          boxShadow:'0 0 20px rgba(245,158,11,0.3)',
        }}>
          <span style={{ fontSize:14, fontWeight:800, color:'#f59e0b' }}>
            ⚠ סטופ קרוב! {stopWarning.dist.toFixed(2)}pt
          </span>
        </div>
      )}
    </div>
  );
}
