'use client';
// ShadowTab / HistTab — עסקאות-היום בתוך לשונית-הצד (מייקל 2026-07-09).
// Shadow = "מה המערכת הייתה עושה" (mode=shadow); Hist = עסקאות שבוצעו היום (live/sim).
// מקור: fetchTrades() ב-lib/api (טוקן מובנה). פולינג 20s.
import { useEffect, useState, type ReactNode } from 'react';
import { COLORS } from '../../../../design/tokens';
import { fetchTrades } from '../../../../lib/api';
import type { Trade } from '../../../../types';
import { PATTERN_HELP } from '../plan/planHelp';
import { systemColor } from '../../../../design/system_colors';
import { useTradeStore } from '../../../../stores/tradeStore';

const RTL = { direction: 'rtl', textAlign: 'right' } as const;

function isToday(ts?: string | null): boolean {
  if (!ts) return false;
  const d = new Date(ts);
  const n = new Date();
  return d.getFullYear() === n.getFullYear() && d.getMonth() === n.getMonth() && d.getDate() === n.getDate();
}
function tsMs(ts?: string | null): number { return ts ? new Date(ts).getTime() : 0; }
function hhmm(ts?: string | null): string {
  if (!ts) return '--:--';
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

const OUTCOME_HE: Record<string, string> = {
  WIN: 'רווח', LOSS: 'הפסד', SCRATCH: 'תיקו', BE: 'ברייקאיבן',
  OPEN: 'פתוחה', CANCELLED: 'בוטלה',
};

function targetsStr(t: Trade): string {
  const uniq = [t.t1, t.t2, t.t3].filter((v): v is number => v != null);
  return [...new Set(uniq)].join(' / ');
}

function TradeCard({ t, showMode }: { t: Trade; showMode?: boolean }) {
  const isLong = String(t.direction).toUpperCase() === 'LONG';
  const dirColor = isLong ? COLORS.bull : COLORS.bear;
  const nick = (t.pattern_id && PATTERN_HELP[t.pattern_id]?.nick) || t.pattern_id || t.classification || '—';
  const pnl = t.pnl_usd;
  const closed = pnl != null && (t.state === 'CLOSED' || t.exit_ts || t.outcome === 'CANCELLED');
  const pnlColor = pnl == null ? COLORS.textTertiary : pnl > 0 ? COLORS.bull : pnl < 0 ? COLORS.bear : COLORS.textSecondary;
  const outHe = t.outcome ? (OUTCOME_HE[t.outcome] || t.outcome) : null;
  const blockedBy = (t as unknown as { blocked_by?: string | null }).blocked_by;
  const targets = targetsStr(t);
  const sys = Number(t.system) || null;
  const sysColor = sys ? systemColor(sys) : COLORS.textTertiary;
  const dt = t.day_type && t.day_type !== 'UNKNOWN' ? t.day_type : null;
  return (
    <div
      onClick={() => useTradeStore.getState().setSelectedTradeId(t.id)}
      title="לחיצה לפירוט מלא"
      style={{ padding: '5px 7px', borderRadius: 6, border: `1px solid #21262d`, background: '#0d1117', cursor: 'pointer', ...RTL }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 6 }}>
        <span style={{ fontSize: 11, color: COLORS.textPrimary }}>
          <span style={{ color: COLORS.textTertiary }}>{hhmm(t.entry_ts ?? t.exit_ts)}</span>{' '}
          {sys ? (
            <span style={{ fontSize: 8.5, fontWeight: 700, padding: '0 3px', borderRadius: 3,
              color: sysColor, background: `${sysColor}22`, border: `1px solid ${sysColor}66`,
              fontFamily: 'ui-monospace' }}>S{sys}</span>
          ) : null}{' '}
          <span style={{ color: dirColor, fontWeight: 600 }}>{isLong ? '▲' : '▼'} {nick}</span>
          {showMode && t.mode ? <span style={{ fontSize: 8.5, color: COLORS.textTertiary }}> · {String(t.mode)}</span> : null}
        </span>
        <span style={{ fontSize: 10.5, color: pnlColor, whiteSpace: 'nowrap', fontWeight: 600 }}>
          {pnl != null ? `${pnl >= 0 ? '+' : ''}$${Math.round(pnl)}` : (outHe ?? '')}
          {t.pnl_r != null ? ` · ${t.pnl_r > 0 ? '+' : ''}${t.pnl_r.toFixed(1)}R` : ''}
        </span>
      </div>
      <div style={{ fontSize: 9.5, color: COLORS.textSecondary, marginTop: 2 }}>
        כניסה {t.entry_price ?? '—'} · סטופ {t.stop ?? '—'}{targets ? ` · יעד ${targets}` : ''}
        {dt ? <span style={{ color: COLORS.textTertiary }}>{` · יום ${dt}`}</span> : null}
        {closed && outHe ? <span style={{ color: pnlColor }}>{` · ${outHe}`}</span> : null}
      </div>
      {blockedBy ? (
        <div style={{ fontSize: 9.5, color: '#d29922', marginTop: 1 }}>נחסמה מ-live: {blockedBy}</div>
      ) : null}
    </div>
  );
}

