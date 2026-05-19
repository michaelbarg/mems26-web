'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BG = '#2D5555';
const BORDER = '#1A3A3A';
const CCI_MIN = -240;
const CCI_MAX = 240;
const AXIS_VALUES = [240, 200, 160, 120, 80, 40, 0, -40, -80, -120, -160, -200, -240];
const REF_LINES = [
  { v: 200, color: '#DC2020' },
  { v: 100, color: '#22BBBB' },
  { v: 0, color: '#22CC22' },
  { v: -100, color: '#22BBBB' },
  { v: -200, color: '#DC2020' },
];
const LS_W = 'mems26-woodies-panel-w';
const LS_H = 'mems26-woodies-panel-h';
const LS_DATA = 'mems26-woodies-panel-data-w';

export type WoodiesChartBar = {
  ts_unix: number;
  cci_14: number;
  cci_14_prev?: number | null;
  cci_6_tcci?: number | null;
  trend_state: string;
  trend_color: string;
  zlr_detected?: boolean;
  zlr_direction?: string;
  hfe_detected?: boolean;
  close?: number | null;
  high?: number | null;
  low?: number | null;
  lsma_value?: number | null;
  predictor_next_cci?: number | null;
};

function loadNum(key: string, fallback: number, min: number, max: number): number {
  if (typeof window === 'undefined') return fallback;
  const v = Number(localStorage.getItem(key));
  if (!Number.isFinite(v)) return fallback;
  return Math.min(max, Math.max(min, v));
}

function yForCci(v: number, top: number, h: number): number {
  const t = (CCI_MAX - v) / (CCI_MAX - CCI_MIN);
  return top + t * h;
}

function formatEtTime(tsUnix: number): string {
  return new Date(tsUnix * 1000).toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: '2-digit',
    hour12: false,
  });
}

function formatEtDate(tsUnix: number): string {
  const d = new Date(tsUnix * 1000);
  return d.toLocaleDateString('en-US', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  });
}

function trendCounts(bars: WoodiesChartBar[]): { up: number; down: number; neutral: number } {
  let up = 0;
  let down = 0;
  let neutral = 0;
  for (const b of bars) {
    const s = (b.trend_state || '').toUpperCase();
    if (s === 'BLUE') up += 1;
    else if (s === 'RED') down += 1;
    else neutral += 1;
  }
  return { up, down, neutral };
}

function drawChart(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  bars: WoodiesChartBar[],
) {
  const padL = 8;
  const padR = 4;
  const padT = 4;
  const padB = 4;
  const chartW = w - padL - padR;
  const chartH = h - padT - padB;

  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, w, h);

  for (const ref of REF_LINES) {
    const y = yForCci(ref.v, padT, chartH);
    ctx.strokeStyle = ref.color;
    ctx.lineWidth = 3.5;
    ctx.setLineDash([0.5, 7]);
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(padL + chartW, y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = ref.v === 0 || ref.v === 200 || ref.v === -200 ? ref.color : '#22BBBB';
    ctx.beginPath();
    ctx.arc(padL + 2, y, 2.2, 0, Math.PI * 2);
    ctx.fill();
  }

  const n = bars.length;
  if (n === 0) return;
  const slotW = chartW / n;

  bars.forEach((bar, i) => {
    const cx = padL + i * slotW + slotW / 2;
    const y0 = yForCci(0, padT, chartH);
    const y1 = yForCci(bar.cci_14, padT, chartH);
    const bh = Math.max(2, Math.abs(y1 - y0));
    const by = Math.min(y0, y1);
    ctx.fillStyle = bar.trend_color;
    ctx.fillRect(cx - 3, by, 6, bh);
    if (bar.zlr_detected) {
      ctx.fillStyle = bar.cci_14 >= 0 ? '#E03030' : '#22CC22';
      ctx.font = 'bold 9px ui-monospace, monospace';
      ctx.fillText('ZLR', cx - 10, bar.cci_14 >= 0 ? padT + 10 : padT + chartH - 4);
    }
    if (bar.hfe_detected && i === n - 1) {
      ctx.fillStyle = '#ffffff';
      ctx.font = '12px sans-serif';
      ctx.fillText('✦', cx - 4, y1 - 6);
    }
  });

  ctx.lineWidth = 2.5;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
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
  let started = false;
  bars.forEach((bar, i) => {
    if (bar.cci_6_tcci == null) return;
    const x = padL + i * slotW + slotW / 2;
    const y = yForCci(bar.cci_6_tcci, padT, chartH);
    if (!started) {
      ctx.moveTo(x, y);
      started = true;
    } else ctx.lineTo(x, y);
  });
  if (started) ctx.stroke();

  const last = bars[n - 1];
  const lx = padL + (n - 1) * slotW + slotW / 2;
  const ly = yForCci(last.cci_14, padT, chartH);
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(lx, padT);
  ctx.lineTo(lx, padT + chartH);
  ctx.stroke();
}

