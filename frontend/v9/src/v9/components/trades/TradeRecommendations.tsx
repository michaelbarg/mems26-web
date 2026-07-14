'use client';
// TradeRecommendations — per-trade "מה השתבש + המלצת-שיפור" (what went wrong +
// improvement recommendation), read-only / display-only. Added for quick
// per-trade review on the /trades page; mounted inside TradeRowExpand.
//
// Source of truth: GET /api/v9/s6/diagnose/{id} (alias of
// /api/v9/system6/diagnose/{id}) — the System-6 supervisor's 9 management
// invariants → { healthy, issues:[{code, severity, action, detail, correction}] }.
// The endpoint diagnoses only; it never executes. This component only renders it.
//
// Fail-soft (mandatory): a 404 (pre-restart backend), a network error, a non-JSON
// body, or an {error:...} payload all collapse to a muted "אין אבחון זמין" note —
// it never throws. The derived hints (R:R, סיכון, T1-hit, סטופ→BE, MFE/MAE) are
// computed purely from the already-loaded trade row, so they still render even
// when the endpoint is unavailable. No localStorage, no mutations, no shared state.
import { useEffect, useState } from 'react';
import type { Trade } from '../../types';
import { getApiBase } from '../../lib/api';

interface S6Correction {
  op?: string;
  price?: number;
  target?: string;
}
interface S6Issue {
  code: string;
  severity: string; // INFO | WARN | CRITICAL
  action?: string; // AUTO | ALERT
  detail: string;
  correction?: S6Correction | null;
}
interface S6Diagnose {
  trade_id?: number;
  state?: string | null;
  outcome?: string | null;
  healthy?: boolean;
  issues?: S6Issue[];
  error?: string;
}

type LoadState = 'loading' | 'ok' | 'unavailable';

// code → Hebrew "מה השתבש" headline. The raw English `detail` (with live numbers)
// is always shown underneath, so an unmapped/new code still renders sensibly.
const CODE_TITLE: Record<string, string> = {
  reconcile_mismatch: 'מקורות הפוזיציה לא מסונכרנים (gateway / DB / Sierra)',
  no_entry: 'לעסקה אין מחיר כניסה',
  naked_stop: 'פוזיציה פתוחה ללא סטופ מגן',
  stop_wrong_side: 'הסטופ בצד הלא-נכון של הכניסה',
  stop_not_at_be: 'T1 נגע אך הסטופ לא הועבר ל-BE',
  stop_too_tight: 'סטופ צר מדי (ממומן) — מתחת לרצפת ATR',
  stop_too_wide: 'סטופ רחב מדי — מעל התקרה',
  t1_wrong_side: 'יעד T1 בצד הלא-נכון של הכניסה',
  t2_wrong_side: 'יעד T2 בצד הלא-נכון של הכניסה',
  t3_wrong_side: 'יעד T3 בצד הלא-נכון של הכניסה',
  t1_too_close: 'T1 קרוב מדי לכניסה — לא שווה',
  contract_mismatch: 'מספר החוזים שונה מהצפוי',
  eod_open_position: 'פוזיציה פתוחה בתוך חלון סגירת-היום',
};

// code → Hebrew "המלצה" fallback, used when the API brings no structured
// `correction` object (that dict, when present, wins — see recommendationText).
const CODE_ADVICE: Record<string, string> = {
  reconcile_mismatch: 'בצע reconcile ידני / FLATTEN_ACCOUNT ואמת מול Sierra לפני המשך',
  no_entry: 'בדוק את רישום העסקה — חסר מחיר כניסה',
  naked_stop: 'הצב סטופ מגן מייד (לפחות ב-BE)',
  stop_wrong_side: 'מקם את הסטופ בצד המגן — LONG מתחת לכניסה, SHORT מעליה',
  stop_not_at_be: 'העבר את הסטופ ל-BE אחרי מגע T1',
  stop_too_tight: 'הרחב את הסטופ אל מעל רצפת ה-ATR (או דלג על הכניסה)',
  stop_too_wide: 'הדק את הסטופ אל מתחת לתקרה / בחר מבנה כניסה קרוב יותר',
  t1_wrong_side: 'תקן את יעד T1 לצד הרווח',
  t2_wrong_side: 'תקן את יעד T2 לצד הרווח',
  t3_wrong_side: 'תקן את יעד T3 לצד הרווח',
  t1_too_close: 'בחר T1 רחוק יותר (מעל רצפת ATR) — אחרת אין ערך במימוש',
  contract_mismatch: 'התאם את מספר החוזים לצפוי',
  eod_open_position: 'שקול לסגור את הפוזיציה לפני חלון ה-EOD',
};

