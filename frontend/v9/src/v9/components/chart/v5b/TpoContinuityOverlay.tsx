'use client';

import { useEffect, useRef, useState } from 'react';
import {
  LineSeries,
  LineStyle,
  LineType,
  type IChartApi,
  type ISeriesApi,
  type LineWidth,
  type Time,
} from 'lightweight-charts';
import {
  coerceMesPrice,
  parseSierraTsToMs,
  PINK_RTH,
  type TpoOverlayData,
  type TpoPeriod,
} from './tpoLevels';

type LevelKey = 'poc' | 'vah' | 'val';
type StepPoint = { time: Time; value: number };

const CONTINUITY_OPACITY = 0.6;
const LEVEL_CONFIGS: Array<{ key: LevelKey; periodKey: string; width: LineWidth }> = [
  { key: 'poc', periodKey: 'poc_price', width: 2 },
  { key: 'vah', periodKey: 'vah_price', width: 1 },
  { key: 'val', periodKey: 'val_price', width: 1 },
];

function periodToUnix(ts: string | null): number {
  const ms = parseSierraTsToMs(ts);
  return ms > 0 ? Math.floor(ms / 1000) : 0;
}

function sessionDay(ts: string | null): string | null {
  if (!ts) return null;
  const m = String(ts).match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : null;
}

function buildStepData(
  periods: TpoPeriod[],
  dayFilter: string | null,
  levelKey: string,
  nowUnix: number,
): StepPoint[] {
  const filtered = dayFilter
    ? periods.filter((p) => sessionDay(p.opened_ts) === dayFilter)
    : periods;

  const sorted = [...filtered].sort(
    (a, b) => periodToUnix(a.opened_ts) - periodToUnix(b.opened_ts),
  );

  const points: StepPoint[] = [];
  for (const p of sorted) {
    const t = periodToUnix(p.opened_ts);
    if (t <= 0) continue;
    const raw = (p as any)[levelKey];
    const price = coerceMesPrice(raw);
    if (price == null) continue;
    points.push({ time: t as Time, value: price });
  }

  // Extend last point to right edge (already capped by caller to last bar + buffer)
  if (points.length > 0 && nowUnix > 0) {
    const last = points[points.length - 1];
    if (nowUnix > Number(last.time)) {
      points.push({ time: nowUnix as Time, value: last.value });
    }
  }

  return points;
}

type Props = {
  chart: IChartApi | null;
  tpo: TpoOverlayData | null;
  paneIndex?: number;
};

/**
 * TPO continuity stepped lines — shows how POC/VAH/VAL evolved over the session.
 * Uses lightweight-charts LineSeries with LineType.WithSteps (chart-engine-locked).
 *
 * Refresh cadence (Michael 2026-05-22 18:24 IL — "they have a 2-bar
 * delay"): the underlying `tpo` overlay only updates every 30 min in
 * RTH, so without an internal tick the stepped right edge would lag the
 * live tape by up to 6 bars. A 10 s self-tick re-runs the effect to
 * re-anchor the right edge at `Math.floor(Date.now()/1000)`. When the
 * series count is unchanged we reuse existing LineSeries via `setData`
 * — no flicker, no canvas churn.
 */
