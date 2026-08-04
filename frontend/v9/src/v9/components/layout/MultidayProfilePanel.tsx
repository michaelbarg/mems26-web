'use client';
/**
 * MultidayProfilePanel — פרופיל-TPO רב-יומי בדפוס-הוודיס (מייקל 02.08:
 * "כמו שיש את הוודי שנפתח ונסגר... שיהיה מדויק כמו זה [צ'ארט-ה-TPO של סיירה]").
 *
 * שתי שכבות:
 * 1. רצועת-סיכום דקה בדשבורד (נדידה · חפיפה · מיקום-פתיחה · ערכי-המורכב) —
 *    לחיצה פותחת/סוגרת את החלון הצף. לא נוגעת בטבלת-החשבון/רדאר.
 * 2. חלון צף נגרר (localStorage למיקום/גודל/מצב) — היסטוגרמת-TPO אמיתית
 *    פר-רבע-נקודה לכל אחד מ-7 הימים + ציר-מחיר בצד ימין כמו סיירה:
 *    POC צהוב, VA מודגש, singles, קו-POC-מורכב מקווקו, ימים חשודים עמומים.
 *
 * מקור: GET /api/v9/context/multiday (מהברים הקנוניים, cache 5 דק').
 * Poll 60000ms — הקשר-סשן (רצפות-P30). שדה חסר ⇒ לא מציירים, לא מנחשים.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { getApiBase } from '../../lib/api';

const API_BASE = getApiBase();

const LS_OPEN = 'mems26-multiday-panel-open';
const LS_LEFT = 'mems26-multiday-panel-left';
const LS_TOP = 'mems26-multiday-panel-top';
const LS_W = 'mems26-multiday-panel-w';
const LS_H = 'mems26-multiday-panel-h';

const MIN_W = 420, MAX_W = 1400, DEF_W = 760;
const MIN_H = 320, MAX_H = 1000, DEF_H = 560;

interface DayProf {
  poc: number; vah: number; val: number; high: number; low: number;
  singles?: number[];
  // [price, count, letters] — letters = אות פר-תקופת-30-דק' (A=ראשונה), כמו סיירה
  profile?: [number, number, string?][];
}
interface TodayProf extends DayProf {
  partial?: boolean; day_type?: string | null; day_type_conf?: number | null;
  opening_type?: string | null;
}
interface Multiday {
  days?: DayProf[]; dates?: string[];
  composite?: { range_high: number; range_low: number; vah: number; val: number; poc: number } | null;
  value_migration?: { direction?: string | null; slope?: number | null };
  va_overlap_pct?: number | null;
  open_location?: string | null;
  suspect_dates?: string[];
  today?: TodayProf | null;
}

const G = '#16a34a', R = '#dc2626', Y = '#eab308', C = '#67e8f9';
const LOC_HE: Record<string, string> = {
  above_range: 'מעל-הטווח', above_value: 'מעל-הערך', in_value: 'בתוך-הערך',
  below_value: 'מתחת-לערך', below_range: 'מתחת-לטווח',
};

function loadNum(key: string, fb: number, min: number, max: number): number {
  if (typeof window === 'undefined') return fb;
  const v = Number(localStorage.getItem(key));
  return Number.isFinite(v) && v !== 0 ? Math.min(max, Math.max(min, v)) : fb;
}

export function MultidayProfilePanel() {
  const [d, setD] = useState<Multiday | null>(null);
  // מייקל 03.08 ("להוסיף לשורת הביקורת"): סיווג-היום החי מהרדאר — מוצג מיד,
  // גם לפני שה-endpoint מגיש את עמודת-היום (עד ריסטארט-בקאנד בחלון-מת).
  const [liveDT, setLiveDT] = useState<{ t?: string | null; c?: number | null }>({});
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ left: 60, top: 90 });
  const [size, setSize] = useState({ w: DEF_W, h: DEF_H });
  const drag = useRef<null | { mode: 'move' | 'resize'; sx: number; sy: number; ox: number; oy: number }>(null);

  useEffect(() => {
    setOpen(localStorage.getItem(LS_OPEN) === '1');
    setPos({ left: loadNum(LS_LEFT, 60, 0, 2400), top: loadNum(LS_TOP, 90, 0, 1400) });
    setSize({ w: loadNum(LS_W, DEF_W, MIN_W, MAX_W), h: loadNum(LS_H, DEF_H, MIN_H, MAX_H) });
  }, []);

  const toggle = useCallback(() => {
    setOpen(o => { localStorage.setItem(LS_OPEN, o ? '0' : '1'); return !o; });
  }, []);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v9/context/multiday`);
        if (!r.ok) return;
        const j = await r.json();
        if (alive) setD(j);
      } catch { /* honest silence — the strip shows nothing */ }
    };
    load();
    const loadDT = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v9/context/radar`);
        if (!r.ok) return;
        const j = await r.json();
        if (alive) setLiveDT({ t: j.day_type, c: j.confidence });
      } catch { /* dashes */ }
    };
    loadDT();
    const id = setInterval(load, 60000);
    const id2 = setInterval(loadDT, 60000);
    return () => { alive = false; clearInterval(id); clearInterval(id2); };
  }, []);

  // drag / resize (Woodies pattern — window listeners, persist on release)
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const st = drag.current;
      if (!st) return;
      if (st.mode === 'move') {
        setPos({ left: Math.max(0, st.ox + e.clientX - st.sx), top: Math.max(0, st.oy + e.clientY - st.sy) });
      } else {
        setSize({
          w: Math.min(MAX_W, Math.max(MIN_W, st.ox + e.clientX - st.sx)),
          h: Math.min(MAX_H, Math.max(MIN_H, st.oy + e.clientY - st.sy)),
        });
      }
    };
    const onUp = () => {
      if (!drag.current) return;
      drag.current = null;
      setPos(p => { localStorage.setItem(LS_LEFT, String(p.left)); localStorage.setItem(LS_TOP, String(p.top)); return p; });
      setSize(s => { localStorage.setItem(LS_W, String(s.w)); localStorage.setItem(LS_H, String(s.h)); return s; });
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);

  const days = d?.days ?? [];
  const comp = d?.composite;
  if (!comp || days.length === 0) return null;

  const mig = d?.value_migration?.direction;
  const migTxt = mig === 'UP' ? '▲ ערך נודד מעלה' : mig === 'DOWN' ? '▼ ערך נודד מטה' : '↔ ערך חופף';
  const migColor = mig === 'UP' ? G : mig === 'DOWN' ? R : Y;
  const overlap = d?.va_overlap_pct;
  const regime = overlap == null ? '' : overlap >= 0.6 ? 'מאזן' : overlap <= 0.35 ? 'מגמה' : 'מעורב';
  const loc = d?.open_location ? (LOC_HE[d.open_location] ?? d.open_location) : null;
  const suspects = new Set(d?.suspect_dates ?? []);

  return (
    <>
      {/* מייקל 04.08 ("כמו הכפתור של הוודי"): כפתור-קצה אנכי צף — אפס-שורות מהטבלה */}
      <div onClick={toggle} title={open ? 'סגור מאזן 7-ימים' : 'פתח מאזן 7-ימים'}
        style={{
          position: 'fixed', right: 0, top: '46%', zIndex: 15,
          writingMode: 'vertical-rl', padding: '10px 3px',
          background: '#0b1418', border: `1px dashed ${C}`, borderRight: 'none',
          borderRadius: '6px 0 0 6px', color: C, fontSize: 10, fontWeight: 800,
          letterSpacing: '1px', cursor: 'pointer', userSelect: 'none',
        }}>
        מאזן 7 {mig === 'UP' ? '▲' : mig === 'DOWN' ? '▼' : '↔'}
      </div>

      {open && (
        <div style={{
          position: 'fixed', left: pos.left, top: pos.top, width: size.w, height: size.h,
          zIndex: 20, background: '#0b1418', border: '1px solid #24444f', borderRadius: 6,
          boxShadow: '0 8px 30px rgba(0,0,0,0.55)', display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
        }}>
          {/* כותרת נגררת */}
          <div
            onMouseDown={(e) => { drag.current = { mode: 'move', sx: e.clientX, sy: e.clientY, ox: pos.left, oy: pos.top }; e.preventDefault(); }}
            style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '5px 10px',
              cursor: 'move', background: '#10222a', borderBottom: '1px solid #24444f', userSelect: 'none',
            }}>
            <span style={{ color: '#546e7a', fontSize: 11 }}>⋮⋮</span>
            <span style={{ fontSize: 11, fontWeight: 800, color: C }}>מאזן 7 ימים — TPO</span>
            <span style={{ fontSize: 10, color: migColor, fontWeight: 700 }}>{migTxt}</span>
            <span style={{ fontSize: 9, color: COLORS.textDim }}>חפיפה {overlap ?? '—'}{regime ? ` · ${regime}` : ''}</span>
            {loc && <span style={{ fontSize: 10, fontWeight: 700, color: C }}>פתיחה: {loc}</span>}
            {(d?.today?.day_type ?? liveDT.t) && (
              <span style={{ fontSize: 10, fontWeight: 800, color: '#fbbf24' }}>
                היום: {d?.today?.day_type ?? liveDT.t}
                {(d?.today?.day_type_conf ?? liveDT.c) != null
                  ? ` ${Math.round(((d?.today?.day_type_conf ?? liveDT.c) as number) * 100)}%` : ''}
              </span>
            )}
            <button onClick={toggle}
              style={{
                marginInlineStart: 'auto', background: 'transparent', border: 'none',
                color: '#8aa5b0', fontSize: 13, cursor: 'pointer', padding: '0 2px',
              }}>✕</button>
          </div>

          <TpoCanvas days={days} dates={d?.dates ?? []} comp={comp} suspects={suspects}
            today={d?.today ?? null} w={size.w} h={size.h - 30} />

          {/* פינת-שינוי-גודל — z-index above the canvas so mouse events reach it */}
          <div
            onMouseDown={(e) => { drag.current = { mode: 'resize', sx: e.clientX, sy: e.clientY, ox: size.w, oy: size.h }; e.preventDefault(); }}
            style={{
              position: 'absolute', right: 0, bottom: 0, width: 18, height: 18,
              cursor: 'nwse-resize', borderRight: '3px solid #24444f', borderBottom: '3px solid #24444f',
              zIndex: 5,
            }} />
        </div>
      )}
    </>
  );
}

/** ציור-הפרופילים בקנבס — 7 עמודות-TPO פר-רבע-נקודה + ציר-מחיר כמו סיירה. */
function TpoCanvas({ days, dates, comp, suspects, today, w, h }: {
  days: DayProf[]; dates: string[];
  comp: { range_high: number; range_low: number; vah: number; val: number; poc: number };
  suspects: Set<string>; today: TodayProf | null; w: number; h: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const dpr = window.devicePixelRatio || 1;
    cv.width = w * dpr; cv.height = h * dpr;
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const AXIS_W = 58, PAD_T = 8, PAD_B = 18;
    const chartW = w - AXIS_W, chartH = h - PAD_T - PAD_B;
    // מייקל 03.08: עמודת-היום-המתהווה — הסקאלה חייבת לכלול גם אותה
    const pLo = Math.min(comp.range_low, today?.low ?? comp.range_low) - 2;
    const pHi = Math.max(comp.range_high, today?.high ?? comp.range_high) + 2;
    const span = pHi - pLo;
    const y = (price: number) => PAD_T + chartH - ((price - pLo) / span) * chartH;
    const rowH = Math.max(1, (0.25 / span) * chartH);

    // רקע + פס-הערך-המורכב
    ctx.fillStyle = '#0b1418'; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = 'rgba(103,232,249,0.05)';
    ctx.fillRect(0, y(comp.vah), chartW, Math.max(2, y(comp.val) - y(comp.vah)));

    // ציר-מחיר (ימין, כמו סיירה) — טיק כל 10 נק'
    ctx.strokeStyle = '#24444f'; ctx.beginPath();
    ctx.moveTo(chartW + 0.5, 0); ctx.lineTo(chartW + 0.5, h); ctx.stroke();
    ctx.font = '9px ui-monospace, monospace'; ctx.textAlign = 'left';
    const tickStep = span > 120 ? 20 : 10;
    for (let p = Math.ceil(pLo / tickStep) * tickStep; p <= pHi; p += tickStep) {
      const yy = y(p);
      ctx.strokeStyle = 'rgba(255,255,255,0.05)';
      ctx.beginPath(); ctx.moveTo(0, yy + 0.5); ctx.lineTo(chartW, yy + 0.5); ctx.stroke();
      ctx.fillStyle = '#7a99a5'; ctx.fillText(String(p), chartW + 6, yy + 3);
    }

    // עמודות-הימים (+1 להיום-המתהווה כשקיים)
    const nCols = days.length + (today ? 1 : 0);
    const colW = chartW / nCols;
    days.forEach((day, i) => {
      const x0 = i * colW + 4;
      const date = dates[i] ?? '';
      const dim = suspects.has(date);
      const alpha = dim ? 0.4 : 1;
      const prof = day.profile ?? [];
      const maxC = Math.max(1, ...prof.map(([, c]) => c));
      const barMax = colW - 26;

      // מייקל 02.08: "לכל 30 דקות יש קוביה עם אות — שגם אצלנו יהיה זהה".
      // כשגובה-השורה מספיק (≥6px) מציירים קוביות-אותיות A,B,C... פר-תקופה,
      // בדיוק כמו סיירה; בזום-אאוט נופלים חזרה לברים (מה שסיירה עצמה עושה).
      const drawLetters = rowH >= 6;
      const cellW = drawLetters ? Math.min(9, barMax / 13) : 0;
      ctx.textAlign = 'left';
      for (const [p, c, ltrs] of prof) {
        const inVA = p >= day.val && p <= day.vah;
        if (drawLetters && ltrs) {
          ctx.font = `${Math.min(rowH - 1, 9)}px ui-monospace, monospace`;
          for (let k = 0; k < ltrs.length; k++) {
            const cx = x0 + k * cellW;
            ctx.fillStyle = inVA
              ? `rgba(22,163,74,${0.35 * alpha})`
              : `rgba(90,120,132,${0.22 * alpha})`;
            ctx.fillRect(cx, y(p) - rowH / 2, cellW - 1, rowH - 1);
            ctx.fillStyle = inVA
              ? `rgba(190,242,210,${alpha})`
              : `rgba(170,195,205,${0.85 * alpha})`;
            ctx.fillText(ltrs[k], cx + 1.5, y(p) + rowH / 2 - 2);
          }
        } else {
          const bw = Math.max(1, (c / maxC) * barMax);
          ctx.fillStyle = inVA
            ? `rgba(22,163,74,${0.75 * alpha})`
            : `rgba(90,120,132,${0.5 * alpha})`;
          ctx.fillRect(x0, y(p) - rowH / 2, bw, Math.max(1, rowH * 0.9));
        }
      }
      // singles — נקודות לבנות בקצה
      for (const p of day.singles ?? []) {
        ctx.fillStyle = `rgba(255,255,255,${0.55 * alpha})`;
        ctx.fillRect(x0, y(p) - 0.5, 2, 1);
      }
      // POC — קו צהוב על כל רוחב-העמודה
      ctx.fillStyle = `rgba(234,179,8,${alpha})`;
      ctx.fillRect(x0, y(day.poc) - 1, barMax, 2);
      // VAH/VAL — סימוני-גבול קצרים
      ctx.fillStyle = `rgba(103,232,249,${0.65 * alpha})`;
      ctx.fillRect(x0, y(day.vah) - 0.5, 10, 1);
      ctx.fillRect(x0, y(day.val) - 0.5, 10, 1);
      // תווית-תאריך
      ctx.fillStyle = dim ? '#546e7a' : '#9fb8c2';
      ctx.textAlign = 'center'; ctx.font = 'bold 9px ui-monospace, monospace';
      ctx.fillText(date.slice(5) + (dim ? '?' : ''), x0 + barMax / 2, h - 5);
      ctx.textAlign = 'left';
      // מפריד-עמודות
      if (i > 0) {
        ctx.strokeStyle = 'rgba(255,255,255,0.06)';
        ctx.beginPath(); ctx.moveTo(i * colW + 0.5, PAD_T); ctx.lineTo(i * colW + 0.5, PAD_T + chartH); ctx.stroke();
      }
    });

    // עמודת-היום-המתהווה (מייקל 03.08) — מסגרת מקווקו + צהוב-ענבר, חלקי
    if (today) {
      const x0 = days.length * colW + 6;
      const barMax = colW - 26;
      const prof = today.profile ?? [];
      const maxC = Math.max(1, ...prof.map(([, c]) => c));
      ctx.strokeStyle = '#fbbf24'; ctx.setLineDash([3, 3]);
      ctx.strokeRect(x0 - 3, PAD_T, colW - 8, chartH);
      ctx.setLineDash([]);
      for (const [p, c] of prof) {
        const inVA = p >= today.val && p <= today.vah;
        ctx.fillStyle = inVA ? 'rgba(251,191,36,0.55)' : 'rgba(251,191,36,0.22)';
        ctx.fillRect(x0, y(p) - rowH / 2, Math.max(1, (c / maxC) * barMax), Math.max(1, rowH * 0.9));
      }
      ctx.fillStyle = '#fbbf24';
      ctx.fillRect(x0, y(today.poc) - 1, barMax, 2);
      ctx.textAlign = 'center'; ctx.font = 'bold 9px ui-monospace, monospace';
      ctx.fillText(`היום${today.day_type ? ' · ' + today.day_type : ''}`,
        x0 + barMax / 2, h - 5);
      ctx.textAlign = 'left';
    }

    // POC-מורכב — מקווקו ציאן על כל הרוחב
    ctx.strokeStyle = C; ctx.setLineDash([4, 4]); ctx.globalAlpha = 0.7;
    ctx.beginPath(); ctx.moveTo(0, y(comp.poc) + 0.5); ctx.lineTo(chartW, y(comp.poc) + 0.5); ctx.stroke();
    ctx.setLineDash([]); ctx.globalAlpha = 1;
  }, [days, dates, comp, suspects, today, w, h]);

  return <canvas ref={ref} style={{ width: w, height: h, display: 'block' }} />;
}
