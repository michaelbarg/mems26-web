'use client';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_NAMES, SYSTEM_BORDER_STYLE } from '../../types';
import type { SystemId } from '../../types';

export function TradeDetailsModal() {
  const { trades, selectedTradeId, setSelectedTradeId } = useTradeStore();
  const trade = trades.find((t) => t.id === selectedTradeId);
  if (!trade) return null;

  const color = SYSTEM_COLORS[trade.system_id as SystemId];
  const borderStyle = SYSTEM_BORDER_STYLE[trade.mode];

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
              Trade #{trade.id} \u2014 S{trade.system_id} {SYSTEM_NAMES[trade.system_id as SystemId]}
            </span>
          </div>
          <button onClick={() => setSelectedTradeId(null)} className="text-lg hover:opacity-70" style={{ color: 'var(--text-secondary)' }}>
            \u00D7
          </button>
        </div>
        <div className="p-4 space-y-3">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <DetailRow label="Direction" value={trade.direction} color={trade.direction === 'LONG' ? 'var(--green)' : 'var(--red)'} />
            <DetailRow label="Mode" value={trade.mode} />
            <DetailRow label="Entry" value={`${trade.entry_price.toFixed(2)} @ ${new Date(trade.entry_time).toLocaleTimeString()}`} />
            <DetailRow label="Exit" value={trade.exit_price ? `${trade.exit_price.toFixed(2)} @ ${new Date(trade.exit_time!).toLocaleTimeString()}` : 'Open'} />
            <DetailRow label="Stop" value={trade.stop_price.toFixed(2)} color="var(--red)" />
            <DetailRow label="Target" value={trade.target_price.toFixed(2)} color="var(--green)" />
            <DetailRow label="Quantity" value={String(trade.quantity)} />
            <DetailRow
              label="P&L"
              value={trade.pnl_dollars !== null ? `$${trade.pnl_dollars.toFixed(0)} (${trade.pnl_ticks} ticks)` : '\u2014'}
              color={trade.pnl_dollars !== null ? (trade.pnl_dollars >= 0 ? 'var(--green)' : 'var(--red)') : undefined}
            />
            <DetailRow label="Outcome" value={trade.outcome} color={
              trade.outcome === 'WIN' ? 'var(--green)' : trade.outcome === 'LOSS' ? 'var(--red)' : 'var(--text-secondary)'
            } />
            <DetailRow label="Quality" value={trade.quality_score !== null ? `${(trade.quality_score * 100).toFixed(0)}%` : '\u2014'} />
            <DetailRow label="Pattern" value={trade.pattern_name || '\u2014'} />
          </div>
          {trade.notes && (
            <div className="mt-2">
              <span className="text-[10px] block mb-1" style={{ color: 'var(--text-muted)' }}>Notes</span>
              <div className="text-xs p-2 rounded" style={{ background: 'var(--bg-primary)', color: 'var(--text-secondary)' }}>
                {trade.notes}
              </div>
            </div>
          )}
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
