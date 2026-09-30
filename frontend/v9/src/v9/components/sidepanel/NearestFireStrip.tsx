'use client';
/**
 * NearestFireStrip — "🎯 תור לירי" (מייקל 27.08: "ביקשתי לשים לי בפאנל את התבנית
 * הכי קרובה לירי כדי שאדע"; מייקל 30.09: "אני לא באמת מבין מה התבנית שעומדת בתור לירי").
 *
 * מקור: /api/v9/build/pattern-status (אותו זרם שהטלפון צורך — systems[].patterns[]
 * עם status+reason+components[]) + /api/v9/tree/state (הצומת והתוכנית של העץ).
 *
 * דירוג (30.09): קודם הדירוג היה "הפער-המספרי הקטן, ובלעדיו — הראשונה החמושה" — כלומר
 * ברוב היום השורה הציגה תבנית שרירותית (הראשונה ברשימה) או נעלמה. עכשיו: לפי
 * התקדמות-בשלבים — components[].present (כמה בדיקות עברו מתוך כמה; המפקח מוסיף בדיקות
 * ככל שהזיהוי מתקדם, אז יחס גבוה = קרובה יותר), שובר-שוויון: פער-מספרי בהודעת-ההמתנה
 * (gap=Xpts) — הקטן מנצח. מציגים את 3 הראשונות + לְמה כל אחת מחכה + מה העץ לוקח
 * עכשיו לכל כיוון. השורה לעולם לא נעלמת: "אין תבנית בתור" נראה אחרת מ"שגיאת-קריאה".
 * פולינג 15s לשני המקורות (רצפת-הפולינג הדיאגנוסטית — לא להוריד בלי אישור).
 */
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const QUEUE_STATUSES = new Set(['armed', 'forming', 'ready']);
// רק מערכות-ירי; S1 (סיווג-יום) ו-bridge אינם "תבנית בתור".
const FIRING_SYS: Record<string, string> = { five_min: 'S2', woodies: 'S4', footprint: 'S3' };
const KINDS = ['WITH_DRIVE', 'REVERSAL', 'EDGE_FADE', 'PULLBACK', 'BREAK', 'VALUE_RETURN'] as const;
const KIND_HEB: Record<string, string> = {
  WITH_DRIVE: 'עם-הדרייב', REVERSAL: 'היפוך', EDGE_FADE: 'דהיית-קצה',
  PULLBACK: 'פולבק', BREAK: 'פריצה', VALUE_RETURN: 'חזרה-לערך',
};
const TOP_N = 3;

type Comp = { stage?: string; key?: string; present?: boolean };
type Pat = { id?: string; name?: string; status?: string; reason?: string; components?: Comp[] };
type Row = {
  id: string; name: string; sys: string; dir: 'LONG' | 'SHORT' | null;
  ok: number; total: number; ratio: number; gap: number | null;
  awaitKey: string | null; awaitDetail: string; ready: boolean;
};
type Counts = { queued: number; blocked: number; fired: number };
type Leaf = { leaf?: string };
type TreePlan = { LONG?: Record<string, Leaf>; SHORT?: Record<string, Leaf> };
type TreeState = { mode?: string; plan?: TreePlan; error?: string };

function direction(p: Pat): 'LONG' | 'SHORT' | null {
  const s = `${p.id || ''} ${p.name || ''}`.toUpperCase();
  if (/(^|[_\s])LONG($|[_\s])/.test(s)) return 'LONG';
  if (/(^|[_\s])SHORT($|[_\s])/.test(s)) return 'SHORT';
  return null;
}

function toRow(p: Pat, sysId: string): Row {
  const comps = p.components || [];
  const total = comps.length;
  const ok = comps.filter((c) => c.present === true).length;
  const reason = String(p.reason || '');
  const m = /gap=(-?[0-9.]+)\s*pts/.exec(reason);
  const aw = /^Awaiting:\s*([^—]+?)\s*(?:—\s*(.*))?$/.exec(reason);
  const firstMissing = comps.find((c) => c.present !== true)?.key || null;
  return {
    id: String(p.id || ''), name: String(p.name || p.id || '?'), sys: FIRING_SYS[sysId] || sysId,
    dir: direction(p), ok, total, ratio: total ? ok / total : 0,
    gap: m ? Math.abs(parseFloat(m[1])) : null,
    awaitKey: aw ? aw[1].trim() : firstMissing,
    awaitDetail: aw ? (aw[2] || '').trim() : reason,
    ready: total > 0 && ok === total,
  };
}

