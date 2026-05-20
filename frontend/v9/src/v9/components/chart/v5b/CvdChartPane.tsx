'use client';

import {
  ColorType,
  createChart,
  CrosshairMode,
  type IChartApi,
  CandlestickSeries,
  type CandlestickData,
  type ISeriesApi,
  type Time,
  type WhitespaceData,
} from 'lightweight-charts';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  aggregateCvdPoints,
  densifyCvdPoints,
  tsToUnix,
  type CvdPoint,
} from './cvdMapping';
import { registerVolumeChart, unregisterVolumeChart } from '../../../stores/chartSyncStore';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const POLL_MS = 5000;
const LS_CVD_PANEL = 'mems26-cvd-panel-pct';

/**
 * Bucket size (seconds) per TF — must match TF_SECONDS in ChartV5b. Drives
 * CVD aggregation so the CVD candle period mirrors the price chart's TF.
 */
const TF_BUCKET_SECONDS: Record<string, number> = {
  '3m': 180,
  '5m': 300,
  '15m': 900,
  '30m': 1800,
  '1h': 3600,
};

/**
 * Build the CVD candle series, ALIGNED 1:1 with the price chart's bars.
 *
 * P30 (2026-05-20) alignment guarantee:
 *   lightweight-charts auto-computes barSpacing = chartWidth / N where
 *   N is the candle count in the visible range. If price and CVD have
 *   different N in the same range, their candles render at different
 *   widths and the bottom pane no longer lines up under the top pane.
 *   This was the cockpit symptom — CVD bars compressed or stretched
 *   relative to price bars when CVD points were sparser than bars
 *   (e.g. first session of the day before CVD started, or any host
 *   bar slot where the DLL skipped a point).
 *
 * Strategy:
 *   - When CVD points carry their own `t` (canonical post-v9.4.2 DLL),
 *     iterate over PRICE BARS and emit one entry per bar's timestamp.
 *     Carry the cumulative-delta value forward from the latest CVD
 *     point at or before the bar; emit `WhitespaceData` for bars that
 *     are strictly before the first CVD point so the time slot is
 *     reserved on the X-axis but no misleading zero candle is drawn.
 *   - Legacy fallback (no `t`): pair by index against the last N bars,
 *     identical to the pre-v9.4.2 behaviour.
 */
function cumOhlcSeries(
  bars: Array<{ ts: string }>,
  points: CvdPoint[],
): Array<CandlestickData<Time> | WhitespaceData<Time>> {
  if (!points.length) return [];
  const haveAllT = points.every((p) => typeof p.t === 'number');

  if (!haveAllT) {
    const n = Math.min(points.length, bars.length);
    if (n === 0) return [];
    const pSlice = points.slice(-n);
    const bSlice = bars.slice(-n);
    return pSlice.map((pt, idx) => {
      const prevCum = idx > 0 ? pSlice[idx - 1].cum : pt.cum - pt.d;
      const open = prevCum;
      const close = pt.cum;
      return {
        time: tsToUnix(bSlice[idx].ts) as Time,
        open,
        high: Math.max(open, close),
        low: Math.min(open, close),
        close,
      };
    });
  }

  if (!bars.length) {
    const sortedPts = points.slice().sort((a, b) => (a.t ?? 0) - (b.t ?? 0));
    return sortedPts.map((pt, idx) => {
      const prevCum = idx > 0 ? sortedPts[idx - 1].cum : pt.cum - pt.d;
      const open = prevCum;
      const close = pt.cum;
      return {
        time: pt.t as Time,
        open,
        high: Math.max(open, close),
        low: Math.min(open, close),
        close,
      };
    });
  }

  const pointsByT = new Map<number, CvdPoint>();
  for (const p of points) {
    if (typeof p.t === 'number') pointsByT.set(p.t, p);
  }
  const sortedT = Array.from(pointsByT.keys()).sort((a, b) => a - b);
  const firstCvdT = sortedT[0];

  const out: Array<CandlestickData<Time> | WhitespaceData<Time>> = [];
  let cvdPtr = 0;
  let lastCum: number | null = null;
  let prevClose: number | null = null;
  for (const bar of bars) {
    const barT = tsToUnix(bar.ts);
    if (!Number.isFinite(barT)) continue;
    if (barT < firstCvdT) {
      out.push({ time: barT as Time });
      continue;
    }
    while (cvdPtr < sortedT.length && sortedT[cvdPtr] <= barT) {
      lastCum = pointsByT.get(sortedT[cvdPtr])!.cum;
      cvdPtr += 1;
    }
    if (lastCum === null) {
      out.push({ time: barT as Time });
      continue;
    }
    const close = lastCum;
    const open = prevClose ?? close;
    out.push({
      time: barT as Time,
      open,
      high: Math.max(open, close),
      low: Math.min(open, close),
      close,
    });
    prevClose = close;
  }
  return out;
}

