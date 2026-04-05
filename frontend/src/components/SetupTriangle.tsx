"use client";

import { useEffect, useRef, useCallback } from "react";

export interface TriangleSetup {
  entry:     number;
  stop:      number;
  t1:        number;
  t2:        number;
  t3:        number;
  direction: "LONG" | "SHORT";
  visible:   boolean;
}

interface Props {
  series: any;   // candlestick series — has priceToCoordinate
  chart:  any;   // IChartApi — for timeScale subscriptions
  setup:  TriangleSetup | null;
}

export function SetupTriangle({ series, chart, setup }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const container = canvas.parentElement;
    if (!container) return;

    const W = container.clientWidth;
    const H = container.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);

    if (!series || !setup || !setup.visible) return;

    const p2y = (price: number): number | null => {
      try { return series.priceToCoordinate(price); }
      catch { return null; }
    };

    const { entry, stop, t1, t2, t3, direction } = setup;
    const entY  = p2y(entry);
    const stopY = p2y(stop);
    const t1Y   = p2y(t1);
    const t2Y   = p2y(t2);
    const t3Y   = p2y(t3);

    if (entY === null || stopY === null || t3Y === null) return;

    const scaleW = 72;
    const chartW = W - scaleW;
    const apexX = chartW * 0.20;
    const baseMaxW = chartW * 0.75;

    const rwd3 = Math.abs(t3 - entry);
    const risk = Math.abs(entry - stop);

    const wAtPrice = (price: number, isReward: boolean): number => {
      if (isReward) {
        const frac = rwd3 > 0 ? Math.abs(price - entry) / rwd3 : 0;
        return baseMaxW * Math.min(frac, 1);
      } else {
        const frac = risk > 0 ? Math.abs(price - entry) / risk : 0;
        return (baseMaxW * 0.25) * Math.min(frac, 1);
      }
    };

    // ═══ REWARD TRIANGLE ════════════════════════════
    if (t3Y !== null && t1Y !== null && t2Y !== null) {
      const rewardTop = Math.min(entY, t3Y);
      const rewardBot = Math.max(entY, t3Y);
      const grad = ctx.createLinearGradient(0, rewardBot, 0, rewardTop);

      if (direction === "LONG") {
        grad.addColorStop(0, "rgba(0,188,212,0.0)");
        grad.addColorStop(0.4, "rgba(0,188,212,0.08)");
        grad.addColorStop(1, "rgba(0,188,212,0.22)");
      } else {
        grad.addColorStop(0, "rgba(0,188,212,0.22)");
        grad.addColorStop(0.6, "rgba(0,188,212,0.08)");
        grad.addColorStop(1, "rgba(0,188,212,0.0)");
      }

      const w3 = wAtPrice(t3, true);
      ctx.beginPath();
      ctx.moveTo(apexX, entY);
      ctx.lineTo(apexX - w3, t3Y);
      ctx.lineTo(apexX + w3, t3Y);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();

      // Triangle edges
      ctx.strokeStyle = "rgba(0,188,212,0.45)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(apexX, entY);
      ctx.lineTo(apexX - w3, t3Y);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(apexX, entY);
      ctx.lineTo(apexX + w3, t3Y);
      ctx.stroke();

      // T1, T2 dashed lines
      const targets: [number | null, number, string, string][] = [
        [t1Y, t1, "T1", "rgba(0,188,212,0.6)"],
        [t2Y, t2, "T2", "rgba(0,188,212,0.75)"],
      ];
      for (const [y, p, _lbl, col] of targets) {
        if (y === null) continue;
        const w = wAtPrice(p, true);
        ctx.strokeStyle = col;
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 4]);
        ctx.beginPath();
        ctx.moveTo(apexX - w, y);
        ctx.lineTo(apexX + w, y);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // T3 base line
      ctx.strokeStyle = "rgba(0,188,212,0.9)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(apexX - w3, t3Y);
      ctx.lineTo(apexX + w3, t3Y);
      ctx.stroke();
    }

    // ═══ RISK TRIANGLE ════════════════════════════
    {
      const wS = wAtPrice(stop, false);
      ctx.beginPath();
      ctx.moveTo(apexX, entY);
      ctx.lineTo(apexX - wS, stopY);
      ctx.lineTo(apexX + wS, stopY);
      ctx.closePath();
      ctx.fillStyle = "rgba(233,30,99,0.10)";
      ctx.fill();
      ctx.strokeStyle = "rgba(233,30,99,0.5)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // ═══ LABELS ════════════════════════════════════
    const w3f = wAtPrice(t3, true);
    const w2f = wAtPrice(t2, true);
    const w1f = wAtPrice(t1, true);
    const wSf = wAtPrice(stop, false);
    const rr1 = risk > 0 ? (Math.abs(t1 - entry) / risk).toFixed(1) : "0";
    const rr2 = risk > 0 ? (Math.abs(t2 - entry) / risk).toFixed(1) : "0";
    const rr3 = risk > 0 ? (Math.abs(t3 - entry) / risk).toFixed(1) : "0";

    const label = (y: number | null, x: number, text: string, sub: string, color: string) => {
      if (y === null) return;
      ctx.font = "bold 10px monospace";
      ctx.fillStyle = color;
      ctx.textAlign = "left";
      ctx.fillText(text, x + 6, y - 3);
      ctx.font = "9px monospace";
      ctx.fillStyle = color.replace("0.9", "0.55").replace("1)", "0.6)");
      ctx.fillText(sub, x + 6, y + 9);
    };

    label(t3Y, apexX + w3f, `T3  ${t3.toFixed(2)}`, `R:R ${rr3}:1 runner`, "rgba(0,210,220,0.95)");
    label(t2Y, apexX + w2f, `T2  ${t2.toFixed(2)}`, `R:R ${rr2}:1 25%`, "rgba(0,188,212,0.85)");
    label(t1Y, apexX + w1f, `T1  ${t1.toFixed(2)}`, `R:R ${rr1}:1 50%`, "rgba(0,170,200,0.75)");
    label(stopY, apexX + wSf, `STP ${stop.toFixed(2)}`, `Risk ${risk.toFixed(2)} pt`, "rgba(233,30,99,0.9)");

    // ENTRY dot + label
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(apexX, entY, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = "bold 10px monospace";
    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "left";
    ctx.fillText(`ENT  ${entry.toFixed(2)}`, apexX + 10, entY + 4);

    // Direction arrow
    const aDir = direction === "LONG" ? -1 : 1;
    ctx.fillStyle = direction === "LONG" ? "#00c853" : "#e91e63";
    ctx.beginPath();
    ctx.moveTo(apexX, entY + aDir * 10);
    ctx.lineTo(apexX - 6, entY + aDir * 20);
    ctx.lineTo(apexX + 6, entY + aDir * 20);
    ctx.closePath();
    ctx.fill();

  }, [series, setup]);

  useEffect(() => {
    if (!chart || !series) return;
    requestAnimationFrame(draw);

    chart.timeScale().subscribeVisibleLogicalRangeChange(draw);

    const container = canvasRef.current?.parentElement;
    let ro: ResizeObserver | null = null;
    if (container) {
      ro = new ResizeObserver(draw);
      ro.observe(container);
    }

    const interval = setInterval(draw, 500);

    return () => {
      try { chart.timeScale().unsubscribeVisibleLogicalRangeChange(draw); } catch {}
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
        zIndex: 6,
      }}
    />
  );
}
