'use client';
import { useEffect, useMemo, useState, lazy, Suspense, type ReactNode } from 'react';
import Link from 'next/link';
import { fetchTradeById } from '../../lib/api';
import { SYSTEM_COLORS } from '../../types';
import type { SystemId, Trade } from '../../types';
import { useTradeStore } from '../../stores/tradeStore';
import {
  rLevels,
  riskReward,
  stopMovement,
  formatUsdAccounting,
  durationMinutes,
  formatDuration,
  cumulativeByClose,
  cumulativeByOpen,
} from '../../lib/tradeMath';
import MgmtTimeline from './MgmtTimeline';
import SpecFlags from './SpecFlags';
import { TradeRecommendations } from './TradeRecommendations';

const TradeChart = lazy(() => import('./TradeChart'));

interface SystemRecognition {
  id: number;
  name: string;
  role: string;
  is_firing: boolean;
  agree: boolean | null;
  lines: string[];
}

interface TradeFireInsight {
  headline?: string;
  trigger?: string;
  pattern_id?: string;
  classification?: string;
  day_type?: string;
}

interface TradeInsight {
  fire?: TradeFireInsight;
  recognition?: SystemRecognition[];
}

function agreeChip(agree: boolean | null | undefined): { text: string; color: string } {
  if (agree === true) return { text: 'מסכים', color: 'var(--green)' };
  if (agree === false) return { text: 'נגד', color: 'var(--red)' };
  return { text: 'ניטרלי', color: 'var(--text-muted)' };
}

/** Table row already has systems_agreement — use until full insight loads. */
function recognitionFromAgreement(trade: Trade): SystemRecognition[] {
  const sa = trade.systems_agreement;
  if (!sa?.length) return [];
  return sa.map((s) => ({
    id: s.id,
    name: s.name,
    role: s.is_firing ? 'fire' : 'observe',
    is_firing: !!s.is_firing,
    agree: s.agree ?? null,
    lines: s.hint ? [String(s.hint)] : ['אין snapshot בכניסה — טוען פירוט…'],
  }));
}

function StopVerdict({ trade }: { trade: Trade }) {
  const sm = stopMovement(trade);
  if (sm === 'moved') {
    return (
      <span style={{ color: 'var(--green)' }}>
        ✓ זז ל-BE לפי אפיון (SMART_BE: {trade.stop_initial?.toFixed(2)} → {trade.stop?.toFixed(2)})
      </span>
    );
  }
  if (sm === 't1_no_be') {
    return <span style={{ color: '#eab308' }}>⚠ T1 נגע אך הסטופ לא זז (T1_NO_BE)</span>;
  }
  return <span style={{ color: 'var(--text-secondary)' }}>סטופ ב-−1R — לא זז</span>;
}

