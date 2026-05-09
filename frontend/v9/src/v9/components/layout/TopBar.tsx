'use client';
import { useLayoutStore } from '../../stores/layoutStore';
import { useTradeStore } from '../../stores/tradeStore';
import { useMarketStore } from '../../stores/marketStore';
import Link from 'next/link';

export function TopBar() {
  const { activeChartType, setActiveChartType, togglePanels, panelsCollapsed } = useLayoutStore();
  const accountStatus = useTradeStore((s) => s.accountStatus);
  const bars = useMarketStore((s) => s.bars5min);
  const lastBar = bars[bars.length - 1];

  return (
    <div
      className="h-[40px] flex items-center justify-between px-4 border-b shrink-0"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      {/* Left: Logo + Chart Type */}
      <div className="flex items-center gap-4">
        <span className="font-bold text-sm tracking-wider" style={{ color: 'var(--sys1)' }}>
          MEMS26
        </span>
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>V9</span>
        <div className="flex gap-1 ml-4">
          <button
            onClick={() => setActiveChartType('5min')}
            className="px-2 py-0.5 rounded text-xs"
            style={{
              background: activeChartType === '5min' ? 'var(--bg-tertiary)' : 'transparent',
              color: activeChartType === '5min' ? 'var(--text-primary)' : 'var(--text-secondary)',
            }}
          >
            5 Min
          </button>
          <button
            onClick={() => setActiveChartType('tick_reversal')}
            className="px-2 py-0.5 rounded text-xs"
            style={{
              background: activeChartType === 'tick_reversal' ? 'var(--bg-tertiary)' : 'transparent',
              color: activeChartType === 'tick_reversal' ? 'var(--text-primary)' : 'var(--text-secondary)',
            }}
          >
            Tick Rev
          </button>
        </div>
      </div>

      {/* Center: Last Price */}
      <div className="flex items-center gap-4">
        {lastBar && (
          <>
            <span className="text-lg font-mono font-bold" style={{
              color: lastBar.close >= lastBar.open ? 'var(--green)' : 'var(--red)',
            }}>
              {lastBar.close.toFixed(2)}
            </span>
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>MES</span>
          </>
        )}
      </div>

      {/* Right: Account + Nav */}
      <div className="flex items-center gap-4">
        {accountStatus && (
          <div className="flex items-center gap-3 text-xs">
            <span style={{ color: accountStatus.daily_pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
              P&L: ${accountStatus.daily_pnl.toFixed(0)}
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              Trades: {accountStatus.trade_count}
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              WR: {(accountStatus.win_rate * 100).toFixed(0)}%
            </span>
          </div>
        )}
        <Link
          href="/trades"
          className="text-xs px-2 py-0.5 rounded hover:bg-[var(--bg-tertiary)]"
          style={{ color: 'var(--text-secondary)' }}
        >
          Trades
        </Link>
        <button
          onClick={togglePanels}
          className="text-xs px-2 py-0.5 rounded hover:bg-[var(--bg-tertiary)]"
          style={{ color: 'var(--text-secondary)' }}
        >
          {panelsCollapsed ? 'Show Panels' : 'Hide Panels'}
        </button>
      </div>
    </div>
  );
}