function DataColumn({ bar, width }: { bar: WoodiesChartBar | null; width: number }) {
  if (!bar) {
    return (
      <div
        style={{
          width,
          flexShrink: 0,
          borderLeft: `1px solid ${BORDER}`,
          padding: '4px 6px',
          fontSize: 9,
          fontFamily: 'ui-monospace, monospace',
          color: '#7A8080',
        }}
      >
        —
      </div>
    );
  }
  const diff =
    bar.cci_14_prev != null ? bar.cci_14 - bar.cci_14_prev : null;
  const row = (text: string, color: string, bold = false) => (
    <div
      key={`${text}-${color}`}
      style={{
        textAlign: 'right',
        color,
        fontWeight: bold ? 700 : 400,
        fontSize: bold ? 11 : 9,
        lineHeight: 1.35,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
      }}
    >
      {text}
    </div>
  );
  return (
    <div
      style={{
        width,
        flexShrink: 0,
        borderLeft: `1px solid ${BORDER}`,
        padding: '4px 6px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-start',
        gap: 1,
        fontFamily: 'ui-monospace, monospace',
      }}
    >
      {diff != null && row(`${diff.toFixed(2)} CCIDiff`, '#00DD00')}
      {diff != null && row(`${diff.toFixed(2)} CCIDiff`, '#FFFFFF')}
      {bar.close != null && row(`${bar.close.toFixed(2)} L`, '#000000', true)}
      {bar.high != null && bar.low != null && row(`${bar.high.toFixed(2)} H`, '#000000')}
      {bar.high != null && bar.low != null && row(`${bar.low.toFixed(2)} L`, '#000000')}
      {bar.predictor_next_cci != null &&
        row(`${bar.predictor_next_cci.toFixed(1)} Proj`, '#5EB8FF')}
      {row(`${bar.cci_14.toFixed(1)} CC`, '#000000')}
      {bar.lsma_value != null && row(`${bar.lsma_value.toFixed(2)} LSMA`, '#888888')}
    </div>
  );
}

function AxisColumn() {
  return (
    <div
      style={{
        width: 44,
        flexShrink: 0,
        borderLeft: `1px solid ${BORDER}`,
        padding: '4px 4px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        fontFamily: 'ui-monospace, monospace',
        fontSize: 10,
        fontWeight: 700,
      }}
    >
      {AXIS_VALUES.map((v) => {
        let color = '#5EB8FF';
        if (v === 200 || v === -200) color = '#FF2020';
        if (v === 0) color = '#22CC22';
        return (
          <div key={v} style={{ textAlign: 'right', color, lineHeight: 1 }}>
            {v}
          </div>
        );
      })}
    </div>
  );
}

function TimeAxis({ bars }: { bars: WoodiesChartBar[] }) {
  if (bars.length === 0) return null;
  const first = bars[0];
  const ticks: { label: string; key: string }[] = [
    { label: formatEtDate(first.ts_unix), key: 'date' },
  ];
  const n = bars.length;
  const step = Math.max(1, Math.floor(n / 8));
  for (let i = 0; i < n; i += step) {
    ticks.push({ label: formatEtTime(bars[i].ts_unix), key: `t-${i}` });
  }
  const last = bars[n - 1];
  if ((n - 1) % step !== 0) {
    ticks.push({ label: formatEtTime(last.ts_unix), key: 't-last' });
  }
  return (
    <div
      style={{
        height: 18,
        background: '#2A4A4A',
        borderTop: `1px solid ${BORDER}`,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '0 8px',
        overflow: 'hidden',
        fontFamily: 'ui-monospace, monospace',
        fontSize: 10,
        fontWeight: 700,
        color: '#DDDD20',
      }}
    >
      {ticks.map((t) => (
        <span key={t.key} style={{ flexShrink: 0 }}>
          {t.label}
        </span>
      ))}
    </div>
  );
}

