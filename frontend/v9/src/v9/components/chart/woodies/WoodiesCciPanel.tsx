'use client';

import { useEffect, useRef, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const PANEL_W = 400;
const PANEL_H = 200;
const CCI_MIN = -240;
const CCI_MAX = 240;
const REF_LINES = [
  { v: 200, color: '#DC2020' },
  { v: 100, color: '#22BBBB' },
  { v: 0, color: '#22CC22' },
  { v: -100, color: '#22BBBB' },
  { v: -200, color: '#DC2020' },
];

export type WoodiesChartBar = {
  ts_unix: number;
  cci_14: number;
  cci_6_tcci?: number | null;
  trend_state: string;
  trend_color: string;
  zlr_detected?: boolean;
};

function yForCci(v: number, top: number, h: number): number {
  const t = (CCI_MAX - v) / (CCI_MAX - CCI_MIN);
  return top + t * h;
}

export function WoodiesCciPanel({ visible }: { visible: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [bars, setBars] = useState<WoodiesChartBar[]>([]);
  const [titleCci, setTitleCci] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/v9/woodies/chart?limit=30`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = await r.json();
        if (d.error && !d.bars?.length) {
          setError(d.error);
          setBars([]);
          return;
        }
        setError(null);
        const list = (d.bars || []) as WoodiesChartBar[];
        setBars(list);
        const cur = d.current_bar || list[list.length - 1];
        setTitleCci(cur?.cci_14 ?? null);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'fetch failed');
      }
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [visible]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !visible) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = PANEL_W * dpr;
    canvas.height = PANEL_H * dpr;
    canvas.style.width = `${PANEL_W}px`;
    canvas.style.height = `${PANEL_H}px`;
    ctx.scale(dpr, dpr);

    const padL = 28;
    const padR = 36;
    const padT = 22;
    const padB = 18;
    const chartW = PANEL_W - padL - padR;
    const chartH = PANEL_H - padT - padB;

    ctx.fillStyle = '#2D5555';
    ctx.fillRect(0, 0, PANEL_W, PANEL_H);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 11px ui-monospace, monospace';
    const cciLabel = titleCci != null ? `[CCI:${titleCci.toFixed(2)}]` : '[CCI:—]';
    ctx.fillText(`Woodies CCI Trend ${cciLabel}`, 8, 14);

    if (error) {
      ctx.fillStyle = '#f97316';
      ctx.font = '10px ui-monospace, monospace';
      ctx.fillText(error.slice(0, 48), 8, PANEL_H - 8);
      return;
    }

    for (const ref of REF_LINES) {
      const y = yForCci(ref.v, padT, chartH);
      ctx.strokeStyle = ref.color;
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 4]);
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(padL + chartW, y);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    const n = bars.length;
    if (n === 0) return;
    const slotW = chartW / n;

    bars.forEach((bar, i) => {
      const cx = padL + i * slotW + slotW / 2;
      const y0 = yForCci(0, padT, chartH);
      const y1 = yForCci(bar.cci_14, padT, chartH);
      const h = Math.max(2, Math.abs(y1 - y0));
      const y = Math.min(y0, y1);
      ctx.fillStyle = bar.trend_color;
      ctx.fillRect(cx - 3, y, 6, h);
      if (bar.zlr_detected) {
        ctx.fillStyle = bar.cci_14 >= 0 ? '#E03030' : '#22CC22';
        ctx.font = 'bold 8px ui-monospace';
        ctx.fillText('Z', cx - 3, y - 4);
      }
    });

    ctx.lineWidth = 2;
    ctx.strokeStyle = '#000000';
    ctx.beginPath();
    bars.forEach((bar, i) => {
      const x = padL + i * slotW + slotW / 2;
      const y = yForCci(bar.cci_14, padT, chartH);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.strokeStyle = '#DDDD20';
    ctx.beginPath();
    bars.forEach((bar, i) => {
      if (bar.cci_6_tcci == null) return;
      const x = padL + i * slotW + slotW / 2;
      const y = yForCci(bar.cci_6_tcci, padT, chartH);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.fillStyle = '#5EB8FF';
    ctx.font = '9px ui-monospace, monospace';
    for (const v of [200, 0, -200]) {
      const y = yForCci(v, padT, chartH);
      ctx.fillText(String(v), PANEL_W - padR + 4, y + 3);
    }
  }, [bars, titleCci, error, visible]);

  if (!visible) return null;

  return (
    <div
      data-testid="woodies-cci-panel"
      style={{
        position: 'absolute',
        left: 8,
        bottom: 8,
        zIndex: 15,
        borderRadius: 4,
        border: '1px solid #1A3A3A',
        boxShadow: '0 4px 12px rgba(0,0,0,0.45)',
        pointerEvents: 'none',
      }}
    >
      <canvas ref={canvasRef} />
    </div>
  );
}
