'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface TradeEvent {
  ts: string;
  type: 'LONG_ENTRY' | 'SHORT_ENTRY' | 'STOP_HIT' | 'TARGET_HIT';
  price: number;
  details?: string;
}

export function TradeHistoryStrip() {
  const [trades, setTrades] = useState<TradeEvent[]>([]);

  useEffect(() => {
    fetch(`${API}/api/v9/trades/recent`)
      .then(r => r.json())
      .then(d => { if (Array.isArray(d)) setTrades(d); })
      .catch(() => {}); // endpoint may not exist yet
  }, []);

  const markers: Record<string, { symbol: string; color: string }> = {
    LONG_ENTRY: { symbol: '\u25B2', color: '#16a34a' },   // green ▲
    SHORT_ENTRY: { symbol: '\u25BC', color: '#dc2626' },   // red ▼
    STOP_HIT: { symbol: '\u2716', color: '#dc2626' },      // red ✖
    TARGET_HIT: { symbol: '\u2713', color: '#16a34a' },    // green ✓
  };

  return (
    <div style={{
      height: 14, background: COLORS.bgSurface2 || '#111111',
      borderTop: `1px solid ${COLORS.borderFaint}`,
      display: 'flex', alignItems: 'center', paddingLeft: 8,
      overflow: 'hidden',
    }}>
      {trades.length === 0 ? (
        <span style={{ fontSize: 9, color: '#525252', fontFamily: 'ui-monospace, monospace' }}>
          No trades yet
        </span>
      ) : (
        trades.map((t, i) => {
          const m = markers[t.type] || { symbol: '?', color: '#737373' };
          return (
            <span key={i} title={`${t.type} @ ${t.price} — ${t.ts}`}
              style={{ fontSize: 9, color: m.color, marginRight: 4, cursor: 'default' }}>
              {m.symbol}
            </span>
          );
        })
      )}
    </div>
  );
}
