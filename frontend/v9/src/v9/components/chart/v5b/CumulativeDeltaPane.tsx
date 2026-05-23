'use client';
import { useEffect, useRef, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const POLL_MS = 10000;
const PANE_HEIGHT = 100;

interface CvdPoint {
  i: number;
  d: number;   // bar delta
  cum: number; // cumulative delta
  p: number;   // price at bar
}

interface CvdData {
  source: string;
  stale?: boolean;
  points: CvdPoint[];
  current_delta: number | null;
  session_delta: number | null;
  peak: number | null;
  trough: number | null;
}

/**
 * Cumulative Delta pane — renders below the price chart.
 * Reads from /api/v9/cumulative_delta/current (Sierra file, no bridge).
 * Shows delta bars (green up / red down) with cumulative line.
 */
export function CumulativeDeltaPane() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [data, setData] = useState<CvdData | null>(null);

  useEffect(() => {
    let inFlight = false;
    const poll = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const res = await fetch(`${API}/api/v9/cumulative_delta/current`);
        const d = await res.json();
        if (d.source && d.points) setData(d);
      } catch {} finally { inFlight = false; }
    };
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data?.points?.length) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, w, h);

    const pts = data.points;
    const n = pts.length;
    if (n === 0) return;

    // Find range for cum values
    let minCum = Infinity, maxCum = -Infinity;
    for (const pt of pts) {
      if (pt.cum < minCum) minCum = pt.cum;
      if (pt.cum > maxCum) maxCum = pt.cum;
    }
    const range = maxCum - minCum || 1;
    const pad = 8;
    const barW = Math.max(2, Math.floor((w - pad * 2) / n) - 2);

    // Zero line
    const zeroY = pad + ((maxCum - 0) / range) * (h - pad * 2);
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(pad, zeroY);
    ctx.lineTo(w - pad, zeroY);
    ctx.stroke();

    // Draw delta bars
    for (let i = 0; i < n; i++) {
      const pt = pts[i];
      const x = pad + i * ((w - pad * 2) / n);
      const cumY = pad + ((maxCum - pt.cum) / range) * (h - pad * 2);
      const barH = Math.abs(zeroY - cumY);
      const top = Math.min(zeroY, cumY);

      ctx.fillStyle = pt.d >= 0 ? 'rgba(22,163,74,0.7)' : 'rgba(220,38,38,0.7)';
      ctx.fillRect(x, top, barW, Math.max(1, barH));
    }

    // Cumulative line
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const x = pad + i * ((w - pad * 2) / n) + barW / 2;
      const y = pad + ((maxCum - pts[i].cum) / range) * (h - pad * 2);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Labels
    ctx.fillStyle = '#525252';
    ctx.font = '9px ui-monospace, monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`CVD: ${data.current_delta ?? '—'}`, pad, 10);
    ctx.textAlign = 'right';
    ctx.fillText(`Peak: ${data.peak ?? '—'} / Trough: ${data.trough ?? '—'}`, w - pad, 10);
  }, [data]);

  return (
    <div style={{
      height: PANE_HEIGHT,
      borderTop: '1px solid #1a1a1a',
      background: '#0a0a0a',
      flexShrink: 0,
      position: 'relative',
    }}>
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: '100%', display: 'block' }}
      />
    </div>
  );
}
