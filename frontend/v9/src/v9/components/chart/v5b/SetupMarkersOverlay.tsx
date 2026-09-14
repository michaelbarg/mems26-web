'use client';
/**
 * T-320: Setup markers overlay on the main chart.
 * Hollow = armed, Filled = fired, ✕ = blocked.
 * Color by system (S2 cyan, S4 orange). Dashed border = shadow_only.
 * Tooltip shows time, pattern, direction, entry/stop/T1, blocked_by+reason.
 * Polls every 5000ms (CLAUDE.md floor).
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import type { IChartApi, ISeriesApi, SeriesMarker, Time } from 'lightweight-charts';
import { systemColor } from '../../../design/system_colors';

interface SetupMarker {
  ts: string | null;
  price: number | null;
  system: number | null;
  classification: string | null;
  direction: string | null;
  state: 'armed' | 'fired' | 'blocked';
  blocked_by: string | null;
  reason: string | null;
  stop: number | null;
  t1: number | null;
  t2: number | null;
  t3: number | null;
  shadow_only: boolean;
}

interface Props {
  chart: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const POLL_MS = 5000;

function markerShape(state: string): SeriesMarker<Time>['shape'] {
  if (state === 'blocked') return 'square'; // closest to ✕ in lightweight-charts
  if (state === 'fired') return 'circle';
  return 'circle'; // armed
}

function markerText(m: SetupMarker): string {
  if (m.state === 'blocked') return '✕';
  if (m.state === 'fired') return '●';
  return '○'; // armed (hollow)
}

function tooltipText(m: SetupMarker): string {
  const parts: string[] = [];
  if (m.ts) {
    try {
      const d = new Date(m.ts);
      parts.push(d.toLocaleTimeString('he-IL', { timeZone: 'Asia/Jerusalem', hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    } catch {
      parts.push(m.ts);
    }
  }
  if (m.classification) parts.push(m.classification);
  if (m.direction) parts.push(m.direction);
  if (m.price != null) parts.push(`entry=${m.price}`);
  if (m.stop != null) parts.push(`stop=${m.stop}`);
  if (m.t1 != null) parts.push(`T1=${m.t1}`);
  if (m.shadow_only) parts.push('[shadow]');
  if (m.blocked_by) parts.push(`blocked: ${m.blocked_by}`);
  if (m.reason) parts.push(m.reason);
  return parts.join(' · ');
}

export function SetupMarkersOverlay({ chart, candleSeries }: Props) {
  const [markers, setMarkers] = useState<SetupMarker[]>([]);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  // Poll the API
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Jerusalem' }).format(new Date());
        const res = await fetch(`${API}/api/v9/chart/setup_markers?session=${today}`);
        if (res.ok && alive) {
          const data: SetupMarker[] = await res.json();
          setMarkers(data);
        }
      } catch { /* ignore */ }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => { alive = false; clearInterval(id); };
  }, []);

  // Apply markers to the candle series
  useEffect(() => {
    if (!candleSeries || markers.length === 0) return;

    const lwMarkers: SeriesMarker<Time>[] = markers
      .filter((m) => m.ts && m.price != null)
      .map((m) => {
        const epoch = Math.floor(new Date(m.ts!).getTime() / 1000) as Time;
        const color = systemColor(m.system ?? 0);
        const isShadow = m.shadow_only;
        return {
          time: epoch,
          position: (m.direction === 'LONG' ? 'belowBar' : 'aboveBar') as 'belowBar' | 'aboveBar',
          color: isShadow ? `${color}88` : color, // semi-transparent for shadow
          shape: markerShape(m.state),
          text: markerText(m),
          size: 1,
        };
      })
      .sort((a, b) => (a.time as number) - (b.time as number));

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- setMarkers exists at runtime; types lag (same as TradeChart.tsx:133)
      (candleSeries as any).setMarkers(lwMarkers);
    } catch {
      // lightweight-charts may throw if series is disposed
    }

    return () => {
      try { (candleSeries as any).setMarkers([]); } catch { /* */ }
    };
  }, [candleSeries, markers]);

  // Crosshair move → tooltip
  useEffect(() => {
    if (!chart || markers.length === 0) return;

    const handler = (param: { time?: Time; point?: { x: number; y: number } }) => {
      if (!param.time || !param.point) {
        setTooltip(null);
        return;
      }
      const barTime = param.time as number;
      // Find markers at this bar time (within 300s = 5min bar)
      const hits = markers.filter((m) => {
        if (!m.ts) return false;
        const mTime = Math.floor(new Date(m.ts).getTime() / 1000);
        return Math.abs(mTime - barTime) < 300;
      });
      if (hits.length > 0) {
        const text = hits.map(tooltipText).join('\n');
        setTooltip({ x: param.point.x, y: param.point.y, text });
      } else {
        setTooltip(null);
      }
    };

    chart.subscribeCrosshairMove(handler);
    return () => { chart.unsubscribeCrosshairMove(handler); };
  }, [chart, markers]);

  return (
    <>
      {/* Legend */}
      <div style={{
        position: 'absolute', top: 4, right: 90, zIndex: 20,
        display: 'flex', gap: 8, fontSize: 9, fontFamily: 'ui-monospace, monospace',
        color: '#8b949e', background: '#0d111780', padding: '2px 6px', borderRadius: 3,
        pointerEvents: 'none',
      }}>
        <span>○ armed</span>
        <span>● fired</span>
        <span>✕ blocked</span>
        <span style={{ color: systemColor(2) }}>■ S2</span>
        <span style={{ color: systemColor(4) }}>■ S4</span>
        <span style={{ opacity: 0.5 }}>░ shadow</span>
      </div>
      {/* Tooltip */}
      {tooltip && (
        <div
          ref={tooltipRef}
          style={{
            position: 'absolute',
            left: Math.min(tooltip.x + 12, (typeof window !== 'undefined' ? window.innerWidth - 400 : 400)),
            top: tooltip.y + 12,
            zIndex: 30,
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: 4,
            padding: '4px 8px',
            fontSize: 10,
            fontFamily: 'ui-monospace, monospace',
            color: '#c9d1d9',
            whiteSpace: 'pre-wrap',
            maxWidth: 380,
            pointerEvents: 'none',
          }}
        >
          {tooltip.text}
        </div>
      )}
    </>
  );
}
