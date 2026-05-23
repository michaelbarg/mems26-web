'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { fetchRecentTrades } from '../../lib/api';
import { fmtTimeETIL } from '../../lib/tradeTime';

interface TradeSummary {
  id: number;
  direction: string;
  entry_ts: string;
  exit_ts: string | null;
  pnl: number | null;
  outcome: string; // WIN / LOSS / BE / OPEN
  pattern_id?: string | null;
  trigger?: string | null;
}

export function TradeHistoryStrip() {
  const [trades, setTrades] = useState<TradeSummary[]>([]);

  useEffect(() => {
    const load = () => {
      fetchRecentTrades(20).then((rows) => {
        setTrades(
          rows.map((t) => ({
            id: (t.id as number) ?? 0,
            direction: (t.direction as string) ?? 'LONG',
            entry_ts: (t.entry_ts as string) ?? '',
            exit_ts: (t.exit_ts as string | null) ?? null,
            pnl: (t.pnl_usd as number | null) ?? null,
            outcome: (t.outcome as string) ?? 'OPEN',
            pattern_id: (t.pattern_id as string | null) ?? null,
            trigger: (t.trigger as string | null) ?? null,
          })),
        );
      });
    };
    load();
    const id = setInterval(load, 30000);
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
              title={[
                `#${t.id} ${t.direction}`,
                t.pattern_id,
                t.trigger,
                t.outcome,
                t.pnl != null ? `$${t.pnl.toFixed(0)}` : '',
                t.entry_ts ? fmtTimeETIL(t.entry_ts) : '',
              ].filter(Boolean).join(' · ')}
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
