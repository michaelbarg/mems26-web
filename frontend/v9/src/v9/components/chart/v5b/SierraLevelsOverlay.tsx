'use client';

import { useEffect, useMemo, useState } from 'react';
import type { IChartApi, ISeriesApi, Time } from 'lightweight-charts';

export type TpoPeriod = {
  opened_ts: string | null;
  closed_ts: string | null;
  poc_price: number | null;
  vah_price?: number | null;
  val_price?: number | null;
};

export type TpoOverlayData = {
  poc?: number | null;
  vah?: number | null;
  val?: number | null;
  periods?: TpoPeriod[];
  ib_high?: number | null;
  ib_mid?: number | null;
  ib_low?: number | null;
  ib_locked?: boolean;
  prior_day?: {
    found?: boolean;
    high?: number | null;
    low?: number | null;
    close?: number | null;
  };
  previous_session?: {
    found?: boolean;
    poc?: number | null;
    vah?: number | null;
    val?: number | null;
  };
};

type BarPoint = { ts: string };

const POC_STEPS = [
  { width: 1.0, opacity: 0.28 },
  { width: 1.0, opacity: 0.4 },
  { width: 1.1, opacity: 0.52 },
  { width: 1.3, opacity: 0.65 },
  { width: 1.9, opacity: 0.95 },
];

function toEpoch(ts: string): number {
  if (/^\d+$/.test(ts)) return Number(ts) * 1000;
  return new Date(ts.replace(' ', 'T')).getTime();
}

function tsToUnix(ts: string): number {
  return Math.floor(toEpoch(ts) / 1000);
}

function chartSpan(bars: BarPoint[]): { t0: number; t1: number; firstMs: number; lastMs: number } | null {
  if (!bars.length) return null;
  const firstMs = toEpoch(bars[0].ts);
  const lastMs = toEpoch(bars[bars.length - 1].ts);
  return { t0: tsToUnix(bars[0].ts), t1: tsToUnix(bars[bars.length - 1].ts), firstMs, lastMs };
}

function sessionXRange(s: TpoPeriod, bars: BarPoint[]): { t0: number; t1: number } | null {
  if (!bars.length || !s.opened_ts) return null;
  const span = chartSpan(bars);
  if (!span) return null;
  const openMs = toEpoch(s.opened_ts);
  const closeMs = s.closed_ts ? toEpoch(s.closed_ts) : span.lastMs;
  if (openMs > span.lastMs) return null;
  const effOpen = Math.max(openMs, span.firstMs);
  const effClose = Math.min(closeMs, span.lastMs);
  if (effOpen > effClose) return null;

  let fi = 0;
  let li = bars.length - 1;
  for (let i = 0; i < bars.length; i++) {
    if (toEpoch(bars[i].ts) >= effOpen) {
      fi = i;
      break;
    }
  }
  for (let i = bars.length - 1; i >= 0; i--) {
    if (toEpoch(bars[i].ts) <= effClose) {
      li = i;
      break;
    }
  }
  if (fi > li) return null;
  return { t0: tsToUnix(bars[fi].ts), t1: tsToUnix(bars[li].ts) };
}

type Segment = {
  x1: number;
  x2: number;
  y: number;
  color: string;
  width: number;
  opacity: number;
  dash?: string;
};

type Props = {
  chartRef: React.RefObject<IChartApi | null>;
  candleRef: React.RefObject<ISeriesApi<'Candlestick'> | null>;
  bars: BarPoint[];
  tpo: TpoOverlayData | null;
  width: number;
  height: number;
};

