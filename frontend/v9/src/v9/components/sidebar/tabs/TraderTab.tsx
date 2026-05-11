'use client';
import { useMemo } from 'react';
import { useTradeStore } from '../../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_NAMES, type SystemId } from '../../../types';

const FIRING_SYSTEMS: SystemId[] = [1, 2, 4];

export function TraderTab() {
  const trades = useTradeStore((s) => s.trades);
  const accountStatus = useTradeStore((s) => s.accountStatus);

  const todayStats = useMemo(() => {
    const closed = trades.filter((t) => t.outcome && t.outcome !== 'OPEN');
    const wins = closed.filter((t) => t.outcome === 'WIN');
    const wr = closed.length > 0 ? ((wins.length / closed.length) * 100).toFixed(0) : '0';
    const netPnl = closed.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);
    return { total: trades.length, closed: closed.length, wr, netPnl };
  }, [trades]);

  const activeTrade = useMemo(() => {
    return trades.find((t) => t.outcome === 'OPEN') ?? null;
  }, [trades]);

  const perSystemPnl = useMemo(() => {
    return FIRING_SYSTEMS.map((sysId) => {
      const sysTrades = trades.filter((t) => t.system === sysId);
      const pnl = sysTrades.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);
      return { sysId, count: sysTrades.length, pnl };
    });
  }, [trades]);

  const totalPnl = perSystemPnl.reduce((sum, s) => sum + s.pnl, 0);
  const totalCount = perSystemPnl.reduce((sum, s) => sum + s.count, 0);

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Today's Trades Summary */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Today&apos;s Trades
        </div>
        <div className="grid grid-cols-2 gap-1" style={{ color: 'var(--text-secondary)' }}>
          <span>Trades: {todayStats.total}</span>
          <span>Closed: {todayStats.closed}</span>
          <span>WR: {todayStats.wr}%</span>
          <span style={{ color: todayStats.netPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
            P&L: ${todayStats.netPnl.toFixed(0)}
          </span>
        </div>
      </div>

      {/* Active Trade */}
      {activeTrade && (
        <div
          className="p-2 rounded border"
          style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--green)' }}
        >
          <div className="font-bold mb-1" style={{ color: 'var(--green)' }}>
            ACTIVE TRADE
          </div>
          <div className="flex flex-col gap-0.5" style={{ color: 'var(--text-secondary)' }}>
            <span>
              Direction:{' '}
              <span style={{ color: activeTrade.direction === 'LONG' ? 'var(--green)' : 'var(--red)' }}>
                {activeTrade.direction}
              </span>
            </span>
            {activeTrade.entry_price && <span>Entry: {activeTrade.entry_price.toFixed(2)}</span>}
            {activeTrade.entry_ts && (
              <span>Time: {new Date(activeTrade.entry_ts).toLocaleTimeString('he-IL')}</span>
            )}
            <span>System: S{activeTrade.system} {SYSTEM_NAMES[activeTrade.system as SystemId]}</span>
            <span>Mode: {activeTrade.mode}</span>
          </div>
        </div>
      )}

      {!activeTrade && (
        <div className="p-2 rounded text-center" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}>
          No active trade
        </div>
      )}

      {/* Per-system PnL */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Per-System P&L (SHADOW)
        </div>
        <div className="flex flex-col gap-1">
          {perSystemPnl.map(({ sysId, count, pnl }) => (
            <div key={sysId} className="flex justify-between" style={{ color: 'var(--text-secondary)' }}>
              <span style={{ color: SYSTEM_COLORS[sysId] }}>
                S{sysId}: {count} trades
              </span>
              <span style={{ color: pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                ${pnl.toFixed(0)}
              </span>
            </div>
          ))}
          <div
            className="flex justify-between pt-1 mt-1"
            style={{ borderTop: '1px solid var(--border)', color: 'var(--text-primary)' }}
          >
            <span>TOTAL: {totalCount} trades</span>
            <span style={{ color: totalPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
              ${totalPnl.toFixed(0)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
