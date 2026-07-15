'use client';
// AllPatternsPlan — כל תבנית שיכולה להיווצר, איך היא מתגבשת, ולמה היא ממתינה.
// מקור: /api/v9/build/pattern-status (s2_inspector / woodies). פולינג 15s.
// מייקל 2026-07-09: בלי שורת-לינקים · "איך מתגבשת" פר-תבנית · "מה חסר" בעברית · הרלוונטית בולטת.
// מייקל 2026-07-15: "שיהיה ברור בכל רגע נתון למה לא ירה" — מיזוג פיד-ההחלטות החי
// של ה-gateway (/api/v9/gateway/decisions): פס-סיכום יומי, חותמת ירי/חסימה
// פר-תבנית עם שם-השער בעברית, ויומן-החלטות אחרון.
import { useCallback, useEffect, useState } from 'react';
import { COLORS } from '../../../../design/tokens';
import { PATTERN_HELP, planReasonHe, gateHe } from './planHelp';

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

interface Decision {
  ts: string;
  t_il?: string | null;
  system: number;
  pattern?: string | null;
  direction?: string | null;
  entry?: number | null;
  blocked_by?: string | null;
  outcome: string;
  trade_id?: number | string | null;
}

interface DecisionsPayload {
  decisions: Decision[];
  today?: { fired: number; blocked: number; shadow_only: number; by_gate: Record<string, number> };
}

