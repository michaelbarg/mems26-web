'use client';
/**
 * NearestFireStrip — "🎯 הכי קרוב לירי" (מייקל 27.08: "ביקשתי לשים לי בפאנל
 * את התבנית הכי קרובה לירי כדי שאדע").
 *
 * מקור: /api/v9/mobile/data (אותו זרם שהטלפון צורך — patterns[] עם status+reason).
 * דירוג: תבנית חמושה עם פער-מספרי בהודעת-ההמתנה (gap=Xpts) — הקטן ביותר מנצח;
 * בלי פער מדיד — הראשונה החמושה. פולינג 15s (רצפת-הפולינג: לא להוריד בלי אישור).
 */
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

type Pat = { name?: string; sys?: string; status?: string; reason?: string };

export function NearestFireStrip() {
  const [near, setNear] = useState<{ p: Pat; gap: number | null } | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        // מקור ציבורי-מקומי (בלי מפתח): build/pattern-status — אותו זרם
        // שמזין את הטלפון, systems[].patterns[] עם status+reason.
        const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const r = await fetch(`${API}/api/v9/build/pattern-status`, { cache: 'no-store' });
        if (!r.ok) throw new Error(String(r.status));
        const d = await r.json();
        const pats: Pat[] = (d?.systems || []).flatMap(
          (s: { id?: string; patterns?: Pat[] }) =>
            (s.patterns || []).map((p) => ({ ...p, sys: s.id })));
        let best: { p: Pat; gap: number | null } | null = null;
        for (const p of pats) {
          if (!['armed', 'forming', 'ready'].includes(String(p.status))) continue;
          const m = /gap=(-?[0-9.]+)\s*pts/.exec(String(p.reason || ''));
          const g = m ? Math.abs(parseFloat(m[1])) : null;
          if (!best) { best = { p, gap: g }; continue; }
          if (g !== null && (best.gap === null || g < best.gap)) best = { p, gap: g };
        }
        if (alive) { setNear(best); setErr(false); }
      } catch { if (alive) setErr(true); }
    };
    load();
    const t = setInterval(load, 15000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  // ביקורת-UX 29.08: קודם `if (err || !near) return null` — כלומר כשל-רשת
  // והיעדר-תבנית נראו זהים: השורה פשוט נעלמה. מייקל ביקש את השורה הזו כדי
  // *לדעת*, אז "לא הצלחתי לקרוא" חייב להיראות אחרת מ"אין תבנית קרובה".
  if (err) return (
    <div dir="rtl" style={{
      margin: '4px 6px', padding: '5px 8px', background: '#2a1f0a',
      border: '1px solid #eab30855', borderRadius: 6, fontSize: 10, color: '#facc15',
    }} title="הקריאה ל-/api/v9/build/pattern-status נכשלה — אין לדעת מה קרוב לירי">
      ⚠ הכי-קרוב-לירי: אין נתונים (שגיאת-קריאה)
    </div>
  );
  if (!near) return null; // באמת אין תבנית קרובה — לא תופסים מקום
  return (
    <div dir="rtl" style={{
      margin: '4px 6px', padding: '5px 8px',
      background: '#13261a', border: '1px solid #2ea04355', borderRadius: 6,
      fontSize: 11, lineHeight: 1.5, color: COLORS.textPrimary,
    }}>
      <span style={{ color: '#3fb950', fontWeight: 700 }}>
        🎯 הכי קרוב לירי: {near.p.name}
      </span>
      {near.gap !== null && (
        <span> · {near.gap.toFixed(2)} נק׳ מהטריגר</span>
      )}
      <div style={{ color: COLORS.textTertiary, fontSize: 10, direction: 'ltr', textAlign: 'right' }}>
        {String(near.p.reason || '').slice(0, 90)}
      </div>
    </div>
  );
}
