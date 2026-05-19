'use client';
import {
  createChart, ColorType, CrosshairMode, IChartApi, ISeriesApi,
  CandlestickSeries, HistogramSeries, LineSeries,
} from 'lightweight-charts';
import { useEffect, useRef, useState, useCallback } from 'react';
import { usePriceStore } from '../../../stores/priceStore';
import { SierraLevelsOverlay, type TpoOverlayData } from './SierraLevelsOverlay';
import { mapCvdToBarTimes, type CvdPoint } from './cvdMapping';
import { WoodiesCciPanel } from '../woodies/WoodiesCciPanel';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const INITIAL_BAR_LIMIT = 600;

const TF_ENDPOINTS: Record<string, string> = {
  '3m': 'bars3m', '5m': 'bars5min', '15m': 'bars15m', '30m': 'bars30m', '1h': 'bars1h',
};

const TF_SECONDS: Record<string, number> = { '3m': 180, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600 };

function tsToUnix(ts: string): number {
  return Math.floor(new Date(ts.replace(' ', 'T')).getTime() / 1000);
}

function latestBarUnix(bars: Array<{ ts?: string }>): number | null {
  const last = bars[bars.length - 1];
  return last?.ts ? tsToUnix(last.ts) : null;
}

export function ChartV5b() {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const cvdHistRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const cvdLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  const [overlaySize, setOverlaySize] = useState({ width: 0, height: 0 });
  const [barsForOverlay, setBarsForOverlay] = useState<Array<{ ts: string }>>([]);
  const [tpoOverlay, setTpoOverlay] = useState<TpoOverlayData | null>(null);
  const earliestTsRef = useRef<string | null>(null);
  const latestTsRef = useRef<number | null>(null);
  const loadingHistoryRef = useRef(false);
  const skipRangeEventsRef = useRef(2);
  const allBarsRef = useRef<any[]>([]);
  const [activeTf, setActiveTf] = useState('5m');
  const [kzLabel, setKzLabel] = useState('MKT');

  // Create chart once
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
        scaleMargins: { top: 0.05, bottom: 0.22 },
      },
      timeScale: {
        borderColor: '#262626',
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#525252', style: 3, width: 1, labelBackgroundColor: '#06b6d4' },
        horzLine: { color: '#525252', style: 3, width: 1, labelBackgroundColor: '#06b6d4' },
      },
    });

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: '#16a34a',
      downColor: '#dc2626',
      borderUpColor: '#16a34a',
      borderDownColor: '#dc2626',
      wickUpColor: '#16a34a',
      wickDownColor: '#dc2626',
    });

    const cvdHist = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'cvd',
    });
    const cvdLine = chart.addSeries(LineSeries, {
      color: '#06b6d4',
      lineWidth: 1,
      priceScaleId: 'cvd',
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    chart.priceScale('cvd').applyOptions({
      scaleMargins: { top: 0.78, bottom: 0 },
    });

    chartRef.current = chart;
    candleRef.current = candles;
    cvdHistRef.current = cvdHist;
    cvdLineRef.current = cvdLine;

    const ro = new ResizeObserver(([entry]) => {
      chart.resize(entry.contentRect.width, entry.contentRect.height);
    });
    ro.observe(containerRef.current);

    return () => { ro.disconnect(); chart.remove(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    if (!wrapperRef.current) return;
    const ro = new ResizeObserver(([entry]) => {
      setOverlaySize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    ro.observe(wrapperRef.current);
    return () => ro.disconnect();
  }, []);

  const applyCvdToChart = useCallback(async (bars: Array<{ ts: string }>) => {
    if (!cvdHistRef.current || !cvdLineRef.current || !bars.length) return;
    try {
      const res = await fetch(`${API}/api/v9/cumulative_delta/current`);
      const d = await res.json();
      const points = (d.points ?? []) as CvdPoint[];
      if (!points.length) return;
      const { hist, line } = mapCvdToBarTimes(bars, points);
      if (hist.length) {
        cvdHistRef.current.setData(hist as any);
        cvdLineRef.current.setData(line as any);
      }
    } catch {
      /* keep last CVD on transient errors */
    }
  }, []);

  // Fetch bars on TF change
  const loadBars = useCallback(async (tf: string) => {
    if (!candleRef.current) return;
    const ep = TF_ENDPOINTS[tf] || 'bars5min';
    try {
      const res = await fetch(`${API}/api/v9/chart/${ep}?limit=${INITIAL_BAR_LIMIT}`);
      const raw = await res.json();
      const bars = Array.isArray(raw) ? raw : [];
      if (!bars.length) return;

      const cData = bars.map((b: any) => ({
        time: tsToUnix(b.ts) as any,
        open: b.open ?? b.o,
        high: b.high ?? b.h,
        low: b.low ?? b.l,
        close: b.close ?? b.c,
      }));
      allBarsRef.current = bars;
      setBarsForOverlay(bars.map((b: { ts: string }) => ({ ts: b.ts })));
      latestTsRef.current = latestBarUnix(bars);
      formingBarRef.current = null;
      candleRef.current.setData(cData);
      await applyCvdToChart(bars);
      earliestTsRef.current = bars[0]?.ts || null;
      chartRef.current?.timeScale().fitContent();
    } catch (e) {
      console.error('ChartV5b load error:', e);
    }
  }, [applyCvdToChart]);

  useEffect(() => { loadBars(activeTf); }, [activeTf, loadBars]);

  // Real-time: live_price tick every 1s → update forming bar
  const formingBarRef = useRef<{ time: number; open: number; high: number; low: number; close: number; vol: number } | null>(null);

  useEffect(() => {
    if (!candleRef.current) return;

    const bucketSize = TF_SECONDS[activeTf] || 300;

    // Subscribe to priceStore (fed by WebSocket) instead of polling /api/v9/live_price
    const unsubPrice = usePriceStore.subscribe((state) => {
      const price = state.price;
      if (!price || !candleRef.current) return;

      const nowSec = Math.floor(Date.now() / 1000);
      const bucket = Math.floor(nowSec / bucketSize) * bucketSize;
      const latestTs = latestTsRef.current;
      if (!latestTs || bucket - latestTs > bucketSize * 3) {
        // Do not draw a detached "now" candle when historical DB bars are stale.
        formingBarRef.current = null;
        return;
      }

      const fb = formingBarRef.current;
      if (fb && fb.time === bucket) {
        fb.high = Math.max(fb.high, price);
        fb.low = Math.min(fb.low, price);
        fb.close = price;
        fb.vol += 1;
      } else {
        formingBarRef.current = { time: bucket, open: price, high: price, low: price, close: price, vol: 1 };
      }

      const bar = formingBarRef.current!;
      candleRef.current?.update({ time: bar.time as any, open: bar.open, high: bar.high, low: bar.low, close: bar.close });
    });

    // Finalized bars poll every 5s — replaces historical bars with DB truth
    const barsPoll = setInterval(async () => {
      const ep = TF_ENDPOINTS[activeTf] || 'bars5min';
      try {
        const res = await fetch(`${API}/api/v9/chart/${ep}?limit=3`);
        const raw = await res.json();
        const bars = Array.isArray(raw) ? raw : [];
        const latest = latestBarUnix(bars);
        if (latest) latestTsRef.current = Math.max(latestTsRef.current ?? latest, latest);
        for (const b of bars) {
          const time = tsToUnix(b.ts) as any;
          candleRef.current?.update({ time, open: b.open ?? b.o, high: b.high ?? b.h, low: b.low ?? b.l, close: b.close ?? b.c });
        }
        if (allBarsRef.current.length) applyCvdToChart(allBarsRef.current);
      } catch {}
    }, 5000);

    return () => { unsubPrice(); clearInterval(barsPoll); };
  }, [activeTf, applyCvdToChart]);

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
            // Re-set full data (sorted time-ascending)
            candleRef.current?.setData(merged.map((b: any) => ({
              time: tsToUnix(b.ts) as any,
              open: b.open ?? b.o, high: b.high ?? b.h,
              low: b.low ?? b.l, close: b.close ?? b.c,
            })));
            applyCvdToChart(merged);
            loadingHistoryRef.current = false;
          })
          .catch(() => { loadingHistoryRef.current = false; });
      }
    };
    chartRef.current.timeScale().subscribeVisibleLogicalRangeChange(onRangeChange);
    return () => { try { chartRef.current?.timeScale().unsubscribeVisibleLogicalRangeChange(onRangeChange); } catch {} };
  }, [activeTf, applyCvdToChart]);

  // Sierra TPO overlay: stepped POC, cyan IB, white prior-day (not full-width price lines)
  useEffect(() => {
    const loadLevels = async () => {
      try {
        const [curRes, prevRes] = await Promise.all([
          fetch(`${API}/api/v9/tpo/current`),
          fetch(`${API}/api/v9/tpo/previous_day`),
        ]);
        const d = await curRes.json();
        const prev = await prevRes.json();
        setTpoOverlay({
          poc: d.poc,
          vah: d.vah,
          val: d.val,
          periods: d.periods,
          ib_high: d.ib_high,
          ib_mid: d.ib_mid,
          ib_low: d.ib_low,
          ib_locked: d.ib_locked,
          prior_day: d.prior_day,
          previous_session: prev?.found
            ? { found: true, poc: prev.poc, vah: prev.vah, val: prev.val }
            : { found: false },
        });
      } catch {
        /* keep last overlay on transient errors */
      }
    };
    loadLevels();
    const id = setInterval(loadLevels, 10000);
    return () => clearInterval(id);
  }, []);

  // Killzone label
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/killzone/current`).then(r => r.json())
      .then(d => setKzLabel(d?.current_zone?.name || 'MKT')).catch(() => {});
    f(); const id = setInterval(f, 30000); return () => clearInterval(id);
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
      </div>
      {/* Chart + Sierra overlay (stepped POC / cyan IB / prior-day) */}
      <div ref={wrapperRef} data-testid="chart-v5b"
        style={{ flex: 1, minHeight: 200, position: 'relative' }}>
        <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
        <SierraLevelsOverlay
          chartRef={chartRef}
          candleRef={candleRef}
          bars={barsForOverlay}
          tpo={tpoOverlay}
          width={overlaySize.width}
          height={overlaySize.height}
        />
        <WoodiesCciPanel visible={activeTf === '5m'} />
      </div>
    </div>
  );
}
