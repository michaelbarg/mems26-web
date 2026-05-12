'use client';
import { useEffect, useState } from 'react';
import { COLORS, SIZES } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function Layer0Strip() {
  const [dayType, setDayType] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number>(0);
  const [fiveMinMode, setFiveMinMode] = useState<string | null>(null);
  const dtColor = systemColor(1);
  const fmColor = systemColor(2);

  useEffect(() => {
    const poll = () => {
      fetch(`${API_BASE}/api/v9/day_type/current`)
        .then((r) => r.json())
        .then((d) => {
          setDayType(d.day_type?.replace('_', ' ') ?? null);
          setConfidence(d.confidence ?? 0);
        })
        .catch(() => {});
      fetch(`${API_BASE}/api/v9/five_min/current`)
        .then((r) => r.json())
        .then((d) => {
          const mode = d.mode ?? null;
          if (mode === 'FIRST_HOUR_TACTICAL') setFiveMinMode('FH-TACT');
          else if (mode === 'DAY_TYPE_MODE') setFiveMinMode('DT-MODE');
          else if (mode === 'OVERNIGHT_MODE') setFiveMinMode('OVERNIGHT');
          else if (mode === 'WEEKEND') setFiveMinMode('WEEKEND');
          else if (mode === 'MAINTENANCE') setFiveMinMode('MAINT');
          else if (mode === 'MARKET_CLOSED') setFiveMinMode('CLOSED');
          else setFiveMinMode(mode);
        })
        .catch(() => {});
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      id="layer0-strip"
      style={{
        height: SIZES.layer0Height,
        background: COLORS.bgSurface2,
        display: 'flex',
        alignItems: 'center',
        paddingLeft: 12,
        gap: 12,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        flexShrink: 0,
      }}
    >
      <span style={{ fontSize: 9, fontWeight: 600, color: dtColor }}>
        Day {dayType ?? '...'}
      </span>
      {confidence > 0 && (
        <span style={{ fontSize: 8, color: COLORS.textTertiary }}>
          {(confidence * 100).toFixed(0)}%
        </span>
      )}
      <span style={{ color: COLORS.borderPrimary, fontSize: 9 }}>|</span>
      <span style={{ fontSize: 9, fontWeight: 600, color: fmColor }}>
        5min {fiveMinMode ?? '...'}
      </span>
    </div>
  );
}
