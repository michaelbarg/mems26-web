'use client';
import { useEffect, useState, useMemo } from 'react';
import { COLORS, SIZES } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Indicators {
  dayType: string | null;
  confidence: number;
  killzone: string | null;
  ibClass: string | null;
  openingType: string | null;
  cotTrend: 'UP' | 'DOWN' | 'FLAT' | null;
  pocMigration: string | null;
  dominance: string | null;
}

function Chip({ label, value, color }: { label: string; value: string | null; color: string }) {
  return (
    <span style={{
      fontSize: 9, fontWeight: 500, padding: '1px 6px', borderRadius: 3,
      background: 'rgba(255,255,255,0.04)', color,
    }}>
      {label} <b>{value ?? '\u2014'}</b>
    </span>
  );
}

export function Layer0Strip() {
  const [ind, setInd] = useState<Indicators>({
    dayType: null, confidence: 0, killzone: null, ibClass: null,
    openingType: null, cotTrend: null, pocMigration: null, dominance: null,
  });
  const [prevDelta, setPrevDelta] = useState<number | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const [dt, kz, tpo, fp] = await Promise.allSettled([
          fetch(`${API}/api/v9/day_type/current`).then(r => r.json()),
          fetch(`${API}/api/v9/killzone/current`).then(r => r.json()),
          fetch(`${API}/api/v9/tpo/current`).then(r => r.json()),
          fetch(`${API}/api/v9/footprint/current`).then(r => r.json()),
        ]);
        const dtD = dt.status === 'fulfilled' ? dt.value : {};
        const kzD = kz.status === 'fulfilled' ? kz.value : {};
        const tpoD = tpo.status === 'fulfilled' ? tpo.value : {};
        const fpD = fp.status === 'fulfilled' ? fp.value : {};

        // COT Trend: derive from cumulative_delta change
        const currentDelta = fpD.cumulative_delta ?? 0;
        let cotTrend: 'UP' | 'DOWN' | 'FLAT' | null = null;
        if (prevDelta != null) {
          const diff = currentDelta - prevDelta;
          cotTrend = diff > 5 ? 'UP' : diff < -5 ? 'DOWN' : 'FLAT';
        }
        setPrevDelta(currentDelta);

        setInd({
          dayType: dtD.day_type?.replace('_', ' ') ?? dtD.state?.day_type?.replace('_', ' ') ?? null,
          confidence: dtD.confidence ?? dtD.state?.confidence ?? 0,
          killzone: kzD.current_zone?.name ?? null,
          ibClass: tpoD.ib_class ?? null,
          openingType: tpoD.opening_type ?? null,
          cotTrend,
          pocMigration: tpoD.poc_migration?.direction ?? tpoD.poc_migration ?? null,
          dominance: fpD.dominance ?? null,
        });
      } catch { /* silent */ }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, [prevDelta]);

  const cotColor = ind.cotTrend === 'UP' ? '#16a34a' : ind.cotTrend === 'DOWN' ? '#dc2626' : '#737373';

  return (
    <div
      id="layer0-strip"
      style={{
        height: SIZES.layer0Height,
        background: COLORS.bgSurface2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingLeft: 12,
        paddingRight: 12,
        gap: 8,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        flexShrink: 0,
      }}
    >
      {/* 7 indicators left-aligned */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Chip label="Day" value={ind.dayType} color={systemColor(1)} />
        {ind.confidence > 0 && (
          <span style={{ fontSize: 8, color: COLORS.textTertiary }}>{(ind.confidence * 100).toFixed(0)}%</span>
        )}
        <Chip label="KZ" value={ind.killzone} color={systemColor(6) || '#f97316'} />
        <Chip label="IB" value={ind.ibClass} color="#4ade80" />
        <Chip label="Open" value={ind.openingType} color="#a78bfa" />
        <Chip label="COT" value={ind.cotTrend} color={cotColor} />
        <Chip label="POC" value={ind.pocMigration} color="#ec4899" />
        <Chip label="Dom" value={ind.dominance} color="#06b6d4" />
      </div>

      {/* News window (right side — placeholder) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ fontSize: 9, color: '#525252', fontFamily: 'ui-monospace, monospace' }}>
          News —
        </span>
      </div>
    </div>
  );
}