function rank(a: Row, b: Row): number {
  if (a.ready !== b.ready) return a.ready ? -1 : 1;
  if (a.ratio !== b.ratio) return b.ratio - a.ratio;
  if (a.gap !== b.gap) {
    if (a.gap === null) return 1;
    if (b.gap === null) return -1;
    return a.gap - b.gap;
  }
  return a.name.localeCompare(b.name);
}

function kindsOf(plan: TreePlan | undefined, dir: 'LONG' | 'SHORT', leaf: string): string[] {
  const side = plan?.[dir] || {};
  return KINDS.filter((k) => side[k]?.leaf === leaf).map((k) => KIND_HEB[k] || k);
}

export function NearestFireStrip() {
  const [rows, setRows] = useState<Row[]>([]);
  const [counts, setCounts] = useState<Counts>({ queued: 0, blocked: 0, fired: 0 });
  const [tree, setTree] = useState<TreeState | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      const [ps, ts] = await Promise.allSettled([
        fetch(`${API}/api/v9/build/pattern-status`, { cache: 'no-store' }).then((r) => {
          if (!r.ok) throw new Error(String(r.status));
          return r.json();
        }),
        fetch(`${API}/api/v9/tree/state`, { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)),
      ]);
      if (!alive) return;
      if (ps.status === 'fulfilled') {
        const d = ps.value as { systems?: Array<{ id?: string; patterns?: Pat[] }> };
        const all: Row[] = [];
        const c: Counts = { queued: 0, blocked: 0, fired: 0 };
        for (const s of d?.systems || []) {
          const sysId = String(s.id || '');
          if (!FIRING_SYS[sysId]) continue;
          for (const p of s.patterns || []) {
            const st = String(p.status || '');
            if (st === 'blocked') c.blocked += 1;
            else if (st === 'fired') c.fired += 1;
            if (!QUEUE_STATUSES.has(st)) continue;
            c.queued += 1;
            all.push(toRow(p, sysId));
          }
        }
        all.sort(rank);
        setRows(all.slice(0, TOP_N));
        setCounts(c);
        setErr(false);
      } else {
        setErr(true);
      }
      setTree(ts.status === 'fulfilled' ? (ts.value as TreeState | null) : null);
      setLoaded(true);
    };
    load();
    const t = setInterval(load, 15000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  // ביקורת-UX 29.08: כשל-רשת והיעדר-תבנית חייבים להיראות שונים. מייקל ביקש את
  // השורה הזו כדי *לדעת* — אז גם "אין תבנית בתור" מוצג במפורש (30.09), לא נעלם.
  if (err) return (
    <div dir="rtl" style={{
      margin: '4px 6px', padding: '5px 8px', background: '#2a1f0a',
      border: '1px solid #eab30855', borderRadius: 6, fontSize: 10, color: '#facc15',
    }} title="הקריאה ל-/api/v9/build/pattern-status נכשלה — אין לדעת מה בתור לירי">
      ⚠ תור-לירי: אין נתונים (שגיאת-קריאה)
    </div>
  );

  const plan = tree?.plan;
  const treeLine = !tree
    ? 'העץ: אין נתונים'
    : tree.mode === 'off'
      ? 'העץ כבוי'
      : (() => {
          const fmt = (dir: 'LONG' | 'SHORT') => {
            const take = kindsOf(plan, dir, 'TAKE');
            const shadow = kindsOf(plan, dir, 'SHADOW');
            if (!take.length && !shadow.length) return 'סגור';
            return `${take.join('·') || '—'}${shadow.length ? ` (צל: ${shadow.join('·')})` : ''}`;
          };
          return `העץ לוקח עכשיו · לונג: ${fmt('LONG')} · שורט: ${fmt('SHORT')}`;
        })();

  const mono = { fontFamily: 'ui-monospace, monospace' } as const;

  return (
    <div dir="rtl" style={{
      margin: '4px 6px', padding: '5px 8px',
      background: '#13261a', border: '1px solid #2ea04355', borderRadius: 6,
      fontSize: 10, lineHeight: 1.45, color: COLORS.textPrimary,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 6 }}>
        <span style={{ color: '#3fb950', fontWeight: 700, fontSize: 11, whiteSpace: 'nowrap' }}>🎯 תור לירי</span>
        <span style={{ color: COLORS.textTertiary, fontSize: 9, whiteSpace: 'nowrap' }}
          title="חמושות = ממתינות לתנאי; חסומות = חסר נתון/מושתקות; ירו = ירו כבר היום">
          {loaded ? `${counts.queued} חמושות · ${counts.blocked} חסומות · ${counts.fired} ירו` : 'טוען…'}
        </span>
      </div>

      {loaded && rows.length === 0 && (
        <div style={{ color: COLORS.textTertiary, marginTop: 2 }}>
          אין תבנית בתור כרגע — אף תבנית חמושה (מחוץ ל-RTH / חסר נתון / כולן ירו)
        </div>
      )}

      {rows.map((r, i) => (
        <div key={`${r.sys}:${r.id}`} title={`${r.name} · ${r.sys} · ${r.awaitKey ? 'ממתינה ל-' + r.awaitKey : ''}\n${r.awaitDetail}`}
          style={{ borderTop: `1px solid ${COLORS.borderFaint}`, paddingTop: 3, marginTop: 3 }}>
          {/* שורה 1: שם · מערכת · כיוון — שורה אחת קבועה (ellipsis), בלי גלישה */}
          <div style={{ display: 'flex', gap: 5, alignItems: 'baseline', whiteSpace: 'nowrap', minWidth: 0 }}>
            <span style={{ color: COLORS.textTertiary, flexShrink: 0 }}>{i + 1}.</span>
            <span dir="ltr" style={{
              fontWeight: 700, color: r.ready ? '#facc15' : '#e5e7eb',
              flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', textAlign: 'right',
            }}>{r.name}</span>
            <span style={{ color: COLORS.textTertiary, flexShrink: 0 }}>{r.sys}</span>
            {r.dir && (
              <span style={{ color: r.dir === 'LONG' ? '#4ade80' : '#f87171', fontWeight: 700, flexShrink: 0 }}>
                {r.dir === 'LONG' ? '▲ לונג' : '▼ שורט'}
              </span>
            )}
          </div>
          {/* שורה 2: התקדמות · פער · לְמה מחכה */}
          <div style={{
            display: 'flex', gap: 5, alignItems: 'baseline', whiteSpace: 'nowrap', minWidth: 0,
            fontSize: 9, color: COLORS.textTertiary,
          }}>
            <span dir="ltr" style={{ ...mono, color: r.ready ? '#facc15' : '#67e8f9', flexShrink: 0 }}
              title="בדיקות שעברו מתוך כלל בדיקות-המפקח (נתונים · שער-סוג-יום · זיהוי · יעדים)">
              {r.ok}/{r.total} ✓
            </span>
            {r.gap !== null && (
              <span style={{ color: '#facc15', flexShrink: 0 }} title="המרחק (בנקודות) מהטריגר של התנאי החסר">
                {r.gap.toFixed(2)} נק׳
              </span>
            )}
            <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {r.ready
                ? 'כל הבדיקות עברו — ממתינה לניתוב (שער/עץ)'
                : <>ממתינה ל-<span dir="ltr" style={{ ...mono, color: '#e5e7eb' }}>{r.awaitKey || '?'}</span></>}
            </span>
          </div>
          {/* שורה 3 (רק לראשונה בתור): הפירוט המספרי של התנאי החסר */}
          {i === 0 && r.awaitDetail && (
            <div dir="ltr" style={{
              ...mono, fontSize: 9, color: COLORS.textTertiary, direction: 'ltr', textAlign: 'right',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {r.awaitDetail}
            </div>
          )}
        </div>
      ))}

      <div style={{
        marginTop: 3, paddingTop: 3, borderTop: `1px solid ${COLORS.borderFaint}`,
        color: COLORS.textTertiary, fontSize: 9,
      }} title="מה עץ-ההחלטות (v3) לוקח כרגע לכל כיוון — מתוך /api/v9/tree/state (אותו מקור כמו שורת-העץ למעלה)">
        🌳 {treeLine}
      </div>
    </div>
  );
}