/** Sierra §5.3 Woodies CCI panel — live table layout, resizable data/price column + panel size. */
export function WoodiesCciPanel({ visible }: { visible: boolean }) {
  const [panelW, setPanelW] = useState(() => loadNum(LS_W, 480, 320, 720));
  const [panelH, setPanelH] = useState(() => loadNum(LS_H, 360, 220, 520));
  const [dataColW, setDataColW] = useState(() => loadNum(LS_DATA, 132, 88, 220));
  const [bars, setBars] = useState<WoodiesChartBar[]>([]);
  const [current, setCurrent] = useState<WoodiesChartBar | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ageS, setAgeS] = useState<number | null>(null);
  const chartHostRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dragRef = useRef<'corner' | 'data' | null>(null);
  const dragStart = useRef({ x: 0, y: 0, w: 0, h: 0, dataW: 0 });

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v9/woodies/chart?limit=50`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      if (d.error && !d.bars?.length) {
        setError(d.error);
        setBars([]);
        return;
      }
      setError(d.stale ? d.error || 'stale export' : null);
      setAgeS(typeof d.age_s === 'number' ? d.age_s : null);
      const list = (d.bars || []) as WoodiesChartBar[];
      setBars(list);
      setCurrent((d.current_bar as WoodiesChartBar) || list[list.length - 1] || null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'fetch failed');
    }
  }, []);

  useEffect(() => {
    if (!visible) return;
    load();
    const id = setInterval(load, 2000);
    return () => clearInterval(id);
  }, [visible, load]);

  useEffect(() => {
    if (!visible) return;
    localStorage.setItem(LS_W, String(panelW));
    localStorage.setItem(LS_H, String(panelH));
    localStorage.setItem(LS_DATA, String(dataColW));
  }, [panelW, panelH, dataColW, visible]);

  useEffect(() => {
    const host = chartHostRef.current;
    const canvas = canvasRef.current;
    if (!host || !canvas || !visible) return;

    const paint = () => {
      const rect = host.getBoundingClientRect();
      const w = Math.max(80, Math.floor(rect.width));
      const h = Math.max(60, Math.floor(rect.height));
      const dpr = window.devicePixelRatio || 1;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawChart(ctx, w, h, bars);
    };

    paint();
    const ro = new ResizeObserver(paint);
    ro.observe(host);
    return () => ro.disconnect();
  }, [bars, visible]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      if (dragRef.current === 'corner') {
        setPanelW(Math.min(720, Math.max(320, dragStart.current.w + dx)));
        setPanelH(Math.min(520, Math.max(220, dragStart.current.h - dy)));
      } else if (dragRef.current === 'data') {
        setDataColW(Math.min(220, Math.max(88, dragStart.current.dataW - dx)));
      }
    };
    const onUp = () => {
      dragRef.current = null;
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  if (!visible) return null;

  const counts = trendCounts(bars);
  const cci = current?.cci_14;

  return (
    <div
      data-testid="woodies-cci-panel"
      style={{
        position: 'absolute',
        left: 8,
        bottom: 8,
        zIndex: 15,
        width: panelW,
        height: panelH,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 4,
        border: `1px solid ${BORDER}`,
        boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
        background: BG,
        overflow: 'hidden',
        pointerEvents: 'auto',
        userSelect: 'none',
      }}
    >
      <div
        style={{
          height: 22,
          flexShrink: 0,
          padding: '0 8px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          fontFamily: 'ui-monospace, monospace',
          fontSize: 11,
          fontWeight: 700,
          color: '#fff',
          borderBottom: `1px solid ${BORDER}`,
        }}
      >
        <span>Woodies CCI Trend</span>
        <span style={{ color: '#7A8080' }}>
          [CCI:{cci != null ? cci.toFixed(2) : '—'}]
        </span>
        <span style={{ color: '#B33B3B' }}>TrendDown:{counts.down.toFixed(2)}</span>
        <span style={{ color: '#B0A030' }}>TrendNeutral:{counts.neutral.toFixed(2)}</span>
        <span style={{ color: '#5588FF' }}>TrendUp:{counts.up.toFixed(2)}</span>
        {ageS != null && (
          <span style={{ marginLeft: 'auto', color: '#7A8080', fontSize: 9 }}>
            {ageS.toFixed(0)}s
          </span>
        )}
      </div>

      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <div ref={chartHostRef} style={{ flex: 1, minWidth: 100, position: 'relative' }}>
          <canvas ref={canvasRef} style={{ display: 'block' }} />
          {error && (
            <div
              style={{
                position: 'absolute',
                left: 8,
                bottom: 4,
                fontSize: 9,
                color: '#f97316',
                fontFamily: 'ui-monospace, monospace',
              }}
            >
              {error.slice(0, 40)}
            </div>
          )}
        </div>

        <div
          role="separator"
          title="גרור לשינוי רוחב עמודת מחיר/נתונים"
          onMouseDown={(e) => {
            e.preventDefault();
            dragRef.current = 'data';
            dragStart.current = {
              x: e.clientX,
              y: e.clientY,
              w: panelW,
              h: panelH,
              dataW: dataColW,
            };
          }}
          style={{
            width: 5,
            flexShrink: 0,
            cursor: 'col-resize',
            background: BORDER,
          }}
        />

        <DataColumn bar={current} width={dataColW} />
        <AxisColumn />
      </div>

      <TimeAxis bars={bars} />

      <div
        style={{
          position: 'absolute',
          right: 2,
          bottom: 20,
          width: 14,
          height: 14,
          cursor: 'nwse-resize',
          background: 'transparent',
        }}
        title="גרור לשינוי גודל הפאנל"
        onMouseDown={(e) => {
          e.preventDefault();
          dragRef.current = 'corner';
          dragStart.current = {
            x: e.clientX,
            y: e.clientY,
            w: panelW,
            h: panelH,
            dataW: dataColW,
          };
        }}
      />

      <div
        style={{
          position: 'absolute',
          right: 6,
          bottom: 22,
          background: '#22CC22',
          color: '#fff',
          fontSize: 10,
          fontWeight: 700,
          padding: '2px 6px',
          borderRadius: 2,
          fontFamily: 'ui-monospace, monospace',
        }}
      >
        9LE
      </div>
    </div>
  );
}