function TradeDetailBlock({ trade }: { trade: Trade }) {
  const allTrades = useTradeStore((s) => s.trades);
  const cumClose = useMemo(() => cumulativeByClose(allTrades).get(trade.id), [allTrades, trade.id]);
  const cumOpen = useMemo(() => cumulativeByOpen(allTrades).get(trade.id), [allTrades, trade.id]);
  const L = rLevels(trade);
  const rr = riskReward(trade);
  const dur = durationMinutes(trade);
  const f = (v: number | null | undefined) => (v != null ? v.toFixed(2) : '—');
  const rtxt = (v: number | null) => (v != null ? `${v >= 0 ? '+' : ''}${v.toFixed(1)}R` : '—');

  const cell = (label: string, value: ReactNode, color?: string) => (
    <div className="flex justify-between gap-3 py-0.5">
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ color: color ?? 'var(--text-primary)' }}>{value}</span>
    </div>
  );

  return (
    <div
      className="mb-3 p-2 rounded grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-5 gap-y-0.5 text-[11px]"
      style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
    >
      {cell('כניסה', `${f(trade.entry_price)} · 0`)}
      {cell('סטופ', `${f(trade.stop_initial ?? trade.stop)} · −1R`, 'var(--red)')}
      {cell('יציאה', `${f(trade.exit_price)} · ${rtxt(L.exitR)}`, 'var(--sys4)')}
      {cell('T1 · T2', `${f(trade.t1)} (${rtxt(L.t1R)}) · ${trade.t2 != null ? `${f(trade.t2)} (${rtxt(L.t2R)})` : '—'}`, 'var(--sys1)')}
      {cell('סיכון/סיכוי (R:R)', rr && rr.t2 != null ? `1:${rr.t1?.toFixed(1) ?? '—'} (T1) · 1:${rr.t2.toFixed(1)} (T2)` : '—')}
      {cell('סיכון (נק\')', (() => {
        const init = trade.stop_initial ?? trade.stop;
        const risk = init != null && trade.entry_price != null ? Math.abs(trade.entry_price - init) : null;
        return risk != null ? `${risk.toFixed(1)}pt` : '—';
      })(), (() => {
        const init = trade.stop_initial ?? trade.stop;
        const risk = init != null && trade.entry_price != null ? Math.abs(trade.entry_price - init) : 0;
        return risk > 25 ? 'var(--red)' : risk > 10 ? '#eab308' : 'var(--green)';
      })())}
      {cell('MFE / שמרנו', (() => {
        const mfe = trade.mfe_pts;
        const captured = trade.pnl_usd != null && trade.entry_price != null ? Math.abs(trade.pnl_usd / 5) : null;
        if (mfe == null) return '—';
        const pct = captured != null && mfe > 0 ? Math.round((captured / mfe) * 100) : null;
        return `${mfe.toFixed(1)}pt MFE · ${captured != null ? captured.toFixed(1) : '?'}pt captured${pct != null ? ` (${pct}%)` : ''}`;
      })())}
      {cell('משך', formatDuration(dur))}
      {cell('P&L', formatUsdAccounting(trade.pnl_usd), trade.pnl_usd != null ? (trade.pnl_usd > 0 ? 'var(--green)' : trade.pnl_usd < 0 ? 'var(--red)' : 'var(--text-secondary)') : 'var(--text-muted)')}
      {cell('קומ׳ פתיחה', cumOpen != null ? formatUsdAccounting(cumOpen) : '—', cumOpen != null && cumOpen < 0 ? 'var(--red)' : 'var(--green)')}
      {cell('קומ׳ סגירה', cumClose != null ? formatUsdAccounting(cumClose) : '—', cumClose != null && cumClose < 0 ? 'var(--red)' : 'var(--green)')}
      <div className="md:col-span-2 lg:col-span-3 pt-1 mt-1 border-t flex justify-between gap-3 py-0.5" style={{ borderColor: 'var(--border)' }}>
        <span style={{ color: 'var(--text-muted)' }}>ניהול סטופ</span>
        <span><StopVerdict trade={trade} /></span>
      </div>
    </div>
  );
}

