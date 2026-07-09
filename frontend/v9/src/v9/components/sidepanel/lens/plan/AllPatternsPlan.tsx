'use client';
// AllPatternsPlan — כל תבנית שיכולה להיווצר, איך היא מתגבשת, ולמה היא ממתינה.
// מקור: /api/v9/build/pattern-status (s2_inspector / woodies). פולינג 15s.
// מייקל 2026-07-09: בלי שורת-לינקים · "איך מתגבשת" פר-תבנית · "מה חסר" בעברית · הרלוונטית בולטת.
import { useCallback, useEffect, useState } from 'react';
import { COLORS } from '../../../../design/tokens';
import { PATTERN_HELP, planReasonHe } from './planHelp';

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
  const [openIds, setOpenIds] = useState<Record<string, boolean>>({});

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

  // מיון: הכי-קרוב-לירי קודם (שיעור רכיבים ירוקים), SKIP בסוף
  const scored = rows.map((p) => {
    const comps = p.components || [];
    const present = comps.filter((c) => c.present).length;
    const score = p.status === 'skip' ? -1 : comps.length ? present / comps.length : 0;
    return { ...p, _score: score, _present: present, _total: comps.length };
  }).sort((a, b) => b._score - a._score);

  return (
    <div style={{ marginBottom: 10, direction: 'rtl', textAlign: 'right' }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: COLORS.textPrimary, marginBottom: 6 }}>
        כל התבניות — מי הכי קרובה לירי, איך היא מתגבשת, ולמה ממתינים
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {scored.map((p, i) => {
          const st = ST[p.status] || ST.blocked;
          const top = i === 0 && p._score > 0;
          const help = PATTERN_HELP[p.id];
          const isOpen = openIds[p.id] ?? top;
          const showMissing = !!p.reason && p.status !== 'ready' && p.status !== 'fired';
          return (
            <div key={p.id} style={{
              padding: '6px 8px', borderRadius: 6,
              border: `1px solid ${top ? st.color : '#21262d'}`,
              background: top ? `${st.color}14` : '#0d1117',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 12, color: COLORS.textPrimary, fontWeight: top ? 700 : 400 }}>
                  {top ? '⭐ ' : ''}{p.name}
                  {help?.nick ? <span style={{ fontSize: 10, color: COLORS.textTertiary }}> · {help.nick}</span> : null}
                </span>
                <span style={{ fontSize: 10, color: st.color, whiteSpace: 'nowrap' }}>
                  {st.he}{p._total ? ` · ${p._present}/${p._total}` : ''}
                </span>
              </div>
              {showMissing && (
                <div style={{ fontSize: 10.5, color: COLORS.textSecondary, marginTop: 3 }}>
                  <span style={{ color: '#d29922' }}>מה חסר: </span>{planReasonHe(p.reason)}
                </div>
              )}
              {help && (
                <div style={{ marginTop: 4 }}>
                  <button
                    onClick={() => setOpenIds((o) => ({ ...o, [p.id]: !isOpen }))}
                    style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                             fontSize: 10, color: COLORS.textTertiary, fontFamily: 'inherit' }}
                  >
                    איך מתגבשת {isOpen ? '▾' : '▸'}
                  </button>
                  {isOpen && (
                    <div style={{ fontSize: 10, color: COLORS.textSecondary, lineHeight: 1.5, marginTop: 2 }}>
                      <div><span style={{ color: COLORS.textTertiary }}>מבנה: </span>{help.structure}</div>
                      <div><span style={{ color: COLORS.textTertiary }}>מפעיל: </span>{help.trigger}</div>
                      <div><span style={{ color: COLORS.textTertiary }}>מבטל: </span>{help.cancel}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
