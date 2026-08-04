'use client';
import {
  createChart,
  ColorType,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  CandlestickSeries,
} from 'lightweight-charts';
import { useEffect, useRef, useState, useCallback } from 'react';
import { usePriceStore } from '../../../stores/priceStore';
import { SierraLevelsOverlay } from './SierraLevelsOverlay';
import {
  buildTpoPlan,
  collectTpoPrices,
  extendAutoscaleForTpo,
  isValidMesTpoPrice,
  refitPriceScaleForTpo,
  syncIbLines,
  resolveTodayLevels,
  syncTpoPriceLines,
  syncYesterdayTpoLines,
  type TpoOverlayData,
} from './tpoLevels';
import { useMarketStore } from '../../../stores/marketStore';
import {
  applyCvdSeriesData,
  applyPaneStretchFactors,
  CVD_PANE_DOWN,
  CVD_PANE_HEADER_BG,
  CVD_PANE_HEADER_TEXT,
  CVD_PANE_PRICE_LINE,
  CVD_PANE_UP,
  loadCvdPanelDefaultPct,
  paneHeightsFromChart,
  saveCvdPanelPct,
  type CvdAlignBar,
} from './CvdChartPane';
import type { CvdPoint } from './cvdMapping';
import { WoodiesCciPanel } from '../woodies/WoodiesCciPanel';
import { WoodiesPanelTab } from '../woodies/WoodiesPanelTab';
import { TpoContinuityOverlay } from './TpoContinuityOverlay';
import { LiveTradeOverlay } from './LiveTradeOverlay';
import { LsmaLine } from '../LsmaLine';

const LS_WOODIES_OPEN = 'mems26-woodies-panel-open';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const INITIAL_BAR_LIMIT = 600;
const CHART_FETCH_TIMEOUT_MS = 90_000;

/** Avoid browser "Failed to fetch" when backend is busy (Woodies/bar handlers).
 *  Resilience (iMac→dev 07-14): a backend restart (launchctl kickstart/bootstrap)
 *  briefly drops :8000 while loadBars/chartFetch is polling → a transient
 *  TypeError "Failed to fetch". Retry a couple times with short backoff so a
 *  momentary blip is absorbed silently instead of surfacing a scary console
 *  error; the next poll cycle recovers regardless. A genuine longer outage still
 *  rejects after the retries (caller degrades gracefully — keeps last bars). */
async function chartFetch(
  path: string, timeoutMs = CHART_FETCH_TIMEOUT_MS, retries = 2,
): Promise<Response> {
  for (let attempt = 0; ; attempt++) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      return await fetch(`${API}${path}`, { signal: ctrl.signal });
    } catch (e) {
      if (attempt >= retries) throw e;                 // exhausted → let caller handle
      await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));  // 400ms, 800ms
    } finally {
      clearTimeout(timer);
    }
  }
}
const CVD_POLL_MS = 10000;
const TPO_RTH_REFRESH_MS = 30 * 60 * 1000;
const TPO_OFF_HOURS_REFRESH_MS = 10 * 60 * 1000;

/** US equities RTH 09:30–16:00 ET (for 30-min TPO refresh). */
function isRthSessionNow(): boolean {
  try {
    const et = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const mins = et.getHours() * 60 + et.getMinutes();
    return mins >= 9 * 60 + 30 && mins < 16 * 60;
  } catch {
    return false;
  }
}

const TF_ENDPOINTS: Record<string, string> = {
  '3m': 'bars3m', '5m': 'bars5min', '15m': 'bars15m', '30m': 'bars30m', '1h': 'bars1h',
};

const TF_SECONDS: Record<string, number> = { '3m': 180, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600 };

/* (Legacy -04:00 ET shim comment removed 2026-07-14 — it described behavior the
 *  code no longer does and confused the iMac read. tsToUnix below is offset-aware
 *  and correct for the PG "+03:00"-suffixed timestamps; see the P31-FE-TZ-2 note.) */
/**
 * P31-FE-TZ-2 fix (2026-05-22 RTH UAT): post-§9 the DB stores bar `ts` as
 * real UTC wall-clock strings (e.g., RTH-open = `"2026-05-22 13:30:00..."`).
 * The legacy `-04:00` shim re-interpreted them as ET, inflating every bar
 * by 4 h on the chart's internal time axis. That mis-aligned the
 * price pane against CVD (which uses raw UTC unix), and shifted TPO
 * pink lines 4 h to the right of the actual RTH-open candle. Parse as
 * UTC (`Z`) — bars now sit at the same chart-internal unix as the
 * underlying real-UTC moment, the chart's local-TZ formatter shows IL
 * labels naturally, and RTH-open at real 13:30 UTC = display 16:30 IL.
 */
function tsToUnix(ts: string): number {
  // PG returns timestamps with timezone offset ("2026-06-04 17:55:00+03:00").
  // SQLite returned bare timestamps ("2026-06-04 17:55:00") needing a 'Z' suffix.
  // Handle both: if the string already contains +/- offset or Z, parse as-is;
  // otherwise append 'Z' (legacy UTC assumption).
  const s = ts.replace(' ', 'T');
  const hasOffset = /[+-]\d{2}:\d{2}$/.test(s) || s.endsWith('Z');
  return Math.floor(new Date(hasOffset ? s : s + 'Z').getTime() / 1000);
}

function latestBarUnix(bars: Array<{ ts?: string }>): number | null {
  const last = bars[bars.length - 1];
  return last?.ts ? tsToUnix(last.ts) : null;
}

type OhlcBar = { open: number; high: number; low: number; close: number };

