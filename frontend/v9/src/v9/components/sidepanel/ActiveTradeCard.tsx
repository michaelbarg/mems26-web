'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { SYSTEM_META, systemColor } from '../../design/system_colors';
import { useTradeStore } from '../../stores/tradeStore';
import { exitTrade, fetchActiveTrade, getApiBase } from '../../lib/api';
import { fmtTimeET, fmtTimeIL } from '../../lib/tradeTime';
// System-6 diagnose payload + Hebrew issue titles — the same reading the /trades
// page uses for this endpoint (one source, no duplicated map).
import { CODE_TITLE as S6_CODE_TITLE, sevColor as s6SevColor, type S6Diagnose } from '../trades/TradeRecommendations';
// Live price — REUSES the store the dashboard already feeds (usePriceStream WS
// + useLivePricePoll fallback mounted in V9Dashboard). Subscribing here adds
// ZERO new network polls (CLAUDE.md Frontend Polling Floors).
import { usePriceStore } from '../../stores/priceStore';
// Shared active-trade types + math (UI round 2) — the exact same payload shape
// and distance/progress/elapsed/BE logic is imported by DemoMonitor too; single
// source, no duplication. See lib/activeTrade.ts for backend evidence.
import {
  CONTRACT_STATUS_COLORS,
  elapsedLabel,
  isStopAtBE,
  parseActiveTrade,
  progressPct,
  ptsToTarget,
  type ActiveTrade,
} from '../../lib/activeTrade';

export type ActiveTradeContext = {
  firingSystemId: number;
  entryPrice: number;
} | null;

interface ActiveTradeCardProps {
  onTradeContext?: (ctx: ActiveTradeContext) => void;
}

