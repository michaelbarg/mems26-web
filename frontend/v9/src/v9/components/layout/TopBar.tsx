'use client';
import { useMemo, useState, useEffect } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useTradeStore } from '../../stores/tradeStore';
import { useSystemStateStore } from '../../stores/systemStateStore';
import { PriceDisplay } from '../topbar/PriceDisplay';
import { PriceMeta } from '../topbar/PriceMeta';
import { ConnectionIndicator } from '../topbar/ConnectionIndicator';
import { AgentHeartbeatDot } from '../topbar/AgentHeartbeatDot';
import Link from 'next/link';
import { NewsDropdown } from './NewsDropdown';
import { LibraryModal } from '../banners/LibraryModal';
import { dayTypeColor, DAY_TYPE_DIRECTION_HE } from '../../lib/dayType';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const MODE_STYLES: Record<string, { bg: string; border: string; text: string; label: string }> = {
  SHADOW: { bg: 'rgba(250,204,21,0.12)', border: '#facc15', text: '#facc15', label: 'SHADOW' },  // V5 §4.1 yellow
  SIM:    { bg: 'rgba(6,182,212,0.12)', border: '#06b6d4', text: '#06b6d4', label: 'DEMO' },     // V5 §4.1 cyan
  LIVE:   { bg: 'rgba(220,38,38,0.12)', border: '#dc2626', text: '#fca5a5', label: 'LIVE' },     // V5 §4.1 red
  // ביקורת-UX 29.08: מצב-לא-ידוע חייב להיראות שונה משלושת המצבים האמיתיים.
  // קודם היה ברירת-מחדל 'SHADOW' — כלומר תג-צל צהוב בזמן מסחר-אמת (ראה למטה).
  UNKNOWN: { bg: 'rgba(148,163,184,0.14)', border: '#94a3b8', text: '#e2e8f0', label: 'מצב ?' },
};

// Killzone chip colour by the zone's edge class (backend killzone/definitions.py:
// NY_OPEN high · LONDON/NY_PREMARKET/NY_PM medium · ASIA/MIDDAY/POST_MARKET low ·
// CLOSED/WEEKEND none).
const KZ_EDGE_COLOR: Record<string, string> = {
  high: '#56d364', medium: '#d29922', low: '#8b949e', none: '#f85149',
};

