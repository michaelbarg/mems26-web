'use client';
import { useEffect, useState } from 'react';
import { fetchTradeById } from '../../lib/api';
import { SYSTEM_COLORS, SYSTEM_NAMES } from '../../types';
import type { SystemId, Trade } from '../../types';

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

export function TradeRowExpand({ trade }: { trade: Trade }) {
  const [insight, setInsight] = useState<TradeInsight | null>(null);
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
    </div>
  );
}
