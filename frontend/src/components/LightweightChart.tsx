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

interface SweepData {
  dir: 'long' | 'short';
  sweepBarTs: number;
  entryBarTs: number;
  setupBarTs: number[];
  entry: number;
  stop: number;
  t1: number;
  t2: number;
  t3?: number;
  delta: number;
  relVol: number;
  score: number;
  // Future bar timestamps for markers
  stopBarTs?: number;
  t1BarTs?: number;
  t2BarTs?: number;
  t3BarTs?: number;
  status?: string;
}

interface Props {
  candles: Candle[];
  livePrice?: number;
  liveBar?: { ts: number; o: number; h: number; l: number; c: number; buy?: number; sell?: number } | null;
  vwap?: number;
  levels?: { prev_high?: number; prev_low?: number; daily_open?: number; overnight_high?: number; overnight_low?: number };
  profile?: { poc?: number; vah?: number; val?: number };
  session?: { ibh?: number; ibl?: number };
  signal?: Signal | null;
  activeSetups?: { name: string; dir: 'long'|'short'; col: string }[];
  sweepData?: SweepData;
  sweepEvents?: Array<{ id:string; ts:number; dir:'long'|'short'; levelName:string; score:number; sweepBarTs:number }>;
  onSweepClick?: (sweepTs: number) => void;
  patterns?: Array<{id:string; nameHeb:string; direction:string; confidence:number; keyLevel:number; breakoutLevel?:number; stopLevel?:number; col:string; barIndex?:number}>;
  selectedPatternId?: string;
  height?: number;
}