export function TopBar() {
  const { togglePanels, panelsCollapsed } = useLayoutStore();
  const accountStatus = useTradeStore((s) => s.accountStatus);
  const trades = useTradeStore((s) => s.trades);

  // Mode + backend health — lightweight heartbeat (no Redis)
  // ביקורת-UX 29.08 (שקר-תצוגה #1): הערך ההתחלתי היה 'SHADOW'. ה-fetch נבלע
  // ב-.catch(() => {}) ריק, כך שכל כשל-רשת השאיר תג "SHADOW" צהוב על המסך —
  // בזמן ש-MEMS26_MODE=live, is_sim=0, חשבון 37138283 = כסף אמיתי.
  // ברירת-המחדל היא 'UNKNOWN'; הודעת-האמת מגיעה רק מה-heartbeat.
  const [mode, setMode] = useState('UNKNOWN');
  const [backendHealth, setBackendHealth] = useState<{ wsClients: number; priceFileOk: boolean } | null>(null);
  const [showPlaybook, setShowPlaybook] = useState(false);
  useEffect(() => {
    let inFlight = false;
    const f = () => {
      if (inFlight) return;
      inFlight = true;
      fetch(`${API}/api/v9/cockpit/heartbeat`).then(r => r.json()).then(d => {
        // heartbeat returns lowercase MEMS26_MODE ("shadow"/"demo"/"live"); map to the
        // MODE_STYLES key (demo→SIM) so the badge shows correctly (was defaulting to
        // SHADOW for any non-uppercase value — hid DEMO and would hide LIVE).
        const MK: Record<string, string> = { shadow: 'SHADOW', demo: 'SIM', sim: 'SIM', live: 'LIVE' };
        // ערך חסר/לא-מוכר => UNKNOWN, לא SHADOW.
        setMode(MK[String(d.mode ?? '').toLowerCase()] || 'UNKNOWN');
        setBackendHealth({
          wsClients: d.ws_clients ?? 0,
          priceFileOk: d.price_file_age_ms >= 0 && d.price_file_age_ms < 120000,
        });
        // כשל-רשת => מפסיקים לטעון מצב; לא "נשארים" על הערך האחרון ולא על SHADOW.
      }).catch(() => { setMode('UNKNOWN'); }).finally(() => { inFlight = false; });
    };
    f(); const id = setInterval(f, 15000); return () => clearInterval(id);
  }, []);

  // Day Type — LIVE badge from systems[1] in systemStateStore. That slot is filled
  // Label = get_live_day_type when present (systemStateStore.overrideS1 → /day_type/live),
  // else classify_replay detail (GAP G-16 / S124 G5). Poll via useSystemStatePolling 5000ms.
  // Dead endpoints /api/v9/day_type/current + /day_type/v9/current are NOT used (retired 06-22).
  const dtSystem = useSystemStateStore((s) => s.systems[1]);
  const dtRaw = (dtSystem?.raw ?? {}) as {
    direction?: string | null; reason?: string | null; invalidated?: boolean; source?: string;
  };
  const dayTypeName = dtSystem?.state || 'UNKNOWN';
  const dayTypeStatus = dtSystem?.subState || null;
  const dtColor = dayTypeColor(dayTypeName);
  const dtClassified = dayTypeStatus === 'CLASSIFIED';
  const dtStance = dtRaw.direction ? (DAY_TYPE_DIRECTION_HE[dtRaw.direction] ?? dtRaw.direction) : null;
  const dtTitle = [
    'Day-Type (S1 · get_live_day_type (override-aware))',
    `${dayTypeName.replace(/_/g, ' ')}${dayTypeStatus ? ` · ${dayTypeStatus}` : ''}`,
    dtStance ? `כיוון: ${dtStance}` : null,
    dtRaw.reason ? String(dtRaw.reason) : null,
    dtRaw.invalidated ? '⚠ הפתיחה נחצתה (INVALIDATED)' : null,
  ].filter(Boolean).join('\n');

  // WR today (ν.2)
  const [wrToday, setWrToday] = useState<number | null>(null);
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/shadow/today_wr`).then(r => r.json())
      .then(d => setWrToday(d.today_wr_pct ?? d.wr_pct ?? d.win_rate ?? null)).catch(() => {});
    f(); const id = setInterval(f, 30000); return () => clearInterval(id);
  }, []);

  // Killzone (S6) — from systemStateStore.systems[6]: /cockpit/systems-snapshot every 5 s
  // (useSystemStatePolling), raw = the /api/v9/killzone/current payload. Fix 23.10
  // (audit §3): the chip listened to WS /ws/v9/signals/6, which never sends an update
  // (no Redis — ws_manager.py), so it sat on "— CLOSED" all day.
  const kzSys = useSystemStateStore((s) => s.systems[6]);
  const kzRaw = (kzSys?.raw ?? {}) as {
    current_zone?: { name?: string | null; edge_class?: string | null; minutes_remaining?: number | null; ends_at_et?: string | null } | null;
    next_zone?: { name?: string | null; starts_in_minutes?: number | null } | null;
    gate_open?: boolean; is_open?: boolean;
  };
  const kzZone = kzRaw.current_zone?.name ?? kzSys?.state ?? null;
  const kzEdge = kzRaw.current_zone?.edge_class ?? kzSys?.subState ?? null;
  // /killzone/current does not expose the gate itself (only zone + edge) — OPEN/CLOSED
  // is shown only if a gate field ever arrives; never inferred.
  const kzGate = typeof kzRaw.gate_open === 'boolean' ? kzRaw.gate_open
    : typeof kzRaw.is_open === 'boolean' ? kzRaw.is_open : null;
  const kzColor = kzGate === true ? '#56d364' : kzGate === false ? '#f85149'
    : kzEdge ? (KZ_EDGE_COLOR[kzEdge] ?? '#8b949e') : '#525252';
  const kzTitle = [
    'Killzone (S6) · /api/v9/killzone/current',
    kzZone ? `אזור: ${kzZone}${kzRaw.current_zone?.ends_at_et ? ` (עד ${kzRaw.current_zone.ends_at_et} ET)` : ''}` : 'אין נתון עדיין',
    kzEdge ? `edge: ${kzEdge}` : null,
    kzRaw.current_zone?.minutes_remaining != null ? `נותרו ${kzRaw.current_zone.minutes_remaining} דק׳` : null,
    kzRaw.next_zone?.name ? `הבא: ${kzRaw.next_zone.name} בעוד ${kzRaw.next_zone.starts_in_minutes ?? '—'} דק׳` : null,
  ].filter(Boolean).join('\n');

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
          const ms = MODE_STYLES[mode] || MODE_STYLES.UNKNOWN;
          return (
            <span
              title={mode === 'UNKNOWN'
                ? 'מצב-המסחר לא נקרא מה-backend (/api/v9/cockpit/heartbeat). אל תניח צל — בדוק לפני ירי.'
                : `מצב-מסחר: ${ms.label}`}
              style={{
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
        {/* Day-Type badge — colored per type (same palette as the labeler / build-status
            tables); dimmed until CLASSIFIED; tooltip = status/stance/reason. */}
        <span
          title={dtTitle}
          data-testid="topbar-daytype-chip"
          style={{
            fontSize: 10, fontWeight: 700, padding: '1px 7px', borderRadius: 3,
            background: `${dtColor}${dtClassified ? '26' : '14'}`,
            border: `1px solid ${dtColor}${dtClassified ? 'cc' : '55'}`,
            color: dtColor,
            opacity: dayTypeName === 'UNKNOWN' ? 0.65 : 1,
            fontFamily: 'ui-monospace, monospace',
            whiteSpace: 'nowrap',
          }}
        >
          {dayTypeName === 'UNKNOWN' ? 'DT —' : dayTypeName.replace(/_/g, ' ')}
          {dayTypeStatus && !dtClassified && dayTypeStatus !== dayTypeName && (
            <span style={{ fontWeight: 400, opacity: 0.8 }}>
              {dayTypeStatus === 'PROVISIONAL' ? ' ·prov' : ' ·forming'}
            </span>
          )}
          {dtRaw.invalidated ? ' ⚠' : ''}
        </span>
        <span className="text-xs" style={{ color: kzColor, whiteSpace: 'nowrap' }} title={kzTitle} data-testid="topbar-killzone-chip">
          {kzZone ? kzZone.replace(/_/g, ' ') : 'KZ —'}
          {kzEdge && kzEdge !== 'none' ? ` · ${kzEdge}` : ''}
          {kzGate != null ? (kzGate ? ' OPEN' : ' CLOSED') : ''}
        </span>
        {/* The "5 Min / Tick Rev" buttons were removed 23.10 (audit §4ב): they set
            layoutStore.activeChartType, which only the deleted VolumePanel/ChartArea read. */}
      </div>

      {/* Center: Live Price from Event Bus */}
      <div className="flex items-center gap-3">
        <PriceDisplay />
        <PriceMeta />
      </div>

      {/* Right: Status dots + Cap + Library + WR + Mode PnL + Nav */}
      <div className="flex items-center gap-3">
        {/* Agent-alive beacon (§6 — session-watch heartbeat) */}
        <AgentHeartbeatDot />
        {/* Status dots */}
        <div className="flex items-center gap-1" title={backendHealth ? `WS: ${backendHealth.wsClients} clients` : 'Unknown'}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
            background: backendHealth?.priceFileOk ? '#16a34a' : (backendHealth ? '#eab308' : '#525252') }} />
          <span style={{ width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
            background: backendHealth && backendHealth.wsClients > 0 ? '#16a34a' : (backendHealth ? '#dc2626' : '#525252') }} />
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
        {/* Library icon (η.J4 — V5 §3.4). 23.10: the duplicate 📚 button (it opened the
            same LibraryModal) and the second ConnectionIndicator (one is at the left
            edge of this bar) were removed (audit §4ב). */}
        <button onClick={() => setShowPlaybook(true)} title="Library (Journal / Spec / Settings)"
          style={{ fontSize: 16, cursor: 'pointer', background: 'none', border: 'none', padding: 0 }}>
          📘
        </button>
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
        {/* ניווט מסודר (מייקל 07-09: "אזור לא מסודר, לא פרקטי") — סדר קבוע:
            הלוח (משימות+לדג'ר+מערכת-6) · עסקאות · כלי-עיון · ולבסוף כפתור הפאנלים */}
        <nav style={{
          display: 'flex', alignItems: 'center', gap: 2,
          border: '1px solid var(--border, #21262d)', borderRadius: 8, padding: '1px 4px',
        }}>
          {/* דרופ-דאון הודעות-היום (מייקל 07-13) — צ'יפ קומפקטי, לא מזיז את הפריסה */}
          <NewsDropdown />
          <a
            href="/board"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-0.5 rounded hover:bg-[var(--bg-tertiary)]"
            style={{ color: 'var(--accent, #58a6ff)', whiteSpace: 'nowrap', textDecoration: 'none', fontWeight: 600 }}
            title="הלוח החי: משימות · לדג'ר סיירה · לוג מערכת 6 · עמודי המערכת"
          >
            📋 לוח
          </a>
          <Link
            href="/trades"
            className="text-xs px-2 py-0.5 rounded hover:bg-[var(--bg-tertiary)]"
            style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap', textDecoration: 'none' }}
            title="היסטוריית עסקאות + ניתוח + לוג-Sheets"
          >
            📊 עסקאות
          </Link>
          <a
            href="/patterns-visual.html"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-0.5 rounded hover:bg-[var(--bg-tertiary)]"
            style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap', textDecoration: 'none' }}
            title="Playbook תבניות — נפתח בטאב חדש"
          >
            תבניות
          </a>
          <a
            href="/trade-placement.html"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-0.5 rounded hover:bg-[var(--bg-tertiary)]"
            style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap', textDecoration: 'none' }}
            title="מיקומי-מימוש (stops/targets) — נפתח בטאב חדש"
          >
            מימושים
          </a>
        </nav>
        <button
          onClick={togglePanels}
          className="text-xs px-2 py-0.5 rounded hover:bg-[var(--bg-tertiary)]"
          style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}
          title="הסתר/הצג פאנלים צדדיים"
        >
          {panelsCollapsed ? '⊞ פאנלים' : '⊟ פאנלים'}
        </button>
      </div>
      {/* Playbook modal */}
      {showPlaybook && <LibraryModal onClose={() => setShowPlaybook(false)} />}
    </div>
  );
}
