'use client';
/**
 * MultidayProfilePanel — הקשר-TPO רב-יומי (מייקל 02.08, עם צילום צ'ארט-ה-TPO:
 * "להכניס 7 ימים אחורה כדי לדעת לפי דלתון סוגי-פתיחה וסוג-יום בצורה מדויקת —
 * נוסיף לפרונטאנד כמו וודיס").
 *
 * מציג את 7 הסשנים האחרונים כסולם-ערכים: קופסת-VA פר-יום עם קו-POC, פס-המאזן
 * המורכב, קו-פתיחת-היום, וחץ-נדידת-הערך. מקור: GET /api/v9/context/multiday
 * (מחושב מהברים הקנוניים, cache 5 דק'). ‏Poll 60000ms — הקשר-סשן, לא טיקים
 * (רצפות-P30 נשמרות). שדה חסר ⇒ "—", לעולם לא ניחוש.
 */
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { getApiBase } from '../../lib/api';

const API_BASE = getApiBase();

interface DayProf { poc: number; vah: number; val: number; high: number; low: number; }
interface Multiday {
  days?: DayProf[]; dates?: string[];
  composite?: { range_high: number; range_low: number; vah: number; val: number; poc: number } | null;
  value_migration?: { direction?: string | null; slope?: number | null };
  va_overlap_pct?: number | null;
  open_location?: string | null;
  n_days_used?: number;
  suspect_dates?: string[];
}

const G = '#16a34a', R = '#dc2626', Y = '#eab308', C = '#67e8f9';
const LOC_HE: Record<string, string> = {
  above_range: 'מעל-הטווח', above_value: 'מעל-הערך', in_value: 'בתוך-הערך',
  below_value: 'מתחת-לערך', below_range: 'מתחת-לטווח',
};

export function MultidayProfilePanel() {
  const [d, setD] = useState<Multiday | null>(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v9/context/multiday`);
        if (!r.ok) return;
        const j = await r.json();
        if (alive) setD(j);
      } catch { /* honest silence — the panel shows dashes */ }
    };
    load();
    const id = setInterval(load, 60000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const days = d?.days ?? [];
  const comp = d?.composite;
  if (!comp || days.length === 0) {
    return (
      <div style={{ padding: '4px 10px', borderBottom: `1px solid ${COLORS.borderFaint}` }}>
        <span style={{ fontSize: 8, color: COLORS.textDim }}>מאזן 7-ימים — אין נתונים</span>
      </div>
    );
  }

  // scale: composite range → panel height
  const H = 92, PADW = 46;
  const pLo = comp.range_low, pHi = comp.range_high, span = pHi - pLo || 1;
  const y = (price: number) => H - ((price - pLo) / span) * H;

  const mig = d?.value_migration?.direction;
  const migTxt = mig === 'UP' ? '▲ ערך נודד מעלה' : mig === 'DOWN' ? '▼ ערך נודד מטה' : '↔ ערך חופף';
  const migColor = mig === 'UP' ? G : mig === 'DOWN' ? R : Y;
  const overlap = d?.va_overlap_pct;
  const regime = overlap == null ? '' : overlap >= 0.6 ? 'מאזן' : overlap <= 0.35 ? 'מגמה' : 'מעורב';
  const loc = d?.open_location ? (LOC_HE[d.open_location] ?? d.open_location) : null;
  const suspects = new Set(d?.suspect_dates ?? []);

  return (
    <div style={{ padding: '4px 10px', borderBottom: `1px solid ${COLORS.borderFaint}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 2 }}>
        <span style={{ fontSize: 8, fontWeight: 800, letterSpacing: '1px', color: C }}>מאזן 7-ימים</span>
        <span style={{ fontSize: 9, color: migColor, fontWeight: 700 }}>{migTxt}
          {d?.value_migration?.slope != null ? ` (${d.value_migration.slope > 0 ? '+' : ''}${d.value_migration.slope}/יום)` : ''}
        </span>
        <span style={{ fontSize: 8, color: COLORS.textDim }}>
          חפיפה {overlap ?? '—'}{regime ? ` · משטר-${regime}` : ''}
        </span>
        {loc && (
          <span style={{ fontSize: 9, fontWeight: 700, color: C }}>פתיחת-היום: {loc}</span>
        )}
        <span style={{ fontSize: 8, color: COLORS.textDim, marginInlineStart: 'auto' }}>
          ערך {comp.val}–{comp.vah} · POC {comp.poc} · טווח {comp.range_low}–{comp.range_high}
        </span>
      </div>
      <svg width={days.length * PADW + 8} height={H + 14} style={{ display: 'block' }}>
        {/* פס-הערך-המורכב */}
        <rect x={0} y={y(comp.vah)} width={days.length * PADW}
          height={Math.max(2, y(comp.val) - y(comp.vah))}
          fill="rgba(103,232,249,0.07)" />
        <line x1={0} x2={days.length * PADW} y1={y(comp.poc)} y2={y(comp.poc)}
          stroke={C} strokeDasharray="3 3" strokeWidth={1} opacity={0.6} />
        {days.map((p, i) => {
          const x = i * PADW + 6;
          const date = d?.dates?.[i] ?? '';
          const suspect = suspects.has(date);
          return (
            <g key={i} opacity={suspect ? 0.45 : 1}>
              {/* טווח-היום */}
              <line x1={x + 14} x2={x + 14} y1={y(p.high)} y2={y(p.low)}
                stroke={COLORS.textDim} strokeWidth={1} />
              {/* קופסת-VA */}
              <rect x={x + 4} y={y(p.vah)} width={20}
                height={Math.max(2, y(p.val) - y(p.vah))}
                fill="rgba(22,163,74,0.25)" stroke={COLORS.borderFaint} />
              {/* POC */}
              <line x1={x + 2} x2={x + 26} y1={y(p.poc)} y2={y(p.poc)}
                stroke={Y} strokeWidth={2} />
              <text x={x + 14} y={H + 11} textAnchor="middle"
                fontSize={7} fill={suspect ? COLORS.textDim : COLORS.textSecondary}>
                {date.slice(5)}{suspect ? '?' : ''}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
