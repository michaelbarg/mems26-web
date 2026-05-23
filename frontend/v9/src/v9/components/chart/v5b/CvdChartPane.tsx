'use client';

import type {
  CandlestickData,
  HistogramData,
  ISeriesApi,
  Time,
  WhitespaceData,
} from 'lightweight-charts';
import {
  aggregateCvdPoints,
  alignCvdPointTimesToPriceBars,
  densifyCvdPoints,
  tsToUnix,
  type CvdPoint,
} from './cvdMapping';

const LS_CVD_PANEL = 'mems26-cvd-panel-pct';

const TF_BUCKET_SECONDS: Record<string, number> = {
  '3m': 180,
  '5m': 300,
  '15m': 900,
  '30m': 1800,
  '1h': 3600,
};

export type CvdAlignBar = { ts: string; t?: number };
export type CvdRenderMode = 'histogram' | 'ohlc';

/** CVD shelf green — distinct from price candles (#16a34a). */
export const CVD_PANE_UP = '#34d399';
export const CVD_PANE_DOWN = '#f87171';
export const CVD_PANE_PRICE_LINE = '#34d399';
export const CVD_PANE_HEADER_BG = 'rgba(52, 211, 153, 0.14)';
export const CVD_PANE_HEADER_TEXT = '#6ee7b7';

const HIST_UP = 'rgba(52, 211, 153, 0.88)';
const HIST_DOWN = 'rgba(248, 113, 113, 0.88)';

function barUnix(bar: CvdAlignBar): number {
  return typeof bar.t === 'number' ? bar.t : tsToUnix(bar.ts);
}

/** Sierra /api/v9/cumulative_delta/current ships {i,d,cum,p,t} — not OHLC. */
export function cvdPointsUseOhlc(raw: unknown[]): boolean {
  if (!Array.isArray(raw) || raw.length === 0) return false;
  const p = raw[0] as Record<string, unknown>;
  const long = ['open', 'high', 'low', 'close'] as const;
  const short = ['o', 'h', 'l', 'c'] as const;
  return (
    long.every((k) => typeof p[k] === 'number' && Number.isFinite(p[k] as number)) ||
    short.every((k) => typeof p[k] === 'number' && Number.isFinite(p[k] as number))
  );
}

export function resolveCvdRenderMode(raw: unknown[]): CvdRenderMode {
  // Sierra ships {d,cum,t} — render as cumulative delta candles, not volume histogram.
  if (cvdPointsUseOhlc(raw)) return 'ohlc';
  return 'ohlc';
}

function normalizePoints(rawPoints: CvdPoint[], activeTf: string): CvdPoint[] {
  const bucketSeconds = TF_BUCKET_SECONDS[activeTf] ?? 300;
  const denseRaw = densifyCvdPoints(rawPoints, 300);
  return aggregateCvdPoints(denseRaw, bucketSeconds);
}

/** Per-bar delta histogram aligned 1:1 with price bar times. */
export function buildCvdHistogramData(
  barList: CvdAlignBar[],
  rawPoints: CvdPoint[],
  activeTf: string,
): Array<HistogramData<Time> | WhitespaceData<Time>> {
  if (!rawPoints.length || !barList.length) return [];
  const bucketSeconds = TF_BUCKET_SECONDS[activeTf] ?? 300;
  const points = normalizePoints(rawPoints, activeTf);
  const pointsByT = new Map<number, CvdPoint>();
  for (const p of points) {
    if (typeof p.t === 'number') pointsByT.set(p.t, p);
  }

  const out: Array<HistogramData<Time> | WhitespaceData<Time>> = [];
  for (const bar of barList) {
    const barT = barUnix(bar);
    if (!Number.isFinite(barT)) continue;
    const bucketT = Math.floor(barT / bucketSeconds) * bucketSeconds;
    const pt = pointsByT.get(bucketT);
    if (!pt || !Number.isFinite(pt.d)) {
      out.push({ time: barT as Time });
      continue;
    }
    out.push({
      time: barT as Time,
      value: Math.abs(pt.d),
      color: pt.d >= 0 ? HIST_UP : HIST_DOWN,
    });
  }
  return out;
}

