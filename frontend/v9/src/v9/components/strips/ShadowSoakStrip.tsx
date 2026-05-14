'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SoakProgress {
  day: number;
  total_days: number;
  wr_7d: number | null;
  wr_30d: number | null;
  trades_today: number;
}

export function ShadowSoakStrip() {
  const [mode, setMode] = useState<string>('');
  const [soak, setSoak] = useState<SoakProgress | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v9/status`)
      .then(r => r.json())
      .then(d => setMode(d?.mode || d?.trading_mode || ''))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (mode !== 'SHADOW') return;
    const fetchSoak = () => {
      fetch(`${API}/api/v9/shadow/soak_progress`)
        .then(r => r.json())
        .then(d => setSoak({
          day: d?.day ?? 1,
          total_days: d?.total_days ?? 30,
          wr_7d: d?.wr_7d ?? null,
          wr_30d: d?.wr_30d ?? null,
          trades_today: d?.trades_today ?? 0,
        }))
        .catch(() => setSoak({ day: 1, total_days: 30, wr_7d: null, wr_30d: null, trades_today: 0 }));
    };
    fetchSoak();
    const id = setInterval(fetchSoak, 60000);
    return () => clearInterval(id);
  }, [mode]);

  if (mode !== 'SHADOW') return null;

  const day = soak?.day ?? 1;
  const total = soak?.total_days ?? 30;
  const pct = Math.min(100, (day / total) * 100);

  return (
    <div style={{
      height: 22, background: COLORS.bgSurface2 || '#111111',
      borderTop: `1px solid ${COLORS.borderFaint}`,
      display: 'flex', alignItems: 'center', paddingLeft: 8, gap: 8,
      overflow: 'hidden',
    }}>
      {/* Day X/30 label */}
      <span style={{ fontSize: 9, color: '#facc15', fontFamily: 'ui-monospace, monospace', fontWeight: 600, flexShrink: 0 }}>
        Day {day}/{total}
      </span>

      {/* Progress bar */}
      <div style={{ flex: 1, maxWidth: 120, height: 6, background: '#1a1a1a', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: '#facc15', borderRadius: 3, transition: 'width 0.5s' }} />
      </div>

      {/* WR indicators */}
      {soak?.wr_7d != null && (
        <span style={{ fontSize: 8, color: soak.wr_7d >= 50 ? '#16a34a' : '#dc2626', fontFamily: 'ui-monospace, monospace' }}>
          7d:{soak.wr_7d.toFixed(0)}%
        </span>
      )}
      {soak?.wr_30d != null && (
        <span style={{ fontSize: 8, color: soak.wr_30d >= 50 ? '#16a34a' : '#dc2626', fontFamily: 'ui-monospace, monospace' }}>
          30d:{soak.wr_30d.toFixed(0)}%
        </span>
      )}

      {/* Trades today count */}
      <span style={{ fontSize: 8, color: '#525252', fontFamily: 'ui-monospace, monospace' }}>
        {soak?.trades_today ?? 0} trades
      </span>
    </div>
  );
}
