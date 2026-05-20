'use client';

import { useEffect, useRef } from 'react';
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
  PINK_RTH,
  WHITE_YDAY,
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
  if (!ts) return 0;
  return Math.floor(new Date(ts.replace(' ', 'T') + '-04:00').getTime() / 1000);
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

  // Extend last point to current time so the step continues to "now"
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
 */
export function TpoContinuityOverlay({ chart, tpo, paneIndex = 0 }: Props) {
  const seriesRef = useRef<ISeriesApi<'Line'>[]>([]);

  useEffect(() => {
    if (!chart || !tpo) return;

    // Remove previous series
    for (const s of seriesRef.current) {
      try {
        chart.removeSeries(s);
      } catch {
        /* noop */
      }
    }
    seriesRef.current = [];

    const periods = tpo.periods ?? [];
    if (periods.length < 2) return;

    const nowUnix = Math.floor(Date.now() / 1000);

    // Determine today and yesterday dates from session_opened_ts
    const todayDay = sessionDay(tpo.session_opened_ts ?? null);
    const allDays = periods
      .map((p) => sessionDay(p.opened_ts))
      .filter((d): d is string => d != null);
    const uniqueDays = [...new Set(allDays)].sort();
    const yesterdayDay =
      uniqueDays.length >= 2
        ? uniqueDays[uniqueDays.length - (todayDay ? 2 : 1)]
        : null;

    const next: ISeriesApi<'Line'>[] = [];

    // Yesterday: straight horizontal lines only (from syncTpoPriceLines).
    // No stepped continuity — yesterday's levels are static history.

    // Today continuity (pink, solid) — RTH only (09:30–16:00 ET)
    const isRth = (() => {
      try {
        const et = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
        const mins = et.getHours() * 60 + et.getMinutes();
        return mins >= 9 * 60 + 30 && mins < 16 * 60;
      } catch { return false; }
    })();
    if (todayDay && isRth) {
      for (const cfg of LEVEL_CONFIGS) {
        const data = buildStepData(periods, todayDay, cfg.periodKey, nowUnix);
        if (data.length < 2) continue;
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
          console.error('[TPO continuity] today series failed', cfg.key, e);
        }
      }
    }

    seriesRef.current = next;
    console.info('[TPO continuity]', {
      yesterdayDay,
      todayDay,
      series: next.length,
      periods: periods.length,
    });

    return () => {
      for (const s of next) {
        try {
          chart.removeSeries(s);
        } catch {
          /* noop */
        }
      }
    };
  }, [chart, tpo, paneIndex]);

  return null;
}
