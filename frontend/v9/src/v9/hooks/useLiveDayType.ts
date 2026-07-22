'use client';
// useLiveDayType — the NEW state-machine classifier's current call for TODAY, as a live shadow.
// Polls /api/v9/day_type/classify_replay?date=today (read-only; no engine change). Lets the S1
// square + any S1 surface show the validated 7-type classifier instead of the old live engine,
// BEFORE the promotion to the trading gate (Michael 2026-06-20). 30s poll (CLAUDE.md floors-safe).
//
// P-UI day-type round (2026-07-02): ADDITIVE fields parsed from the SAME response (no new
// requests, interval unchanged): `since` (ET HH:MM the current type became continuous —
// earliest contiguous classify_replay segment with the final day_type), direction/reason
// (classifier output), and the classifier's own IB/VA/opening/volume context
// (ib_* / va_width / opening_type / vol_ratio — daytype_classify_routes.py:229-240).
// Existing consumers (DayTypePill, KeyLevelsStrip) read only day_type/status — unaffected.
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const todayISO = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());

export interface LiveDayType {
  /** The label to DISPLAY = what the trading gate acts on (override-aware) when
   *  available (GAP G-16 / S124 G5); falls back to classify_replay otherwise. */
  day_type: string;
  /** The override-aware gate value from /day_type/live (null pre-market/closed). */
  gate_day_type?: string | null;
  /** True when the gate value differs from classify_replay (a manual override is active). */
  overridden?: boolean;
  status: string;
  invalidated?: boolean;
  /** ET HH:MM the current day_type became continuous (across status upgrades). */
  since?: string | null;
  /** Playbook stance: none | fade_both | with_extension | with_trend | winner_side. */
  direction?: string | null;
  reason?: string | null;
  n_bars?: number | null;
  ib_high?: number | null;
  ib_low?: number | null;
  ib_width?: number | null;
  ib_class?: string | null;
  /** 'sierra_tpo' (SoT) or 'bars' fallback. */
  ib_source?: string | null;
  va_width?: number | null;
  opening_type?: string | null;
  vol_ratio?: number | null;
}

interface ReplaySegment { startBar: number; time: string; day_type: string; status: string }

export function useLiveDayType(): LiveDayType | null {
  const [dt, setDt] = useState<LiveDayType | null>(null);
  useEffect(() => {
    let cancel = false;
    const load = () =>
      // GAP G-16 / S124 G5: keep classify_replay for the rich detail (segments,
      // IB/VA/opening context), but OVERLAY the DISPLAYED label with the
      // override-aware gate value from /day_type/live — so the UI shows what the
      // trading gate actually acts on (not the date-based classifier that ignores
      // a manual override). live=null (pre-market/closed) → byte-identical to before.
      Promise.all([
        fetch(`${API}/api/v9/day_type/classify_replay?date=${todayISO()}`)
          .then((r) => (r.ok ? r.json() : null)).catch(() => null),
        fetch(`${API}/api/v9/day_type/live`)
          .then((r) => (r.ok ? r.json() : null)).catch(() => null),
      ])
        .then(([d, live]) => {
          if (cancel || !d?.final?.day_type) return;
          // since-when: walk segments backwards while the day_type matches the final one,
          // so status-only upgrades (PROVISIONAL→CLASSIFIED) don't reset the clock.
          const segs: ReplaySegment[] = Array.isArray(d.segments) ? d.segments : [];
          let sinceSeg: ReplaySegment | null = null;
          for (let i = segs.length - 1; i >= 0; i--) {
            if (segs[i].day_type === d.final.day_type) sinceSeg = segs[i];
            else break;
          }
          const gate: string | null = live && live.day_type ? String(live.day_type) : null;
          const overridden = !!(gate && gate !== d.final.day_type);
          setDt({
            // P0-2 (one-source): the GATE label only; live=null → honest "—"
            // (never classify_replay — audit-only, flip-flops intra-session)
            day_type: gate ?? '—',
            gate_day_type: gate,
            overridden,
            status: d.final.status,
            invalidated: d.final.invalidated,
            since: sinceSeg?.time ?? null,
            direction: d.final.direction ?? null,
            reason: d.final.reason ?? null,
            n_bars: d.n_bars ?? null,
            ib_high: d.ib_high ?? null,
            ib_low: d.ib_low ?? null,
            ib_width: d.ib_width ?? null,
            ib_class: d.ib_class ?? null,
            ib_source: d.ib_source ?? null,
            va_width: d.va_width ?? null,
            opening_type: d.opening_type ?? null,
            vol_ratio: d.vol_ratio ?? null,
          });
        })
        .catch(() => { /* offline → keep last / null; the caller falls back to the live store */ });
    load();
    const id = setInterval(load, 30000);
    return () => { cancel = true; clearInterval(id); };
  }, []);
  return dt;
}