export default function LightweightChart({
  candles, livePrice, liveBar, vwap, levels, profile, session, signal, activeSetups, sweepData, sweepEvents, onSweepClick, patterns, selectedPatternId, height
}: Props) {
  const containerRef     = useRef<HTMLDivElement>(null);
  const chartRef         = useRef<any>(null);
  const seriesRef        = useRef<any>(null);
  const volRef           = useRef<any>(null);
  const deltaRef         = useRef<any>(null);
  const linesRef         = useRef<any[]>([]);
  const rthBgRef         = useRef<any>(null);
  const sweepEventsRef   = useRef(sweepEvents);
  const onSweepClickRef  = useRef(onSweepClick);
  sweepEventsRef.current  = sweepEvents;
  onSweepClickRef.current = onSweepClick;
  const loadedRef    = useRef(false);

  const initChart = useCallback(() => {
    if (!containerRef.current || chartRef.current) return;
    const LW = (window as any).LightweightCharts;
    if (!LW) return;

    const chart = LW.createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height: height ?? (containerRef.current?.clientHeight ?? 500),
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
        scaleMargins:   { top: 0.04, bottom: 0.32 },
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
      scaleMargins: { top: 0.75, bottom: 0.15 },
    });

    // Delta (buy - sell) histogram
    const delta = chart.addHistogramSeries({
      priceFormat:     { type: 'volume' },
      priceScaleId:    'delta',
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale('delta').applyOptions({
      scaleMargins: { top: 0.88, bottom: 0 },
      visible: false,
    });

    chartRef.current  = chart;
    seriesRef.current = series;
    volRef.current    = vol;
    deltaRef.current  = delta;

    // RTH background overlay — covers full chart height
    const rthBg = chart.addHistogramSeries({
      priceScaleId:    'rth-bg',
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale('rth-bg').applyOptions({
      scaleMargins: { top: 0, bottom: 0 },
      visible: false,
    });
    rthBgRef.current = rthBg;

    // Click handler — find nearest sweep event
    chart.subscribeClick((param: any) => {
      if (!param.time || !sweepEventsRef.current || !onSweepClickRef.current) return;
      const clickTs = param.time as number;
      // Find sweep within ±2 bars (±360 sec)
      const match = sweepEventsRef.current.find((ev: any) =>
        Math.abs(ev.sweepBarTs - clickTs) <= 360
      );
      if (match) onSweepClickRef.current(match.sweepBarTs);
    });

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

    // RTH = 9:30–16:00 ET (EDT=-4h, EST=-5h; אפרוקסימציה: UTC-4 בקיץ)
    const isRTH = (ts: number) => {
      const d = new Date(ts * 1000);
      const utcH = d.getUTCHours();
      const utcM = d.getUTCMinutes();
      const etMin = ((utcH - 4 + 24) % 24) * 60 + utcM; // EDT offset
      return etMin >= 9 * 60 + 30 && etMin < 16 * 60;
    };

    const sorted = [...candles].reverse().filter(c => c.ts > 0);

    const cData = sorted.map(c => ({
      time:  Math.floor(c.ts) as any,
      open:  c.o, high: c.h, low: c.l, close: c.c,
    }));

    const vData = sorted.map(c => ({
      time:  Math.floor(c.ts) as any,
      value: (c.buy || 0) + (c.sell || 0),
      color: (c.c >= c.o) ? '#26a69a44' : '#ef535044',
    }));

    // Add/update live bar
    if (liveBar) {
      const lb = {
        time: Math.floor(liveBar.ts) as any,
        open: liveBar.o, high: liveBar.h, low: liveBar.l,
        close: livePrice ?? liveBar.c,
      };
      if (cData.length > 0 && cData[cData.length - 1].time === lb.time) {
        cData[cData.length - 1] = lb;
      } else {
        cData.push(lb);
        vData.push({ time: Math.floor(liveBar.ts) as any, value: 0, color: '#26a69a44' });
      }
    }

    seriesRef.current.setData(cData);
    volRef.current.setData(vData);

    // Delta bar (buy - sell per candle)
    if (deltaRef.current) {
      const dData = sorted.map(c => {
        const d = (c.buy || 0) - (c.sell || 0);
        return {
          time:  Math.floor(c.ts) as any,
          value: d,
          color: d >= 0 ? '#26a69a99' : '#ef535099',
        };
      });
      if (liveBar) {
        const ld = (liveBar.buy || 0) - (liveBar.sell || 0);
        dData.push({
          time:  Math.floor(liveBar.ts) as any,
          value: ld,
          color: ld >= 0 ? '#26a69a99' : '#ef535099',
        });
      }
      deltaRef.current.setData(dData);
    }

    // RTH background — disabled
    // if (rthBgRef.current) { ... }

  }, [candles, liveBar, livePrice]);

  // Update live price only (no full redraw)
  useEffect(() => {
    if (!seriesRef.current || !liveBar || !livePrice) return;
    seriesRef.current.update({
      time:  Math.floor(liveBar.ts) as any,
      open:  liveBar.o,
      high:  Math.max(liveBar.h, livePrice),
      low:   Math.min(liveBar.l, livePrice),
      close: livePrice,
    });
  }, [liveBar, livePrice]);

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

    add(levels?.prev_high,      '#ef444466', 'PDH ', 3, 1);
    add(levels?.prev_low,       '#ef444466', 'PDL ', 3, 1);
    add(levels?.daily_open,     '#60a5fa66', 'DO  ', 3, 1);
    add(levels?.overnight_high, '#a78bfa66', 'ONH ', 3, 1);
    add(levels?.overnight_low,  '#a78bfa66', 'ONL ', 3, 1);
    add(profile?.vah,           '#22c55e66', 'VAH ', 3, 1);
    add(profile?.val,           '#22c55e66', 'VAL ', 3, 1);
    add(profile?.poc,           '#f9731666', 'POC ', 3, 1);
    add(session?.ibh,           '#38bdf866', 'IBH ', 3, 1);
    add(session?.ibl,           '#38bdf866', 'IBL ', 3, 1);
    add(vwap,                   '#f6c90e66', 'VWAP', 3, 1);

    // Pattern selected — הוסף קווי כניסה וסטופ
    if (patterns && selectedPatternId) {
      const selP = patterns.find(p => p.id === selectedPatternId);
      if (selP) {
        if (selP.breakoutLevel) add(selP.breakoutLevel, selP.col, `▶ ${selP.nameHeb}`, 0, 2);
        if (selP.stopLevel)     add(selP.stopLevel, '#ef5350', '✕ סטופ', 2, 1);
        if (selP.keyLevel)      add(selP.keyLevel, selP.col+'99', '— רמה', 4, 1);
        // Target = כניסה + distance (R:R 1:1)
        if (selP.breakoutLevel && selP.stopLevel) {
          const risk = Math.abs(selP.breakoutLevel - selP.stopLevel);
          const t1 = selP.direction === 'long' ? selP.breakoutLevel + risk : selP.breakoutLevel - risk;
          const t2 = selP.direction === 'long' ? selP.breakoutLevel + risk*2 : selP.breakoutLevel - risk*2;
          add(t1, '#22c55e', `⊕ T1 ${selP.confidence}%`, 2, 1);
          add(t2, '#16a34a', `⊕ T2 ${Math.round(selP.confidence*0.7)}%`, 2, 1);
        }
      }
    }

    // ── Sweep trade lines — entry/stop/C1/C2/C3 as price lines ──────
    if (sweepData && sweepData.entry > 0) {
      const risk = Math.abs(sweepData.entry - sweepData.stop);
      add(sweepData.entry, '#ffffff',    `→ ENTRY ${sweepData.entry.toFixed(2)}`, 0, 2);
      add(sweepData.stop,  '#ef5350',    `✕ STOP ${sweepData.stop.toFixed(2)} (−${risk.toFixed(1)}pt)`, 2, 1);
      add(sweepData.t1,    '#22c55e',    `① C1 50% ${sweepData.t1.toFixed(2)} (+${Math.abs(sweepData.t1-sweepData.entry).toFixed(1)}pt)`, 2, 1);
      add(sweepData.t2,    '#16a34a',    `② C2 25% ${sweepData.t2.toFixed(2)} (+${Math.abs(sweepData.t2-sweepData.entry).toFixed(1)}pt)`, 2, 1);
      if (sweepData.t3) add(sweepData.t3, '#86efac66', `③ C3 Run ${sweepData.t3.toFixed(2)}`, 3, 1);
    }

    // ── Markers: Setup + Pattern ──────────────────────────
    if (seriesRef.current) {
      try {
        const allMarkers: any[] = [];

        // ── Sweep markers — on actual + future candles ──────────
        if (sweepData && sweepData.sweepBarTs > 0) {
          const isLong = sweepData.dir === 'long';
          const pos = isLong ? 'belowBar' : 'aboveBar';
          const entryPts = Math.abs(sweepData.entry - sweepData.stop);

          // Sweep candle
          allMarkers.push({
            time: Math.floor(sweepData.sweepBarTs) as any,
            position: pos, color: isLong ? '#22c55e' : '#ef5350',
            shape: isLong ? 'arrowUp' : 'arrowDown',
            text: `⚡ SWEEP`, size: 2,
          });

          // Entry candle (reversal bar)
          if (sweepData.entryBarTs > 0) {
            allMarkers.push({
              time: Math.floor(sweepData.entryBarTs) as any,
              position: pos, color: '#ffffff',
              shape: isLong ? 'arrowUp' : 'arrowDown',
              text: `→ ENTRY ${sweepData.entry.toFixed(2)}`, size: 2,
            });
          }

          // Setup candles
          if (sweepData.setupBarTs) {
            sweepData.setupBarTs.forEach(ts => {
              if (ts > 0) allMarkers.push({ time: Math.floor(ts) as any, position: pos, color: '#4a556866', shape: 'circle' as any, text: 'setup', size: 0 });
            });
          }

          // Stop/C1/C2/C3 are now shown as horizontal price lines above (not markers)
        }

        // ── Historical sweep dots (tiny circles, no text) ──
        if (sweepEvents && sweepEvents.length > 0 && !sweepData) {
          sweepEvents.forEach((ev: any) => {
            allMarkers.push({
              time: Math.floor(ev.sweepBarTs) as any,
              position: ev.dir === 'long' ? 'belowBar' : 'aboveBar',
              color: ev.dir === 'long' ? '#22c55e55' : '#ef535055',
              shape: 'circle' as any,
              text: '',
              size: 0,
            });
          });
        }

        // Pattern markers — על הנר הרלוונטי
        if (patterns && patterns.length > 0 && candles.length > 0) {
          // candles מגיעים ישן→חדש
          const sortedCandles = [...candles].sort((a,b) => a.ts - b.ts);
          patterns.forEach(p => {
            const isSelected = p.id === selectedPatternId;
            // barIndex מחושב מהסוף — הופכים לאינדקס בsortedCandles
            const idx = p.barIndex !== undefined
              ? Math.max(0, sortedCandles.length - 1 - p.barIndex)
              : sortedCandles.length - 1;
            const candle = sortedCandles[idx];
            if (!candle) return;

            // Marker על נר התבנית
            allMarkers.push({
              time: candle.ts as any,
              position: p.direction === 'long' ? 'belowBar' : 'aboveBar',
              color: isSelected ? p.col : p.col + '99',
              shape: p.direction === 'long' ? 'arrowUp' : p.direction === 'short' ? 'arrowDown' : 'circle',
              text: `${p.nameHeb} ${p.confidence}%`,
              size: isSelected ? 2 : 1,
            });

            // אם נבחר — הוסף marker גם על נר הפריצה (עכשיו)
            if (isSelected && p.breakoutLevel && liveBar) {
              allMarkers.push({
                time: liveBar.ts as any,
                position: p.direction === 'long' ? 'belowBar' : 'aboveBar',
                color: '#a78bfa',
                shape: p.direction === 'long' ? 'arrowUp' : 'arrowDown',
                text: `⚡ כניסה ${p.breakoutLevel?.toFixed(2)}`,
                size: 2,
              });
            }
          });
        }

        // מיין לפי זמן (חובה ב-LightweightCharts)
        allMarkers.sort((a,b) => (a.time as number) - (b.time as number));
        seriesRef.current.setMarkers(allMarkers);
      } catch {}
    }

  }, [levels, profile, session, vwap, signal, activeSetups, sweepData, sweepEvents, liveBar, patterns, selectedPatternId]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: height ?? '100%', minHeight: height ?? 400, background: '#0d1117', borderRadius: 8, overflow: 'hidden' }} />
  );
}
