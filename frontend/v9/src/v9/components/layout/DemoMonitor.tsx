'use client';
import { useEffect, useState } from 'react';

// Pipeline 5 DEMO supervision: a floating button + panel showing the live active
// trade (pattern / entry / stop+BE / C1-C3 with live distance + progress) and the
// recent trades (שעה · תבנית · P&L · סיבת-יציאה · mode · תוצאה).
//
// UI round 2 (2026-07-02):
// - /active is parsed with the REAL payload shape (trade_id — not id; contracts is
//   an ARRAY of C1/C2/C3 rows — trades.py:279-294). The old reads (active.id,
//   active.stop, numeric contracts) never matched, so the panel always said
//   "אין עסקה פעילה" even mid-trade.
// - Distance/progress/elapsed/BE logic is IMPORTED from lib/activeTrade.ts — the
//   exact same helpers the round-1 ActiveTradeCard uses (no duplication).
// - Live price comes from usePriceStore (fed by the dashboard's WS + poll
//   fallback) — ZERO new price requests. The subscription lives INSIDE the
//   open-panel component so price ticks never re-render the closed button.
// - Poll intervals unchanged: /active 5000ms always; recent+status 4000ms only
//   while the panel is open.
// - Pre-existing tsc error fixed: the /status response is typed ({mode?: string},
//   status.py:334) instead of `{} | {}`.
import { fetchActiveTrade, fetchRecentTrades } from '../../lib/api';
import { fmtTimeET } from '../../lib/tradeTime';
import { usePriceStore } from '../../stores/priceStore';
import { dayTypeColor, dayTypeAbbrev } from '../../lib/dayType';
import {
  CONTRACT_STATUS_COLORS,
  elapsedLabel,
  isStopAtBE,
  parseActiveTrade,
  progressPct,
  ptsToTarget,
  type ActiveTrade,
} from '../../lib/activeTrade';
import type { Trade } from '../../types';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const fmt = (n: number | null | undefined): string =>
  n == null ? '—' : n.toLocaleString(undefined, { maximumFractionDigits: 2 });

/** Money — "+$123" / "-$45" (rendered inside dir="ltr"). */
const money = (v: number | null | undefined): string =>
  v == null ? '—' : (v >= 0 ? '+$' : '-$') + Math.abs(v).toFixed(0);

const HE_STATUS: Record<string, string> = {
  OPEN: 'פתוח',
  HIT_TARGET: 'יעד ✓',
  HIT_STOP: 'סטופ ✗',
  BE: 'BE',
};

/** Normalized frontend mode (mapTradeRow: demo→SIM, shadow→SHADOW, live→LIVE) → chip. */
const MODE_CHIP: Record<string, { label: string; color: string }> = {
  SIM: { label: 'DEMO', color: '#06b6d4' },
  SHADOW: { label: 'SHDW', color: '#facc15' },
  LIVE: { label: 'LIVE', color: '#f85149' },
};

const outcomeIcon = (t: Trade): { i: string; c: string } => {
  const o = (t.outcome || '').toUpperCase();
  const p = t.pnl_usd;
  if (o === 'WIN' || (o === '' && p != null && p > 0)) return { i: '✓', c: '#2ea043' };
  if (o === 'LOSS' || (o === '' && p != null && p < 0)) return { i: '✗', c: '#f85149' };
  if (o === 'OPEN' || (!t.exit_ts && p == null)) return { i: '•', c: '#8b949e' };
  return { i: '=', c: '#d29922' }; // BE / SCRATCH
};

function KV({ k, v, hi, dim, tag }: { k: string; v: string; hi?: boolean; dim?: boolean; tag?: string }) {
  return (
    <div style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 6, padding: '6px 8px' }}>
      <div style={{ fontSize: 10, color: '#8b949e' }}>{k}</div>
      <div style={{ fontSize: 15, fontWeight: 700, marginTop: 2, color: hi ? '#2ea043' : dim ? '#8b949e' : '#e6edf3', display: 'flex', alignItems: 'center', gap: 6 }}>
        <span dir="ltr">{v}</span>
        {tag && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '0 5px', borderRadius: 3,
            color: '#d29922', background: 'rgba(210,153,34,0.12)', border: '1px solid rgba(210,153,34,0.45)',
          }} title="הסטופ בנקודת הכניסה (Break-Even)">{tag}</span>
        )}
      </div>
    </div>
  );
}

