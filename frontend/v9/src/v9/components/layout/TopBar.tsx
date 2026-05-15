'use client';
import { useMemo, useState, useEffect } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useTradeStore } from '../../stores/tradeStore';
import { useSystemStore } from '../../stores/systemStore';
import { PriceDisplay } from '../topbar/PriceDisplay';
import { PriceMeta } from '../topbar/PriceMeta';
import { ConnectionIndicator } from '../topbar/ConnectionIndicator';
import Link from 'next/link';
import { LibraryModal } from '../banners/LibraryModal';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const MODE_STYLES: Record<string, { bg: string; border: string; text: string; label: string }> = {
  SHADOW: { bg: 'rgba(250,204,21,0.12)', border: '#facc15', text: '#facc15', label: 'SHADOW' },  // V5 §4.1 yellow
  SIM:    { bg: 'rgba(6,182,212,0.12)', border: '#06b6d4', text: '#06b6d4', label: 'DEMO' },     // V5 §4.1 cyan
  LIVE:   { bg: 'rgba(220,38,38,0.12)', border: '#dc2626', text: '#fca5a5', label: 'LIVE' },     // V5 §4.1 red
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

  // Day Type from V9 classifier (3a-S4 endpoint, falls back to V1)
  const DT_LABELS: Record<string, string> = {
    Trend_Normal: 'TRD', Trend_DD: 'TDD', Variation: 'VAR',
    Neutral: 'NEU', Normal: 'NOR', Nontrend: 'NTR', UNKNOWN: '\u2014',
    trend_normal: 'TRD', trend_dd: 'TDD', variation: 'VAR',
    neutral: 'NEU', normal: 'NOR', nontrend: 'NTR',
  };
  const [dayTypeRaw, setDayTypeRaw] = useState('UNKNOWN');
  const [dayTypeConf, setDayTypeConf] = useState(0);
  const [dayTypeDir, setDayTypeDir] = useState<string | null>(null);
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/day_type/v9/current`).then(r => r.json())
      .then(d => {
        if (d?.data) {
          setDayTypeRaw(d.data.day_type || 'UNKNOWN');
          setDayTypeConf(d.data.probability != null ? Math.round(d.data.probability * 100) : 0);
          setDayTypeDir(d.data.directional_certainty || null);
        } else {
          // Fallback to V1 endpoint
          return fetch(`${API}/api/v9/day_type/current`).then(r2 => r2.json())
            .then(d2 => { setDayTypeRaw(d2.day_type || 'UNKNOWN'); setDayTypeConf(d2.confidence ?? 0); });
        }
      }).catch(() => {});
    f(); const id = setInterval(f, 10000); return () => clearInterval(id);
  }, []);
  const dayType = DT_LABELS[dayTypeRaw] || dayTypeRaw;

  // WR today (ν.2)
  const [wrToday, setWrToday] = useState<number | null>(null);
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/shadow/today_wr`).then(r => r.json())
      .then(d => setWrToday(d.today_wr_pct ?? d.wr_pct ?? d.win_rate ?? null)).catch(() => {});
    f(); const id = setInterval(f, 30000); return () => clearInterval(id);
  }, []);

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
      data-testid="topbar"
      className="h-[40px] flex items-center justify-between px-4 border-b shrink-0"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      {/* Left: Connection + Mode badge + Symbol + Day Type + Killzone */}
      <div className="flex items-center gap-4">
        <ConnectionIndicator />
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
        <span style={{
          fontSize: 10, fontWeight: 600, padding: '1px 6px', borderRadius: 3,
          background: 'rgba(99,102,241,0.15)', color: '#818cf8',
          fontFamily: 'ui-monospace, monospace',
        }}>
          {dayType} {dayTypeConf > 0 ? `${dayTypeConf}%` : ''}{dayTypeDir ? ` ${dayTypeDir[0]}` : ''}
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
        {/* Library icon (η.J4 — V5 §3.4) */}
        <button onClick={() => setShowPlaybook(true)} title="Library (Journal / Spec / Settings)"
          style={{ fontSize: 16, cursor: 'pointer', background: 'none', border: 'none', padding: 0 }}>
          📚
        </button>
        <ConnectionIndicator />
        {wrToday != null && (
          <span style={{
            fontSize: 11, fontWeight: 600, padding: '4px 8px', borderRadius: 12,
            height: 24, flexShrink: 0, whiteSpace: 'nowrap',
            background: wrToday >= 50 ? 'rgba(22,163,74,0.15)' : wrToday === 0 ? 'rgba(82,82,82,0.15)' : 'rgba(220,38,38,0.15)',
            color: '#fff',
            border: `1px solid ${wrToday >= 50 ? '#16a34a' : wrToday === 0 ? '#525252' : '#dc2626'}`,
            fontFamily: 'ui-monospace, monospace',
          }}
          data-testid="topbar-wr-pill">
            WR: {wrToday.toFixed(0)}%
          </span>
        )}
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
      {showPlaybook && <LibraryModal onClose={() => setShowPlaybook(false)} />}
    </div>
  );
}