export function ActiveTradeCard({ onTradeContext }: ActiveTradeCardProps) {
  const [trade, setTrade] = useState<ActiveTrade | null>(null);
  // Dashboard-fed live price (WS + poll fallback) — no new request from this card.
  const livePrice = usePriceStore((s) => s.price);
  // Local clock tick for the elapsed-time label only (no network).
  const [nowMs, setNowMs] = useState<number>(() => Date.now());

  const refreshActiveTrade = () => {
    fetchActiveTrade().then((d) => {
      const t = parseActiveTrade(d);
      setTrade(t);
      if (onTradeContext) {
        onTradeContext(
          t?.firing_system
            ? { firingSystemId: t.firing_system, entryPrice: t.entry_price }
            : null,
        );
      }
    });
  };

  useEffect(() => {
    refreshActiveTrade();
    const id = setInterval(refreshActiveTrade, 10000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 30000);
    return () => clearInterval(id);
  }, []);

  if (!trade) {
    return (
      <div style={{
        padding: 12,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        borderRadius: 6,
        margin: 6,
        background: COLORS.bgSurface4,
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 10, color: COLORS.textTertiary, fontWeight: 500 }}>
          No Active Trade
        </div>
        <div style={{ fontSize: 8, color: COLORS.textDim, marginTop: 2 }}>
          Awaiting setup confirmation
        </div>
      </div>
    );
  }

  const dirColor = trade.direction === 'LONG' ? COLORS.bull : COLORS.bear;
  const isLong = trade.direction === 'LONG';
  // §3.6 5-state: Idle(no card) / Armed(yellow) / Active(green/red) / JustClosed(gray)
  const cardState = trade.hits > 0 || trade.total_pnl !== 0 ? 'Active' : 'Armed';
  const borderColor = cardState === 'Armed' ? '#eab308'
    : trade.total_pnl > 0 ? COLORS.bull
    : trade.total_pnl < 0 ? COLORS.bear
    : '#eab308';
  const entryTimeEt = trade.entry_ts ? fmtTimeET(trade.entry_ts) : '';
  const entryTimeIl = trade.entry_ts ? fmtTimeIL(trade.entry_ts) : '';
  const elapsed = elapsedLabel(trade.entry_ts, nowMs);
  // BE badge — stop parked at entry. Backend convention: |stop − entry| < 0.5
  // == breakeven (trades.py::_stop_note).
  const stopAtBE = isStopAtBE(trade.entry_price, trade.stop_price);

  return (
    <div style={{
      padding: 8,
      borderRadius: 6,
      margin: 6,
      background: COLORS.bgSurface4,
      border: `0.5px solid ${borderColor}`,
    }}>
      {/* Header: direction + entry price + time + elapsed */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 11, color: dirColor, fontWeight: 700 }}>
            {trade.direction === 'LONG' ? '▲' : '▼'} {trade.direction}
          </span>
          <span style={{ fontSize: 10, fontWeight: 600, color: COLORS.textPrimary, fontFamily: 'ui-monospace' }}>
            {trade.entry_price.toFixed(2)}
          </span>
          {/* Size actually in the market. Shown always, because "how many
              contracts am I holding" was not on this card at all — and when a
              reinforcement fired on 17.08 the card silently swapped to the
              child instead of showing the position grow. */}
          {trade.position_contracts != null && (
            <span
              style={{
                fontSize: 9, fontWeight: 700, padding: '0 4px', borderRadius: 2,
                color: COLORS.textPrimary, background: 'rgba(255,255,255,0.10)',
                fontFamily: 'ui-monospace',
              }}
              title="חוזים בפוזיציה בפועל (כולל חיזוק)"
            >
              {trade.position_contracts}c
            </span>
          )}
          {trade.scale_in && (
            <span
              style={{
                fontSize: 9, fontWeight: 700, padding: '0 4px', borderRadius: 2,
                color: COLORS.bull, background: 'rgba(38,166,154,0.18)',
                fontFamily: 'ui-monospace',
              }}
              title={`חיזוק: +${trade.scale_in.added} חוזים (עסקה ${trade.scale_in.child_id})`}
            >
              ⬆ +{trade.scale_in.added}c
            </span>
          )}
          {elapsed && (
            <span
              style={{
                fontSize: 8, fontWeight: 600, padding: '0 4px', borderRadius: 2,
                color: COLORS.textSecondary, background: 'rgba(255,255,255,0.06)',
                fontFamily: 'ui-monospace',
              }}
              title="זמן בעסקה מאז הכניסה"
            >
              ⏱ {elapsed}
            </span>
          )}
        </div>
        <span
          style={{ fontSize: 8, color: COLORS.textTertiary, fontFamily: 'ui-monospace', textAlign: 'right' }}
          title="Trade entry — New York / Israel"
        >
          {entryTimeEt} ET
          {entryTimeIl && (
            <>
              {' · '}
              <span style={{ color: COLORS.textDim }}>{entryTimeIl} IL</span>
            </>
          )}
        </span>
      </div>

      {(trade.pattern_id || trade.trigger || trade.firing_system) && (
        <div
          onClick={() => { const id = Number(trade.trade_id); if (Number.isFinite(id)) useTradeStore.getState().setSelectedTradeId(id); }}
          title="לחיצה לפירוט מלא של העסקה"
          style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4, fontSize: 8, color: COLORS.textTertiary, marginBottom: 4, lineHeight: 1.3, cursor: 'pointer' }}
        >
          {trade.firing_system ? (
            <span style={{
              fontSize: 8.5, fontWeight: 700, padding: '0 4px', borderRadius: 3,
              color: systemColor(trade.firing_system), background: `${systemColor(trade.firing_system)}22`,
              border: `1px solid ${systemColor(trade.firing_system)}66`, fontFamily: 'ui-monospace',
            }}>
              S{trade.firing_system}
            </span>
          ) : null}
          {trade.pattern_id && <span style={{ fontFamily: 'ui-monospace', color: COLORS.textSecondary }}>{trade.pattern_id}</span>}
          {trade.trigger && <span>· {trade.trigger}</span>}
          <span style={{ padding: '0 4px', borderRadius: 3, background: 'rgba(255,255,255,0.05)', color: COLORS.textSecondary }}>
            {trade.day_type && trade.day_type !== 'UNKNOWN' ? `יום: ${trade.day_type}` : 'סיווג בהתהוות'}
          </span>
          <span style={{ color: '#58a6ff' }}>· פירוט ↗</span>
        </div>
      )}

      {trade.systems && trade.systems.length > 0 && (
        <div style={{ marginBottom: 6 }}>
          <div style={{ fontSize: 7, color: COLORS.textDim, marginBottom: 3, textTransform: 'uppercase' }}>
            Systems at entry
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {trade.systems.filter((s) => s.involved).map((s) => {
              const color = SYSTEM_META[s.id]?.color ?? '#888';
              return (
                <span
                  key={s.id}
                  title={s.hint ?? s.name}
                  style={{
                    fontSize: 7,
                    padding: '2px 4px',
                    borderRadius: 3,
                    border: `1px solid ${s.is_firing ? color : COLORS.borderFaint}`,
                    background: s.is_firing ? `${color}22` : 'transparent',
                    color: s.is_firing ? color : COLORS.textTertiary,
                    fontWeight: s.is_firing ? 700 : 500,
                    fontFamily: 'ui-monospace',
                  }}
                >
                  S{s.id}
                  {s.hint ? ` ${String(s.hint).slice(0, 8)}` : ''}
                  {s.is_firing && s.entry_price != null ? ` @${s.entry_price.toFixed(2)}` : ''}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* C1/C2/C3 rows — with live distance-to-target + % progress for OPEN legs */}
      {trade.contracts.map(c => {
        const sc = CONTRACT_STATUS_COLORS[c.status] || '#737373';
        const tgt = c.target_price;
        const showDistance = c.status === 'OPEN' && tgt != null && tgt > 0;
        const dist = showDistance && tgt != null && livePrice != null
          ? ptsToTarget(tgt, livePrice, isLong)
          : null;
        const prog = showDistance && tgt != null && livePrice != null
          ? progressPct(tgt, trade.entry_price, livePrice, isLong)
          : null;
        return (
          <div key={c.id} style={{ borderBottom: `1px solid ${COLORS.borderFaint}`, padding: '2px 0' }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              fontSize: 9,
            }}>
              <span style={{ fontWeight: 600, color: COLORS.textSecondary, width: 22 }}>{c.id}</span>
              <span style={{ color: COLORS.textTertiary, fontFamily: 'ui-monospace', fontSize: 8, width: 52 }}>
                {tgt?.toFixed(2) ?? '—'}
              </span>
              <span style={{
                fontSize: 8, fontWeight: 500, padding: '0 4px', borderRadius: 2,
                color: sc, background: `${sc}15`,
              }}>
                {c.status.replace('_', ' ')}{c.smart_be ? ' ⇄' : ''}
              </span>
              <span style={{ fontFamily: 'ui-monospace', fontSize: 9, width: 40, textAlign: 'right',
                color: c.pnl >= 0 ? COLORS.bull : COLORS.bear }}>
                ${c.pnl.toFixed(0)}
              </span>
              <span style={{ fontFamily: 'ui-monospace', fontSize: 8, width: 30, textAlign: 'right',
                color: COLORS.textTertiary }}>
                {c.r.toFixed(1)}R
              </span>
            </div>
            {showDistance && (
              <div
                style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 1, paddingInlineStart: 22 }}
                title={`מרחק ליעד ${c.id} מהמחיר החי · % מהדרך כניסה→יעד`}
              >
                <span style={{ fontFamily: 'ui-monospace', fontSize: 8, color: COLORS.textTertiary, minWidth: 56 }}>
                  {dist != null
                    ? dist >= 0
                      ? `${dist.toFixed(2)}pt ליעד`
                      : `${Math.abs(dist).toFixed(2)}pt מעבר`
                    : '— אין מחיר חי'}
                </span>
                <div style={{ flex: 1, height: 3, background: COLORS.bgSurface6, borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${prog ?? 0}%`,
                    background: prog != null && prog >= 100 ? COLORS.bull : dirColor,
                    borderRadius: 2,
                    transition: 'width 300ms ease-out',
                  }} />
                </div>
                <span style={{ fontFamily: 'ui-monospace', fontSize: 8, color: COLORS.textSecondary, width: 28, textAlign: 'right' }}>
                  {prog != null ? `${prog.toFixed(0)}%` : '—'}
                </span>
              </div>
            )}
          </div>
        );
      })}

      {/* Summary footer */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 4, marginTop: 2,
        fontSize: 9,
      }}>
        <span style={{ color: COLORS.textTertiary, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          Stop {trade.stop_price.toFixed(2)}
          {stopAtBE && (
            <span
              style={{
                fontSize: 8, fontWeight: 700, padding: '0 4px', borderRadius: 2,
                color: '#eab308', background: 'rgba(234,179,8,0.12)',
                border: '1px solid rgba(234,179,8,0.4)',
              }}
              title="הסטופ בנקודת הכניסה (Break-Even)"
            >
              BE
            </span>
          )}
          <span>| {trade.summary}</span>
        </span>
        <span style={{
          fontWeight: 700, fontSize: 10, fontFamily: 'ui-monospace',
          color: trade.total_pnl >= 0 ? COLORS.bull : COLORS.bear,
        }}>
          ${trade.total_pnl.toFixed(0)} ({trade.total_r.toFixed(1)}R)
        </span>
      </div>

      {/* keyed by trade id → a new trade starts from 'טוען…', never the previous trade's diagnosis */}
      <System6Block
        key={String(trade.trade_id ?? 'none')}
        tradeId={Number.isFinite(Number(trade.trade_id)) ? Number(trade.trade_id) : null}
      />

      {/* §3.5 Flow 5: Exit button. The "Move Stop" button next to it was removed
          23.10 (audit §4ב) — it was never wired: it only popped "not wired to the API yet". */}
      <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
        <button
          onClick={async () => {
            if (!confirm('Exit all contracts?')) return;
            const tid = trade.trade_id;
            if (tid == null || Number.isNaN(Number(tid))) {
              alert('Exit failed — missing trade_id');
              return;
            }
            const result = await exitTrade(Number(tid), { reason: 'manual' });
            if (!result.ok) {
              console.error('[ActiveTradeCard] exit failed', result.status, result.error);
              const hint =
                result.status === 0
                  ? `Cannot reach backend at ${getApiBase()} — is uvicorn on :8000?`
                  : `Exit failed (${result.status}): ${result.error ?? 'unknown'}`;
              alert(hint);
              return;
            }
            refreshActiveTrade();
          }}
          style={{
            flex: 1, fontSize: 9, padding: '3px 0', borderRadius: 3, cursor: 'pointer',
            border: '1px solid #dc2626', background: 'rgba(220,38,38,0.12)', color: '#dc2626',
          }}
        >Exit</button>
      </div>
    </div>
  );
}


/**
 * System6Block — live System-6 supervisor view on the active-trade card (מייקל 07-10:
 * "שמערכת 6 תהיה שם ורואים מה היא חושבת"). Polls every 15s.
 *
 * Source: GET /api/v9/s6/diagnose/{trade_id} (alias of /api/v9/system6/diagnose/{id},
 * backend/v9/api/v9/system6_routes.py) — the 9 management invariants →
 *   { trade_id, state, outcome, healthy, issues:[{code, severity, action, detail, correction}] }
 * Read exactly like trades/TradeRecommendations.tsx. Fix 23.10 (audit §3): this block
 * looked for checks/invariants/diagnostics + ruling/verdict — fields the endpoint never
 * sends — so it always showed "אין נתוני פיקוח". An unknown id comes back as HTTP 200
 * {error}; that, a 404 or a network error → a muted note, never a throw. Read-only.
 */
function System6Block({ tradeId }: { tradeId: number | null }) {
  const [data, setData] = useState<S6Diagnose | null>(null);
  const [status, setStatus] = useState<'loading' | 'ok' | 'unavailable' | 'error'>('loading');

  useEffect(() => {
    if (tradeId == null) return; // rendered as 'unavailable' below — no setState here
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch(`${getApiBase()}/api/v9/s6/diagnose/${tradeId}`, { cache: 'no-store' });
        if (!alive) return;
        if (!res.ok) { setData(null); setStatus(res.status === 404 ? 'unavailable' : 'error'); return; }
        const d = (await res.json()) as S6Diagnose | null;
        if (!alive) return;
        if (!d || typeof d !== 'object' || Array.isArray(d) || d.error || typeof d.healthy !== 'boolean') {
          setData(d && typeof d === 'object' && !Array.isArray(d) ? d : null);
          setStatus('unavailable');
          return;
        }
        setData(d);
        setStatus('ok');
      } catch { if (alive) setStatus('error'); }
    };
    load();
    const id = setInterval(load, 15000);
    return () => { alive = false; clearInterval(id); };
  }, [tradeId]);

  const shown = tradeId == null ? 'unavailable' : status;
  const issues = shown === 'ok' ? (data?.issues ?? []) : [];
  const healthy = shown === 'ok' && data?.healthy === true && issues.length === 0;
  // Worst severity decides the headline colour (same reduction as TradeRecommendations).
  const worst = issues.reduce<string>((acc, i) => {
    const s = (i.severity || '').toUpperCase();
    if (acc === 'CRITICAL') return acc;
    if (s === 'CRITICAL') return 'CRITICAL';
    if (s === 'WARN') return 'WARN';
    return acc || s;
  }, '');

  return (
    <div style={{ marginTop: 6, padding: '5px 7px', borderRadius: 6, border: `1px solid ${COLORS.borderFaint}`, background: COLORS.bgSurface3, direction: 'rtl', textAlign: 'right' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 3 }}>
        <span style={{ fontSize: 9, fontWeight: 700, color: systemColor(6) }}>מערכת 6 — פיקוח</span>
        <a href="/board#system6" target="_blank" rel="noreferrer" style={{ fontSize: 8.5, color: '#58a6ff', textDecoration: 'none' }}>יומן הסוכן ↗</a>
      </div>
      {shown === 'ok' ? (
        <>
          <div style={{ fontSize: 8.5, fontWeight: 700, color: healthy ? COLORS.bull : s6SevColor(worst || 'WARN') }}>
            {healthy
              ? '✓ הניהול תקין — לא אותרו כשלים'
              : issues.length > 0
                ? `⚠ ${issues.length} ${issues.length === 1 ? 'כשל' : 'כשלים'} בניהול העסקה`
                : '⚠ לא תקין (ללא פירוט)'}
          </div>
          {issues.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 2 }}>
              {issues.map((iss, i) => {
                const col = s6SevColor(iss.severity);
                return (
                  <div key={`${iss.code}-${i}`} style={{ fontSize: 8.5, color: COLORS.textSecondary, lineHeight: 1.35 }}>
                    <span style={{ color: col, fontWeight: 700 }}>✗ {S6_CODE_TITLE[iss.code] ?? iss.code}</span>
                    <span style={{ color: col, fontSize: 7.5, marginInlineStart: 4 }}>
                      {(iss.severity || '').toUpperCase()}{iss.action ? ` · ${iss.action}` : ''}
                    </span>
                    {iss.detail ? (
                      <div style={{ color: COLORS.textTertiary }}><bdi>{iss.detail}</bdi></div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </>
      ) : (
        <div style={{ fontSize: 8.5, color: COLORS.textTertiary }}>
          {shown === 'loading' ? 'טוען…'
            : shown === 'error' ? 'שגיאה בקריאת מערכת 6'
            : `אין אבחון זמין${data?.error ? ` — ${data.error}` : ''}`}
        </div>
      )}
    </div>
  );
}
