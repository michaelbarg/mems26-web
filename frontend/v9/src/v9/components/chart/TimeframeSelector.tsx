'use client';
import { useState } from 'react';

const TIMEFRAMES = [
  { label: '1m', value: '1min' },
  { label: '5m', value: '5min', default: true },
  { label: '15m', value: '15min' },
  { label: '1H', value: '1hour' },
  { label: 'D', value: 'daily' },
];

const FILTERS = [
  { label: 'Live', value: 'live', default: true },
  { label: 'Replay', value: 'replay' },
];

const SESSION_FILTERS = [
  { label: 'RTH', value: 'rth' },
  { label: '24h', value: '24h', default: true },
];

interface Props {
  onTimeframeChange?: (tf: string) => void;
  onFilterChange?: (filter: string) => void;
  onSessionChange?: (session: string) => void;
}

export function TimeframeSelector({ onTimeframeChange, onFilterChange, onSessionChange }: Props) {
  const [tf, setTf] = useState('5min');
  const [filter, setFilter] = useState('live');
  const [session, setSession] = useState('24h');

  const btnStyle = (active: boolean) => ({
    fontSize: 9, padding: '2px 6px', borderRadius: 3, cursor: 'pointer',
    border: 'none',
    background: active ? 'rgba(255,255,255,0.12)' : 'transparent',
    color: active ? '#e5e5e5' : '#525252',
  });

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '2px 4px' }}>
      {/* Timeframes */}
      <div style={{ display: 'flex', gap: 2 }}>
        {TIMEFRAMES.map(t => (
          <button key={t.value} style={btnStyle(tf === t.value)}
            onClick={() => { setTf(t.value); onTimeframeChange?.(t.value); }}>
            {t.label}
          </button>
        ))}
      </div>

      <span style={{ color: '#333', fontSize: 9 }}>|</span>

      {/* Live / Replay */}
      <div style={{ display: 'flex', gap: 2 }}>
        {FILTERS.map(f => (
          <button key={f.value} style={btnStyle(filter === f.value)}
            onClick={() => { setFilter(f.value); onFilterChange?.(f.value); }}>
            {f.label}
          </button>
        ))}
      </div>

      <span style={{ color: '#333', fontSize: 9 }}>|</span>

      {/* RTH / 24h */}
      <div style={{ display: 'flex', gap: 2 }}>
        {SESSION_FILTERS.map(s => (
          <button key={s.value} style={btnStyle(session === s.value)}
            onClick={() => { setSession(s.value); onSessionChange?.(s.value); }}>
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
