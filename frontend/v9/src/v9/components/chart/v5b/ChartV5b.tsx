'use client';
import { createChart, ColorType, CrosshairMode, IChartApi, ISeriesApi, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import { useEffect, useRef, useState, useCallback } from 'react';
import { usePriceStore } from '../../../stores/priceStore';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const TF_ENDPOINTS: Record<string, string> = {
  '3m': 'bars3m', '5m': 'bars5min', '15m': 'bars15m', '30m': 'bars30m', '1h': 'bars1h',
};

function tsToUnix(ts: string): number {
  return Math.floor(new Date(ts.replace(' ', 'T')).getTime() / 1000);
}

export function ChartV5b() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const linesRef = useRef<any[]>([]);
  const earliestTsRef = useRef<string | null>(null);
  const loadingHistoryRef = useRef(false);
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
        scaleMargins: { top: 0.05, bottom: 0.2 },
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

    const volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    });
    chart.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chartRef.current = chart;
    candleRef.current = candles;
    volumeRef.current = volume;

    const ro = new ResizeObserver(([entry]) => {
      chart.resize(entry.contentRect.width, entry.contentRect.height);
    });
    ro.observe(containerRef.current);

    return () => { ro.disconnect(); chart.remove(); chartRef.current = null; };
  }, []);

  // Fetch bars on TF change
  const loadBars = useCallback(async (tf: string) => {
    if (!candleRef.current || !volumeRef.current) return;
    const ep = TF_ENDPOINTS[tf] || 'bars5min';
    try {
      const res = await fetch(`${API}/api/v9/chart/${ep}?limit=240`);
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
      const vData = bars.map((b: any) => ({
        time: tsToUnix(b.ts) as any,
        value: b.volume ?? b.v ?? 0,
        color: (b.close ?? b.c) >= (b.open ?? b.o) ? 'rgba(22,163,74,0.5)' : 'rgba(220,38,38,0.5)',
      }));

      allBarsRef.current = bars;
      candleRef.current.setData(cData);
      volumeRef.current.setData(vData);
      earliestTsRef.current = bars[0]?.ts || null;
      chartRef.current?.timeScale().fitContent();
    } catch (e) {
      console.error('ChartV5b load error:', e);
    }
  }, []);

  useEffect(() => { loadBars(activeTf); }, [activeTf, loadBars]);

  // Real-time: live_price tick every 1s → update forming bar
  const formingBarRef = useRef<{ time: number; open: number; high: number; low: number; close: number; vol: number } | null>(null);

  useEffect(() => {
    if (!candleRef.current) return;

    // Compute TF bucket in seconds (5m=300, 15m=900, etc.)
    const tfSeconds: Record<string, number> = { '3m': 180, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600 };
    const bucketSize = tfSeconds[activeTf] || 300;

    // Subscribe to priceStore (fed by WebSocket) instead of polling /api/v9/live_price
    const unsubPrice = usePriceStore.subscribe((state) => {
      const price = state.price;
      if (!price || !candleRef.current) return;

      const nowSec = Math.floor(Date.now() / 1000);
      const bucket = Math.floor(nowSec / bucketSize) * bucketSize;

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
      volumeRef.current?.update({ time: bar.time as any, value: bar.vol, color: bar.close >= bar.open ? 'rgba(22,163,74,0.5)' : 'rgba(220,38,38,0.5)' });
    });

    // Finalized bars poll every 5s — replaces historical bars with DB truth
    const barsPoll = setInterval(async () => {
      const ep = TF_ENDPOINTS[activeTf] || 'bars5min';
      try {
        const res = await fetch(`${API}/api/v9/chart/${ep}?limit=3`);
        const raw = await res.json();
        const bars = Array.isArray(raw) ? raw : [];
        for (const b of bars) {
          const time = tsToUnix(b.ts) as any;
          candleRef.current?.update({ time, open: b.open ?? b.o, high: b.high ?? b.h, low: b.low ?? b.l, close: b.close ?? b.c });
          volumeRef.current?.update({ time, value: b.volume ?? b.v ?? 0, color: (b.close ?? b.c) >= (b.open ?? b.o) ? 'rgba(22,163,74,0.5)' : 'rgba(220,38,38,0.5)' });
        }
      } catch {}
    }, 5000);

    return () => { unsubPrice(); clearInterval(barsPoll); };
  }, [activeTf]);

  // Historical scroll-back: load older bars when user pans left
  useEffect(() => {
    if (!chartRef.current) return;
    const onRangeChange = (range: any) => {
      if (!range || loadingHistoryRef.current || !earliestTsRef.current) return;
      if (allBarsRef.current.length >= 2000) return; // cap memory
      // If visible left edge is within 20 bars of loaded start → fetch more
      if (range.from < 20 && allBarsRef.current.length < 2000) {
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
            earliestTsRef.current = merged[0]?.ts || earliestTsRef.current;
            // Re-set full data (sorted time-ascending)
            candleRef.current?.setData(merged.map((b: any) => ({
              time: tsToUnix(b.ts) as any,
              open: b.open ?? b.o, high: b.high ?? b.h,
              low: b.low ?? b.l, close: b.close ?? b.c,
            })));
            volumeRef.current?.setData(merged.map((b: any) => ({
              time: tsToUnix(b.ts) as any,
              value: b.volume ?? b.v ?? 0,
              color: (b.close ?? b.c) >= (b.open ?? b.o) ? 'rgba(22,163,74,0.5)' : 'rgba(220,38,38,0.5)',
            })));
            loadingHistoryRef.current = false;
          })
          .catch(() => { loadingHistoryRef.current = false; });
      }
    };
    chartRef.current.timeScale().subscribeVisibleLogicalRangeChange(onRangeChange);
    return () => { try { chartRef.current?.timeScale().unsubscribeVisibleLogicalRangeChange(onRangeChange); } catch {} };
  }, [activeTf]);

  // TPO levels (VAH/POC/VAL/IB H/IB L)
  useEffect(() => {
    if (!candleRef.current) return;
    const loadLevels = async () => {
      try {
        const res = await fetch(`${API}/api/v9/tpo/current`);
        const d = await res.json();
        // Remove old lines
        linesRef.current.forEach(l => { try { candleRef.current?.removePriceLine(l); } catch {} });
        linesRef.current = [];
        // POC migration arrow per Cockpit V5 §4.7
        const migDir = d.poc_migration?.direction;
        const pocArrow = migDir === 'UP' ? ' ↑' : migDir === 'DOWN' ? ' ↓' : '';

        // Cockpit V5 §4.5 + §4.7 spec-compliant levels
        const levels = [
          // POC: 2px solid magenta, opacity 0.95 (§4.5)
          { title: `POC${pocArrow}`, price: d.poc, color: '#ec4899', lineWidth: 2, lineStyle: 0 /* Solid */ },
          // VAH/VAL: 1px dashed magenta (0.5px not available, use 1), opacity 0.55 (§4.5)
          { title: 'VAH', price: d.vah, color: '#ec4899', lineWidth: 1, lineStyle: 2 /* Dashed */ },
          { title: 'VAL', price: d.val, color: '#ec4899', lineWidth: 1, lineStyle: 2 /* Dashed */ },
          // IB H/L: 1px light green #4ade80 (§4.5: 0.7-0.8px solid, opacity 0.5)
          // lineStyle: Solid when locked, Dashed when building (09:30-10:30 ET)
          { title: 'IB H', price: d.ib_high, color: '#4ade80', lineWidth: 1,
            lineStyle: d.ib_locked ? 0 /* Solid */ : 2 /* Dashed — building */ },
          { title: 'IB L', price: d.ib_low, color: '#4ade80', lineWidth: 1,
            lineStyle: d.ib_locked ? 0 : 2 },
        ];
        levels.forEach(l => {
          if (l.price && candleRef.current) {
            const line = candleRef.current.createPriceLine({
              price: l.price, color: l.color, lineWidth: l.lineWidth as any,
              lineStyle: l.lineStyle, axisLabelVisible: true, title: l.title,
            });
            linesRef.current.push(line);
          }
        });
      } catch {}
    };
    loadLevels();
    const id = setInterval(loadLevels, 30000);
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
      {/* Chart container — lightweight-charts fills this */}
      <div ref={containerRef} data-testid="chart-v5b"
        style={{ flex: 1, minHeight: 200, position: 'relative' }} />
    </div>
  );
}