export function TradeRowExpand({ trade }: { trade: Trade }) {
  const allTrades = useTradeStore((s) => s.trades);
  const [insight, setInsight] = useState<TradeInsight | null>(null);
  const [mgmtLog, setMgmtLog] = useState<Array<{action: string, created_at?: string}>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    fetchTradeById(trade.id)
      .then((res) => {
        if (!res?.insight) {
          setInsight(null);
          setError(true);
          return;
        }
        setInsight(res.insight as TradeInsight);
        setMgmtLog((res as any).management_log ?? (res.insight as any)?.lifecycle ?? []);
        setError(false);
      })
      .catch(() => {
        setInsight(null);
        setError(true);
      })
      .finally(() => setLoading(false));
  }, [trade.id]);

  const fire = insight?.fire;
  const recognition =
    insight?.recognition?.length
      ? insight.recognition
      : loading
        ? recognitionFromAgreement(trade)
        : error
          ? recognitionFromAgreement(trade)
          : [];

  return (
    <div className="px-3 py-3 text-xs font-mono" style={{ background: 'var(--bg-primary)' }}>
      {/* Spec flags */}
      <div style={{ marginBottom: 6 }}>
        <SpecFlags trade={trade} allTrades={allTrades} />
      </div>

      {/* מה השתבש + המלצת-שיפור (System-6 diagnose, read-only, fail-soft) */}
      <TradeRecommendations trade={trade} />

      <TradeDetailBlock trade={trade} />

      {/* Per-trade price chart (lazy — only rendered when expanded) */}
      <div className="mb-3 rounded overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        <div className="text-[10px] uppercase tracking-wide px-2 py-1" style={{ color: 'var(--text-muted)', background: 'var(--bg-secondary)' }}>
          צ׳ארט עסקה #{trade.id}
        </div>
        <Suspense fallback={<div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 11 }}>טוען צ׳ארט…</div>}>
          <TradeChart trade={trade} />
        </Suspense>
      </div>

      {/* Mgmt log timeline */}
      <div className="mb-3 p-2 rounded" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
        <div className="text-[10px] uppercase tracking-wide mb-1" style={{ color: 'var(--text-muted)' }}>
          ציר-זמן ניהול
        </div>
        <MgmtTimeline entries={mgmtLog} />
      </div>

      {loading && <p style={{ color: 'var(--text-muted)' }}>טוען מה כל מערכת זיהתה בכניסה…</p>}
      {error && !loading && (
        <p style={{ color: 'var(--red)' }}>
          לא נטען פירוט מלא מ-API — מוצגים רמזים מטור Systems (אם יש). בדוק ש-backend על :8000.
        </p>
      )}

      {!loading && fire?.headline && (
        <div className="mb-3 p-2 rounded" style={{ background: 'var(--bg-secondary)', color: SYSTEM_COLORS[(trade.system as SystemId) || 4] }}>
          <span className="text-[10px] uppercase tracking-wide block mb-1" style={{ color: 'var(--text-muted)' }}>
            מה ירה (S{trade.system})
          </span>
          {fire.headline}
          {(fire.trigger || fire.pattern_id) && (
            <span className="block mt-1 opacity-90" style={{ color: 'var(--text-secondary)' }}>
              {fire.trigger && `trigger=${fire.trigger} `}
              {fire.pattern_id && `pattern=${fire.pattern_id}`}
            </span>
          )}
        </div>
      )}

      <div className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
        זיהוי מערכות בזמן הכניסה (S1–S6)
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
        {recognition.map((sys) => {
          const ag = agreeChip(sys.agree);
          const sc = SYSTEM_COLORS[sys.id as SystemId] || 'var(--text-secondary)';
          return (
            <div
              key={sys.id}
              className="p-2 rounded border"
              style={{
                borderColor: sys.is_firing ? sc : 'var(--border)',
                background: sys.is_firing ? `${sc}12` : 'transparent',
              }}
            >
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className="font-semibold" style={{ color: sc }}>
                  S{sys.id} {sys.name}
                  {sys.is_firing ? ' · FIRE' : ''}
                </span>
                <span className="text-[10px] px-1 rounded" style={{ color: ag.color, background: 'rgba(255,255,255,0.05)' }}>
                  {ag.text}
                </span>
                <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{sys.role}</span>
              </div>
              <ul className="list-disc pl-4 space-y-0.5" style={{ color: 'var(--text-secondary)' }}>
                {sys.lines.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {!loading && recognition.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>
          אין cross_context בכניסה — רק סיכום בטור Systems: {trade.systems_agreement?.map((s) => `S${s.id}`).join(' ') || '—'}
        </p>
      )}

      {!loading && trade.system === 2 && (
        <p className="mt-2 text-[10px]" style={{ color: '#eab308' }}>
          S2 Five-Min: אם אין שורות למעלה — בדרך כלל לא היה snapshot או המערכת לא הייתה ב-RTH / לא ירתה.
        </p>
      )}

      {/* P5: Journal → Build deep-link */}
      <div className="mt-3 pt-2 border-t flex items-center gap-3" style={{ borderColor: 'var(--border)' }}>
        <Link
          href="/?view=build_status"
          className="text-[10px] px-2 py-1 rounded hover:opacity-80"
          style={{
            background: 'rgba(59,130,246,0.12)',
            color: 'var(--sys1)',
            border: '1px solid rgba(59,130,246,0.25)',
            fontFamily: 'ui-monospace, monospace',
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          חקור ב-Build Status →
        </Link>
        <span className="text-[9px]" style={{ color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
          S{trade.system} · {fire?.pattern_id || trade.pattern_id || '—'}
        </span>
      </div>
    </div>
  );
}
