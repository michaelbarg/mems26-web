'use client';
import { useMemo, useState, useEffect } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useTradeStore } from '../../stores/tradeStore';
import { useSystemStore } from '../../stores/systemStore';
import { PriceDisplay } from '../topbar/PriceDisplay';
import { PriceMeta } from '../topbar/PriceMeta';
import { ConnectionIndicator } from '../topbar/ConnectionIndicator';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const MODE_STYLES: Record<string, { bg: string; border: string; text: string; label: string }> = {
  SHADOW: { bg: 'rgba(120,53,15,0.40)', border: '#b45309', text: '#fde68a', label: 'SHADOW SOAK' },
  SIM:    { bg: 'rgba(30,58,138,0.40)', border: '#1d4ed8', text: '#bfdbfe', label: 'SIM' },
  LIVE:   { bg: 'rgba(127,29,29,0.40)', border: '#dc2626', text: '#fca5a5', label: 'LIVE' },
};

export function TopBar() {
  const { activeChartType, setActiveChartType, togglePanels, panelsCollapsed } = useLayoutStore();
  const accountStatus = useTradeStore((s) => s.accountStatus);
  const trades = useTradeStore((s) => s.trades);
  const allSignals = useSystemStore((s) => s.signals);

  // Mode + backend health
  const [mode, setMode] = useState('SHADOW');
  const [backendHealth, setBackendHealth] = useState<{ subscribers: number; bridgeOk: boolean } | null>(null);
  const [showPlaybook, setShowPlaybook] = useState(false);
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/status`).then(r => r.json()).then(d => {
      setMode(d.mode || d.trading_mode || 'SHADOW');
      const subs = d.bar_router?.subscribers || {};
      const total = Object.values(subs).reduce((a: number, b) => a + (b as number), 0);
      setBackendHealth({ subscribers: total, bridgeOk: d.bridge?.connected ?? (total > 0) });
    }).catch(() => {});
    f(); const id = setInterval(f, 5000); return () => clearInterval(id);
  }, []);

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
      {/* Left: Mode badge + Symbol + Day Type + Killzone */}
      <div className="flex items-center gap-4">
        {/* Mode badge */}
        {(() => {
          const ms = MODE_STYLES[mode] || MODE_STYLES.SHADOW;
          return (
            <span style={{
              fontSize: 9, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
              background: ms.bg, border: `1px solid ${ms.border}`, color: ms.text,
              animation: mode === 'LIVE' ? 'pulse 2s infinite' : 'none',
            }}>
              {ms.label}
            </span>
          );
        })()}
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

      {/* Right: Status dots + Cap + Connection + Mode PnL + Nav */}
      <div className="flex items-center gap-3">
        {/* Status dots */}
        <div className="flex items-center gap-1" title={backendHealth ? `Backend: ${backendHealth.subscribers} subs` : 'Unknown'}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
            background: backendHealth?.bridgeOk ? '#16a34a' : (backendHealth ? '#eab308' : '#525252') }} />
          <span style={{ width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
            background: backendHealth && backendHealth.subscribers > 0 ? '#16a34a' : (backendHealth ? '#dc2626' : '#525252') }} />
        </div>
        {/* Cap indicator */}
        <div style={{ width: 80, position: 'relative' }} title={`$${stats.shadowPnl.toFixed(0)} / $200`}>
          <div style={{ height: 3, background: '#1a1a1a', borderRadius: 2 }}>
            <div style={{
              height: '100%', borderRadius: 2,
              width: `${Math.min(100, Math.abs(stats.shadowPnl) / 200 * 100)}%`,
              background: stats.shadowPnl >= 0 ? '#16a34a' : '#dc2626',
            }} />
          </div>
          <span style={{ fontSize: 7, color: '#525252', position: 'absolute', right: 0, top: 4 }}>
            ${stats.shadowPnl.toFixed(0)}/$200
          </span>
        </div>
        {/* Playbook icon */}
        <button onClick={() => setShowPlaybook(true)} title="Playbook"
          style={{ fontSize: 16, cursor: 'pointer', background: 'none', border: 'none', padding: 0 }}>
          📘
        </button>
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
      {/* Playbook modal */}
      {showPlaybook && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 999, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.6)',
        }} onClick={() => setShowPlaybook(false)}>
          <div style={{
            background: '#1a1a1a', border: '1px solid #333', borderRadius: 8,
            padding: 24, maxWidth: 400, width: '90%',
          }} onClick={e => e.stopPropagation()}>
            <h3 style={{ color: '#e5e5e5', fontSize: 16, marginBottom: 12 }}>📘 Playbook (coming)</h3>
            <p style={{ color: '#737373', fontSize: 13, lineHeight: 1.5 }}>
              Day Type playbooks + setup templates per system will live here.
              Awaiting P-PLAYBOOK prompt.
            </p>
            <button onClick={() => setShowPlaybook(false)}
              style={{ marginTop: 16, padding: '4px 16px', borderRadius: 4, border: '1px solid #333',
                background: '#262626', color: '#a3a3a3', cursor: 'pointer', fontSize: 12 }}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