export function SierraLevelsOverlay({
  chartRef,
  candleRef,
  bars,
  tpo,
  width,
  height,
}: Props) {
  const [segments, setSegments] = useState<Segment[]>([]);

  const plan = useMemo(() => {
    if (!tpo || !bars.length) return [];
    const span = chartSpan(bars);
    if (!span) return [];
    const out: Array<Omit<Segment, 'x1' | 'x2' | 'y'> & { price: number; t0?: number; t1?: number }> = [];

    const periods = [...(tpo.periods ?? [])]
      .filter((p) => sessionXRange(p, bars) != null)
      .sort((a, b) => toEpoch(a.opened_ts ?? '0') - toEpoch(b.opened_ts ?? '0'));
    const last5 = periods.slice(-5);
    const off = POC_STEPS.length - last5.length;
    last5.forEach((s, i) => {
      if (s.poc_price == null) return;
      const st = POC_STEPS[off + i];
      if (!st) return;
      const range = sessionXRange(s, bars);
      if (!range) return;
      out.push({
        price: s.poc_price,
        t0: range.t0,
        t1: range.t1,
        color: '#ec4899',
        width: st.width,
        opacity: st.opacity,
      });
    });

    if (tpo.poc != null) {
      out.push({
        price: tpo.poc,
        t0: span.t0,
        t1: span.t1,
        color: '#ec4899',
        width: 1.2,
        opacity: 0.45,
        dash: '6 3',
      });
    }
    if (tpo.vah != null) {
      out.push({
        price: tpo.vah,
        t0: span.t0,
        t1: span.t1,
        color: '#ec4899',
        width: 1,
        opacity: 0.55,
        dash: '3 3',
      });
    }
    if (tpo.val != null) {
      out.push({
        price: tpo.val,
        t0: span.t0,
        t1: span.t1,
        color: '#ec4899',
        width: 1,
        opacity: 0.55,
        dash: '3 3',
      });
    }

    const prev = tpo.previous_session;
    if (prev?.found) {
      for (const price of [prev.poc, prev.vah, prev.val]) {
        if (price == null) continue;
        out.push({
          price,
          t0: span.t0,
          t1: span.t1,
          color: '#e2e8f0',
          width: 1,
          opacity: 0.5,
          dash: '2 4',
        });
      }
    }

    if (tpo.prior_day?.found && tpo.prior_day.high != null) {
      out.push({
        price: tpo.prior_day.high,
        t0: span.t0,
        t1: span.t1,
        color: '#f8fafc',
        width: 1,
        opacity: 0.85,
        dash: '4 4',
      });
    }
    if (tpo.prior_day?.found && tpo.prior_day.low != null) {
      out.push({
        price: tpo.prior_day.low,
        t0: span.t0,
        t1: span.t1,
        color: '#f8fafc',
        width: 1,
        opacity: 0.85,
        dash: '4 4',
      });
    }

    if (tpo.ib_locked && tpo.ib_high != null && tpo.ib_high > 0) {
      out.push({
        price: tpo.ib_high,
        t0: span.t0,
        t1: span.t1,
        color: '#06b6d4',
        width: 1,
        opacity: 0.7,
      });
    }
    if (tpo.ib_locked && tpo.ib_mid != null && tpo.ib_mid > 0) {
      out.push({
        price: tpo.ib_mid,
        t0: span.t0,
        t1: span.t1,
        color: '#06b6d4',
        width: 1,
        opacity: 0.55,
        dash: '2 2',
      });
    }
    if (tpo.ib_locked && tpo.ib_low != null && tpo.ib_low > 0) {
      out.push({
        price: tpo.ib_low,
        t0: span.t0,
        t1: span.t1,
        color: '#06b6d4',
        width: 1,
        opacity: 0.55,
        dash: '2 2',
      });
    }

    return out;
  }, [bars, tpo]);

  useEffect(() => {
    const chart = chartRef.current;
    const series = candleRef.current;
    if (!chart || !series || !width || !height) {
      setSegments([]);
      return;
    }

    const rebuild = () => {
      const ts = chart.timeScale();
      const built: Segment[] = [];

      for (const p of plan) {
        const y = series.priceToCoordinate(p.price);
        if (y == null) continue;

        let x1: number | null = null;
        let x2: number | null = null;
        if (p.t0 != null && p.t1 != null) {
          x1 = ts.timeToCoordinate(p.t0 as Time);
          x2 = ts.timeToCoordinate(p.t1 as Time);
        }
        if (x1 == null || x2 == null) continue;
        built.push({
          x1: Math.min(x1, x2),
          x2: Math.max(x1, x2),
          y,
          color: p.color,
          width: p.width,
          opacity: p.opacity,
          dash: p.dash,
        });
      }
      setSegments(built);
    };

    rebuild();
    chart.timeScale().subscribeVisibleLogicalRangeChange(rebuild);
    chart.subscribeCrosshairMove(rebuild);
    return () => {
      try {
        chart.timeScale().unsubscribeVisibleLogicalRangeChange(rebuild);
      } catch {
        /* chart removed */
      }
      try {
        chart.unsubscribeCrosshairMove(rebuild);
      } catch {
        /* chart removed */
      }
    };
  }, [bars, candleRef, chartRef, height, plan, width]);

  if (!segments.length) return null;

  return (
    <svg
      width={width}
      height={height}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        zIndex: 10,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      {segments.map((s, i) => (
        <line
          key={i}
          x1={s.x1}
          y1={s.y}
          x2={s.x2}
          y2={s.y}
          stroke={s.color}
          strokeWidth={s.width}
          strokeDasharray={s.dash}
          opacity={s.opacity}
        />
      ))}
    </svg>
  );
}
