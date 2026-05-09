'use client';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_NAMES } from '../../types';
import type { SystemId } from '../../types';

export function TradesTable() {
  const { filteredTrades, setSelectedTradeId } = useTradeStore();
  const trades = filteredTrades();

  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="sticky top-0" style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
          <th className="text-left px-3 py-2 font-medium">Time</th>
          <th className="text-left px-3 py-2 font-medium">System</th>
          <th className="text-left px-3 py-2 font-medium">Mode</th>
          <th className="text-left px-3 py-2 font-medium">Dir</th>
          <th className="text-right px-3 py-2 font-medium">Entry</th>
          <th className="text-right px-3 py-2 font-medium">Exit</th>
          <th className="text-right px-3 py-2 font-medium">Ticks</th>
          <th className="text-right px-3 py-2 font-medium">P&L</th>
          <th className="text-left px-3 py-2 font-medium">Outcome</th>
          <th className="text-left px-3 py-2 font-medium">Pattern</th>
          <th className="text-right px-3 py-2 font-medium">Quality</th>
        </tr>
      </thead>
      <tbody>
        {trades.map((t) => (
          <tr
            key={t.id}
            className="border-b cursor-pointer hover:bg-[var(--bg-secondary)]"
            style={{ borderColor: 'var(--border)' }}
            onClick={() => setSelectedTradeId(t.id)}
          >
            <td className="px-3 py-1.5" style={{ color: 'var(--text-secondary)' }}>
              {new Date(t.entry_time).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </td>
            <td className="px-3 py-1.5">
              <span style={{ color: SYSTEM_COLORS[t.system_id as SystemId] }}>
                S{t.system_id} {SYSTEM_NAMES[t.system_id as SystemId]}
              </span>
            </td>
            <td className="px-3 py-1.5" style={{ color: 'var(--text-muted)' }}>{t.mode}</td>
            <td className="px-3 py-1.5">
              <span style={{ color: t.direction === 'LONG' ? 'var(--green)' : 'var(--red)' }}>{t.direction}</span>
            </td>
            <td className="px-3 py-1.5 text-right font-mono">{t.entry_price.toFixed(2)}</td>
            <td className="px-3 py-1.5 text-right font-mono" style={{ color: 'var(--text-secondary)' }}>
              {t.exit_price?.toFixed(2) || '\u2014'}
            </td>
            <td className="px-3 py-1.5 text-right font-mono" style={{
              color: t.pnl_ticks !== null
                ? t.pnl_ticks > 0 ? 'var(--green)' : t.pnl_ticks < 0 ? 'var(--red)' : 'var(--text-secondary)'
                : 'var(--text-muted)',
            }}>
              {t.pnl_ticks !== null ? (t.pnl_ticks > 0 ? '+' : '') + t.pnl_ticks : '\u2014'}
            </td>
            <td className="px-3 py-1.5 text-right font-mono" style={{
              color: t.pnl_dollars !== null
                ? t.pnl_dollars > 0 ? 'var(--green)' : t.pnl_dollars < 0 ? 'var(--red)' : 'var(--text-secondary)'
                : 'var(--text-muted)',
            }}>
              {t.pnl_dollars !== null ? '$' + t.pnl_dollars.toFixed(0) : '\u2014'}
            </td>
            <td className="px-3 py-1.5">
              <span className="px-1.5 py-0.5 rounded text-[10px]" style={{
                background:
                  t.outcome === 'WIN' ? 'rgba(86,211,100,0.15)' :
                  t.outcome === 'LOSS' ? 'rgba(248,81,73,0.15)' :
                  t.outcome === 'OPEN' ? 'rgba(88,166,255,0.15)' : 'rgba(139,148,158,0.15)',
                color:
                  t.outcome === 'WIN' ? 'var(--green)' :
                  t.outcome === 'LOSS' ? 'var(--red)' :
                  t.outcome === 'OPEN' ? 'var(--sys1)' : 'var(--text-secondary)',
              }}>
                {t.outcome}
              </span>
            </td>
            <td className="px-3 py-1.5" style={{ color: 'var(--text-secondary)' }}>{t.pattern_name || '\u2014'}</td>
            <td className="px-3 py-1.5 text-right" style={{ color: 'var(--text-secondary)' }}>
              {t.quality_score !== null ? `${(t.quality_score * 100).toFixed(0)}%` : '\u2014'}
            </td>
          </tr>
        ))}
        {trades.length === 0 && (
          <tr>
            <td colSpan={11} className="px-3 py-8 text-center" style={{ color: 'var(--text-muted)' }}>
              No trades found matching filters.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