function sevColor(sev: string | undefined): string {
  const s = (sev || '').toUpperCase();
  if (s === 'CRITICAL') return 'var(--red)';
  if (s === 'WARN') return '#eab308';
  return 'var(--text-secondary)'; // INFO / unknown
}

function recommendationText(iss: S6Issue): string {
  const c = iss.correction;
  if (c && c.op === 'MODIFY_STOP' && typeof c.price === 'number') return `העבר את הסטופ ל-${c.price}`;
  if (c && c.op === 'DROP_TARGET' && c.target) return `הסר את היעד ${String(c.target).toUpperCase()} (צד שגוי)`;
  if (c && c.op) return `בצע ${c.op}${c.price != null ? ` @ ${c.price}` : ''}`;
  return CODE_ADVICE[iss.code] ?? 'בדוק ידנית מול פרוטוקול הניהול';
}

// ── derived, endpoint-independent hints (pure from the trade row) ─────────────
interface Hint {
  label: string;
  value: string;
  color?: string;
}

function deriveHints(t: Trade): Hint[] {
  const hints: Hint[] = [];
  const entry = t.entry_price;
  const stopInit = t.stop_initial ?? t.stop ?? null;
  const risk = entry != null && stopInit != null ? Math.abs(entry - stopInit) : null;
  const t1 = t.t1 != null && t.t1 > 0 ? t.t1 : null;
  const t1dist = entry != null && t1 != null ? Math.abs(t1 - entry) : null;

  // stop distance vs T1 distance → R:R note (the requested derived hint)
  if (risk != null && risk > 0 && t1dist != null) {
    const rr = t1dist / risk;
    const col = rr >= 1.5 ? 'var(--green)' : rr >= 1 ? '#eab308' : 'var(--red)';
    hints.push({ label: 'יחס סיכון/סיכוי (T1)', value: `1:${rr.toFixed(2)}`, color: col });
  } else {
    hints.push({ label: 'יחס סיכון/סיכוי (T1)', value: '—', color: 'var(--text-muted)' });
  }

  // absolute risk in points (financed-stop smell test: >25 red, >10 amber)
  if (risk != null) {
    const col = risk > 25 ? 'var(--red)' : risk > 10 ? '#eab308' : 'var(--green)';
    hints.push({ label: 'סיכון (נק׳)', value: `${risk.toFixed(1)}pt`, color: col });
  }

  // whether T1 was hit (the requested derived hint)
  hints.push(
    t.t1_hit
      ? { label: 'T1', value: 'נגע ✓', color: 'var(--green)' }
      : { label: 'T1', value: 'לא נגע', color: 'var(--text-muted)' },
  );

  // stop → BE follow-through
  if (t.stop_issue === 'T1_NO_BE') {
    hints.push({ label: 'סטופ → BE', value: '⚠ T1 נגע אך הסטופ לא זז', color: '#eab308' });
  } else if (t.t1_hit && entry != null && t.stop != null && Math.abs(t.stop - entry) < 0.5) {
    hints.push({ label: 'סטופ → BE', value: 'הועבר ל-BE ✓', color: 'var(--green)' });
  }

  // realized excursion, if the backend computed it
  if (t.mfe_pts != null || t.mae_pts != null) {
    const mfe = t.mfe_pts != null ? `+${t.mfe_pts.toFixed(1)}` : '—';
    const mae = t.mae_pts != null ? `−${Math.abs(t.mae_pts).toFixed(1)}` : '—';
    hints.push({ label: 'מהלך (MFE / MAE)', value: `${mfe} / ${mae} נק׳`, color: 'var(--text-secondary)' });
  }

  return hints;
}