const norm = (s?: string | null) => (s || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
/** ההחלטה האחרונה של ה-gateway עבור תבנית זו (התאמת-שם גמישה). */
function lastDecisionFor(p: PatternRow, decs: Decision[]): Decision | null {
  const pid = norm(p.id), pname = norm(p.name);
  for (const d of decs) { // decs מגיע חדש-ראשון מהשרת
    const gp = norm(d.pattern);
    if (!gp) continue;
    if (gp.includes(pid) || pid.includes(gp) || gp.includes(pname) || pname.includes(gp)) return d;
  }
  return null;
}

/** שורת-החלטה אחת בעברית: מה קרה + למה. */
function DecisionLine({ d, showPattern }: { d: Decision; showPattern?: boolean }) {
  const t = d.t_il ? d.t_il.slice(0, 5) : '';
  const pat = showPattern ? `${d.pattern || '?'} ${d.direction || ''} ` : '';
  if (d.blocked_by) {
    const g = gateHe(d.blocked_by);
    return (
      <div style={{ fontSize: 10.5, color: '#f0883e', lineHeight: 1.45 }}>
        ⛔ {t} {pat}נחסם — <b>{g.name}</b><span style={{ color: COLORS.textSecondary }}> · {g.why}</span>
      </div>
    );
  }
  if (d.outcome === 'live' || d.outcome === 'demo') {
    return (
      <div style={{ fontSize: 10.5, color: '#3fb950', lineHeight: 1.45 }}>
        🔫 {t} {pat}ירה ({d.outcome === 'live' ? 'לייב' : 'דמו'}{d.trade_id ? ` #${d.trade_id}` : ''})
      </div>
    );
  }
  return (
    <div style={{ fontSize: 10.5, color: '#8b949e', lineHeight: 1.45 }}>
      👁 {t} {pat}עבר את כל השערים — צל בלבד (לייב לא-פעיל או סלוט תפוס)
    </div>
  );
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
  const [dec, setDec] = useState<DecisionsPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [openIds, setOpenIds] = useState<Record<string, boolean>>({});
  const [logOpen, setLogOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [res, dres] = await Promise.all([
        fetch(`${API}/api/v9/build/pattern-status`, { cache: 'no-store' }),
        fetch(`${API}/api/v9/gateway/decisions?limit=150`, { cache: 'no-store' }).catch(() => null),
      ]);
      if (!res.ok) { setErr(`HTTP ${res.status}`); return; }
      const d = await res.json();
      const systems = Array.isArray(d) ? d : d.systems || [];
      const sysKey = systemId === 4 ? 'woodies' : 'five_min';
      const sys = systems.find((s: { id?: string }) => s.id === sysKey);
      setRows(sys?.patterns || []);
      setErr(sys ? null : 'אין נתוני תבניות למערכת זו');
      if (dres && dres.ok) setDec(await dres.json());
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

  // פיד-ההחלטות של המערכת הזו (חדש-ראשון) + ספירות-היום
  const sysDecs = (dec?.decisions || []).filter((d) => d.system === systemId);
  const nFired = sysDecs.filter((d) => d.outcome === 'live' || d.outcome === 'demo').length;
  const nShadow = sysDecs.filter((d) => d.outcome === 'shadow_only').length;
  const nBlocked = sysDecs.filter((d) => !!d.blocked_by).length;
  const gateCounts: Record<string, number> = {};
  for (const d of sysDecs) if (d.blocked_by) gateCounts[d.blocked_by] = (gateCounts[d.blocked_by] || 0) + 1;
  const topGates = Object.entries(gateCounts).sort((a, b) => b[1] - a[1]).slice(0, 3);

  return (
    <div style={{ marginBottom: 10, direction: 'rtl', textAlign: 'right' }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: COLORS.textPrimary, marginBottom: 6 }}>
        כל התבניות — מי הכי קרובה לירי, איך היא מתגבשת, ולמה ממתינים
      </div>
      {/* 07-15: פס "למה לא ירה" — סיכום ניסיונות-הירי מול השער מאז-הריסטארט */}
      <div style={{
        padding: '6px 8px', borderRadius: 6, marginBottom: 6,
        border: `1px solid ${nBlocked > nFired ? '#f0883e55' : '#21262d'}`, background: '#0d1117',
      }}>
        {sysDecs.length ? (
          <>
            <div style={{ fontSize: 11, color: COLORS.textPrimary }}>
              ניסיונות-ירי: <b>{sysDecs.length}</b> · ירו <b style={{ color: '#3fb950' }}>{nFired}</b>
              {nShadow ? <> · צל-בלבד <b style={{ color: '#8b949e' }}>{nShadow}</b></> : null}
              {' '}· נחסמו <b style={{ color: '#f0883e' }}>{nBlocked}</b>
            </div>
            {topGates.length > 0 && (
              <div style={{ fontSize: 10, color: COLORS.textSecondary, marginTop: 2 }}>
                חוסמים עיקריים: {topGates.map(([k, n]) => `${gateHe(k).name} ×${n}`).join(' · ')}
              </div>
            )}
          </>
        ) : (
          <div style={{ fontSize: 10.5, color: COLORS.textSecondary }}>
            אף מועמד לא הגיע לשער-הירי מאז הפעלת-הבקאנד — כשאין ירי, הסיבה היא
            בשלב-ההתגבשות (ראה "מה חסר" בתבניות למטה), לא בחסימת-שער.
          </div>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {scored.map((p, i) => {
          const st = ST[p.status] || ST.blocked;
          const top = i === 0 && p._score > 0;
          const help = PATTERN_HELP[p.id];
          const isOpen = openIds[p.id] ?? top;
          const showMissing = !!p.reason && p.status !== 'ready' && p.status !== 'fired';
          const lastDec = lastDecisionFor(p, sysDecs);
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
              {lastDec && (
                <div style={{ marginTop: 3 }}>
                  <DecisionLine d={lastDec} />
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
      {/* 07-15: יומן-ההחלטות המלא — כל ניסיון-ירי אחרון עם הסיבה, חדש-ראשון */}
      {sysDecs.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <button
            onClick={() => setLogOpen((o) => !o)}
            style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                     fontSize: 10.5, color: COLORS.textTertiary, fontFamily: 'inherit' }}
          >
            יומן ניסיונות-ירי ({sysDecs.length}) {logOpen ? '▾' : '▸'}
          </button>
          {logOpen && (
            <div style={{ marginTop: 3, display: 'flex', flexDirection: 'column', gap: 2,
                          maxHeight: 180, overflowY: 'auto', padding: '4px 6px',
                          border: '1px solid #21262d', borderRadius: 6, background: '#0d1117' }}>
              {sysDecs.slice(0, 25).map((d, i) => <DecisionLine key={i} d={d} showPattern />)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