/** Max wick extension (MES points) beyond the candle body for display. */
const MAX_WICK_PTS = 12;
/** Hard cap on total H-L span for one 5m MES bar (ghost rails are ~53pts). */
const MAX_BAR_SPAN_PTS = 40;
const MES_PRICE_MIN = 3000;
const MES_PRICE_MAX = 10000;
/** Reject tick prices farther than this from the anchor close (bad WS rows). */
const MAX_TICK_DEVIATION_PTS = 80;

function isSaneMesPrice(price: number, anchor: number | null): boolean {
  if (!Number.isFinite(price) || price < MES_PRICE_MIN || price > MES_PRICE_MAX) {
    return false;
  }
  if (anchor != null && Math.abs(price - anchor) > MAX_TICK_DEVIATION_PTS) {
    return false;
  }
  return true;
}

const OHLC_EPS = 0.01;

function rawOhlcFromBar(b: any): OhlcBar | null {
  const open = Number(b.open ?? b.o);
  const high = Number(b.high ?? b.h);
  const low = Number(b.low ?? b.l);
  const close = Number(b.close ?? b.c);
  if (![open, high, low, close].every(Number.isFinite)) return null;
  return { open, high, low, close };
}

/**
 * Bridge/DB sometimes rewrites only `close` while H/L stay pinned (7411.25 /
 * 7358.0 across many bars). Detect against the previous **raw** DB bar — not
 * the sanitized one (otherwise sticky detection breaks after the first clamp).
 * Invalid bars are **rejected** (skipped), not clamped into display.
 */
function sanitizeOhlc(
  raw: { open?: number; high?: number; low?: number; close?: number; o?: number; h?: number; l?: number; c?: number },
  prevRaw?: OhlcBar | null,
): OhlcBar | null {
  const open = Number(raw.open ?? raw.o);
  const close = Number(raw.close ?? raw.c);
  const highIn = Number(raw.high ?? raw.h);
  const lowIn = Number(raw.low ?? raw.l);
  if (![open, highIn, lowIn, close].every(Number.isFinite)) return null;

  if (
    prevRaw &&
    Math.abs(highIn - prevRaw.high) < OHLC_EPS &&
    Math.abs(lowIn - prevRaw.low) < OHLC_EPS &&
    (Math.abs(open - prevRaw.open) > OHLC_EPS || Math.abs(close - prevRaw.close) > OHLC_EPS)
  ) {
    console.warn('[ChartV5b] rejected sticky H/L rail bar', {
      open,
      close,
      high: highIn,
      low: lowIn,
      prevClose: prevRaw.close,
    });
    return null;
  }

  let high = Math.max(open, close, highIn);
  let low = Math.min(open, close, lowIn);
  const span = high - low;
  if (span > MAX_BAR_SPAN_PTS) {
    console.warn('[ChartV5b] rejected oversized bar span', { open, close, span });
    return null;
  }

  const bodyTop = Math.max(open, close);
  const bodyBot = Math.min(open, close);
  if (high - bodyTop > MAX_WICK_PTS) high = bodyTop + MAX_WICK_PTS;
  if (bodyBot - low > MAX_WICK_PTS) low = bodyBot - MAX_WICK_PTS;

  return { open, high, low, close };
}

function rawBarToOhlc(b: any, prevRaw?: OhlcBar | null): OhlcBar | null {
  return sanitizeOhlc(
    { open: b.open ?? b.o, high: b.high ?? b.h, low: b.low ?? b.l, close: b.close ?? b.c },
    prevRaw,
  );
}

