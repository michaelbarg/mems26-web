'use client';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_NAMES, SYSTEM_BORDER_STYLE } from '../../types';
import type { SystemId, TradeMode } from '../../types';

export function TradeDetailsModal() {
  const { trades, selectedTradeId, setSelectedTradeId } = useTradeStore();
  const trade = trades.find((t) => t.id === selectedTradeId);
  if (!trade) return null;

  const color = SYSTEM_COLORS[(trade.system as SystemId) || 1];
  const borderStyle = SYSTEM_BORDER_STYLE[(trade.mode as TradeMode) || 'SHADOW'];

  return (
    <>
      <div className="fixed inset-0 z-40" style={{ background: 'rgba(0,0,0,0.6)' }} onClick={() => setSelectedTradeId(null)} />
      <div
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[480px] rounded-lg"
        style={{ background: 'var(--bg-secondary)', border: `2px ${borderStyle} ${color}` }}
      >
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ background: color }} />
            <span className="font-medium" style={{ color }}>
              Trade #{trade.id} &mdash; S{trade.system} {SYSTEM_NAMES[(trade.system as SystemId) || 1]}
            </span>
          </div>
          <button onClick={() => setSelectedTradeId(null)} className="text-lg hover:opacity-70" style={{ color: 'var(--text-secondary)' }}>
            &times;
          </button>
        </div>
        <div className="p-4 space-y-3">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <DetailRow label="Direction" value={trade.direction} color={trade.direction === 'LONG' ? 'var(--green)' : 'var(--red)'} />
            <DetailRow label="Mode" value={trade.mode} />
            <DetailRow label="Entry" value={trade.entry_price != null ? `${trade.entry_price.toFixed(2)} @ ${trade.entry_ts ? new Date(trade.entry_ts).toLocaleTimeString() : '\u2014'}` : '\u2014'} />
            <DetailRow label="Exit" value={trade.exit_price != null ? `${trade.exit_price.toFixed(2)} @ ${trade.exit_ts ? new Date(trade.exit_ts).toLocaleTimeString() : '\u2014'}` : 'Open'} />
            <DetailRow label="Exit Reason" value={trade.exit_reason ?? '\u2014'} />
            <DetailRow
              label="P&L"
              value={trade.pnl_usd != null ? `$${trade.pnl_usd.toFixed(0)}` : '\u2014'}
              color={trade.pnl_usd != null ? (trade.pnl_usd >= 0 ? 'var(--green)' : 'var(--red)') : undefined}
            />
            <DetailRow label="R Multiple" value={trade.pnl_r != null ? `${trade.pnl_r.toFixed(2)}R` : '\u2014'} />
            <DetailRow label="Outcome" value={trade.outcome ?? '\u2014'} color={
              trade.outcome === 'WIN' ? 'var(--green)' : trade.outcome === 'LOSS' ? 'var(--red)' : 'var(--text-secondary)'
            } />
          </div>
        </div>
      </div>
    </>
  );
}

function DetailRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <span className="text-[10px] block" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span className="text-xs font-mono" style={{ color: color || 'var(--text-primary)' }}>{value}</span>
    </div>
  );
}
