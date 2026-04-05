"use client";

import { useEffect, useRef, useMemo } from "react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  HistogramData,
  LineData,
  ColorType,
  CrosshairMode,
} from "lightweight-charts";

// ─────────────────────────────────────────────
// טיפוסים — מתאים לפורמט הנרות בפרויקט
// ─────────────────────────────────────────────
export interface Candle {
  ts: number;        // Unix timestamp (seconds)
  o: number;
  h: number;
  l: number;
  c: number;
  buy?: number;      // נפח קנייה מSierra/Bridge
  sell?: number;     // נפח מכירה מSierra/Bridge
  delta?: number;
}

interface Props {
  candles: Candle[];
  height?: number;
}

// ─────────────────────────────────────────────
// חישוב Delta
// ─────────────────────────────────────────────
function calcDelta(c: Candle): { buy: number; sell: number; delta: number } {
  const buyVal = c.buy || 0;
  const sellVal = c.sell || 0;
  // אם הBridge שלח buy/sell אמיתי — נשתמש בזה
  if (buyVal + sellVal > 0) {
    return { buy: buyVal, sell: sellVal, delta: buyVal - sellVal };
  }
  // חישוב קירוב (close-low)/(high-low)
  const volume = 100; // fallback volume estimate
  const spread = c.h - c.l;
  if (spread === 0) return { buy: volume / 2, sell: volume / 2, delta: 0 };
  const buyPct  = (c.c - c.l)  / spread;
  const sellPct = (c.h - c.c) / spread;
  return {
    buy:   volume * buyPct,
    sell:  volume * sellPct,
    delta: volume * (buyPct - sellPct),
  };
}

// ─────────────────────────────────────────────
// צבעים
// ─────────────────────────────────────────────
const COLORS = {
  bg:       "#0a0f0a",
  grid:     "#1a2a1a",
  bull:     "#00bcd4",
  bear:     "#e91e63",
  cvd:      "#00e676",
  cvdMa:    "#ffeb3b",
  text:     "#aaaaaa",
  zero:     "#334433",
};

// ─────────────────────────────────────────────
// קומפוננטה 1: Volume Delta Bars
// ─────────────────────────────────────────────
export function VolumeDeltaBars({ candles, height = 120 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef     = useRef<IChartApi | null>(null);
  const buyRef       = useRef<ISeriesApi<"Histogram"> | null>(null);
  const sellRef      = useRef<ISeriesApi<"Histogram"> | null>(null);
  const deltaLineRef = useRef<ISeriesApi<"Line"> | null>(null);

  // יצירת הגרף
  useEffect(() => {
    if (!containerRef.current) return;

    chartRef.current = createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: COLORS.bg },
        textColor:  COLORS.text,
        fontSize:   10,
      },
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: {
        borderColor: COLORS.grid,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor:    COLORS.grid,
        timeVisible:    true,
        secondsVisible: false,
      },
      handleScroll:  true,
      handleScale:   true,
    });

    buyRef.current  = chartRef.current.addHistogramSeries({
      color:   COLORS.bull,
      base:    0,
      priceScaleId: "right",
    });
    sellRef.current = chartRef.current.addHistogramSeries({
      color:   COLORS.bear,
      base:    0,
      priceScaleId: "right",
    });
    deltaLineRef.current = chartRef.current.addLineSeries({
      color:     "#ffffff",
      lineWidth: 1,
      priceScaleId: "right",
    });

    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => { ro.disconnect(); chartRef.current?.remove(); chartRef.current = null; };
  }, [height]);

  // עדכון נתונים
  useEffect(() => {
    if (!candles.length || !buyRef.current || !sellRef.current || !deltaLineRef.current) return;

    const sorted = [...candles].sort((a, b) => a.ts - b.ts).filter(c => c.ts > 0);

    const buyData:   HistogramData[] = [];
    const sellData:  HistogramData[] = [];
    const deltaData: LineData[]      = [];

    for (const c of sorted) {
      const { buy, sell, delta } = calcDelta(c);
      const t = Math.floor(c.ts) as any;

      buyData.push({ time: t, value: buy,   color: COLORS.bull });
      sellData.push({ time: t, value: -sell, color: COLORS.bear });
      deltaData.push({
        time:  t,
        value: delta,
        color: delta >= 0 ? COLORS.bull : COLORS.bear,
      } as any);
    }

    buyRef.current.setData(buyData);
    sellRef.current.setData(sellData);
    deltaLineRef.current.setData(deltaData);
  }, [candles]);

  return (
    <div className="relative">
      <div className="absolute top-1 left-2 z-10 text-xs text-gray-400 font-mono">
        VOL DELTA
        <span className="ml-2 text-cyan-400">Buy</span>
        <span className="ml-2 text-pink-400">Sell</span>
      </div>
      <div ref={containerRef} style={{ width: "100%", height }} />
    </div>
  );
}

