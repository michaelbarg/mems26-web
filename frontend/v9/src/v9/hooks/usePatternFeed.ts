'use client';
// usePatternFeed — פולר משותף יחיד לנתוני-התבניות בזמן-אמת (מייקל 2026-07-17:
// "יותר חשוב לי זמן אמת בתבניות"). מושך יחד:
//   · GET /api/v9/build/pattern-status   (s2_inspector + woodies_inspector)
//   · GET /api/v9/gateway/decisions      (פיד "למה לא ירה" — gateway_routes.py:45)
// קצב: 15s — אותו קצב שכבר היה ל-AllPatternsPlan (אין פולינג מהיר-יותר; ראה
// CLAUDE.md § Frontend Polling Floors). ה-store ברמת-מודול עם ספירת-מנויים:
// כמה פאנלים שיהיו מנויים (PatternsTab בסיידבר + AllPatternsPlan בלנס) —
// לולאת-fetch אחת בלבד, כלומר פחות עומס מהמצב הקודם (שני פולרים נפרדים).
import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import type { BuildStatusResponse } from '../components/build_status/types';

const API =
  process.env.NEXT_PUBLIC_API_BASE ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000';

/** 15s = הקצב הקיים של פאנל-התבניות (AllPatternsPlan). אין להוריד בלי אישור מייקל. */
export const PATTERN_FEED_POLL_MS = 15000;
/** גיל-נתונים שממנו הפאנל מסומן "נתונים ישנים": מחזור-פולינג אחד + 5s חסד. */
export const PATTERN_FEED_STALE_MS = PATTERN_FEED_POLL_MS + 5000;

/** שורת-החלטה מה-gateway — trading_gateway.py:373-383 (outcome: blocked/live/demo/shadow_only/none). */
export interface GatewayDecision {
  ts: string;                 // ISO UTC עם אופסט (+00:00) — ניתן ל-Date.parse
  t_il?: string | null;       // HH:MM:SS שעון-ישראל, מהשרת
  system: number;             // 2=S2 five_min · 4=S4 woodies
  pattern?: string | null;
  direction?: string | null;
  entry?: number | null;
  blocked_by?: string | null; // מפתח-שער — תרגום ב-GATE_HE (planHelp.ts)
  outcome: string;
  trade_id?: number | string | null;
}

export interface DecisionsToday {
  fired: number;
  blocked: number;
  shadow_only: number;
  by_gate: Record<string, number>;
}

export interface DecisionsPayload {
  decisions: GatewayDecision[];
  today?: DecisionsToday;
}

export interface PatternFeedSnapshot {
  build: BuildStatusResponse | null;
  decisions: DecisionsPayload | null;
  error: string | null;
  /** ms-epoch של ה-fetch המוצלח האחרון (pattern-status). */
  lastFetchedAt: number | null;
}

const INITIAL: PatternFeedSnapshot = {
  build: null,
  decisions: null,
  error: null,
  lastFetchedAt: null,
};

let snapshot: PatternFeedSnapshot = INITIAL;
const listeners = new Set<() => void>();
let timer: ReturnType<typeof setInterval> | null = null;
let inFlight = false;

function emit(): void {
  listeners.forEach((l) => l());
}

async function fetchOnce(): Promise<void> {
  if (inFlight) return;
  inFlight = true;
  try {
    const [bRes, dRes] = await Promise.all([
      fetch(`${API}/api/v9/build/pattern-status`, { cache: 'no-store' }),
      fetch(`${API}/api/v9/gateway/decisions?limit=150`, { cache: 'no-store' }).catch(() => null),
    ]);
    if (!bRes.ok) {
      snapshot = { ...snapshot, error: `HTTP ${bRes.status}` };
    } else {
      const build = (await bRes.json()) as BuildStatusResponse;
      let decisions = snapshot.decisions; // בכשל-החלטות שומרים את הישן במקום למחוק
      if (dRes && dRes.ok) {
        try {
          decisions = (await dRes.json()) as DecisionsPayload;
        } catch {
          /* keep previous decisions */
        }
      }
      snapshot = { build, decisions, error: null, lastFetchedAt: Date.now() };
    }
  } catch (e) {
    snapshot = { ...snapshot, error: e instanceof Error ? e.message : String(e) };
  } finally {
    inFlight = false;
    emit();
  }
}

function subscribe(l: () => void): () => void {
  listeners.add(l);
  if (listeners.size === 1) {
    void fetchOnce();
    timer = setInterval(() => {
      void fetchOnce();
    }, PATTERN_FEED_POLL_MS);
  }
  return () => {
    listeners.delete(l);
    if (listeners.size === 0 && timer) {
      clearInterval(timer);
      timer = null;
    }
  };
}

export function usePatternFeed(): PatternFeedSnapshot & { refresh: () => void } {
  const snap = useSyncExternalStore(
    subscribe,
    () => snapshot,
    () => INITIAL,
  );
  const refresh = useCallback(() => {
    void fetchOnce();
  }, []);
  return { ...snap, refresh };
}

/** גיל-הנתונים בשניות + דגל-staleness, עם טיקר מקומי (5s, ללא רשת) לרענון-התצוגה.
 *  מחזיר גם nowMs לשימוש בחלון-ה"חם" של 5 הדקות (רזולוציית 5s מספיקה). */
export function useFeedAge(lastFetchedAt: number | null): {
  ageS: number | null;
  stale: boolean;
  nowMs: number;
} {
  const [nowMs, setNowMs] = useState<number>(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 5000);
    return () => clearInterval(id);
  }, []);
  const ageS =
    lastFetchedAt == null ? null : Math.max(0, Math.round((nowMs - lastFetchedAt) / 1000));
  const stale = ageS != null && ageS * 1000 > PATTERN_FEED_STALE_MS;
  return { ageS, stale, nowMs };
}
