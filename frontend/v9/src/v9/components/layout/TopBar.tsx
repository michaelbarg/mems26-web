'use client';
import { useMemo } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useTradeStore } from '../../stores/tradeStore';
import { useSystemStore } from '../../stores/systemStore';
import { PriceDisplay } from '../topbar/PriceDisplay';
import { PriceMeta } from '../topbar/PriceMeta';
import { ConnectionIndicator } from '../topbar/ConnectionIndicator';
import Link from 'next/link';

export function TopBar() {
  const { activeChartType, setActiveChartType, togglePanels, panelsCollapsed } = useLayoutStore();
  const accountStatus = useTradeStore((s) => s.accountStatus);
  const trades = useTradeStore((s) => s.trades);
  const allSignals = useSystemStore((s) => s.signals);

  // Day Type from System 1 latest signal
  const dayType = useMemo(() => {
    const sys1 = allSignals.filter((s) => s.system_id === 1);
    const latest = sys1[sys1.length - 1];
    return (latest?.payload?.day_type as string) || '\u2014';
  }, [allSignals]);

  // Killzone from System 6 latest signal
  const killzone = useMemo(() => {
    const sys6 = allSignals.filter((s) => s.system_id === 6);
    const latest = sys6[sys6.length - 1];
    const zone = (latest?.payload?.session_phase as string) || '';
    const gate = latest?.payload?.gate_open;
    return { zone: zone || '\u2014', open: !!gate };
  }, [allSignals]);

  // PnL and trade counts by mode
  const stats = useMemo(() => {
    const shadowTrades = trades.filter((t) => t.mode === 'SHADOW');
    const demoTrades = trades.filter((t) => t.mode === 'SIM');
    const liveTrades = trades.filter((t) => t.mode === 'LIVE');
    return {
      shadowPnl: shadowTrades.reduce((s, t) => s + (t.pnl_usd ?? 0), 0),
      demoPnl: demoTrades.reduce((s, t) => s + (t.pnl_usd ?? 0), 0),
      livePnl: liveTrades.reduce((s, t) => s + (t.pnl_usd ?? 0), 0),
      shadowCount: shadowTrades.length,
      demoCount: demoTrades.length,
      liveCount: liveTrades.length,
    };
  }, [trades]);

  return (
    <div
      className="h-[40px] flex items-center justify-between px-4 border-b shrink-0"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      {/* Left: Symbol + Day Type + Killzone */}
      <div className="flex items-center gap-4">
        <span className="font-bold text-sm tracking-wider" style={{ color: '#58a6ff' }}>
          MES
        </span>
        <span className="text-xs font-medium" style={{ color: '#58a6ff' }}>
          {dayType}
        </span>
        <span className="text-xs" style={{ color: killzone.open ? '#56d364' : '#f85149' }}>
          {killzone.zone} {killzone.open ? 'OPEN' : 'CLOSED'}
        </span>
        <div className="flex gap-1 ml-2">
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

      {/* Center: Live Price from Event Bus */}
      <div className="flex items-center gap-3">
        <PriceDisplay />
        <PriceMeta />
      </div>

      {/* Right: Connection + Mode PnL + Nav */}
      <div className="flex items-center gap-3">
        <ConnectionIndicator />
        <div className="flex items-center gap-2 text-xs">
          {accountStatus ? (
            <>
              <span style={{ color: accountStatus.daily_pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                P&L: ${accountStatus.daily_pnl.toFixed(0)}
              </span>
              <span style={{ color: 'var(--text-secondary)' }}>
                Trades: {accountStatus.trade_count}
              </span>
            </>
          ) : (
            <>
              <span style={{ color: 'var(--text-muted)' }}>
                SHADOW: {stats.shadowCount}t
              </span>
              <span style={{ color: stats.shadowPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                ${stats.shadowPnl.toFixed(0)}
              </span>
              {stats.demoCount > 0 && (
                <>
                  <span style={{ color: 'var(--text-muted)' }}>|</span>
                  <span style={{ color: 'var(--text-muted)' }}>
                    DEMO: {stats.demoCount}t
                  </span>
                  <span style={{ color: stats.demoPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                    ${stats.demoPnl.toFixed(0)}
                  </span>
                </>
              )}
            </>
          )}
        </div>
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
