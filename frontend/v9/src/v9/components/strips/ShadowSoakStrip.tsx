'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ShadowEvent {
  ts: string;
  system: 'sys1' | 'sys2' | 'sys4';
  details?: string;
}

const SYS_MARKERS: Record<string, { shape: string; color: string }> = {
  sys1: { shape: '\u25C6', color: '#6366f1' },  // indigo diamond
  sys2: { shape: '\u25A0', color: '#06b6d4' },  // cyan square
  sys4: { shape: '\u25CF', color: '#f97316' },  // orange circle
};

export function ShadowSoakStrip() {
  const [mode, setMode] = useState<string>('');
  const [events, setEvents] = useState<ShadowEvent[]>([]);

  // Check mode
  useEffect(() => {
    fetch(`${API}/api/v9/status`)
      .then(r => r.json())
      .then(d => setMode(d?.mode || d?.trading_mode || ''))
      .catch(() => {});
  }, []);

  // Fetch shadow events
  useEffect(() => {
    if (mode !== 'SHADOW') return;
    fetch(`${API}/api/v9/shadow/events`)
      .then(r => r.json())
      .then(d => { if (Array.isArray(d)) setEvents(d); })
      .catch(() => {}); // endpoint may not exist yet
  }, [mode]);

  // Only render in SHADOW mode
  if (mode !== 'SHADOW') return null;

  return (
    <div style={{
      height: 22, background: COLORS.bgSurface2 || '#111111',
      borderTop: `1px solid ${COLORS.borderFaint}`,
      display: 'flex', alignItems: 'center', paddingLeft: 8,
      overflow: 'hidden',
    }}>
      {events.length === 0 ? (
        <span style={{ fontSize: 9, color: '#525252', fontFamily: 'ui-monospace, monospace' }}>
          SHADOW — no setups detected
        </span>
      ) : (
        events.map((e, i) => {
          const m = SYS_MARKERS[e.system] || { shape: '?', color: '#737373' };
          return (
            <span key={i} title={`${e.system} @ ${e.ts} — ${e.details || ''}`}
              style={{ fontSize: 10, color: m.color, marginRight: 4, cursor: 'default' }}>
              {m.shape}
            </span>
          );
        })
      )}
    </div>
  );
}