/** The ACTIVE-trade body — mounted only while the panel is open AND a trade is
 *  live, so the price-store subscription + elapsed tick exist only then. */
function ActiveTradePanel({ t }: { t: ActiveTrade }) {
  // Dashboard-fed live price (WS + 5s poll fallback) — no new request from here.
  const livePrice = usePriceStore((s) => s.price);
  // Local clock tick for the elapsed label only (no network) — same as ActiveTradeCard.
  const [nowMs, setNowMs] = useState<number>(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 30000);
    return () => clearInterval(id);
  }, []);

  const isLong = t.direction === 'LONG';
  const dirColor = isLong ? '#2ea043' : '#f85149';
  const stopBE = isStopAtBE(t.entry_price, t.stop_price);
  const elapsed = elapsedLabel(t.entry_ts, nowMs);
  const pattern = t.pattern_id || t.classification || t.trigger || null;

  return (
    <div style={{ border: `1px solid ${dirColor}55`, borderRadius: 8, padding: 12, marginBottom: 10 }}>
      {/* Header: direction · id · pattern · day-type · state · elapsed · total P&L */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
        <span style={{ fontWeight: 800, fontSize: 18, color: dirColor }} dir="ltr">
          {isLong ? '▲ LONG' : '▼ SHORT'}
        </span>
        <span style={{ color: '#8b949e', fontSize: 12 }} dir="ltr">#{t.trade_id}</span>
        {pattern && (
          <span style={{
            fontFamily: 'monospace', fontSize: 12, fontWeight: 700, color: '#e3b341',
            background: 'rgba(227,179,65,0.08)', border: '1px solid rgba(227,179,65,0.35)',
            padding: '1px 7px', borderRadius: 5,
          }} dir="ltr" title="תבנית הכניסה">{pattern}</span>
        )}
        {t.day_type && (
          <span style={{
            fontSize: 11, fontWeight: 700, padding: '1px 7px', borderRadius: 5,
            color: dayTypeColor(t.day_type), background: `${dayTypeColor(t.day_type)}1a`,
            border: `1px solid ${dayTypeColor(t.day_type)}55`,
          }} dir="ltr" title={`סוג-יום: ${t.day_type}`}>{dayTypeAbbrev(t.day_type)}</span>
        )}
        {t.state && <span style={{ color: '#8b949e', fontSize: 11 }} dir="ltr">{t.state}</span>}
        {elapsed && (
          <span style={{ fontSize: 11, color: '#8b949e', fontFamily: 'monospace' }} title="זמן בעסקה מאז הכניסה" dir="ltr">
            ⏱ {elapsed}
          </span>
        )}
        <span style={{ marginInlineStart: 'auto', fontWeight: 800, color: t.total_pnl >= 0 ? '#2ea043' : '#f85149' }} dir="ltr">
          {money(t.total_pnl)} ({t.total_r.toFixed(1)}R)
        </span>
      </div>

      {/* Entry / current stop (+BE) / hits summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8, marginBottom: 8 }}>
        <KV k="כניסה" v={fmt(t.entry_price)} />
        <KV k="סטופ נוכחי" v={fmt(t.stop_price)} hi={stopBE} tag={stopBE ? 'BE' : undefined} />
        <KV k="יעדים" v={t.summary} dim />
      </div>

      {/* C1/C2/C3 — live distance in points + % progress for OPEN legs
          (same math as ActiveTradeCard via lib/activeTrade) */}
      {t.contracts.map((c) => {
        const sc = CONTRACT_STATUS_COLORS[c.status] || '#737373';
        const tgt = c.target_price;
        const isOpen = c.status === 'OPEN' && tgt != null && tgt > 0;
        const dist = isOpen && tgt != null && livePrice != null ? ptsToTarget(tgt, livePrice, isLong) : null;
        const prog = isOpen && tgt != null && livePrice != null ? progressPct(tgt, t.entry_price, livePrice, isLong) : null;
        return (
          <div key={c.id} style={{ borderTop: '1px solid #1c222b', padding: '5px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
              <span style={{ fontWeight: 700, color: '#e6edf3', width: 22 }} dir="ltr">{c.id}</span>
              <span style={{ fontFamily: 'monospace', color: '#8b949e', width: 62 }} dir="ltr" title="מחיר היעד">
                {tgt != null ? tgt.toFixed(2) : '—'}
              </span>
              <span style={{
                fontSize: 10, fontWeight: 600, padding: '0 6px', borderRadius: 3,
                color: sc, background: `${sc}18`,
              }} title={c.status}>
                {HE_STATUS[c.status] ?? c.status}{c.smart_be ? ' ⇄' : ''}
              </span>
              {!isOpen && (
                <span style={{ marginInlineStart: 'auto', fontFamily: 'monospace', fontSize: 12, color: c.pnl >= 0 ? '#2ea043' : '#f85149' }} dir="ltr">
                  {money(c.pnl)} · {c.r.toFixed(1)}R
                </span>
              )}
            </div>
            {isOpen && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 3, paddingInlineStart: 22 }}
                title={`מרחק ליעד ${c.id} מהמחיר החי · % מהדרך כניסה→יעד`}>
                <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#8b949e', minWidth: 86 }} dir="ltr">
                  {dist != null
                    ? dist >= 0 ? `${dist.toFixed(2)}pt ליעד` : `${Math.abs(dist).toFixed(2)}pt מעבר`
                    : '— אין מחיר חי'}
                </span>
                <div style={{ flex: 1, height: 4, background: '#1c222b', borderRadius: 2, overflow: 'hidden' }} dir="ltr">
                  <div style={{
                    height: '100%', width: `${prog ?? 0}%`,
                    background: prog != null && prog >= 100 ? '#2ea043' : dirColor,
                    borderRadius: 2, transition: 'width 300ms ease-out',
                  }} />
                </div>
                <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#c9d1d9', width: 34, textAlign: 'left' }} dir="ltr">
                  {prog != null ? `${prog.toFixed(0)}%` : '—'}
                </span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** System 6 supervision — recommendation + HOLD gate + 9 checks + exit signals.
 *  Reads /api/v9/system6/diagnose (which follows demo_slot → live_slot). Mounted
 *  only while a trade is active, so it polls only then. */
function System6Panel() {
  const [d, setD] = useState<{
    active?: boolean;
    trade?: unknown;
    recommendation?: string;
    hold?: { intact?: boolean; continuing?: boolean; broke?: boolean; score?: number; reason?: string };
    supervisor?: { healthy?: boolean; issues?: { code: string; severity: string; action: string; detail: string }[] };
    exit_signals?: { kind: string; score?: number; fired?: boolean; reason?: string; action?: string }[];
  } | null>(null);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const r = await fetch(`${API}/api/v9/system6/diagnose`);
        const j = r.ok ? await r.json() : null;
        if (alive) setD(j);
      } catch { if (alive) setD(null); }
    };
    poll();
    const t = setInterval(poll, 5000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  if (!d || !d.active || !d.trade) return null;
  const REC: Record<string, { l: string; c: string }> = {
    hold: { l: 'החזק ✋', c: '#2ea043' },
    consider_exit: { l: 'שקול יציאה ⚠', c: '#d29922' },
    exit: { l: 'צא ▸', c: '#f85149' },
  };
  const rc = REC[d.recommendation || 'hold'] || REC.hold;
  const hold = d.hold;
  const sup = d.supervisor;
  const sigs = d.exit_signals || [];

  return (
    <div style={{ border: `1px solid ${rc.c}55`, borderRadius: 8, padding: 12, marginBottom: 10, background: '#0d1117' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <b style={{ fontSize: 14 }}>🛰 מערכת 6 — פיקוח</b>
        <span style={{ marginInlineStart: 'auto', fontWeight: 800, color: rc.c, fontSize: 15 }} title="המלצת מערכת 6">{rc.l}</span>
      </div>
      {hold && (
        <div style={{ fontSize: 12, marginBottom: 6 }}>
          <span style={{ color: hold.broke ? '#f85149' : hold.continuing ? '#2ea043' : '#d29922', fontWeight: 700 }}>
            {hold.broke ? 'התבנית נשברה — שקול יציאה' : hold.continuing ? 'התבנית ממשיכה עם המגמה' : 'התבנית שלמה'}
          </span>
          {hold.reason && <span style={{ color: '#8b949e' }}> · {hold.reason}</span>}
        </div>
      )}
      {sup && (sup.healthy ? (
        <div style={{ fontSize: 12, color: '#2ea043', marginBottom: 6 }}>✓ 9 בדיקות-ניהול תקינות</div>
      ) : (
        <div style={{ fontSize: 12, marginBottom: 6, display: 'grid', gap: 2 }}>
          {(sup.issues || []).map((i, k) => (
            <div key={k} style={{ color: i.severity === 'CRITICAL' ? '#f85149' : '#d29922' }} dir="rtl">
              ⚠ <span dir="ltr" style={{ fontFamily: 'monospace' }}>{i.code}</span> · {i.detail} → <b>{i.action}</b>
            </div>
          ))}
        </div>
      ))}
      {sigs.length > 0 && (
        <div style={{ display: 'grid', gap: 3, borderTop: '1px solid #1c222b', paddingTop: 6 }}>
          {sigs.map((s, k) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
              <span>{s.fired ? '🔴' : '⚪'}</span>
              <span style={{ fontFamily: 'monospace', color: '#8b949e', minWidth: 118 }} dir="ltr">{s.kind}</span>
              <span style={{ color: s.fired ? '#e6edf3' : '#6e7681' }}>{s.reason}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function DemoMonitor() {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<ActiveTrade | null>(null);
  const [recent, setRecent] = useState<Trade[]>([]);
  const [mode, setMode] = useState<string>('');
  // Real trading mode: MEMS26_MODE (/status) is a legacy display label; the true
  // live state is the gateway's live_enabled_systems (LIVE_TRADING_V1). Show LIVE
  // when the gateway is routing live, regardless of the MEMS26_MODE env label.
  const [live, setLive] = useState(false);

  // Always poll the active trade (drives the button indicator). 5s — unchanged interval.
  useEffect(() => {
    let alive = true;
    const poll = async () => {
      const d = await fetchActiveTrade(); // publicApiFetch — never throws, null on failure
      if (alive) setActive(parseActiveTrade(d));
    };
    poll();
    const t = setInterval(poll, 5000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  // When the panel is open, also poll recent trades + mode. 4s — unchanged interval.
  useEffect(() => {
    if (!open) return;
    let alive = true;
    const poll = async () => {
      const [rs, ss, gs] = await Promise.all([
        fetchRecentTrades(10).catch(() => [] as Trade[]),
        fetch(`${API}/api/v9/status`)
          .then((r) => (r.ok ? (r.json() as Promise<{ mode?: string }>) : Promise.resolve({} as { mode?: string })))
          .catch(() => ({} as { mode?: string })),
        fetch(`${API}/api/v9/gateway/status`)
          .then((r) => (r.ok ? (r.json() as Promise<{ live_enabled_systems?: number[] }>) : Promise.resolve({} as { live_enabled_systems?: number[] })))
          .catch(() => ({} as { live_enabled_systems?: number[] })),
      ]);
      if (!alive) return;
      setRecent(rs);
      setMode(ss.mode ?? '');
      setLive(Array.isArray(gs.live_enabled_systems) && gs.live_enabled_systems.length > 0);
    };
    poll();
    const t = setInterval(poll, 4000);
    return () => { alive = false; clearInterval(t); };
  }, [open]);

  const hasActive = active != null;
  const modeColor = live ? '#f85149' : mode === 'demo' ? '#d29922' : mode === 'live' ? '#f85149' : '#6e7681';

  return (
    <>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position: 'fixed', bottom: 16, right: 16, zIndex: 60,
          background: '#161b22', color: '#e6edf3', border: '1px solid #30363d', borderRadius: 8,
          padding: '8px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          boxShadow: '0 4px 14px rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', gap: 8,
        }}
      >
        <span style={{
          width: 9, height: 9, borderRadius: '50%', background: hasActive ? '#2ea043' : '#6e7681',
          boxShadow: hasActive ? '0 0 0 3px rgba(46,160,67,0.25)' : 'none',
        }} />
        מוניטור עסקה{hasActive ? ' · פעילה' : ''}
      </button>

      {open && (
        <div dir="rtl" style={{
          position: 'fixed', bottom: 60, right: 16, zIndex: 60, width: 480, maxWidth: 'calc(100vw - 32px)',
          maxHeight: '72vh', overflow: 'auto', background: '#0e1117', color: '#e6edf3',
          border: '1px solid #30363d', borderRadius: 10, boxShadow: '0 8px 28px rgba(0,0,0,0.5)',
          padding: 14, fontSize: 13,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <b>מוניטור פיקוח</b>
            <span style={{ background: modeColor, color: '#10131a', fontWeight: 700, padding: '2px 10px', borderRadius: 5, fontSize: 12 }} title="מצב המסחר בפועל (ניתוב live של הגייטוויי)">
              {live ? 'LIVE' : (mode || 'shadow').toUpperCase()}
            </span>
          </div>

          {active ? (
            <>
              <ActiveTradePanel t={active} />
              <System6Panel />
            </>
          ) : (
            <div style={{ color: '#8b949e', textAlign: 'center', padding: 18 }}>אין עסקה פעילה — ממתין ל-setup.</div>
          )}

          <div style={{ fontSize: 11, color: '#8b949e', margin: '6px 2px' }}>אחרונות</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ color: '#8b949e', fontSize: 10 }}>
                <th style={{ padding: '2px 6px', fontWeight: 500, textAlign: 'start' }}>שעה</th>
                <th style={{ padding: '2px 6px', fontWeight: 500, textAlign: 'start' }}>#</th>
                <th style={{ padding: '2px 6px', fontWeight: 500, textAlign: 'start' }}>תבנית</th>
                <th style={{ padding: '2px 6px', fontWeight: 500, textAlign: 'start' }}>כיוון</th>
                <th style={{ padding: '2px 6px', fontWeight: 500, textAlign: 'start' }}>מצב</th>
                <th style={{ padding: '2px 6px', fontWeight: 500, textAlign: 'end' }}>P&L$</th>
                <th style={{ padding: '2px 6px', fontWeight: 500, textAlign: 'center' }} title="תוצאה">✓</th>
                <th style={{ padding: '2px 6px', fontWeight: 500, textAlign: 'start' }}>סיבת-יציאה</th>
              </tr>
            </thead>
            <tbody>
              {recent.length ? recent.map((t) => {
                const oc = outcomeIcon(t);
                const mc = MODE_CHIP[t.mode ?? ''] ?? { label: t.mode || '—', color: '#8b949e' };
                const pattern = t.pattern_id || t.classification || t.trigger || '—';
                return (
                  <tr key={t.id} style={{ borderBottom: '1px solid #1c222b' }}>
                    <td style={{ padding: '4px 6px', color: '#8b949e', fontFamily: 'monospace' }} dir="ltr">
                      {t.entry_ts ? fmtTimeET(t.entry_ts) : '—'}
                    </td>
                    <td style={{ padding: '4px 6px', color: '#8b949e' }} dir="ltr">#{t.id}</td>
                    <td style={{ padding: '4px 6px', fontFamily: 'monospace', maxWidth: 110, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} dir="ltr" title={String(pattern)}>
                      {pattern}
                    </td>
                    <td style={{ padding: '4px 6px', color: t.direction === 'LONG' ? '#2ea043' : '#f85149', fontWeight: 600 }} dir="ltr">
                      {t.direction === 'LONG' ? '▲L' : '▼S'}
                    </td>
                    <td style={{ padding: '4px 6px' }}>
                      <span style={{ fontSize: 10, fontWeight: 700, color: mc.color, border: `1px solid ${mc.color}55`, borderRadius: 3, padding: '0 4px' }} title={t.mode ?? ''}>
                        {mc.label}
                      </span>
                    </td>
                    <td style={{ padding: '4px 6px', textAlign: 'end', fontFamily: 'monospace', color: t.pnl_usd == null ? '#8b949e' : t.pnl_usd >= 0 ? '#2ea043' : '#f85149' }} dir="ltr">
                      {t.pnl_usd != null ? money(t.pnl_usd) : '—'}
                    </td>
                    <td style={{ padding: '4px 6px', textAlign: 'center', color: oc.c, fontWeight: 700 }}>{oc.i}</td>
                    <td style={{ padding: '4px 6px', color: '#8b949e', fontFamily: 'monospace', fontSize: 11, maxWidth: 92, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} dir="ltr" title={t.exit_reason ?? ''}>
                      {t.exit_reason ?? (t.state || '—')}
                    </td>
                  </tr>
                );
              }) : (
                <tr><td colSpan={8} style={{ color: '#8b949e', padding: 6 }}>—</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
