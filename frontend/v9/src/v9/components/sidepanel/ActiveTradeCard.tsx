'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Contract {
  id: string;
  target_price: number;
  status: 'OPEN' | 'HIT_TARGET' | 'HIT_STOP' | 'BE';
  pnl: number;
  r: number;
  smart_be: boolean;
}

interface ActiveTrade {
  trade_id: number;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  entry_ts: string | null;
  stop_price: number;
  contracts: Contract[];
  hits: number;
  total_pnl: number;
  total_r: number;
  summary: string;
}

const STATUS_COLORS: Record<string, string> = {
  OPEN: '#737373',
  HIT_TARGET: '#16a34a',
  HIT_STOP: '#dc2626',
  BE: '#eab308',
};

export function ActiveTradeCard() {
  const [trade, setTrade] = useState<ActiveTrade | null>(null);

  useEffect(() => {
    const poll = () => fetch(`${API}/api/v9/trades/active`)
      .then(r => r.json())
      .then(d => setTrade(d && d.trade_id ? d : null))
      .catch(() => {});
    poll();
    const id = setInterval(poll, 2000);
    return () => clearInterval(id);
  }, []);

  if (!trade) {
    return (
      <div style={{
        padding: 12,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        borderRadius: 6,
        margin: 6,
        background: COLORS.bgSurface4,
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 10, color: COLORS.textTertiary, fontWeight: 500 }}>
          No Active Trade
        </div>
        <div style={{ fontSize: 8, color: COLORS.textDim, marginTop: 2 }}>
          Awaiting setup confirmation
        </div>
      </div>
    );
  }

  const dirColor = trade.direction === 'LONG' ? COLORS.bull : COLORS.bear;
  // §3.6 5-state: Idle(no card) / Armed(yellow) / Active(green/red) / JustClosed(gray)
  const cardState = trade.hits > 0 || trade.total_pnl !== 0 ? 'Active' : 'Armed';
  const borderColor = cardState === 'Armed' ? '#eab308'
    : trade.total_pnl > 0 ? COLORS.bull
    : trade.total_pnl < 0 ? COLORS.bear
    : '#eab308';
  const entryTime = trade.entry_ts ? new Date(trade.entry_ts).toLocaleTimeString('en-US', {
    timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false,
  }) : '';

  return (
    <div style={{
      padding: 8,
      borderRadius: 6,
      margin: 6,
      background: COLORS.bgSurface4,
      border: `0.5px solid ${borderColor}`,
    }}>
      {/* Header: direction + entry price + time */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 11, color: dirColor, fontWeight: 700 }}>
            {trade.direction === 'LONG' ? '\u25B2' : '\u25BC'} {trade.direction}
          </span>
          <span style={{ fontSize: 10, fontWeight: 600, color: COLORS.textPrimary, fontFamily: 'ui-monospace' }}>
            {trade.entry_price.toFixed(2)}
          </span>
        </div>
        <span style={{ fontSize: 8, color: COLORS.textTertiary }}>{entryTime} ET</span>
      </div>

      {/* C1/C2/C3 rows */}
      {trade.contracts.map(c => {
        const sc = STATUS_COLORS[c.status] || '#737373';
        return (
          <div key={c.id} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            fontSize: 9, padding: '2px 0',
            borderBottom: `1px solid ${COLORS.borderFaint}`,
          }}>
            <span style={{ fontWeight: 600, color: COLORS.textSecondary, width: 22 }}>{c.id}</span>
            <span style={{ color: COLORS.textTertiary, fontFamily: 'ui-monospace', fontSize: 8, width: 52 }}>
              {c.target_price?.toFixed(2) ?? '\u2014'}
            </span>
            <span style={{
              fontSize: 8, fontWeight: 500, padding: '0 4px', borderRadius: 2,
              color: sc, background: `${sc}15`,
            }}>
              {c.status.replace('_', ' ')}{c.smart_be ? ' \u21C4' : ''}
            </span>
            <span style={{ fontFamily: 'ui-monospace', fontSize: 9, width: 40, textAlign: 'right',
              color: c.pnl >= 0 ? COLORS.bull : COLORS.bear }}>
              ${c.pnl.toFixed(0)}
            </span>
            <span style={{ fontFamily: 'ui-monospace', fontSize: 8, width: 30, textAlign: 'right',
              color: COLORS.textTertiary }}>
              {c.r.toFixed(1)}R
            </span>
          </div>
        );
      })}

      {/* Summary footer */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', paddingTop: 4, marginTop: 2,
        fontSize: 9,
      }}>
        <span style={{ color: COLORS.textTertiary }}>
          Stop {trade.stop_price.toFixed(2)} | {trade.summary}
        </span>
        <span style={{
          fontWeight: 700, fontSize: 10, fontFamily: 'ui-monospace',
          color: trade.total_pnl >= 0 ? COLORS.bull : COLORS.bear,
        }}>
          ${trade.total_pnl.toFixed(0)} ({trade.total_r.toFixed(1)}R)
        </span>
      </div>

      {/* §3.5 Flow 5: Exit + Move Stop buttons */}
      <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
        <button
          onClick={() => { if (confirm('Exit all contracts?')) fetch(`${API}/api/v9/trades/${trade.trade_id}/exit`, { method: 'POST' }).catch(() => {}); }}
          style={{
            flex: 1, fontSize: 9, padding: '3px 0', borderRadius: 3, cursor: 'pointer',
            border: '1px solid #dc2626', background: 'rgba(220,38,38,0.12)', color: '#dc2626',
          }}
        >Exit</button>
        <button
          onClick={() => {
            const ticks = prompt('Move stop by N ticks (positive=tighter):');
            if (ticks) fetch(`${API}/api/v9/trades/${trade.trade_id}/move_stop`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ticks: Number(ticks) }),
            }).catch(() => {});
          }}
          style={{
            flex: 1, fontSize: 9, padding: '3px 0', borderRadius: 3, cursor: 'pointer',
            border: `1px solid ${COLORS.borderFaint}`, background: 'transparent', color: COLORS.textTertiary,
          }}
        >Move Stop</button>
      </div>
    </div>
  );
}