export function TpoContinuityOverlay({ chart, tpo, paneIndex = 0 }: Props) {
  const seriesRef = useRef<ISeriesApi<'Line'>[]>([]);
  const [tick, setTick] = useState(0);

  // Internal tick — drives the "follow the price" refresh of the stepped
  // right edge. 10 s matches the bars-poll cadence in ChartV5b.tsx::
  // barsPoll so price candles and TPO right-edge advance in lockstep.
  useEffect(() => {
    const id = setInterval(() => setTick((t) => (t + 1) % 1_000_000), 10_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!chart || !tpo) return;

    const periods = tpo.periods ?? [];
    // P31 Issue B follow-up (2026-05-22 RTH UAT): the original guard
    // required ≥2 periods, which left the chart blank for the first 30 min
    // of RTH (only letter A captured by TPOHistorySnapshotter — see
    // backend/v9/services/tpo_history_snapshotter.py). `buildStepData`
    // extends the last point to `nowUnix`, so even a single period
    // produces a 2-point stepped line from letter A's start to "now".
    // Drop the lower bound to 1 so the first stepped segment appears
    // immediately at 09:30:05 ET — matches Sierra Study ID:3 behavior.
    if (periods.length < 1) {
      // Tear down any prior series — we have nothing to draw now.
      for (const s of seriesRef.current) {
        try { chart.removeSeries(s); } catch { /* noop */ }
      }
      seriesRef.current = [];
      return;
    }

    // `nowUnix` is real-UTC seconds. Aligns directly with the chart's
    // post-P31-FE-TZ-2 frame where bars, TPO periods, and CVD points all
    // share the same real-UTC unix axis (see ChartV5b.tsx::tsToUnix and
    // tpoLevels.ts::parseSierraTsToMs — both parse as `Z` now). Earlier
    // attempted `+ 4*3600` workaround was needed only while the chart
    // applied a stale `-04:00` ET shift; removed once the root TZ-2 fix
    // landed during 2026-05-22 RTH UAT.
    // FIX 3B: cap at the last bar's time, not wall-clock time. When feed is
    // stale (RTH closed or gap), Date.now() projects hours past the last bar.
    // Use the latest period's opened_ts + 30min as a proxy for the last bar.
    const wallNow = Math.floor(Date.now() / 1000);
    const latestPeriodTs = periods.length > 0
      ? Math.max(...periods.map(p => periodToUnix(p.opened_ts)).filter(t => t > 0))
      : 0;
    // Right edge = latest data + one bar (5min), capped at wall clock
    const nowUnix = latestPeriodTs > 0
      ? Math.min(wallNow, latestPeriodTs + 1800 + 300)  // last period + 30min + 5min buffer
      : wallNow;

    const todayDay = sessionDay(tpo.session_opened_ts ?? null);

    // Today continuity (pink, solid) — RTH only (09:30–16:00 ET)
    const isRth = (() => {
      try {
        const et = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
        const mins = et.getHours() * 60 + et.getMinutes();
        return mins >= 9 * 60 + 30 && mins < 16 * 60;
      } catch { return false; }
    })();

    // Off-RTH or no today data — destroy any prior series and exit.
    if (!todayDay || !isRth) {
      for (const s of seriesRef.current) {
        try { chart.removeSeries(s); } catch { /* noop */ }
      }
      seriesRef.current = [];
      return;
    }

    // Build per-level data slices. Some levels may have <2 points (early
    // RTH, only letter A captured) — we skip those and treat the active
    // level set as "the set that has ≥2 points right now".
    const slices: Array<{ cfg: typeof LEVEL_CONFIGS[number]; data: StepPoint[] }> = [];
    for (const cfg of LEVEL_CONFIGS) {
      const data = buildStepData(periods, todayDay, cfg.periodKey, nowUnix);
      if (data.length >= 2) slices.push({ cfg, data });
    }

    // Fast path: reuse existing series when the active level count is
    // unchanged. setData on the same canvas object skips the React/
    // lightweight-charts mount/unmount cycle — no flicker, safe to call
    // at the 10 s tick cadence above.
    if (seriesRef.current.length === slices.length && slices.length > 0) {
      slices.forEach(({ cfg, data }, idx) => {
        try {
          seriesRef.current[idx].applyOptions({
            color: PINK_RTH,
            lineWidth: cfg.width,
            lineStyle: LineStyle.Solid,
            lineType: LineType.WithSteps,
          });
          seriesRef.current[idx].setData(data);
        } catch (e) {
          console.error('[TPO continuity] reuse-update failed', cfg.key, e);
        }
      });
      return;
    }

    // Slow path: level count changed (mount, HMR, session rotation, or
    // a new TPO letter appeared and bumped slices.length). Tear down
    // and rebuild.
    for (const s of seriesRef.current) {
      try { chart.removeSeries(s); } catch { /* noop */ }
    }
    seriesRef.current = [];

    const next: ISeriesApi<'Line'>[] = [];
    for (const { cfg, data } of slices) {
      try {
        const s = chart.addSeries(
          LineSeries,
          {
            color: PINK_RTH,
            lineWidth: cfg.width,
            lineStyle: LineStyle.Solid,
            lineType: LineType.WithSteps,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
            title: '',
          },
          paneIndex,
        );
        s.setData(data);
        next.push(s);
      } catch (e) {
        console.error('[TPO continuity] today series create failed', cfg.key, e);
      }
    }
    seriesRef.current = next;
  }, [chart, tpo, paneIndex, tick]);

  // Cleanup only on unmount — intermediate tick re-runs handle their
  // own reuse/teardown above. Returning a cleanup from the effect that
  // also runs every tick would destroy/recreate series on every 10 s
  // tick, defeating the no-flicker reuse path.
  useEffect(() => {
    return () => {
      for (const s of seriesRef.current) {
        try { chart?.removeSeries(s); } catch { /* noop */ }
      }
      seriesRef.current = [];
    };
  }, [chart]);

  return null;
}