type Props = {
  bars: Array<{ ts: string }>;
  priceChartRef: React.RefObject<IChartApi | null>;
  /** Active timeframe (3m/5m/15m/30m/1h). Drives CVD aggregation. */
  activeTf?: string;
  /**
   * P30 (2026-05-20): parent controls which pane owns the cockpit's shared
   * time axis. When false, the CVD chart hides its own axis labels (parent
   * has restored the price chart's axis because the CVD pane is too small
   * to display labels usefully). Default true preserves prior behaviour.
   */
  axisVisible?: boolean;
};

export function CvdChartPane({
  bars,
  priceChartRef,
  activeTf = '5m',
  axisVisible = true,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [header, setHeader] = useState('Cumulative Delta Bars - Volume');

  const fittedRef = useRef(false);
  const applyData = useCallback(
    (barList: Array<{ ts: string }>, points: CvdPoint[]) => {
      if (!seriesRef.current || !points.length) return;
      const candles = cumOhlcSeries(barList, points);
      if (!candles.length) return;
      seriesRef.current.setData(candles);
      if (!fittedRef.current) {
        fittedRef.current = true;
        const price = priceChartRef.current;
        const cvd = chartRef.current;
        if (price && cvd) {
          try {
            const range = price.timeScale().getVisibleLogicalRange();
            if (range) cvd.timeScale().setVisibleLogicalRange(range);
          } catch {
            cvd.timeScale().fitContent();
          }
        } else {
          chartRef.current?.timeScale().fitContent();
        }
      }
      // P30 (2026-05-20): scan back for the most recent real candle. The
      // tail of `candles` may now be `WhitespaceData` (when bars run ahead
      // of the latest CVD point) which has no OHLC fields — `last.open`
      // would explode at runtime otherwise.
      let lastOhlc: CandlestickData<Time> | null = null;
      for (let i = candles.length - 1; i >= 0; i -= 1) {
        const c = candles[i] as CandlestickData<Time>;
        if (typeof c.open === 'number') {
          lastOhlc = c;
          break;
        }
      }
      if (lastOhlc) {
        setHeader(
          `Cumulative Delta Bars - Volume  Open: ${lastOhlc.open.toFixed(0)}  High: ${lastOhlc.high.toFixed(0)}  Low: ${lastOhlc.low.toFixed(0)}  Close: ${lastOhlc.close.toFixed(0)}`,
        );
      }
    },
    [priceChartRef],
  );

  const bucketSeconds = useMemo(() => TF_BUCKET_SECONDS[activeTf] ?? 300, [activeTf]);

  const fetchCvd = useCallback(async () => {
    if (!seriesRef.current) return;
    try {
      const res = await fetch(`${API}/api/v9/cumulative_delta/current`);
      const d = await res.json();
      const rawPoints = (d.points ?? []) as CvdPoint[];
      if (!rawPoints.length || !bars.length) return;
      // Two-step normalization so a CVD candle is always exactly one TF
      // wide, matching the price candle width visually:
      //   1. densify  — fill 5-min slots when DLL still emits 25-min points
      //                  (pre-Remote-Build legacy DLL); no-op once DLL emits
      //                  one point per host bar.
      //   2. aggregate — collapse to the active TF's bucket. For 5 m this
      //                  is essentially a passthrough; for 15 m / 30 m / 1 h
      //                  it folds multiple buckets into one candle.
      const denseRaw = densifyCvdPoints(rawPoints, 300);
      const points = aggregateCvdPoints(denseRaw, bucketSeconds);
      applyData(bars, points);
    } catch {
      /* keep last */
    }
  }, [applyData, bars, bucketSeconds]);

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0a0a0a' },
        textColor: '#a3a3a3',
        fontSize: 10,
        fontFamily: 'ui-monospace, monospace',
      },
      grid: {
        vertLines: { color: '#1a1a1a', style: 1 },
        horzLines: { color: '#1a1a1a', style: 1 },
      },
      rightPriceScale: {
        borderColor: '#262626',
        // Leave room for the shared time axis at the bottom of this pane.
        scaleMargins: { top: 0.1, bottom: 0.25 },
      },
      timeScale: {
        // The cockpit's shared time axis lives here when this pane is tall
        // enough to render labels — the parent flips visibility off when
        // the user shrinks this pane below the useful-height threshold.
        visible: axisVisible,
        borderVisible: true,
        borderColor: '#262626',
        timeVisible: true,
        secondsVisible: false,
        // P30 alignment guarantee: pin to 0 (lightweight-charts default)
        // so future global default drift can't push CVD candles out of
        // line with price candles.
        rightOffset: 0,
      },
      crosshair: { mode: CrosshairMode.Normal },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#16a34a',
      downColor: '#dc2626',
      borderUpColor: '#16a34a',
      borderDownColor: '#dc2626',
      wickUpColor: '#16a34a',
      wickDownColor: '#dc2626',
      priceLineVisible: false,
      lastValueVisible: true,
    });

    chartRef.current = chart;
    seriesRef.current = series;
    registerVolumeChart(chart);

    const ro = new ResizeObserver(([entry]) => {
      chart.resize(entry.contentRect.width, entry.contentRect.height);
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      unregisterVolumeChart();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    try {
      chart.timeScale().applyOptions({ visible: axisVisible });
    } catch {
      /* chart not ready */
    }
  }, [axisVisible]);

  useEffect(() => {
    fetchCvd();
    const id = setInterval(fetchCvd, POLL_MS);
    return () => clearInterval(id);
  }, [fetchCvd]);

  useEffect(() => {
    fetchCvd();
  }, [bars, fetchCvd]);

  // Re-fit the pane to the new bucket period on TF change so the user sees
  // the new candle layout immediately (otherwise the time-sync would hold
  // the previous TF's window until the next pan).
  useEffect(() => {
    fittedRef.current = false;
    fetchCvd();
  }, [activeTf, fetchCvd]);

  return (
    <div
      data-testid="cvd-chart-pane"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 80,
        background: '#0a0a0a',
        borderTop: '1px solid #262626',
      }}
    >
      <div
        style={{
          flexShrink: 0,
          padding: '2px 8px',
          fontSize: 9,
          fontFamily: 'ui-monospace, monospace',
          color: '#94a3b8',
          borderBottom: '1px solid #1a1a1a',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {header}
      </div>
      <div ref={containerRef} style={{ flex: 1, minHeight: 60 }} />
    </div>
  );
}

export function loadCvdPanelDefaultPct(): number {
  if (typeof window === 'undefined') return 28;
  const v = Number(localStorage.getItem(LS_CVD_PANEL));
  return Number.isFinite(v) && v >= 12 && v <= 55 ? v : 28;
}

export function saveCvdPanelPct(pct: number) {
  localStorage.setItem(LS_CVD_PANEL, String(Math.round(pct)));
}
