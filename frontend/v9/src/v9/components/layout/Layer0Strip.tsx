'use client';
import { useEffect, useState } from 'react';
import { COLORS, SIZES } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function Layer0Strip() {
  const [dayType, setDayType] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number>(0);
  const color = systemColor(1);

  useEffect(() => {
    const poll = () => {
      fetch(`${API_BASE}/api/v9/day_type/current`)
        .then((r) => r.json())
        .then((d) => {
          setDayType(d.day_type?.replace('_', ' ') ?? null);
          setConfidence(d.confidence ?? 0);
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
        gap: 8,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        flexShrink: 0,
      }}
    >
      <span style={{ fontSize: 9, fontWeight: 600, color }}>
        Day {dayType ?? '...'}
      </span>
      {confidence > 0 && (
        <span style={{ fontSize: 8, color: COLORS.textTertiary }}>
          {(confidence * 100).toFixed(0)}%
        </span>
      )}
    </div>
  );
}
