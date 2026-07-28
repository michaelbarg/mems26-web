'use client';
/**
 * SierraTruthStrip — Sierra's own account truth, on the main dashboard
 * (Michael 2026-07-27: "להוסיף למערכת שלנו בפרונט האנד מהסיארה").
 *
 * Replaces the modal alert that was disabled the same evening (LOCAL_ALERTS_V1=0
 * — "מפריעה לי"): the naked-position warning now lives here as a red banner
 * instead of a popup, so it is visible without interrupting.
 *
 * Source: GET /api/v9/account/state → sierra_state.json (NOT DB synthesis).
 * Polling 15000ms (P30 floor — do not lower). Missing field = "—" (Rule 1).
 */
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { getApiBase } from '../../lib/api';

const API_BASE = getApiBase();
const POLL_MS = 15000;

interface SierraState {
  ok?: boolean; stale?: boolean; age_s?: number | null;
  position_qty?: number | null; avg_price?: number | null;
  working_orders?: number | null; is_sim?: number | null;
  order_placement_armed?: number | null;
  open_pnl?: number | null; daily_pnl?: number | null;
  high_during_pos?: number | null; low_during_pos?: number | null;
  trade_account?: string | null; symbol?: string | null;
  last_price?: number | null; daily_total_qty_filled?: number | null;
}

function fmt(v: number | null | undefined, d = 2): string {
  return v == null || Number.isNaN(v) ? '—' : Number(v).toFixed(d);
}
function money(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—';
  const n = Number(v);
  return `${n < 0 ? '-' : ''}$${Math.abs(n).toFixed(2)}`;
}

export function SierraTruthStrip() {
  const [s, setS] = useState<SierraState | null>(null);
  const [verdict, setVerdict] = useState<string | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v9/account/state`);
        if (!r.ok) { if (alive) setErr(true); return; }
        const d = await r.json();
        if (!alive) return;
        setS(d?.sierra_state ?? null);
        setVerdict(d?.verdict ?? null);
        setErr(false);
      } catch { if (alive) setErr(true); }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const qty = s?.position_qty ?? null;
  const flat = qty === 0;
  const isLive = s?.is_sim === 0;
  const stale = !!s?.stale || err;
  const dir = qty == null ? null : qty > 0 ? 'LONG' : qty < 0 ? 'SHORT' : 'FLAT';
  const dirColor = qty == null ? COLORS.textTertiary
    : qty > 0 ? '#16a34a' : qty < 0 ? '#dc2626' : COLORS.textTertiary;
  const pnlColor = (v: number | null | undefined) =>
    v == null ? COLORS.textTertiary : v > 0 ? '#16a34a' : v < 0 ? '#dc2626' : COLORS.textTertiary;

  // stops covering the position? (the banner that replaced the modal alert)
  const stops = s?.working_orders ?? null;
  const naked = !flat && qty != null && (stops === 0 || stops == null);

  const Cell = ({ label, children, title }:
    { label: string; children: React.ReactNode; title?: string }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 54 }} title={title}>
      <span style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.4px' }}>{label}</span>
      <span style={{ fontSize: 9, fontFamily: 'ui-monospace', fontWeight: 600 }}>{children}</span>
    </div>
  );

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap',
      padding: '4px 10px',
      borderBottom: `1px solid ${naked ? '#dc2626' : COLORS.borderFaint}`,
      background: naked ? 'rgba(220,38,38,0.10)' : 'transparent',
    }}>
      <span style={{
        fontSize: 8, fontWeight: 700, letterSpacing: '0.5px',
        color: isLive ? '#dc2626' : '#67e8f9',
        border: `1px solid ${isLive ? '#dc2626' : '#67e8f9'}`,
        borderRadius: 3, padding: '1px 5px',
      }} title={`חשבון ${s?.trade_account ?? '—'} · ${s?.symbol ?? '—'}`}>
        {s == null ? '—' : isLive ? 'LIVE' : 'SIM'}
      </span>

      <Cell label="פוזיציה" title="הפוזיציה הנקייה של סיירה">
        <span style={{ color: dirColor }}>
          {qty == null ? '—' : `${qty > 0 ? '+' : ''}${qty}`}{dir && qty !== 0 ? ` ${dir}` : ''}
        </span>
      </Cell>
      <Cell label="כניסה">{fmt(s?.avg_price)}</Cell>
      <Cell label="מחיר">{fmt(s?.last_price)}</Cell>
      <Cell label="P&L פתוח">
        <span style={{ color: pnlColor(s?.open_pnl) }}>{money(s?.open_pnl)}</span>
      </Cell>
      <Cell label="P&L יומי" title="הרווח/הפסד היומי של החשבון — ישירות מסיירה">
        <span style={{ color: pnlColor(s?.daily_pnl) }}>{money(s?.daily_pnl)}</span>
      </Cell>
      <Cell label="פקודות" title="פקודות עובדות (סטופים/יעדים)">
        <span style={{ color: naked ? '#dc2626' : COLORS.textSecondary }}>{stops ?? '—'}</span>
      </Cell>
      {!flat && (
        <Cell label="שיא/שפל" title="High/Low במהלך הפוזיציה">
          {fmt(s?.high_during_pos)}/{fmt(s?.low_during_pos)}
        </Cell>
      )}
      <Cell label="חוזים היום">{s?.daily_total_qty_filled ?? '—'}</Cell>
      {verdict && (
        <Cell label="בעלות" title="manual = פוזיציה ידנית של מייקל · system = של המערכת">
          <span style={{ color: COLORS.textSecondary }}>{verdict}</span>
        </Cell>
      )}

      {naked && (
        <span style={{
          fontSize: 9, fontWeight: 700, color: '#fca5a5',
          background: '#7f1d1d', borderRadius: 3, padding: '2px 8px',
        }} title="אין פקודות-עובדות על הפוזיציה — הצב סטופ בסיירה">
          🔴 פוזיציה ללא הגנה — הצב סטופ
        </span>
      )}
      {stale && (
        <span style={{ fontSize: 8, color: '#eab308' }} title="קובץ-המצב לא טרי">
          נתוני-סיירה לא טריים
        </span>
      )}
      {s?.age_s != null && !stale && (
        <span style={{ fontSize: 7, color: COLORS.textDim, marginInlineStart: 'auto' }}>
          {Number(s.age_s).toFixed(0)}s
        </span>
      )}
    </div>
  );
}
