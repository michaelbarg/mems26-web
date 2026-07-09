'use client';
// AllPatternsPlan — כל תבנית שיכולה להיווצר + למה ממתינים (מייקל 2026-07-08/09:
// "שבתכנון יהיה אפשר לראות כל תבנית, למה ממתינים, שהרלוונטית תבלוט, הסברים ברורים").
// מקור: /api/v9/build/pattern-status (‏s2_inspector — 10 תבניות עם רכיבים+סיבה).
// פולינג 15s ‏(diagnostic cadence — בתוך רצפות ה-polling המאושרות).
import { useCallback, useEffect, useState } from 'react';
import { COLORS } from '../../../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

interface PatternRow {
  id: string;
  name: string;
  status: string;
  label: string;
  reason?: string | null;
  fired_today?: boolean;
  components?: { present?: boolean; key?: string; stage?: string }[];
}

// תרגום מפתחות-רכיבים לעברית ברורה (ה"מעורפל" של מייקל)
const KEY_HE: Record<string, string> = {
  five_min_bar_recency: 'ברים טריים (5 דק׳)',
  cci_present: 'CCI זמין',
  mode_context: 'הקשר-מצב (FH/RTH)',
  fhb_eligible: 'חלון שעה-ראשונה',
  cot_amt: 'COT/AMT (לא נדרש — S3 מושתק)',
  volume_ok: 'נפח מאשר',
  location_ok: 'מיקום מול POC',
  auth_cell: 'תא-הרשאה לסוג-היום',
};

function heReason(reason?: string | null): string {
  if (!reason) return '';
  let r = reason.replace('Missing: ', 'חסר: ');
  for (const [k, v] of Object.entries(KEY_HE)) r = r.replaceAll(`data.${k}`, v).replaceAll(k, v);
  return r;
}

const ST: Record<string, { he: string; color: string }> = {
  ready: { he: 'מוכן לירי', color: '#3fb950' },
  armed: { he: 'חמוש', color: '#3fb950' },
  building: { he: 'בהתהוות', color: '#d29922' },
  blocked: { he: 'ממתין', color: '#8b949e' },
  skip: { he: 'SKIP לסוג-היום', color: '#f85149' },
  fired: { he: 'ירה היום', color: '#58a6ff' },
};

export function AllPatternsPlan({ systemId }: { systemId: number }) {
  const [rows, setRows] = useState<PatternRow[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v9/build/pattern-status`, { cache: 'no-store' });
      if (!res.ok) { setErr(`HTTP ${res.status}`); return; }
      const d = await res.json();
      const systems = Array.isArray(d) ? d : d.systems || [];
      const sysKey = systemId === 4 ? 'woodies' : 'five_min';
      const sys = systems.find((s: { id?: string }) => s.id === sysKey);
      setRows(sys?.patterns || []);
      setErr(sys ? null : 'אין נתוני תבניות למערכת זו');
    } catch (e) { setErr(String(e)); }
  }, [systemId]);

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [load]);

  if (err) return <div style={{ fontSize: 11, color: COLORS.textSecondary }}>תבניות: {err}</div>;
  if (!rows.length) return null;

  // מיון: הכי-קרוב-לירי קודם (שיעור רכיבים ירוקים), ‏SKIP בסוף
  const scored = rows.map((p) => {
    const comps = p.components || [];
    const present = comps.filter((c) => c.present).length;
    const score = p.status === 'skip' ? -1 : comps.length ? present / comps.length : 0;
    return { ...p, _score: score, _present: present, _total: comps.length };
  }).sort((a, b) => b._score - a._score);

  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: COLORS.textPrimary }}>
          כל התבניות — מי הכי קרובה לירי ולמה ממתינים
        </div>
        <div style={{ fontSize: 10.5, whiteSpace: 'nowrap' }}>
          <a href="/board#tasks" target="_blank" rel="noreferrer" style={{ color: '#58a6ff', textDecoration: 'none' }}>📋 משימות</a>
          <span style={{ color: '#30363d' }}> · </span>
          <a href="/board#system6" target="_blank" rel="noreferrer" style={{ color: '#58a6ff', textDecoration: 'none' }}>🛡 לוג מערכת 6</a>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {scored.map((p, i) => {
          const st = ST[p.status] || ST.blocked;
          const top = i === 0 && p._score > 0;
          return (
            <div key={p.id} style={{
              padding: '6px 8px', borderRadius: 6,
              border: `1px solid ${top ? st.color : '#21262d'}`,
              background: top ? `${st.color}14` : '#0d1117',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontSize: 12, color: COLORS.textPrimary, fontWeight: top ? 700 : 400 }}>
                  {top ? '⭐ ' : ''}{p.name}
                </span>
                <span style={{ fontSize: 10, color: st.color }}>
                  {st.he}{p._total ? ` · ${p._present}/${p._total} תנאים` : ''}
                </span>
              </div>
              {p.reason && p.status !== 'ready' && (
                <div style={{ fontSize: 10.5, color: COLORS.textSecondary, marginTop: 2 }}>
                  {heReason(p.reason)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