export function ChartV5b() {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [candleSeries, setCandleSeries] = useState<ISeriesApi<'Candlestick'> | null>(null);
  const cvdSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const lastCvdPctRef = useRef(loadCvdPanelDefaultPct());
  const [overlaySize, setOverlaySize] = useState({ width: 0, height: 0 });
  const [pricePaneH, setPricePaneH] = useState(0);
  const [cvdPaneH, setCvdPaneH] = useState(0);
  const [cvdHeader, setCvdHeader] = useState('Cumulative Delta Bars - Volume');
  const [barsForOverlay, setBarsForOverlay] = useState<Array<{ ts: string }>>([]);
  /** Bar times actually on the price series — drives CVD 1:1 slots (incl. live bar). */
  const barsForCvdRef = useRef<CvdAlignBar[]>([]);
  const [barsForCvd, setBarsForCvd] = useState<CvdAlignBar[]>([]);
  const [tpoOverlay, setTpoOverlay] = useState<TpoOverlayData | null>(null);
  const tpoOverlayRef = useRef<TpoOverlayData | null>(null);
  const setMarketLevels = useMarketStore((s) => s.setLevels);
  const earliestTsRef = useRef<string | null>(null);
  const latestTsRef = useRef<number | null>(null);
  const loadingHistoryRef = useRef(false);
  // Michael 07-22: keep the user's zoom/pan across the 5s data refresh. Once the
  // user interacts (wheel/drag), stop re-fitting the visible range on reload.
  const userAdjustedRef = useRef(false);
  const skipRangeEventsRef = useRef(2);
  const allBarsRef = useRef<any[]>([]);
  /** Last candle time on the series — guards stale WS ticks / poll rows (TASK B). */
  const lastBarTimeRef = useRef<number | null>(null);
  const staleWarnRef = useRef<number | null>(null);
  /** Block live updates until initial setData completes (prevents refresh glitches). */
  const barsLoadedRef = useRef(false);
  const formingBarRef = useRef<{
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    vol: number;
  } | null>(null);
  const [activeTf, setActiveTf] = useState('5m');

  const applyTpoToChart = useCallback(
    (data: TpoOverlayData | null) => {
      const series = candleRef.current;
      const chart = chartRef.current;
      if (!series || !chart || !data) return 0;
      extendAutoscaleForTpo(series, data);
      const nToday = syncTpoPriceLines(chart, data, 0);
      // Yesterday white POC/VAH/VAL — Sierra-style RTH-bounded references.
      // Spans today's 09:30→16:00 ET only (NOT infinite), refreshed tomorrow
      // when yesterday's values rotate. Dense 5-min LineSeries points avoid
      // lightweight-charts' "bar-gap" truncation that bit the 2-point
      // version. Replaced `createPriceLine` (infinite horizontal) on
      // 2026-05-22 PM after Michael's RTH-window spec.
      const nYday = syncYesterdayTpoLines(chart, series, data, 0);
      // N10: today IB_High/IB_Low — Sierra IB study values from
      // /api/v9/tpo/current (ib_source=sierra_live), RTH-window-bounded.
      const nIb = syncIbLines(chart, series, data, 0);
      const n = nToday + nYday + nIb;
      if (n > 0) refitPriceScaleForTpo(series);
      return n;
    },
    [],
  );

  const [kzLabel, setKzLabel] = useState('MKT');
  const [woodiesOpen, setWoodiesOpen] = useState(false);
  useEffect(() => {
    setWoodiesOpen(localStorage.getItem(LS_WOODIES_OPEN) === '1');
  }, []);

  const updateCandle = useCallback((bar: {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
  }): boolean => {
    const series = candleRef.current;
    if (!series) return false;
    const t = Number(bar.time);
    if (!Number.isFinite(t)) return false;
    const last = lastBarTimeRef.current;
    if (last !== null && t < last) {
      // Rate-limit: at most once per 30s to avoid hundreds of console lines
      const now = Date.now();
      if (!staleWarnRef.current || now - staleWarnRef.current > 30000) {
        staleWarnRef.current = now;
        console.warn('[ChartV5b] dropped stale bar update (rate-limited)', {
          tickTime: t,
          lastTime: last,
          diffSec: last - t,
        });
      }
      return false;
    }
    const lastDb = allBarsRef.current[allBarsRef.current.length - 1];
    const prevRaw = lastDb ? rawOhlcFromBar(lastDb) : null;
    const clean = sanitizeOhlc(bar, prevRaw);
    if (!clean) return false;
    try {
      series.update({ time: t as any, ...clean });
      if (last === null || t >= last) {
        lastBarTimeRef.current = t;
        const cvdList = barsForCvdRef.current;
        const lastCvd = cvdList[cvdList.length - 1];
        if (!lastCvd || (lastCvd.t ?? 0) < t) {
          const next = [...cvdList, { ts: String(t), t }];
          barsForCvdRef.current = next;
          setBarsForCvd(next);
        }
      }
      return true;
    } catch (e) {
      console.warn('[ChartV5b] series.update failed', e);
      return false;
    }
  }, []); // refs only — safe across activeTf changes

  const toggleWoodiesPanel = useCallback(() => {
    setWoodiesOpen((open) => {
      const next = !open;
      localStorage.setItem(LS_WOODIES_OPEN, next ? '1' : '0');
      return next;
    });
  }, []);

  // TASK A: one chart, two panes — shared timeScale (pixel-aligned candles ↔ CVD).
  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const cvdPct = loadCvdPanelDefaultPct();
    lastCvdPctRef.current = cvdPct;

    // Display x-axis in Chicago time (CT) to match Sierra Chart.
    // lightweight-charts uses browser local TZ by default. We override
    // via localization.timeFormatter to show CT times.
    const fmtCT = (ts: number) => {
      const d = new Date(ts * 1000);
      return d.toLocaleTimeString('en-US', { timeZone: 'America/Chicago', hour: '2-digit', minute: '2-digit', hour12: false });
    };
    const fmtCTDate = (ts: number) => {
      const d = new Date(ts * 1000);
      return d.toLocaleDateString('en-US', { timeZone: 'America/Chicago', month: 'numeric', day: 'numeric' });
    };

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0a0a0a' },
        textColor: '#a3a3a3',
        fontSize: 10,
        fontFamily: 'ui-monospace, monospace',
        panes: {
          enableResize: true,
          separatorColor: '#fb950b',
          separatorHoverColor: 'rgba(251, 149, 11, 0.25)',
        },
      },
      localization: {
        timeFormatter: fmtCT,
      },
      grid: {
        vertLines: { color: '#1a1a1a', style: 1 },
        horzLines: { color: '#1a1a1a', style: 1 },
      },
      rightPriceScale: {
        borderColor: '#262626',
        minimumWidth: 72,
      },
      timeScale: {
        visible: true,
        borderColor: '#262626',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 0,
        tickMarkFormatter: (time: number) => {
          const d = new Date(time * 1000);
          const ct = d.toLocaleString('en-US', { timeZone: 'America/Chicago', hour: '2-digit', minute: '2-digit', hour12: false, month: 'numeric', day: 'numeric' });
          // Show date only at day boundaries, time otherwise
          const h = Number(d.toLocaleString('en-US', { timeZone: 'America/Chicago', hour: 'numeric', hour12: false }));
          const m = Number(d.toLocaleString('en-US', { timeZone: 'America/Chicago', minute: 'numeric' }));
          if (h === 8 && m <= 30) return fmtCTDate(time);
          return fmtCT(time);
        },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#525252', style: 3, width: 1, labelBackgroundColor: '#06b6d4' },
        horzLine: { color: '#525252', style: 3, width: 1, labelBackgroundColor: '#06b6d4' },
      },
    });

    const candles = chart.addSeries(
      CandlestickSeries,
      {
        upColor: '#16a34a',
        downColor: '#dc2626',
        borderUpColor: '#16a34a',
        borderDownColor: '#dc2626',
        wickUpColor: '#16a34a',
        wickDownColor: '#dc2626',
      },
      0,
    );

    // Sierra {d,cum,t} → cumulative delta candles (open=prev cum, close=cum).
    const cvdSeries = chart.addSeries(
      CandlestickSeries,
      {
        upColor: CVD_PANE_UP,
        downColor: CVD_PANE_DOWN,
        borderUpColor: CVD_PANE_UP,
        borderDownColor: CVD_PANE_DOWN,
        wickUpColor: CVD_PANE_UP,
        wickDownColor: CVD_PANE_DOWN,
        priceLineVisible: true,
        priceLineColor: CVD_PANE_PRICE_LINE,
        priceLineWidth: 1,
        lastValueVisible: true,
      },
      1,
    );

    applyPaneStretchFactors(chart, cvdPct);

    // Shared time scale still misaligns if each pane's right scale gutter differs.
    const scaleWidth = 80; // keep in sync with SierraLevelsOverlay PRICE_SCALE_W
    candles.priceScale().applyOptions({
      minimumWidth: scaleWidth,
      scaleMargins: { top: 0.08, bottom: 0.12 },
    });
    cvdSeries.priceScale().applyOptions({
      minimumWidth: scaleWidth,
      scaleMargins: { top: 0.1, bottom: 0.25 },
    });

    chartRef.current = chart;
    candleRef.current = candles;
    setCandleSeries(candles);
    cvdSeriesRef.current = cvdSeries;
    if (tpoOverlayRef.current) applyTpoToChart(tpoOverlayRef.current);

    // Michael 07-22: the moment the user zooms (wheel) or pans (drag) the price
    // or time axis, mark the view as user-owned so reloads stop re-fitting it.
    const _markAdjusted = () => { userAdjustedRef.current = true; };
    const _cont = containerRef.current;
    _cont?.addEventListener('wheel', _markAdjusted, { passive: true });
    _cont?.addEventListener('pointerdown', _markAdjusted, { passive: true });

    const syncPaneOverlay = () => {
      const el = containerRef.current;
      if (!el) return;
      const { pricePaneH: pH, cvdPaneH: cH, cvdPct: pct } = paneHeightsFromChart(chart);
      setPricePaneH(pH);
      setCvdPaneH(cH);
      setOverlaySize({ width: el.clientWidth, height: pH > 0 ? pH : el.clientHeight });
      if (Math.abs(pct - lastCvdPctRef.current) >= 1) {
        lastCvdPctRef.current = pct;
        saveCvdPanelPct(pct);
      }
    };

    const syncLayout = (w: number, h: number) => {
      chart.resize(w, h);
      syncPaneOverlay();
    };

    const ro = new ResizeObserver(([entry]) => {
      syncLayout(entry.contentRect.width, entry.contentRect.height);
    });
    ro.observe(containerRef.current);

    // Dragging the orange pane separator resizes pane divs, not the outer container.
    let paneRo: ResizeObserver | null = null;
    const attachPaneObservers = () => {
      const paneEls = chart
        .panes()
        .map((p) => p.getHTMLElement())
        .filter((el): el is HTMLElement => el != null);
      if (!paneEls.length) {
        requestAnimationFrame(attachPaneObservers);
        return;
      }
      paneRo = new ResizeObserver(() => syncPaneOverlay());
      paneEls.forEach((el) => paneRo!.observe(el));
      syncPaneOverlay();
    };
    requestAnimationFrame(attachPaneObservers);

    let paneTrackRaf = 0;
    let lastTrackedPaneH = -1;
    const trackPaneHeights = () => {
      const pH = chart.panes()[0]?.getHeight() ?? 0;
      if (pH !== lastTrackedPaneH) {
        lastTrackedPaneH = pH;
        syncPaneOverlay();
      }
      paneTrackRaf = requestAnimationFrame(trackPaneHeights);
    };
    paneTrackRaf = requestAnimationFrame(trackPaneHeights);

    syncLayout(containerRef.current.clientWidth, containerRef.current.clientHeight);

    return () => {
      cancelAnimationFrame(paneTrackRaf);
      paneRo?.disconnect();
      ro.disconnect();
      _cont?.removeEventListener('wheel', _markAdjusted);
      _cont?.removeEventListener('pointerdown', _markAdjusted);
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      setCandleSeries(null);
      cvdSeriesRef.current = null;
    };
  }, []);

  const fetchCvd = useCallback(async () => {
    const series = cvdSeriesRef.current;
    const barList = barsForCvdRef.current;
    if (!series || !barList.length) return;
    try {
      // `history=1` backfills CVD points from v9_bars_cumulative_delta so
      // the CVD pane renders the full chart window (5h @ 5m default), not
      // just the rolling ~14-point JSON tail. Without this the older 46
      // bars showed empty CVD candles (Michael 2026-05-22 17:32 IL).
      const res = await fetch(`${API}/api/v9/cumulative_delta/current?history=1&limit=600`);
      const d = await res.json();
      const rawPoints = (d.points ?? []) as CvdPoint[];
      const hdr = applyCvdSeriesData(series, barList, rawPoints, activeTf);
      setCvdHeader(hdr);
    } catch {
      /* keep last CVD paint */
    }
  }, [activeTf]);

  // Fetch bars on TF change
  const loadBars = useCallback(async (tf: string) => {
    if (!candleRef.current) return;
    barsLoadedRef.current = false;
    formingBarRef.current = null;
    const ep = TF_ENDPOINTS[tf] || 'bars5min';
    const path = `/api/v9/chart/${ep}?limit=${INITIAL_BAR_LIMIT}`;
    try {
      let res: Response | null = null;
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          res = await chartFetch(path);
          break;
        } catch (err) {
          if (attempt === 0) {
            console.warn('[ChartV5b] bars fetch retry after:', err);
            await new Promise((r) => setTimeout(r, 2000));
            continue;
          }
          throw err;
        }
      }
      if (!res!.ok) {
        throw new Error(`bars HTTP ${res!.status}`);
      }
      const raw = await res!.json();
      const bars = Array.isArray(raw) ? raw : [];
      if (!bars.length) return;

      const tsToFullBar = new Map<string, any>();
      for (const b of bars) tsToFullBar.set(b.ts, b);
      const sortedFull = Array.from(tsToFullBar.values()).sort(
        (a: any, b: any) => tsToUnix(a.ts) - tsToUnix(b.ts),
      );
      const cData: Array<{ time: number; open: number; high: number; low: number; close: number }> = [];
      const cvdBars: CvdAlignBar[] = [];
      let prevRaw: OhlcBar | null = null;
      let rejectedBars = 0;
      // Plausibility reference: some corrupt bars (e.g. close 12693 / 13456 vs ~7450) pass the
      // sticky-H/L sanitizer (they are internally consistent) but are absurdly off-price and
      // blow up the price-pane autoscale, squashing the real candles. Reject bars >±30% off the
      // median close (robust to a few outliers; no legitimate intraday MES bar moves 30%).
      const _plausCloses = sortedFull
        .map((b) => rawOhlcFromBar(b)?.close)
        .filter((c): c is number => Number.isFinite(c as number))
        .sort((a, b) => a - b);
      const _medianClose = _plausCloses.length ? _plausCloses[Math.floor(_plausCloses.length / 2)] : 0;
      for (const b of sortedFull) {
        const t = tsToUnix(b.ts);
        const ohlc = rawBarToOhlc(b, prevRaw);
        const raw = rawOhlcFromBar(b);
        if (raw) prevRaw = raw;
        if (!Number.isFinite(t)) continue;
        if (!ohlc) {
          rejectedBars += 1;
          continue;
        }
        if (_medianClose > 0 && (ohlc.close > _medianClose * 1.3 || ohlc.close < _medianClose * 0.7
            || ohlc.high > _medianClose * 1.3 || ohlc.low < _medianClose * 0.7)) {
          rejectedBars += 1; // absurd-magnitude bar (corrupt) — keep it out of the candle scale
          continue;
        }
        cData.push({ time: t, ...ohlc });
        cvdBars.push({ ts: b.ts, t });
      }
      if (rejectedBars > 0) {
        console.warn(`[ChartV5b] rejected ${rejectedBars} corrupt bar(s) from API (sticky H/L or span)`);
      }
      if (!cData.length) return;

      allBarsRef.current = sortedFull;
      setBarsForOverlay(cvdBars.map((b) => ({ ts: b.ts })));
      barsForCvdRef.current = cvdBars;
      setBarsForCvd(cvdBars);
      latestTsRef.current = latestBarUnix(cvdBars);
      formingBarRef.current = null;
      if (!candleRef.current) return;
      candleRef.current.setData(
        cData.map((c) => ({
          time: c.time as any,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        })),
      );
      lastBarTimeRef.current =
        cData.length > 0 ? Number(cData[cData.length - 1].time) : null;
      barsLoadedRef.current = true;
      earliestTsRef.current = sortedFull[0]?.ts || null;
      // Default view shows the most recent 60 bars (5 h of 5 m, 3 h of 3 m, 15 h of 15 m).
      // fitContent on 600 bars produced a sub-1-px-per-candle view that the
      // CVD sync then mirrored onto a 17 h window — user saw 10 price candles
      // and only 2 CVD candles. Lazy-load handler in this file still fetches
      // older data when the user pans left.
      // Michael 07-22: only auto-fit the FIRST load (or after "Auto" reset).
      // Once the user zoomed/panned (userAdjustedRef), leave the view exactly
      // as they set it — new data streams in, the frame does not jump back.
      const DEFAULT_VISIBLE = 60;
      const last = cData.length - 1; // index of newest sanitized bar
      const bucketSize = TF_SECONDS[tf] || 300;
      const nowBucket = Math.floor(Date.now() / 1000 / bucketSize) * bucketSize;
      if (!userAdjustedRef.current) {
        if (last >= 0) {
          const fromIdx = Math.max(0, last - DEFAULT_VISIBLE + 1);
          const fromTime = cData[fromIdx].time as any;
          const toTime = Math.max(cData[last].time, nowBucket) as any;
          chartRef.current?.timeScale().setVisibleRange({ from: fromTime, to: toTime });
        } else {
          chartRef.current?.timeScale().fitContent();
        }
      }
      void fetchCvd();
      if (tpoOverlayRef.current) applyTpoToChart(tpoOverlayRef.current);
    } catch (e) {
      console.error('ChartV5b load error:', e);
    }
  }, [applyTpoToChart, fetchCvd]);

  useEffect(() => { loadBars(activeTf); }, [activeTf, loadBars]);

  useEffect(() => {
    void fetchCvd();
  }, [barsForCvd, fetchCvd]);

  useEffect(() => {
    void fetchCvd();
    const id = setInterval(() => void fetchCvd(), CVD_POLL_MS);
    return () => clearInterval(id);
  }, [fetchCvd]);

  const applyLiveTickToFormingBar = (price: number, bucket: number, bucketSize: number) => {
    const lastDb = allBarsRef.current[allBarsRef.current.length - 1];
    const lastSanitized = lastDb ? rawBarToOhlc(lastDb) : null;
    const anchor =
      formingBarRef.current?.close ??
      lastSanitized?.close ??
      (lastSanitized ? (lastSanitized.open + lastSanitized.close) / 2 : null);

    if (!isSaneMesPrice(price, anchor)) {
      console.warn('[ChartV5b] dropped insane tick price', { price, anchor, bucket });
      return;
    }

    const lastT = lastDb?.ts ? tsToUnix(lastDb.ts) : null;
    const lastBarT = lastBarTimeRef.current;
    if (lastBarT != null && bucket < lastBarT) return;
    if (lastBarT != null && bucket > lastBarT + bucketSize) {
      console.warn('[ChartV5b] dropped tick bucket too far ahead', {
        bucket,
        lastBarT,
        gap: bucket - lastBarT,
      });
      return;
    }

    let fb = formingBarRef.current;
    if (!fb || fb.time !== bucket) {
      if (lastDb && lastT === bucket && lastSanitized) {
        fb = {
          time: bucket,
          open: lastSanitized.open,
          high: lastSanitized.high,
          low: lastSanitized.low,
          close: lastSanitized.close,
          vol: 0,
        };
      } else {
        fb = { time: bucket, open: price, high: price, low: price, close: price, vol: 0 };
      }
      formingBarRef.current = fb;
    }

    fb.close = price;
    const bodyTop = Math.max(fb.open, fb.close);
    const bodyBot = Math.min(fb.open, fb.close);
    fb.high = Math.min(Math.max(fb.high, price), bodyTop + MAX_WICK_PTS);
    fb.low = Math.max(Math.min(fb.low, price), bodyBot - MAX_WICK_PTS);

    updateCandle(fb);
  };

  useEffect(() => {
    if (!candleRef.current) return;

    const bucketSize = TF_SECONDS[activeTf] || 300;
    let lastSeenPrice: number | null = null;

    const unsubPrice = usePriceStore.subscribe((state) => {
      if (!barsLoadedRef.current || !candleRef.current) return;

      const price = state.price;
      if (price == null || price === lastSeenPrice) return;
      lastSeenPrice = price;

      const nowSec = Math.floor(Date.now() / 1000);
      const bucket = Math.floor(nowSec / bucketSize) * bucketSize;
      const latestTs = latestTsRef.current;
      if (!latestTs || bucket - latestTs > bucketSize * 3) {
        formingBarRef.current = null;
        return;
      }

      applyLiveTickToFormingBar(price, bucket, bucketSize);
    });

    // Finalized bars poll every 5s — replaces historical bars with DB truth.
    // P30 2026-05-20: lightweight-charts `update()` requires strictly
    // monotonic time (>= last bar). Sort ASC and skip duplicates/older
    // times to avoid `Cannot update oldest data` crashes; previously the
    // CVD pane stayed empty because every update call threw.
    const barsPoll = setInterval(async () => {
      const ep = TF_ENDPOINTS[activeTf] || 'bars5min';
      try {
        const res = await chartFetch(`/api/v9/chart/${ep}?limit=3`, 15_000);
        const raw = await res.json();
        const bars = Array.isArray(raw) ? raw : [];
        const latest = latestBarUnix(bars);
        if (latest) latestTsRef.current = Math.max(latestTsRef.current ?? latest, latest);
        const sorted = bars
          .map((b: any) => {
            const t = tsToUnix(b.ts);
            return Number.isFinite(t) ? { ...b, _t: t } : null;
          })
          .filter(Boolean)
          .sort((a: any, b: any) => a._t - b._t);
        for (const b of sorted) {
          updateCandle({
            time: b._t,
            open: b.open ?? b.o,
            high: b.high ?? b.h,
            low: b.low ?? b.l,
            close: b.close ?? b.c,
          });
        }
        // "Follow the price" refresh — re-anchor the yesterday white
        // lines' right edge to `now + 5min` so they extend with each new
        // candle instead of stalling between 30-min TPO refreshes.
        // `applyTpoToChart` is idempotent on the yesterday series
        // (setData reuse path in syncYesterdayTpoLines), so the 10 s
        // cadence is cheap. Pink lines self-tick inside
        // TpoContinuityOverlay (independent of this poll).
        if (tpoOverlayRef.current) applyTpoToChart(tpoOverlayRef.current);
      } catch {}
    }, 10000);

    return () => { unsubPrice(); clearInterval(barsPoll); };
  }, [activeTf, applyTpoToChart, updateCandle]);

  // Historical scroll-back: load older bars when user pans left
  useEffect(() => {
    if (!chartRef.current) return;
    const onRangeChange = (range: any) => {
      if (skipRangeEventsRef.current > 0) {
        skipRangeEventsRef.current -= 1;
        return;
      }
      if (!range || loadingHistoryRef.current || !earliestTsRef.current) return;
      if (allBarsRef.current.length >= 2000) return; // cap memory
      // User panned near left edge → fetch older bars (not on initial fitContent)
      if (range.from < 20 && range.from >= 0 && allBarsRef.current.length < 2000) {
        loadingHistoryRef.current = true;
        const ep = TF_ENDPOINTS[activeTf] || 'bars5min';
        fetch(`${API}/api/v9/chart/${ep}?limit=240&before=${encodeURIComponent(earliestTsRef.current!)}`)
          .then(r => r.json())
          .then(raw => {
            const older = Array.isArray(raw) ? raw : [];
            if (!older.length) { loadingHistoryRef.current = false; return; }
            // Prepend + dedup by timestamp
            const existing = new Set(allBarsRef.current.map((b: any) => b.ts));
            const fresh = older.filter((b: any) => !existing.has(b.ts));
            const merged = [...fresh, ...allBarsRef.current];
            allBarsRef.current = merged;
            setBarsForOverlay(merged.map((b: { ts: string }) => ({ ts: b.ts })));
            earliestTsRef.current = merged[0]?.ts || earliestTsRef.current;
            const histData: Array<{ time: any; open: number; high: number; low: number; close: number }> = [];
            let prevHistRaw: OhlcBar | null = null;
            for (const b of merged) {
              const t = tsToUnix(b.ts);
              const ohlc = rawBarToOhlc(b, prevHistRaw);
              const raw = rawOhlcFromBar(b);
              if (raw) prevHistRaw = raw;
              if (!Number.isFinite(t) || !ohlc) continue;
              histData.push({ time: t as any, ...ohlc });
            }
            candleRef.current?.setData(histData);
            lastBarTimeRef.current =
              histData.length > 0 ? Number(histData[histData.length - 1].time) : null;
            if (tpoOverlayRef.current) applyTpoToChart(tpoOverlayRef.current);
            loadingHistoryRef.current = false;
          })
          .catch(() => { loadingHistoryRef.current = false; });
      }
    };
    chartRef.current.timeScale().subscribeVisibleLogicalRangeChange(onRangeChange);
    return () => { try { chartRef.current?.timeScale().unsubscribeVisibleLogicalRangeChange(onRangeChange); } catch {} };
  }, [activeTf, applyTpoToChart]);

  // TASK C: six TPO lines — hydrate from DB/periods when Sierra JSON has corrupt zeros.
  useEffect(() => {
    const loadLevels = async () => {
      try {
        const [curRes, prevDayRes] = await Promise.all([
          fetch(`${API}/api/v9/tpo/current`),
          fetch(`${API}/api/v9/tpo/previous_day`),
        ]);
        const d = await curRes.json();
        const prevDay = await prevDayRes.json();

        // Prefer previous_session from /current (DLL reads Sierra TPO study).
        // Fall back to /previous_day only if DLL values are invalid.
        const rawPrev = d.previous_session as TpoOverlayData['previous_session'] | undefined;
        let yPoc = rawPrev?.poc;
        let yVah = rawPrev?.vah;
        let yVal = rawPrev?.val;
        if (
          !isValidMesTpoPrice(yPoc) ||
          !isValidMesTpoPrice(yVah) ||
          !isValidMesTpoPrice(yVal)
        ) {
          if (prevDay?.found) {
            if (!isValidMesTpoPrice(yPoc)) yPoc = prevDay.poc;
            if (!isValidMesTpoPrice(yVah)) yVah = prevDay.vah;
            if (!isValidMesTpoPrice(yVal)) yVal = prevDay.val;
          }
        }
        const yOpen = rawPrev?.opened_ts ?? null;
        const yClose = rawPrev?.closed_ts ?? null;

        const hasPrevPrices =
          isValidMesTpoPrice(yPoc) || isValidMesTpoPrice(yVah) || isValidMesTpoPrice(yVal);

        const overlayPayload: TpoOverlayData = {
          poc: d.poc,
          vah: d.vah,
          val: d.val,
          // N10: today IB from the Sierra IB study (ib_source=sierra_live).
          // Null when the DLL does not export it — never synthesized.
          ib_high: d.ib_high,
          ib_low: d.ib_low,
          ib_found: d.ib_found,
          periods: (d.periods ?? []) as TpoOverlayData['periods'],
          session_opened_ts: d.session_opened_ts ?? d.opened_ts ?? null,
          previous_session: hasPrevPrices
            ? {
                found: true,
                poc: yPoc,
                vah: yVah,
                val: yVal,
                opened_ts: yOpen,
                closed_ts: yClose,
              }
            : { found: false },
        };
        tpoOverlayRef.current = overlayPayload;
        setTpoOverlay(overlayPayload);
        const todayLv = resolveTodayLevels(overlayPayload);
        setMarketLevels({
          currentPOC: todayLv.poc,
          currentVAH: todayLv.vah,
          currentVAL: todayLv.val,
        });
        const lineCount = applyTpoToChart(overlayPayload);
        console.info('[ChartV5b] TPO loaded', {
          raw: { poc: d.poc, vah: d.vah, val: d.val },
          ib: { high: d.ib_high, low: d.ib_low, found: d.ib_found },
          hydrated: todayLv,
          plotPrices: collectTpoPrices(overlayPayload),
          lineCount,
          prevFound: hasPrevPrices,
        });
      } catch (e) {
        console.warn('[ChartV5b] TPO load failed', e);
      }
    };
    loadLevels();
    let refreshId: ReturnType<typeof setInterval> | undefined;
    const armRefresh = () => {
      if (refreshId) clearInterval(refreshId);
      refreshId = setInterval(
        loadLevels,
        isRthSessionNow() ? TPO_RTH_REFRESH_MS : TPO_OFF_HOURS_REFRESH_MS,
      );
    };
    armRefresh();
    const modeTick = setInterval(armRefresh, 60_000);
    return () => {
      if (refreshId) clearInterval(refreshId);
      clearInterval(modeTick);
    };
  }, [applyTpoToChart]);

  useEffect(() => {
    if (tpoOverlay) applyTpoToChart(tpoOverlay);
  }, [applyTpoToChart, candleSeries, tpoOverlay]);

  // Killzone label
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/killzone/current`).then(r => r.json())
      .then(d => setKzLabel(d?.current_zone?.name || 'MKT')).catch(() => {});
    f(); const id = setInterval(f, 60000); return () => clearInterval(id);
  }, []);

  // TR countdown
  const [trText, setTrText] = useState('0:00');
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const min5 = Math.floor(now.getMinutes() / 5) * 5 + 5;
      const nb = new Date(now); nb.setMinutes(min5, 0, 0);
      if (nb <= now) nb.setMinutes(nb.getMinutes() + 5);
      const s = Math.max(0, Math.floor((nb.getTime() - now.getTime()) / 1000));
      setTrText(`${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`);
    };
    tick(); const id = setInterval(tick, 1000); return () => clearInterval(id);
  }, []);

  /**
   * Q2 fix — snap-to-latest: lazy-load left edge keeps old bars in memory
   * (working as intended, cap 2000), but there was no way to jump back to
   * the rightmost bar once the user scrolled into history. lightweight-charts
   * `scrollToRealTime()` pans the visible window to the latest bar without
   * resetting `allBarsRef` — older bars stay loaded for re-scroll left.
   */
  const goToLatest = useCallback(() => {
    try {
      // Michael 07-22: "Latest" also re-hands the view to auto-fit (clears the
      // user-adjusted lock) so the frame tracks new bars again from here.
      userAdjustedRef.current = false;
      chartRef.current?.timeScale().scrollToRealTime();
    } catch {
      /* chart not ready */
    }
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%' }}>
      {/* TF selector row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2px 0',
        background: '#0d0d0d', borderBottom: '1px solid #1a1a1a', flexShrink: 0, gap: 4 }}>
        <span suppressHydrationWarning style={{
          fontSize: 9, padding: '2px 8px', borderRadius: 3, fontFamily: 'ui-monospace, monospace',
          background: '#141414', border: '1px solid #f97316', color: '#f97316', fontWeight: 600,
        }}>{kzLabel} · {trText}</span>
        <span style={{ color: '#333', fontSize: 9 }}>|</span>
        {['3m','5m','15m','30m','1h'].map(tf => (
          <button key={tf} data-testid={`tf-btn-${tf}`} suppressHydrationWarning
            onClick={() => setActiveTf(tf)}
            style={{ fontSize: 9, padding: '2px 8px',
              border: tf === activeTf ? '1px solid #06b6d4' : '1px solid transparent',
              borderRadius: 3, cursor: 'pointer',
              background: tf === activeTf ? 'rgba(6,180,212,0.15)' : 'transparent',
              color: tf === activeTf ? '#06b6d4' : '#525252',
              fontWeight: tf === activeTf ? 600 : 400,
            }}>{tf}</button>
        ))}
        <span style={{ color: '#333', fontSize: 9 }}>|</span>
        <button
          data-testid="go-to-latest"
          suppressHydrationWarning
          onClick={goToLatest}
          title="Snap to latest bar"
          style={{
            fontSize: 9,
            padding: '2px 8px',
            border: '1px solid transparent',
            borderRadius: 3,
            cursor: 'pointer',
            background: 'transparent',
            color: '#525252',
            fontWeight: 600,
          }}
        >
          ▶|
        </button>
      </div>
      <div
        ref={wrapperRef}
        data-testid="chart-v5b-unified"
        style={{ flex: 1, minHeight: 200, position: 'relative', width: '100%' }}
      >
        <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
        <SierraLevelsOverlay
          chartRef={chartRef}
          candleSeries={candleSeries}
          tpo={tpoOverlay}
          width={overlaySize.width}
          height={overlaySize.height}
        />
        <TpoContinuityOverlay
          chart={chartRef.current}
          tpo={tpoOverlay}
          paneIndex={0}
        />
        <LsmaLine chart={chartRef.current} />
        {/* §7 מייקל 07-11: העסקה החיה על הגרף — כניסה/סטופ-נע/יעדים + באנר (live/sim/demo בלבד) */}
        <LiveTradeOverlay chart={chartRef.current} candleSeries={candleSeries} />
        {pricePaneH > 0 && cvdPaneH > 20 && (
          <div
            data-testid="cvd-chart-header"
            style={{
              position: 'absolute',
              left: 0,
              right: 80,
              top: pricePaneH,
              height: 18,
              padding: '2px 8px',
              fontSize: 9,
              fontFamily: 'ui-monospace, monospace',
              color: CVD_PANE_HEADER_TEXT,
              background: CVD_PANE_HEADER_BG,
              borderLeft: `3px solid ${CVD_PANE_PRICE_LINE}`,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              zIndex: 11,
              pointerEvents: 'none',
            }}
          >
            {cvdHeader}
          </div>
        )}
        {activeTf === '5m' && (
          <WoodiesPanelTab open={woodiesOpen} onToggle={toggleWoodiesPanel} />
        )}
        <WoodiesCciPanel
          visible={activeTf === '5m' && woodiesOpen}
          onVisibilityChange={(open) => {
            setWoodiesOpen(open);
            localStorage.setItem(LS_WOODIES_OPEN, open ? '1' : '0');
          }}
        />
      </div>
    </div>
  );
}
