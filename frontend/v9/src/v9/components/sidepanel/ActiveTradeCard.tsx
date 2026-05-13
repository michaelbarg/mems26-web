'use client';
import { COLORS } from '../../design/tokens';

interface ActiveTrade {
  symbol: string;
  side: 'LONG' | 'SHORT';
  contracts: { label: string; filled: number; pnl: number; rMultiple: number }[];
  stopPrice: number;
  totalPnl: number;
}

interface Props {
  trade?: ActiveTrade | null;
}

export function ActiveTradeCard({ trade = null }: Props) {
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

  const sideColor = trade.side === 'LONG' ? COLORS.bull : COLORS.bear;

  return (
    <div style={{
      padding: 8,
      borderBottom: `1px solid ${COLORS.borderFaint}`,
      borderRadius: 6,
      margin: 6,
      background: COLORS.bgSurface4,
      border: `0.5px solid ${sideColor}`,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: COLORS.textPrimary }}>{trade.symbol}</span>
        <span style={{ fontSize: 9, fontWeight: 600, color: sideColor, padding: '1px 4px', borderRadius: 2, background: `${sideColor}1a` }}>
          {trade.side}
        </span>
      </div>
      {trade.contracts.map((c, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8, color: COLORS.textSecondary, marginBottom: 2 }}>
          <span>{c.label}</span>
          <span style={{ fontFamily: 'ui-monospace', color: c.pnl >= 0 ? COLORS.bull : COLORS.bear }}>
            ${c.pnl.toFixed(0)} ({c.rMultiple.toFixed(1)}R)
          </span>
        </div>
      ))}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8, color: COLORS.textTertiary, borderTop: `1px solid ${COLORS.borderFaint}`, paddingTop: 3, marginTop: 3 }}>
        <span>Stop: {trade.stopPrice.toFixed(2)}</span>
        <span style={{ fontWeight: 700, fontSize: 10, color: trade.totalPnl >= 0 ? COLORS.bull : COLORS.bear }}>
          ${trade.totalPnl.toFixed(0)}
        </span>
      </div>
    </div>
  );
}
