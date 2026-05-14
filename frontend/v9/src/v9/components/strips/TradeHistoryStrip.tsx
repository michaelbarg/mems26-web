'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface TradeSummary {
  id: number;
  direction: string;
  entry_ts: string;
  exit_ts: string | null;
  pnl: number | null;
  outcome: string; // WIN / LOSS / BE / OPEN
}

export function TradeHistoryStrip() {
  const [trades, setTrades] = useState<TradeSummary[]>([]);

  useEffect(() => {
    const fetchTrades = () => {
      fetch(`${API}/api/v9/trades/recent`)
        .then(r => r.json())
        .then(d => {
          if (Array.isArray(d)) {
            setTrades(d.map((t: any) => ({
              id: t.id ?? 0,
              direction: t.direction ?? 'LONG',
              entry_ts: t.entry_ts ?? t.ts ?? '',
              exit_ts: t.exit_ts ?? null,
              pnl: t.pnl ?? t.realized_pnl ?? null,
              outcome: t.pnl > 0 ? 'WIN' : t.pnl < 0 ? 'LOSS' : t.pnl === 0 ? 'BE' : 'OPEN',
            })));
          }
        })
        .catch(() => {});
    };
    fetchTrades();
    const id = setInterval(fetchTrades, 10000);
    return () => clearInterval(id);
  }, []);

  // V5 V1.1 trade colors + opacity
  const segmentStyle = (outcome: string) => {
    if (outcome === 'WIN') return { color: '#16a34a', opacity: 0.75 };
    if (outcome === 'LOSS') return { color: '#dc2626', opacity: 0.5 };
    if (outcome === 'BE') return { color: '#facc15', opacity: 0.6 };
    if (outcome === 'TO') return { color: '#404040', opacity: 0.7 };  // timeout
    if (outcome === 'OPEN') return { color: '#06b6d4', opacity: 0.8 };
    return { color: '#525252', opacity: 0.5 };
  };

  return (
    <div data-testid="strip-trade-history" style={{
      height: 18, minHeight: 18, flexShrink: 0, background: '#0a0a0a',
      borderTop: `1px solid ${COLORS.borderFaint}`,
      display: 'flex', alignItems: 'center', padding: '0 8px', gap: 2,
      overflow: 'hidden',
    }}>
      <span style={{ fontSize: 8, color: '#525252', fontFamily: 'ui-monospace, monospace', marginRight: 4, flexShrink: 0 }}>
        TH
      </span>
      {trades.length === 0 ? (
        <span style={{ fontSize: 9, color: '#525252', fontFamily: 'ui-monospace, monospace' }}>
          No trades yet
        </span>
      ) : (
        trades.map((t, i) => {
          const s = segmentStyle(t.outcome);
          return (
            <div key={t.id || i}
              title={`${t.direction} ${t.outcome} ${t.pnl != null ? '$' + t.pnl.toFixed(0) : ''} — ${t.entry_ts.slice(11, 16)}`}
              style={{
                flex: 1, minWidth: 8, maxWidth: 40,
                height: 10, borderRadius: 1,
                background: s.color,
                opacity: s.opacity,
                cursor: 'default',
              }}
            />
          );
        })
      )}
    </div>
  );
}