function useTodayTrades(systemId: number | undefined, kind: 'shadow' | 'hist') {
  const [trades, setTrades] = useState<Trade[] | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const all = kind === 'shadow' ? await fetchTrades('shadow', 60) : await fetchTrades(undefined, 60);
        if (!alive) return;
        const list = all
          .filter((t) => systemId == null || Number(t.system) === systemId)
          .filter((t) => (kind === 'shadow' ? true : String(t.mode).toUpperCase() !== 'SHADOW'))
          .filter((t) => isToday(t.entry_ts ?? t.exit_ts))
          .sort((a, b) => tsMs(b.entry_ts ?? b.exit_ts) - tsMs(a.entry_ts ?? a.exit_ts));
        setTrades(list);
        setErr(false);
      } catch { if (alive) setErr(true); }
    };
    load();
    const id = setInterval(load, 20000);
    return () => { alive = false; clearInterval(id); };
  }, [systemId, kind]);
  return { trades, err };
}

function Muted({ children }: { children: ReactNode }) {
  return <div style={{ fontSize: 10.5, color: COLORS.textTertiary, padding: 6, ...RTL }}>{children}</div>;
}

function Frame({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <div style={{ ...RTL }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: COLORS.textPrimary }}>{title}</span>
        {hint ? (
          <a href="/trades" target="_blank" rel="noreferrer"
             style={{ fontSize: 10, color: '#58a6ff', textDecoration: 'none', whiteSpace: 'nowrap' }}>
            {hint} ↗
          </a>
        ) : null}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>{children}</div>
    </div>
  );
}

export function ShadowTab({ systemId }: { systemId?: number }) {
  const { trades, err } = useTodayTrades(systemId, 'shadow');
  return (
    <Frame title="עסקאות-צל היום — מה המערכת הייתה עושה">
      {err ? <Muted>שגיאה בטעינת עסקאות-צל</Muted>
        : trades == null ? <Muted>טוען…</Muted>
        : trades.length === 0 ? <Muted>אין עסקאות-צל היום.</Muted>
        : trades.map((t) => <TradeCard key={t.id} t={t} />)}
    </Frame>
  );
}

export function HistTab({ systemId }: { systemId?: number }) {
  const { trades, err } = useTodayTrades(systemId, 'hist');
  return (
    <Frame title="עסקאות היום" hint="כל העסקאות">
      {err ? <Muted>שגיאה בטעינת עסקאות</Muted>
        : trades == null ? <Muted>טוען…</Muted>
        : trades.length === 0 ? <Muted>אין עסקאות היום.</Muted>
        : trades.map((t) => <TradeCard key={t.id} t={t} showMode />)}
    </Frame>
  );
}
