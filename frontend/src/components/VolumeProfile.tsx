"use client";

import { useEffect, useRef, useCallback } from "react";

interface Candle {
  ts: number;
  o: number; h: number; l: number; c: number;
  buy?: number; sell?: number; delta?: number;
}

interface Props {
  series: any;                    // candlestick series ref — has priceToCoordinate
  chart: any;                     // IChartApi — for timeScale subscriptions
  candles: Candle[];
  tickSize?: number;              // MES = 0.25
  profileWidth?: number;          // px width of the profile bars
  opacity?: number;
}

const BULL_COLOR = "rgba(0, 188, 212, 0.75)";
const BEAR_COLOR = "rgba(233, 30, 99, 0.75)";
const POC_COLOR  = "rgba(255, 235, 59, 0.9)";
const VA_COLOR   = "rgba(255, 255, 255, 0.25)";

function calcBuySell(c: Candle): { buy: number; sell: number } {
  const buyVal = c.buy || 0;
  const sellVal = c.sell || 0;
  if (buyVal + sellVal > 0) return { buy: buyVal, sell: sellVal };
  // Fallback: estimate from price position
  const spread = c.h - c.l;
  if (spread === 0) return { buy: 50, sell: 50 };
  const buyPct = (c.c - c.l) / spread;
  return { buy: 100 * buyPct, sell: 100 * (1 - buyPct) };
}

