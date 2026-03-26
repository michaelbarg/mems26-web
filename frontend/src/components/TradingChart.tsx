// frontend/src/components/TradingChart.tsx
"use client";
import { useEffect, useRef } from "react";
import { Signal } from "@/types/signal";

type Props = {
  priceHistory: number[];
  signal:       Signal | null;
  woodi:        Record<string, number>;
  levels:       Record<string, number>;
  features:     Record<string, number | string | boolean>;
};

const LEVEL_DEFS = [
  { key: "poc_today", col: "#6d28d9", lbl: "POC today", lw: 2,   dash: [] as number[] },
  { key: "poc_yest",  col: "#ea580c", lbl: "POC yest",  lw: 2,   dash: [] },
  { key: "pp",        col: "#f59e0b", lbl: "Woodi PP",  lw: 1.5, dash: [6, 3] },
  { key: "r1",        col: "#22c55e", lbl: "R1",        lw: 1,   dash: [3, 4] },
  { key: "r2",        col: "#22c55e", lbl: "R2",        lw: 1,   dash: [3, 4] },
  { key: "s1",        col: "#ef4444", lbl: "S1",        lw: 1,   dash: [3, 4] },
  { key: "s2",        col: "#ef4444", lbl: "S2",        lw: 1,   dash: [3, 4] },
  { key: "h72",       col: "#06b6d4", lbl: "72H Hi",   lw: 1,   dash: [2, 5] },
  { key: "l72",       col: "#06b6d4", lbl: "72H Lo",   lw: 1,   dash: [2, 5] },
  { key: "hwk",       col: "#0891b2", lbl: "Wk Hi",    lw: 1,   dash: [1, 6] },
  { key: "lwk",       col: "#0891b2", lbl: "Wk Lo",    lw: 1,   dash: [1, 6] },
];

export default function TradingChart({ priceHistory, signal, woodi, levels, features }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const H = 260;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.offsetWidth;
    canvas.width = W;
    canvas.height = H;
    const LABW = 58;

    const allPrices = [...priceHistory];
    const levelSrc = {
      ...Object.fromEntries(LEVEL_DEFS.map(d => [d.key, woodi[d.key] ?? levels[d.key] ?? 0])),
      poc_today: (features.poc_today as number) ?? 0,
      poc_yest:  (features.poc_yest  as number) ?? 0,
      h72: levels.h72 ?? 0,
      l72: levels.l72 ?? 0,
      hwk: levels.hwk ?? 0,
      lwk: levels.lwk ?? 0,
    };

    Object.values(levelSrc).forEach(v => { if (v) allPrices.push(v); });
    if (signal) [signal.entry, signal.stop, signal.target1, signal.target2, signal.target3]
      .forEach(v => allPrices.push(v));

    const minP = Math.min(...allPrices) - 4;
    const maxP = Math.max(...allPrices) + 4;
    const range = maxP - minP;

    const toY = (p: number) => H - ((p - minP) / range) * (H - 28) + 12;

    ctx.clearRect(0, 0, W, H);

    // Grid
    const step = [0.25, 0.5, 1, 2, 5, 10, 20, 50].find(s => s >= (range / 7)) ?? 50;
    let gp = Math.ceil(minP / step) * step;
    ctx.font = "9px monospace";
    ctx.fillStyle = "rgba(255,255,255,.28)";
    while (gp < maxP) {
      const y = toY(gp);
      ctx.beginPath(); ctx.strokeStyle = "rgba(255,255,255,.04)"; ctx.lineWidth = 1;
      ctx.moveTo(0, y); ctx.lineTo(W - LABW, y); ctx.stroke();
      ctx.fillText(gp.toFixed(2), W - LABW + 3, y + 3);
      gp = Math.round((gp + step) * 100) / 100;
    }

    // Market levels
    LEVEL_DEFS.forEach(({ key, col, lbl, lw, dash }) => {
      const v = (levelSrc as Record<string, number>)[key];
      if (!v || v < minP || v > maxP) return;
      const y = toY(v);
      ctx.beginPath(); ctx.strokeStyle = col + "99"; ctx.lineWidth = lw;
      ctx.setLineDash(dash); ctx.moveTo(0, y); ctx.lineTo(W - LABW, y); ctx.stroke();
      ctx.setLineDash([]); ctx.fillStyle = col; ctx.font = "bold 9px monospace";
      ctx.fillText(lbl, 5, y - 2);
    });

    // Signal TP/SL zones + lines
    if (signal) {
      const s = signal;
      const isLong = s.direction === "LONG";
      const eY = toY(s.entry), slY = toY(s.stop), t3Y = toY(s.target3);

      // profit zone
      ctx.fillStyle = "rgba(34,197,94,.04)";
      if (isLong) ctx.fillRect(0, t3Y, W - LABW, eY - t3Y);
      else        ctx.fillRect(0, eY,  W - LABW, t3Y - eY);
      // risk zone
      ctx.fillStyle = "rgba(239,68,68,.04)";
      if (isLong) ctx.fillRect(0, eY, W - LABW, slY - eY);
      else        ctx.fillRect(0, slY, W - LABW, eY - slY);

      const drawSig = (p: number, col: string, lbl: string, lw: number, dash: number[]) => {
        const y = toY(p);
        if (y < 4 || y > H - 4) return;
        ctx.beginPath(); ctx.strokeStyle = col; ctx.lineWidth = lw;
        ctx.setLineDash(dash); ctx.moveTo(0, y); ctx.lineTo(W - LABW, y); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = col + "25"; ctx.fillRect(W - LABW, y - 8, LABW, 14);
        ctx.fillStyle = col; ctx.font = "bold 9px monospace";
        ctx.fillText(lbl, W - LABW + 3, y + 3);
      };
      drawSig(s.target3, "#22c55e", "T3 " + s.target3.toFixed(2), 2,   [6, 3]);
      drawSig(s.target2, "#4ade80", "T2 " + s.target2.toFixed(2), 1.5, [6, 3]);
      drawSig(s.target1, "#86efac", "T1 " + s.target1.toFixed(2), 1.5, [6, 3]);
      drawSig(s.entry,   "#f59e0b", "EN " + s.entry.toFixed(2),   2.5, []);
      drawSig(s.stop,    "#ef4444", "SL " + s.stop.toFixed(2),    2,   [4, 3]);
    }

    // Price line
    if (priceHistory.length > 1) {
      ctx.beginPath(); ctx.strokeStyle = "rgba(255,255,255,.75)"; ctx.lineWidth = 1.5;
      priceHistory.forEach((p, i) => {
        const x = (i / (priceHistory.length - 1)) * (W - LABW - 10) + 5;
        const y = toY(p);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();

      // Current price dot
      const lastY = toY(priceHistory[priceHistory.length - 1]);
      ctx.beginPath(); ctx.arc(W - LABW - 5, lastY, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#f59e0b"; ctx.fill();
      ctx.fillStyle = "#f59e0b"; ctx.fillRect(W - LABW, lastY - 8, LABW, 14);
      ctx.fillStyle = "#000"; ctx.font = "bold 9px monospace";
      ctx.fillText(priceHistory[priceHistory.length - 1].toFixed(2), W - LABW + 3, lastY + 3);
    }

    // Axis bg
    ctx.fillStyle = "rgba(255,255,255,.03)"; ctx.fillRect(W - LABW, 0, LABW, H);

  }, [priceHistory, signal, woodi, levels, features]);

  return (
    <div className="relative border border-[#1e1e2e] rounded-xl overflow-hidden bg-[#0a0a0f]">
      <canvas ref={canvasRef} height={H} className="w-full block" />
    </div>
  );
}
