'use client';
/**
 * OpeningTypeChip — compact chip showing current opening type classification.
 * Polls /api/v9/open_type/current at 15000ms (P30 floor).
 * Placed above S2 in the Switcher.
 */
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

interface OpenTypeData {
  opening_type: string | null;
  direction: string | null;
  confidence: number;
  status: string;
  bars_used?: number;
  reasoning?: string[];
}

const DIR_COLORS: Record<string, string> = {
  UP: '#16a34a',
  DOWN: '#dc2626',
  NEUTRAL: '#a1a1aa',
};

const POLL_MS = 15000;

export function OpeningTypeChip() {
  const [data, setData] = useState<OpenTypeData | null>(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch('/api/v9/open_type/current');
        if (!r.ok) return;
        const d = await r.json();
        if (alive) setData(d);
      } catch { /* fail-silent */ }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const type = data?.opening_type;
  const dir = data?.direction;
  const conf = data?.confidence;
  const status = data?.status;

  const isPending = !type || status === 'PENDING';
  const dirColor = dir ? (DIR_COLORS[dir] ?? COLORS.textTertiary) : COLORS.textTertiary;
  const label = isPending
    ? 'Opening — PENDING'
    : `${type?.replace(/^OPEN_/, '').replace(/_/g, ' ')} ${dir ?? ''}`;

  return (
    <div
      title={
        isPending
          ? 'סוג-פתיחה: ממתין לבר הראשון (16:35 IL)'
          : `Opening: ${type} · ${dir} · ${conf != null ? (conf * 100).toFixed(0) + '%' : '—'} · ${status}${data?.bars_used ? ` · ${data.bars_used} bars` : ''}`
      }
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 5,
        padding: '2px 6px',
        borderRadius: 4,
        fontSize: 8,
        fontFamily: 'ui-monospace',
        background: isPending ? COLORS.bgSurface5 : `${dirColor}14`,
        border: `1px solid ${isPending ? COLORS.borderFaint : `${dirColor}44`}`,
        color: isPending ? COLORS.textTertiary : '#e4e4e7',
      }}
    >
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: isPending ? '#525252' : dirColor,
        flexShrink: 0,
      }} />
      <span style={{ fontWeight: 600, color: isPending ? COLORS.textTertiary : dirColor }}>
        {label}
      </span>
      {!isPending && conf != null && (
        <span style={{ color: COLORS.textTertiary, fontSize: 7 }}>
          {(conf * 100).toFixed(0)}%
        </span>
      )}
      {status === 'LOCKED' && (
        <span style={{ color: '#a1a1aa', fontSize: 7 }}>🔒</span>
      )}
    </div>
  );
}