export function VolumeProfile({
  series,
  chart,
  candles,
  tickSize = 0.25,
  profileWidth = 130,
  opacity = 1,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !series || !candles.length) return;

    const container = canvas.parentElement;
    if (!container) return;

    const dpr = window.devicePixelRatio || 1;
    const w = container.clientWidth;
    const h = container.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    // ─── 1. Build price→volume map ───────────────────────
    const priceMap = new Map<number, { buy: number; sell: number }>();
    const round = (p: number) => Math.round(p / tickSize) * tickSize;

    for (const c of candles) {
      if (c.ts <= 0) continue;
      const { buy, sell } = calcBuySell(c);
      const levels = Math.max(1, Math.round((c.h - c.l) / tickSize));
      const buyPer = buy / levels;
      const sellPer = sell / levels;

      for (let i = 0; i <= levels; i++) {
        const price = round(c.l + i * tickSize);
        const existing = priceMap.get(price) ?? { buy: 0, sell: 0 };
        existing.buy += buyPer;
        existing.sell += sellPer;
        priceMap.set(price, existing);
      }
    }

    if (priceMap.size === 0) return;

    // ─── 2. Find POC, VAH, VAL ──────────────────────────
    let maxVol = 0, pocPrice = 0;
    priceMap.forEach((v, price) => {
      const total = v.buy + v.sell;
      if (total > maxVol) { maxVol = total; pocPrice = price; }
    });
    if (maxVol === 0) return;

    const allPrices = Array.from(priceMap.keys()).sort((a, b) => a - b);
    const totalVolAll = Array.from(priceMap.values()).reduce((s, v) => s + v.buy + v.sell, 0);
    const target70 = totalVolAll * 0.7;

    // Expand from POC outward
    const pocIdx = allPrices.indexOf(pocPrice);
    let lo = pocIdx, hi = pocIdx;
    let cumVol = (priceMap.get(pocPrice)?.buy ?? 0) + (priceMap.get(pocPrice)?.sell ?? 0);
    while (cumVol < target70 && (lo > 0 || hi < allPrices.length - 1)) {
      const upVol = hi < allPrices.length - 1
        ? (priceMap.get(allPrices[hi + 1])?.buy ?? 0) + (priceMap.get(allPrices[hi + 1])?.sell ?? 0)
        : 0;
      const downVol = lo > 0
        ? (priceMap.get(allPrices[lo - 1])?.buy ?? 0) + (priceMap.get(allPrices[lo - 1])?.sell ?? 0)
        : 0;
      if (upVol >= downVol && hi < allPrices.length - 1) { hi++; cumVol += upVol; }
      else if (lo > 0) { lo--; cumVol += downVol; }
      else if (hi < allPrices.length - 1) { hi++; cumVol += upVol; }
      else break;
    }
    const vahPrice = allPrices[hi];
    const valPrice = allPrices[lo];

    // ─── 3. Price → Y coordinate via series ─────────────
    const priceToY = (price: number): number | null => {
      try { return series.priceToCoordinate(price); }
      catch { return null; }
    };

    // ─── 4. Draw bars ───────────────────────────────────
    // Bar height from adjacent ticks
    const testY1 = priceToY(allPrices[0]);
    const testY2 = priceToY(allPrices[0] + tickSize);
    const barHeight = (testY1 !== null && testY2 !== null)
      ? Math.max(2, Math.abs(testY2 - testY1) - 1)
      : 3;

    const xRight = w - 4; // snug to right edge

    for (const price of allPrices) {
      const vol = priceMap.get(price)!;
      const total = vol.buy + vol.sell;
      if (total === 0) continue;

      const y = priceToY(price);
      if (y === null || y < -20 || y > h + 20) continue;

      const totalWidth = (total / maxVol) * profileWidth;
      const buyWidth = (vol.buy / total) * totalWidth;
      const sellWidth = totalWidth - buyWidth;
      const yTop = y - barHeight / 2;

      // VA background highlight
      if (price >= valPrice && price <= vahPrice) {
        ctx.fillStyle = "rgba(255,255,255,0.03)";
        ctx.fillRect(xRight - profileWidth, yTop, profileWidth, barHeight);
      }

      // Buy (cyan) — from right edge going left
      ctx.fillStyle = BULL_COLOR;
      ctx.fillRect(xRight - buyWidth, yTop, buyWidth, barHeight);

      // Sell (pink) — continues left from buy
      ctx.fillStyle = BEAR_COLOR;
      ctx.fillRect(xRight - buyWidth - sellWidth, yTop, sellWidth, barHeight);

      // POC highlight
      if (price === pocPrice) {
        ctx.strokeStyle = POC_COLOR;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 2]);
        ctx.beginPath();
        ctx.moveTo(xRight - totalWidth, y);
        ctx.lineTo(xRight, y);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = POC_COLOR;
        ctx.font = "bold 9px monospace";
        ctx.textAlign = "right";
        ctx.fillText(`POC ${price.toFixed(2)}`, xRight - totalWidth - 4, y + 3);
      }
    }

    // ─── 5. VAH / VAL labels ────────────────────────────
    const drawHLine = (price: number, label: string) => {
      const y = priceToY(price);
      if (y === null) return;
      ctx.strokeStyle = VA_COLOR;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(xRight - profileWidth, y);
      ctx.lineTo(xRight, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = VA_COLOR;
      ctx.font = "9px monospace";
      ctx.textAlign = "right";
      ctx.fillText(`${label} ${price.toFixed(2)}`, xRight - profileWidth - 4, y + 3);
    };
    drawHLine(vahPrice, "VAH");
    drawHLine(valPrice, "VAL");

    // ─── 6. Legend ──────────────────────────────────────
    ctx.font = "bold 9px monospace";
    ctx.textAlign = "right";
    ctx.fillStyle = BULL_COLOR;
    ctx.fillText("BUY", xRight - 36, 12);
    ctx.fillStyle = BEAR_COLOR;
    ctx.fillText("SELL", xRight - 2, 12);

  }, [series, candles, tickSize, profileWidth]);

  useEffect(() => {
    if (!chart || !series) return;

    // Initial draw after chart renders
    requestAnimationFrame(draw);

    // Redraw on scroll/zoom
    const unsubTime = chart.timeScale().subscribeVisibleLogicalRangeChange(draw);

    // Redraw on resize
    const container = canvasRef.current?.parentElement;
    let ro: ResizeObserver | null = null;
    if (container) {
      ro = new ResizeObserver(draw);
      ro.observe(container);
    }

    // Periodic redraw for live data updates
    const interval = setInterval(draw, 3000);

    return () => {
      unsubTime();
      ro?.disconnect();
      clearInterval(interval);
    };
  }, [chart, series, draw]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 5,
        opacity,
      }}
    />
  );
}
