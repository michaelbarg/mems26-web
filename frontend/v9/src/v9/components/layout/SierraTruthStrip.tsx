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
import { finiteOrNull, pickAccountPnl, type SierraAccountState } from '../../lib/accountPnl';

const API_BASE = getApiBase();
const POLL_MS = 15000;

type SierraState = SierraAccountState;

// Sentinels (DBL_MAX ≈ 1.8e308, inf) and non-numbers → "—", never a number (audit 23.10).
function fmt(v: number | null | undefined, d = 2): string {
  const n = finiteOrNull(v);
  return n == null ? '—' : n.toFixed(d);
}
function money(v: number | null | undefined): string {
  const n = finiteOrNull(v);
  if (n == null) return '—';
  return `${n < 0 ? '-' : ''}$${Math.abs(n).toFixed(2)}`;
}
/** גיל-הנתונים בקריאה אנושית. ביקורת-UX 29.08: הגיל הוצג רק כשהנתונים טריים,
 *  כלומר נעלם בדיוק כשצריך אותו. "לא טרי" ב-40 שניות ו"לא טרי" ב-11 שעות הם
 *  שני עולמות — בלי המספר אי-אפשר להבדיל (נמדד age_s=39,832 = 11ש').
 *  יחידות בעברית בכוונה: עם סיומת לטינית ("11.1h") מנוע ה-bidi מפריד את ה-'h'
 *  מהמספר בתוך משפט עברי ומעיף אותו לקצה הנגדי של השורה — נמדד בפועל
 *  ("11.1 … h"). מספר + יחידה עברית נשארים צמודים. */
function ageLabel(sec: number | null | undefined): string | null {
  if (sec == null || Number.isNaN(sec)) return null;
  const s = Math.max(0, Math.round(Number(sec)));
  if (s < 90) return `${s} שנ׳`;
  if (s < 5400) return `${Math.round(s / 60)} דק׳`;
  return `${(s / 3600).toFixed(1)} שע׳`;
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

  // P&L of the account we trade (lib/accountPnl). Audit 23.10: in DEMO the Account
  // Monitor looked at another account (acct_is_sim 0 vs is_sim 1 / Sim1) → "P&L יומי
  // $0.00" while Sim1 was −$175. Then the P&L comes from Sim1's own numbers and the
  // account-value cells (the other account's — DBL_MAX sentinels that day) show "—".
  const pnl = pickAccountPnl(s);
  const acctSame = pnl.source === 'account_monitor';
  const acctName = pnl.account ?? 'החשבון';
  const pnlSrcTitle = pnl.source === 'trade_account'
    ? `מהחשבון ${acctName} עצמו (open_pnl / daily_pnl) — מוניטור-החשבון של סיירה מסתכל על חשבון אחר`
    : 'מה-Account Monitor';

  const Cell = ({ label, children, title }:
    { label: string; children: React.ReactNode; title?: string }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 54 }} title={title}>
      {/* ביקורת-UX 29.08: התוויות היו textDim (#404040) = 1.91:1 ניגודיות ב-7px.
          חמש תאי-כסף צמודים ("P&L פתוח" / "P&L יומי" / "שווי חשבון" / "מזומן" /
          "פנוי למסחר") שאי-אפשר לקרוא את התווית שלהם = סיכון-לקריאה-שגויה. */}
      <span style={{ fontSize: 7, color: COLORS.textSecondary, letterSpacing: '0.4px' }}>{label}</span>
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
      {/* P&L of the account we trade (lib/accountPnl): the Account Monitor
          (sc.GetTradeAccountData — Sierra's Trade Accounts window) when it describes
          that account; when it looks at another account (DEMO on Sim1, 23.10) →
          Sim1's own open_pnl/daily_pnl. acct_ok=false → "—" (07-28 rule). */}
      <Cell label="P&L פתוח" title={`Open P/L — ${pnlSrcTitle}`}>
        <span style={{ color: pnlColor(pnl.open) }}>{money(pnl.open)}</span>
      </Cell>
      <Cell label="P&L יומי" title={`Daily P/L — ${pnlSrcTitle}`}>
        <span style={{ color: pnlColor(pnl.daily) }}>{money(pnl.daily)}</span>
      </Cell>
      {/* Value / cash / available exist only in the Account Monitor — shown only when it
          describes the account we trade (else they are another account's numbers). */}
      <Cell label="שווי חשבון" title="Account Value (NLV) — מה-Account Monitor">
        {acctSame ? money(s?.acct_account_value) : '—'}
      </Cell>
      <Cell label="מזומן" title="Cash Balance — מה-Account Monitor">
        {acctSame ? money(s?.acct_cash_balance) : '—'}
      </Cell>
      <Cell label="פנוי למסחר" title="Available Funds — מה-Account Monitor">
        {acctSame ? money(s?.acct_available_funds) : '—'}
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
      {s != null && s.acct_ok === false && (
        <span style={{ fontSize: 8, color: '#eab308' }}
          title="ה-DLL עדיין לא מייצא את נתוני ה-Account Monitor — נדרש Remote Build">
          נתוני-חשבון: ממתין לבילד
        </span>
      )}
      {pnl.monitorMismatch && (
        <span style={{ fontSize: 8, color: '#eab308' }}
          title={`ה-Account Monitor של סיירה מתאר חשבון אחר (acct_is_sim=${s?.acct_is_sim ?? '—'}) מהחשבון שהמערכת סוחרת בו (${acctName}, is_sim=${s?.is_sim ?? '—'}). ה-P&L מוצג מ-${acctName} עצמו; שווי/מזומן/פנוי — לא מוצגים.`}>
          מוניטור-חשבון ≠ {acctName}
        </span>
      )}
      {(s?.acct_trading_disabled === 1 || s?.acct_under_margin === 1) && (
        <span style={{
          fontSize: 9, fontWeight: 700, color: '#fca5a5',
          background: '#7f1d1d', borderRadius: 3, padding: '2px 8px',
        }}>
          {s?.acct_under_margin === 1 ? '🔴 מתחת למרג\'ין' : '🔴 המסחר מושבת בחשבון'}
        </span>
      )}
      {/* הגיל מוצג תמיד — עם דגש כשהנתונים לא טריים. */}
      {stale && (
        <span dir="rtl" style={{
          fontSize: 9, fontWeight: 700, color: '#facc15',
          background: 'rgba(234,179,8,0.14)', border: '1px solid rgba(234,179,8,0.45)',
          borderRadius: 3, padding: '1px 6px',
        }} title={err ? 'הקריאה ל-/api/v9/account/state נכשלה' : 'קובץ-המצב לא טרי — כל המספרים בשורה הם מהרגע הזה בעבר'}>
          {err ? 'אין קשר לחשבון' : `נתונים לא טריים${ageLabel(s?.age_s) ? ` · לפני ${ageLabel(s?.age_s)}` : ''}`}
        </span>
      )}
      {s?.age_s != null && !stale && (
        <span dir="rtl" style={{ fontSize: 8, color: COLORS.textTertiary, marginInlineStart: 'auto' }}
          title="גיל נתוני-החשבון">
          {ageLabel(s.age_s)}
        </span>
      )}
    </div>
  );
}