// ─────────────────────────────────────────────
// קומפוננטה 2: CVD (Cumulative Volume Delta)
// ─────────────────────────────────────────────
export function CVDChart({ candles, height = 120 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef     = useRef<IChartApi | null>(null);
  const cvdRef       = useRef<ISeriesApi<"Area"> | null>(null);
  const maRef        = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    chartRef.current = createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: COLORS.bg },
        textColor:  COLORS.text,
        fontSize:   10,
      },
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: {
        borderColor: COLORS.grid,
        scaleMargins: { top: 0.15, bottom: 0.15 },
      },
      timeScale: {
        borderColor:    COLORS.grid,
        timeVisible:    true,
        secondsVisible: false,
      },
      handleScroll:  true,
      handleScale:   true,
    });

    cvdRef.current = chartRef.current.addAreaSeries({
      lineColor:   COLORS.cvd,
      topColor:    "rgba(0,230,118,0.25)",
      bottomColor: "rgba(0,230,118,0.02)",
      lineWidth:   2,
      priceScaleId: "right",
    });

    maRef.current = chartRef.current.addLineSeries({
      color:     COLORS.cvdMa,
      lineWidth: 1,
      lineStyle: 2, // dashed
      priceScaleId: "right",
    });

    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => { ro.disconnect(); chartRef.current?.remove(); chartRef.current = null; };
  }, [height]);

  // חישוב CVD מצטבר + MA20 + Divergence
  const { cvdData, maData, divergences } = useMemo(() => {
    const cvdData: LineData[]        = [];
    const maData:  LineData[]        = [];
    const divergences: {
      time: number; type: "bull" | "bear"
    }[] = [];

    const sorted = [...candles].sort((a, b) => a.ts - b.ts).filter(c => c.ts > 0);

    let cvd = 0;
    let prevDayOfYear = -1;
    const window20: number[] = [];

    for (let i = 0; i < sorted.length; i++) {
      const c = sorted[i];
      const { delta } = calcDelta(c);

      // איפוס יומי — אם היום השתנה
      const dayOfYear = Math.floor(c.ts / 86400);
      if (dayOfYear !== prevDayOfYear && prevDayOfYear !== -1) {
        cvd = 0;
      }
      prevDayOfYear = dayOfYear;

      cvd += delta;
      cvdData.push({ time: Math.floor(c.ts) as any, value: cvd });

      // MA20
      window20.push(cvd);
      if (window20.length > 20) window20.shift();
      const ma = window20.reduce((s, v) => s + v, 0) / window20.length;
      maData.push({ time: Math.floor(c.ts) as any, value: ma });

      // Divergence — 3 נרות אחרון
      if (i >= 3) {
        const prev = sorted[i - 3];
        const prevCvdVal = cvdData[i - 3]?.value ?? 0;
        if (c.c > prev.c && cvd < (prevCvdVal as number)) {
          divergences.push({ time: c.ts, type: "bear" });
        } else if (c.c < prev.c && cvd > (prevCvdVal as number)) {
          divergences.push({ time: c.ts, type: "bull" });
        }
      }
    }

    return { cvdData, maData, divergences };
  }, [candles]);

  useEffect(() => {
    if (!cvdRef.current || !maRef.current) return;
    if (cvdData.length)  cvdRef.current.setData(cvdData);
    if (maData.length)   maRef.current.setData(maData);
  }, [cvdData, maData]);

  // הדגשה ויזואלית לDivergence האחרון
  const lastDiv = divergences[divergences.length - 1];
  const divLabel = lastDiv
    ? lastDiv.type === "bull"
      ? { text: "CVD BULL DIV", color: "#00bcd4" }
      : { text: "CVD BEAR DIV", color: "#e91e63" }
    : null;

  return (
    <div className="relative">
      <div className="absolute top-1 left-2 z-10 flex items-center gap-3 text-xs font-mono">
        <span className="text-gray-400">CVD</span>
        <span className="text-emerald-400">-- Line</span>
        <span className="text-yellow-400">- - MA20</span>
        {divLabel && (
          <span style={{ color: divLabel.color }} className="font-bold animate-pulse">
            {divLabel.text}
          </span>
        )}
      </div>
      <div ref={containerRef} style={{ width: "100%", height }} />
    </div>
  );
}