/** Legacy OHLC-style candles from cumulative series (only when API ships OHLC). */
export function cumOhlcSeries(
  bars: CvdAlignBar[],
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
        time: barUnix(bSlice[idx]) as Time,
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
    const barT = barUnix(bar);
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

export function cvdHeaderFromCandles(
  candles: Array<CandlestickData<Time> | WhitespaceData<Time>>,
): string {
  for (let i = candles.length - 1; i >= 0; i -= 1) {
    const c = candles[i] as CandlestickData<Time>;
    if (typeof c.open === 'number') {
      return `Cumulative Delta Bars - Volume  Open: ${c.open.toFixed(0)}  High: ${c.high.toFixed(0)}  Low: ${c.low.toFixed(0)}  Close: ${c.close.toFixed(0)}`;
    }
  }
  return 'Cumulative Delta Bars - Volume';
}

export function applyCvdSeriesData(
  series: ISeriesApi<'Candlestick'> | null,
  barList: CvdAlignBar[],
  rawPoints: CvdPoint[],
  activeTf: string,
): string {
  if (!series || !rawPoints.length || !barList.length) return 'Cumulative Delta Bars - Volume';

  const aligned = alignCvdPointTimesToPriceBars(rawPoints, barList);
  const normalized = normalizePoints(aligned, activeTf);
  const candles = cumOhlcSeries(barList, normalized);
  if (!candles.length) return 'Cumulative Delta Bars - Volume';
  series.setData(candles);
  const lastBar = barList[barList.length - 1];
  const lastBarT = barUnix(lastBar);
  let lastCvdT: number | null = null;
  for (let i = candles.length - 1; i >= 0; i -= 1) {
    const c = candles[i];
    if (typeof (c as { open?: number }).open === 'number') {
      lastCvdT = Number((c as { time: number }).time);
      break;
    }
  }
  const et = (u: number | null) =>
    u == null
      ? '—'
      : new Date(u * 1000).toLocaleString('en-US', {
          timeZone: 'America/New_York',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        });
  console.info('[ChartV5b] CVD align check', {
    lastBarEt: et(lastBarT),
    lastCvdEt: et(lastCvdT),
    deltaSec: lastBarT != null && lastCvdT != null ? lastBarT - lastCvdT : null,
    aligned: lastBarT != null && lastCvdT != null && Math.abs(lastBarT - lastCvdT) < 60,
  });
  return cvdHeaderFromCandles(candles);
}

export function loadCvdPanelDefaultPct(): number {
  if (typeof window === 'undefined') return 28;
  const v = Number(localStorage.getItem(LS_CVD_PANEL));
  return Number.isFinite(v) && v >= 12 && v <= 55 ? v : 28;
}

export function saveCvdPanelPct(pct: number) {
  localStorage.setItem(LS_CVD_PANEL, String(Math.round(pct)));
}

export function applyPaneStretchFactors(
  chart: { panes: () => Array<{ setStretchFactor: (n: number) => void; getHeight: () => number }> },
  cvdPct: number,
) {
  const panes = chart.panes();
  if (panes.length < 2) return;
  const top = Math.max(35, 100 - cvdPct);
  const bot = Math.max(12, cvdPct);
  panes[0].setStretchFactor(top);
  panes[1].setStretchFactor(bot);
}

export function paneHeightsFromChart(chart: {
  panes: () => Array<{ getHeight: () => number }>;
}): {
  pricePaneH: number;
  cvdPaneH: number;
  cvdPct: number;
} {
  const panes = chart.panes();
  if (panes.length < 2) {
    const pct = loadCvdPanelDefaultPct();
    return { pricePaneH: 0, cvdPaneH: 0, cvdPct: pct };
  }
  const h0 = panes[0].getHeight();
  const h1 = panes[1].getHeight();
  const total = h0 + h1;
  const cvdPct = total > 0 ? Math.round((h1 / total) * 100) : loadCvdPanelDefaultPct();
  return { pricePaneH: h0, cvdPaneH: h1, cvdPct };
}
