'use client';

import { useEffect, useRef } from 'react';

interface Candle {
  ts: number;
  o: number; h: number; l: number; c: number;
  buy: number; sell: number; delta: number;
}

interface Signal {
  direction: 'LONG' | 'SHORT' | 'NO_TRADE';
  entry: number; stop: number;
  target1: number; target2: number; target3: number;
  tl_color: string;
}

interface LevelLine {
  price: number;
  color: string;
  label: string;
  style?: number; // 0=solid, 1=dotted, 2=dashed, 3=large_dashed
  width?: number;
}

interface LightweightChartProps {
  candles: Candle[];
  liveBar?: { ts: number; o: number; h: number; l: number; c: number } | null;
  price?: number;
  vwap?: number;
  levels?: {
    prev_high?: number; prev_low?: number; daily_open?: number;
    overnight_high?: number; overnight_low?: number;
  };
  profile?: { poc?: number; vah?: number; val?: number };
  session?: { ibh?: number; ibl?: number };
  signal?: Signal | null;
  tf?: string;
  onTFChange?: (tf: string) => void;
}

export default function LightweightChart({
  candles, liveBar, price, vwap, levels, profile, session, signal, tf = 'm3', onTFChange
}: LightweightChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef     = useRef<any>(null);
  const candleRef    = useRef<any>(null);
  const volRef       = useRef<any>(null);
  const linesRef     = useRef<any[]>([]);

  // ── Init chart ─────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js';
    script.async = true;
    script.onload = () => {
      const LW = (window as any).LightweightCharts;
      if (!LW || !containerRef.current) return;

      const chart = LW.createChart(containerRef.current, {
        width:  containerRef.current.clientWidth,
        height: 400,
        layout: {
          background: { color: '#0d1117' },
          textColor:  '#6b7280',
          fontSize:   11,
        },
        grid: {
          vertLines: { color: '#161d2a' },
          horzLines: { color: '#161d2a' },
        },
        crosshair: {
          mode: LW.CrosshairMode.Normal,
          vertLine: { color: '#3d4a5e', labelBackgroundColor: '#1e2738' },
          horzLine: { color: '#3d4a5e', labelBackgroundColor: '#1e2738' },
        },
        rightPriceScale: {
          borderColor: '#1e2738',
          textColor:   '#6b7280',
        },
        timeScale: {
          borderColor:     '#1e2738',
          timeVisible:     true,
          secondsVisible:  false,
          fixLeftEdge:     false,
          fixRightEdge:    false,
        },
        handleScroll:  { mouseWheel: true, pressedMouseMove: true },
        handleScale:   { mouseWheel: true, axisPressedMouseMove: true },
      });

      // Candlestick series
      const candleSeries = chart.addCandlestickSeries({
        upColor:          '#26a69a',
        downColor:        '#ef5350',
        wickUpColor:      '#1a756d',
        wickDownColor:    '#a33535',
        borderVisible:    false,
        priceLineVisible: false,
      });

      // Volume series
      const volSeries = chart.addHistogramSeries({
        color:      '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

      chartRef.current   = chart;
      candleRef.current  = candleSeries;
      volRef.current     = volSeries;

      // Resize observer
      const ro = new ResizeObserver(() => {
        if (containerRef.current && chartRef.current)
          chartRef.current.resize(containerRef.current.clientWidth, 400);
      });
      ro.observe(containerRef.current);

      return () => { ro.disconnect(); chart.remove(); };
    };
    document.head.appendChild(script);
  }, []);

  // ── Update candle data ────────────────────────────────────
  useEffect(() => {
    if (!candleRef.current || !volRef.current) return;

    const data = [...candles].reverse().map(c => ({
      time:  c.ts as any,
      open:  c.o, high: c.h, low: c.l, close: c.c,
    }));

    const volData = [...candles].reverse().map(c => ({
      time:  c.ts as any,
      value: (c.buy || 0) + (c.sell || 0),
      color: c.c >= c.o ? '#26a69a44' : '#ef535044',
    }));

    // Add live bar
    if (liveBar) {
      const lb = { time: liveBar.ts as any, open: liveBar.o, high: liveBar.h, low: liveBar.l, close: liveBar.c };
      if (data.length === 0 || data[data.length - 1].time !== lb.time) data.push(lb);
      else data[data.length - 1] = lb;
    }

    if (data.length > 0) {
      candleRef.current.setData(data);
      volRef.current.setData(volData);
    }
  }, [candles, liveBar]);

  // ── Update live price ─────────────────────────────────────
  useEffect(() => {
    if (!candleRef.current || !liveBar || !price) return;
    candleRef.current.update({
      time:  liveBar.ts as any,
      open:  liveBar.o,
      high:  Math.max(liveBar.h, price),
      low:   Math.min(liveBar.l, price),
      close: price,
    });
  }, [price, liveBar]);

  // ── Update level lines ────────────────────────────────────
  useEffect(() => {
    if (!candleRef.current) return;

    // Remove old lines
    linesRef.current.forEach(l => { try { candleRef.current.removePriceLine(l); } catch {} });
    linesRef.current = [];

    const addLine = (p: number | undefined, color: string, title: string, style = 2, width = 1) => {
      if (!p || p <= 0) return;
      const line = candleRef.current.createPriceLine({ price: p, color, lineWidth: width, lineStyle: style, axisLabelVisible: true, title });
      linesRef.current.push(line);
    };

    // Standard levels
    addLine(levels?.prev_high,     '#ef4444', 'PDH', 2);
    addLine(levels?.prev_low,      '#ef4444', 'PDL', 2);
    addLine(levels?.daily_open,    '#60a5fa', 'DO',  2);
    addLine(levels?.overnight_high,'#a78bfa', 'ONH', 1);
    addLine(levels?.overnight_low, '#a78bfa', 'ONL', 1);
    addLine(profile?.vah,          '#22c55e', 'VAH', 2);
    addLine(profile?.val,          '#22c55e', 'VAL', 2);
    addLine(profile?.poc,          '#f97316', 'POC', 3, 2);
    addLine(session?.ibh,          '#38bdf8', 'IBH', 2);
    addLine(session?.ibl,          '#38bdf8', 'IBL', 2);
    addLine(vwap,                  '#f6c90e', 'VWAP', 0, 2);

    // Signal lines
    if (signal && signal.direction !== 'NO_TRADE' && signal.entry) {
      const isLong = signal.direction === 'LONG';
      addLine(signal.entry,   '#ffffff',  '→ ENTRY', 0, 2);
      addLine(signal.stop,    '#ef5350',  '✕ STOP',  2, 1);
      addLine(signal.target1, '#22c55e',  '⊕ T1',    2, 1);
      addLine(signal.target2, '#16a34a',  '⊕ T2',    2, 1);
      addLine(signal.target3, '#86efac',  '★ T3',    1, 1);
    }
  }, [levels, profile, session, vwap, signal]);

  const tfs = ['m3', 'm15', 'm30', 'm60'];

  return (
    <div style={{ background: '#111827', border: '1px solid #1e2738', borderRadius: 8, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', background: '#111827', borderBottom: '1px solid #1e2738' }}>
        <span style={{ fontSize: 9, color: '#4a5568', letterSpacing: 2 }}>גרף נרות</span>
        <div style={{ display: 'flex', gap: 3, marginLeft: 'auto' }}>
          {tfs.map(t => (
            <button key={t} onClick={() => onTFChange?.(t)} style={{
              padding: '2px 8px', borderRadius: 5, fontSize: 9, fontWeight: 700,
              border: 'none', cursor: 'pointer', fontFamily: 'inherit',
              background: tf === t ? '#f6c90e' : '#1e2738',
              color: tf === t ? '#0d1117' : '#6b7280',
              transition: 'all .15s',
            }}>{t.toUpperCase()}</button>
          ))}
        </div>
      </div>

      {/* Chart container */}
      <div ref={containerRef} style={{ width: '100%', height: 400 }} />
    </div>
  );
}