export function TradeRecommendations({ trade }: { trade: Trade }) {
  const [state, setState] = useState<LoadState>('loading');
  const [data, setData] = useState<S6Diagnose | null>(null);

  useEffect(() => {
    // One expanded row at a time (TradesTable keys the expand by trade id), so
    // this component mounts fresh per trade → the useState defaults ('loading' /
    // null) are the reset; no synchronous setState in the effect body needed.
    let dead = false;
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 12_000);

    const base = getApiBase();
    const token = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';
    fetch(`${base}/api/v9/s6/diagnose/${trade.id}`, {
      signal: ctrl.signal,
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (dead) return;
        if (!res.ok) {
          // 404 (pre-restart alias missing) / 401 / 5xx → fail-soft, keep hints.
          setState('unavailable');
          return;
        }
        const json = (await res.json()) as S6Diagnose;
        if (dead) return;
        if (!json || typeof json !== 'object' || Array.isArray(json) || json.error) {
          setData(json && typeof json === 'object' ? json : null);
          setState('unavailable');
          return;
        }
        setData(json);
        setState('ok');
      })
      .catch(() => {
        if (!dead) setState('unavailable');
      })
      .finally(() => clearTimeout(timer));

    return () => {
      dead = true;
      ctrl.abort();
      clearTimeout(timer);
    };
  }, [trade.id]);

  const hints = deriveHints(trade);
  const issues = data?.issues ?? [];
  const healthy = state === 'ok' && data?.healthy === true && issues.length === 0;
  const worst = issues.reduce<string>((acc, i) => {
    const s = (i.severity || '').toUpperCase();
    if (acc === 'CRITICAL') return acc;
    if (s === 'CRITICAL') return 'CRITICAL';
    if (s === 'WARN') return 'WARN';
    return acc || s;
  }, '');

  const pattern = trade.pattern_id ?? '—';
  const dayType = trade.day_type && trade.day_type !== 'UNKNOWN' ? trade.day_type : 'בהתהוות';
  const outcome = data?.outcome ?? trade.outcome ?? null;

  return (
    <div
      className="mb-3 p-2 rounded"
      style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
    >
      {/* Title + context (pattern · day-type · outcome) */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
          המלצות · מה השתבש + שיפור
        </span>
        <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
          תבנית <b style={{ color: 'var(--text-primary)' }}>{pattern}</b> · סוג-יום{' '}
          <b style={{ color: 'var(--text-primary)' }}>{dayType}</b>
          {outcome ? (
            <>
              {' · '}תוצאה <b style={{ color: 'var(--text-primary)' }}>{outcome}</b>
            </>
          ) : null}
        </span>
      </div>

      {/* One-line verdict */}
      <div className="mb-2 text-[11px]" style={{ lineHeight: 1.5 }}>
        {state === 'loading' && <span style={{ color: 'var(--text-muted)' }}>טוען אבחון…</span>}
        {state === 'unavailable' && (
          <span style={{ color: 'var(--text-muted)' }}>
            אין אבחון זמין (System-6){data?.error ? ` — ${data.error}` : ' — יופיע לאחר restart של ה-backend'}. מוצגים רמזים נגזרים מנתוני העסקה בלבד.
          </span>
        )}
        {state === 'ok' && healthy && (
          <span style={{ color: 'var(--green)', fontWeight: 600 }}>✓ הניהול תקין — לא אותרו כשלים ב-System-6</span>
        )}
        {state === 'ok' && !healthy && (
          <span style={{ color: sevColor(worst), fontWeight: 600 }}>
            ⚠ אותרו {issues.length} כשלים בניהול העסקה
          </span>
        )}
      </div>

      {/* Issues — each: "מה השתבש" + "המלצה" */}
      {state === 'ok' && issues.length > 0 && (
        <div className="space-y-2 mb-2">
          {issues.map((iss, i) => {
            const col = sevColor(iss.severity);
            return (
              <div
                key={`${iss.code}-${i}`}
                className="p-2 rounded border"
                style={{ borderColor: col, background: 'var(--bg-primary)' }}
              >
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span style={{ color: col, fontWeight: 700 }}>{CODE_TITLE[iss.code] ?? iss.code}</span>
                  <span
                    className="text-[9px] px-1 rounded uppercase"
                    style={{ color: col, border: `1px solid ${col}`, background: 'rgba(255,255,255,0.04)' }}
                  >
                    {iss.severity}
                    {iss.action ? ` · ${iss.action}` : ''}
                  </span>
                </div>
                <div className="text-[10.5px]" style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>מה השתבש: </span>
                  <bdi>{iss.detail}</bdi>
                </div>
                <div className="text-[10.5px] mt-0.5" style={{ color: 'var(--text-primary)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>המלצה: </span>
                  <bdi style={{ color: 'var(--sys1)' }}>{recommendationText(iss)}</bdi>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Derived hints — always available (pure from the trade row) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-x-4 gap-y-0.5 pt-1 border-t" style={{ borderColor: 'var(--border)' }}>
        {hints.map((h) => (
          <div key={h.label} className="flex justify-between gap-2 py-0.5 text-[10.5px]">
            <span style={{ color: 'var(--text-muted)' }}>{h.label}</span>
            <bdi style={{ color: h.color ?? 'var(--text-primary)' }}>{h.value}</bdi>
          </div>
        ))}
      </div>

      <div className="text-[9px] mt-1" style={{ color: 'var(--text-muted)' }}>
        אבחון System-6 — ייעוץ בלבד (read-only), לא מבוצע אוטומטית.
      </div>
    </div>
  );
}
