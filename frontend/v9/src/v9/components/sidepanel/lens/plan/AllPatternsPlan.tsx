'use client';
// AllPatternsPlan — כל תבנית שיכולה להיווצר, איך היא מתגבשת, ולמה היא ממתינה.
// מקור: /api/v9/build/pattern-status (s2_inspector / woodies). פולינג 15s.
// מייקל 2026-07-09: בלי שורת-לינקים · "איך מתגבשת" פר-תבנית · "מה חסר" בעברית · הרלוונטית בולטת.
// מייקל 2026-07-15: "שיהיה ברור בכל רגע נתון למה לא ירה" — מיזוג פיד-ההחלטות החי
// של ה-gateway (/api/v9/gateway/decisions): פס-סיכום יומי, חותמת ירי/חסימה
// פר-תבנית עם שם-השער בעברית, ויומן-החלטות אחרון.
// 2026-07-17 (זמן-אמת בתבניות): עבר לפולר-המשותף usePatternFeed — אותם 15s, אבל
// לולאת-רשת אחת לכל פאנלי-התבניות (במקום פולר-פר-פאנל) + מחוון-טריות "נתונים
// ישנים"; lastDecisionFor עבר למודול המשותף patternTiers (כולל תיקון: החלטת
// CONFLUENCE_RI_ZLR לא תוצג עוד כהחלטה של שורת ה-ZLR ההורה).
import { useState } from 'react';
import { COLORS } from '../../../../design/tokens';
import { PATTERN_HELP, planReasonHe, gateHe } from './planHelp';
import {
  usePatternFeed, useFeedAge,
  type GatewayDecision as Decision, type DecisionsPayload,
} from '../../../../hooks/usePatternFeed';
import { lastDecisionFor } from './patternTiers';

interface PatternRow {
  id: string;
  name: string;
  status: string;
  label: string;
  reason?: string | null;
  fired_today?: boolean;
  components?: { present?: boolean; key?: string; stage?: string }[];
}

// Decision / DecisionsPayload / lastDecisionFor — עברו למקור משותף (07-17):
// usePatternFeed.ts (טיפוסי-הפיד) + patternTiers.ts (התאמת החלטה→תבנית).

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
  // 07-17 fix: הבקאנד פולט גם vetoed/unknown (s2_inspector.py:461-494,
  // woodies_inspector.py:530-569) — vetoed הוצג עד עכשיו כ"ממתין" אפור מטעה.
  vetoed: { he: 'וטו-הרשאה', color: '#f85149' },
  unknown: { he: 'אין-נתונים', color: '#8b949e' },
};

export function AllPatternsPlan({ systemId }: { systemId: number }) {
  const [openIds, setOpenIds] = useState<Record<string, boolean>>({});
  const [logOpen, setLogOpen] = useState(false);
  // 07-17: פולר משותף — 15s כמו קודם, לולאת-רשת אחת גם כשכמה פאנלים פתוחים
  const { build, decisions, error, lastFetchedAt } = usePatternFeed();
  const { ageS, stale } = useFeedAge(lastFetchedAt);

  const sysKey = systemId === 4 ? 'woodies' : 'five_min';
  const sys = (build?.systems ?? []).find((s) => s.id === sysKey);
  const rows: PatternRow[] = sys?.patterns ?? [];
  const dec: DecisionsPayload | null = decisions;
  const err = build && !sys ? 'אין נתוני תבניות למערכת זו' : !build && error ? error : null;

  if (err) return <div style={{ fontSize: 11, color: COLORS.textSecondary }}>תבניות: {err}</div>;
  if (!build) return <div style={{ fontSize: 11, color: COLORS.textSecondary }}>תבניות: טוען…</div>;
  // 07-17 fix: מערכת ללא-תבניות נעלמה בשקט — עכשיו מוצג מצב-ריק מפורש
  if (!rows.length) {
    return (
      <div style={{ fontSize: 11, color: COLORS.textSecondary, direction: 'rtl', textAlign: 'right' }}>
        אין נתוני-תבניות עדיין מהבקאנד (pattern-status ריק) — ממתין לרענון הבא.
      </div>
    );
  }

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
      {/* 07-17: מחוון-טריות — גיל-הנתונים; ישן (מחזור-פולינג שהוחמץ) = אזהרה + עמעום */}
      <div style={{ fontSize: 9, color: stale ? '#f85149' : COLORS.textTertiary, marginBottom: 4 }}>
        {stale
          ? `⚠ נתונים ישנים — עדכון אחרון לפני ${ageS}s`
          : ageS != null ? `עודכן לפני ${ageS}s · מתרענן כל 15s` : 'טוען…'}
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4,
                    opacity: stale ? 0.55 : 1, filter: stale ? 'grayscale(0.5)' : undefined }}>
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
                      {/* 07-17 (מייקל): הסבר + מבנה-גאומטרי + כמה-נרות מקוד-הדטקטור, פר-תבנית */}
                      <div><span style={{ color: COLORS.textTertiary }}>ההסבר: </span>{help.explain}</div>
                      <div style={{ marginTop: 2 }}>
                        <span style={{ color: COLORS.textTertiary }}>מבנה גאומטרי: </span>{help.structure}
                      </div>
                      <div style={{ marginTop: 2 }}>
                        <span style={{ color: '#d29922' }}>כמה נרות: </span>{help.candles}
                      </div>
                      <div style={{ marginTop: 2 }}>
                        <span style={{ color: COLORS.textTertiary }}>מפעיל: </span>{help.trigger}
                      </div>
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
              {/* 07-17 fix: key אינדקסי על רשימה שמתחדשת מלמעלה גרר שורות-DOM ממוחזרות שגויות */}
              {sysDecs.slice(0, 25).map((d, i) => (
                <DecisionLine key={`${d.ts}|${d.pattern ?? ''}|${d.direction ?? ''}|${i}`} d={d} showPattern />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
