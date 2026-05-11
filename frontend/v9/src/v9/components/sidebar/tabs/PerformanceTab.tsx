'use client';
import { useMemo } from 'react';
import { useTradeStore } from '../../../stores/tradeStore';

export function PerformanceTab() {
  const trades = useTradeStore((s) => s.trades);

  const dailyStats = useMemo(() => {
    const closed = trades.filter((t) => t.outcome && t.outcome !== 'OPEN');
    const wins = closed.filter((t) => t.outcome === 'WIN');
    const losses = closed.filter((t) => t.outcome === 'LOSS');
    const wr = closed.length > 0 ? ((wins.length / closed.length) * 100).toFixed(1) : '0.0';
    const pnl = closed.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);
    const avgWin = wins.length > 0 ? wins.reduce((s, t) => s + (t.pnl_usd ?? 0), 0) / wins.length : 0;
    const avgLoss = losses.length > 0 ? losses.reduce((s, t) => s + (t.pnl_usd ?? 0), 0) / losses.length : 0;
    return { closed: closed.length, wins: wins.length, losses: losses.length, wr, pnl, avgWin, avgLoss };
  }, [trades]);

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Daily Stats */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
          Daily Statistics
        </div>
        <div className="flex flex-col gap-1" style={{ color: 'var(--text-secondary)' }}>
          <div className="flex justify-between">
            <span>Trades</span>
            <span>{dailyStats.closed}</span>
          </div>
          <div className="flex justify-between">
            <span>Wins / Losses</span>
            <span>
              <span style={{ color: 'var(--green)' }}>{dailyStats.wins}</span>
              {' / '}
              <span style={{ color: 'var(--red)' }}>{dailyStats.losses}</span>
            </span>
          </div>
          <div className="flex justify-between">
            <span>Win Rate</span>
            <span>{dailyStats.wr}%</span>
          </div>
          <div className="flex justify-between">
            <span>P&L</span>
            <span style={{ color: dailyStats.pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
              ${dailyStats.pnl.toFixed(0)}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Avg Win</span>
            <span style={{ color: 'var(--green)' }}>${dailyStats.avgWin.toFixed(0)}</span>
          </div>
          <div className="flex justify-between">
            <span>Avg Loss</span>
            <span style={{ color: 'var(--red)' }}>${dailyStats.avgLoss.toFixed(0)}</span>
          </div>
        </div>
      </div>

      {/* Placeholder sections */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Weekly Stats
        </div>
        <div style={{ color: 'var(--text-muted)' }}>Requires historical data aggregation</div>
      </div>

      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Pattern Stats
        </div>
        <div style={{ color: 'var(--text-muted)' }}>Requires pattern tracking data</div>
      </div>

      <div className="p-2 rounded text-center" style={{ background: 'var(--bg-tertiary)' }}>
        <button
          className="px-3 py-1 rounded text-xs"
          style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
          disabled
        >
          Open Full Journal
        </button>
      </div>
    </div>
  );
}
