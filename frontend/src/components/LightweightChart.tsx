'use client';

import { useEffect, useRef, useCallback } from 'react';

interface Candle {
  ts: number;
  o: number; h: number; l: number; c: number;
  buy?: number; sell?: number; delta?: number;
}

interface Signal {
  direction: 'LONG' | 'SHORT' | 'NO_TRADE';
  entry: number; stop: number;
  target1: number; target2: number; target3: number;
  tl_color?: string;
}

interface Props {
  candles: Candle[];
  livePrice?: number;
  liveBar?: { ts: number; o: number; h: number; l: number; c: number } | null;
  vwap?: number;
  levels?: { prev_high?: number; prev_low?: number; daily_open?: number; overnight_high?: number; overnight_low?: number };
  profile?: { poc?: number; vah?: number; val?: number };
  session?: { ibh?: number; ibl?: number };
  signal?: Signal | null;
  activeSetups?: { name: string; dir: 'long'|'short'; col: string }[];
  height?: number;
}

export default function LightweightChart({
  candles, livePrice, liveBar, vwap, levels, profile, session, signal, activeSetups, height
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef     = useRef<any>(null);
  const seriesRef    = useRef<any>(null);
  const volRef       = useRef<any>(null);
  const linesRef     = useRef<any[]>([]);
  const loadedRef    = useRef(false);

  const initChart = useCallback(() => {
    if (!containerRef.current || chartRef.current) return;
    const LW = (window as any).LightweightCharts;
    if (!LW) return;

    const chart = LW.createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height: height ?? (containerRef.current?.clientHeight ?? 480),
      layout: {
        background: { color: '#0d1117' },
        textColor:  '#94a3b8',
        fontSize:   12,
        fontFamily: 'JetBrains Mono, Fira Code, monospace',
      },
      grid: {
        vertLines: { color: '#161d2a', style: 1 },
        horzLines: { color: '#161d2a', style: 1 },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: '#4a5568', width: 1, style: 0, labelBackgroundColor: '#1e2738' },
        horzLine: { color: '#4a5568', width: 1, style: 0, labelBackgroundColor: '#1e2738' },
      },
      rightPriceScale: {
        borderColor:    '#1e2738',
        textColor:      '#94a3b8',
        scaleMargins:   { top: 0.05, bottom: 0.2 },
      },
      timeScale: {
        borderColor:    '#1e2738',
        timeVisible:    true,
        secondsVisible: false,
        barSpacing:     8,
        rightOffset:    5,
      },
      handleScroll:  { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
      handleScale:   { mouseWheel: true, axisPressedMouseMove: true, pinch: true },
    });

    // Candlestick
    const series = chart.addCandlestickSeries({
      upColor:          '#26a69a',
      downColor:        '#ef5350',
      wickUpColor:      '#26a69a',
      wickDownColor:    '#ef5350',
      borderVisible:    false,
      priceLineVisible: false,
      lastValueVisible: true,
    });

    // Volume
    const vol = chart.addHistogramSeries({
      priceFormat:     { type: 'volume' },
      priceScaleId:    'vol',
    });
    chart.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    chartRef.current  = chart;
    seriesRef.current = series;
    volRef.current    = vol;

    // Resize
    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);
  }, [height]);

  // Load script once
  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;

    if ((window as any).LightweightCharts) {
      initChart();
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js';
    script.async = true;
    script.onload = initChart;
    document.head.appendChild(script);

    return () => { chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null; volRef.current = null; };
  }, [initChart]);

  // Update candles
  useEffect(() => {
    if (!seriesRef.current || !volRef.current) return;
    if (candles.length === 0) return;

    const sorted = [...candles].reverse();

    const cData = sorted.map(c => ({
      time:  c.ts as any,
      open:  c.o, high: c.h, low: c.l, close: c.c,
    }));

    const vData = sorted.map(c => ({
      time:  c.ts as any,
      value: (c.buy || 0) + (c.sell || 0),
      color: (c.c >= c.o) ? '#26a69a44' : '#ef535044',
    }));

    // Add/update live bar
    if (liveBar) {
      const lb = {
        time: liveBar.ts as any,
        open: liveBar.o, high: liveBar.h, low: liveBar.l,
        close: livePrice ?? liveBar.c,
      };
      if (cData.length > 0 && cData[cData.length - 1].time === lb.time) {
        cData[cData.length - 1] = lb;
      } else {
        cData.push(lb);
        vData.push({ time: liveBar.ts as any, value: 0, color: '#26a69a44' });
      }
    }

    seriesRef.current.setData(cData);
    volRef.current.setData(vData);

  }, [candles, liveBar, livePrice]);

  // Update live price only (no full redraw)
  useEffect(() => {
    if (!seriesRef.current || !liveBar || !livePrice) return;
    seriesRef.current.update({
      time:  liveBar.ts as any,
      open:  liveBar.o,
      high:  Math.max(liveBar.h, livePrice),
      low:   Math.min(liveBar.l, livePrice),
      close: livePrice,
    });
  }, [livePrice]);

  // Update level lines + setup markers
  useEffect(() => {
    if (!seriesRef.current) return;

    linesRef.current.forEach(l => { try { seriesRef.current.removePriceLine(l); } catch {} });
    linesRef.current = [];

    const add = (price: number | undefined, color: string, title: string, style = 2, width = 1) => {
      if (!price || price <= 0) return;
      const l = seriesRef.current.createPriceLine({ price, color, lineWidth: width, lineStyle: style, axisLabelVisible: true, title });
      linesRef.current.push(l);
    };

    add(levels?.prev_high,      '#ef4444', 'PDH ', 2);
    add(levels?.prev_low,       '#ef4444', 'PDL ', 2);
    add(levels?.daily_open,     '#60a5fa', 'DO  ', 2);
    add(levels?.overnight_high, '#a78bfa', 'ONH ', 1);
    add(levels?.overnight_low,  '#a78bfa', 'ONL ', 1);
    add(profile?.vah,           '#22c55e', 'VAH ', 2);
    add(profile?.val,           '#22c55e', 'VAL ', 2);
    add(profile?.poc,           '#f97316', 'POC ', 0, 2);
    add(session?.ibh,           '#38bdf8', 'IBH ', 2);
    add(session?.ibl,           '#38bdf8', 'IBL ', 2);
    add(vwap,                   '#f6c90e', 'VWAP', 0, 2);

    if (signal && signal.direction !== 'NO_TRADE' && signal.entry) {
      add(signal.entry,   '#ffffff', '→ ENTRY  ', 0, 2);
      add(signal.stop,    '#ef5350', '✕ STOP   ', 2, 1);
      add(signal.target1, '#22c55e', '⊕ T1·C1  ', 2, 1);
      add(signal.target2, '#16a34a', '⊕ T2·C2  ', 2, 1);
      add(signal.target3, '#86efac', '★ T3     ', 1, 1);
    }

    // ── Setup markers on live bar ──────────────────────────
    if (seriesRef.current && activeSetups && activeSetups.length > 0 && liveBar) {
      try {
        const markers = activeSetups.map((s, i) => ({
          time: liveBar.ts as any,
          position: s.dir === 'long' ? 'belowBar' : 'aboveBar',
          color: s.col,
          shape: s.dir === 'long' ? 'arrowUp' : 'arrowDown',
          text: s.name,
          size: 1,
        }));
        seriesRef.current.setMarkers(markers);
      } catch {}
    } else if (seriesRef.current) {
      try { seriesRef.current.setMarkers([]); } catch {}
    }

  }, [levels, profile, session, vwap, signal, activeSetups, liveBar]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: height ?? '100%', minHeight: height ?? 400, background: '#0d1117', borderRadius: 8, overflow: 'hidden' }} />
  );
}
