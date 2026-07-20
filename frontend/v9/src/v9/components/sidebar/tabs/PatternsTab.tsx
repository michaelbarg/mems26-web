'use client';
// PatternsTab — לוח-התבניות בזמן-אמת (מייקל 2026-07-17: "יותר חשוב לי זמן אמת
// בתבניות... כרגע מבולבל"). במבט אחד, מהחם לקר:
//   🔥 ירי עכשיו (מפיד-ההחלטות, 5 דק׳) → 🟠 קרוב לירי → 🟡 בהתהוות → ⚪ סורק → 🚫 חסום/וטו.
// לכל שורה: התקדמות מנתוני-אמת בלבד (S4 = build_pct מהבקאנד; S2 = שלבי-הבדיקה
// האמיתיים — בלי אחוז מומצא), "מה חסר עכשיו", ורמז "מה חסם" (שם-השער בעברית).
// ההסבר הסטטי (ההסבר/מבנה-גאומטרי/נרות, 07-17 בוקר) נשאר בהרחבה — משני למידע-החי.
// נתונים: usePatternFeed — פולר משותף אחד, 15s (הקצב הקיים של פאנל-התבניות;
// אין פולינג מהיר-יותר — CLAUDE.md § Frontend Polling Floors).
import { useState } from 'react';
import { COLORS } from '../../../design/tokens';
import type { Pattern, Component, FormulaCondition, SystemBlock } from '../../build_status/types';
import {
  usePatternFeed, useFeedAge, type GatewayDecision,
} from '../../../hooks/usePatternFeed';
import {
  PATTERN_HELP, planReasonHe, gateHe, blockWhy, COMPONENT_KEY_HE,
} from '../../sidepanel/lens/plan/planHelp';
import {
  computeRow, TIER_META, TIER_ORDER, type PatternRowInfo,
} from '../../sidepanel/lens/plan/patternTiers';

const SYS_CHIP: Record<string, { label: string; color: string; system: number }> = {
  five_min: { label: 'S2', color: '#06b6d4', system: 2 },
  woodies: { label: 'S4', color: '#f59e0b', system: 4 },
};

const STATUS_HE: Record<string, { he: string; color: string }> = {
  fired: { he: 'ירה היום', color: '#3fb950' },
  armed: { he: 'חמוש', color: '#3fb950' },
  blocked: { he: 'חסום', color: '#f85149' },
  vetoed: { he: 'וטו', color: '#f85149' },
  not_applicable: { he: 'לא-פעיל', color: '#8b949e' },
  unknown: { he: 'אין-נתונים', color: '#8b949e' },
};

interface RowModel {
  p: Pattern;
  sysId: string; // 'five_min' | 'woodies'
  info: PatternRowInfo;
}

/** פס-התקדמות S4 — מ-build_pct האמיתי של הבקאנד (woodies_inspector.py:577-578). */
function BuildBar({ pct, met, total }: { pct: number; met: number; total: number }) {
  const color = pct >= 80 ? '#3fb950' : pct >= 50 ? '#d29922' : '#8b949e';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <div style={{ flex: 1, height: 4, background: '#21262d', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${Math.max(0, Math.min(100, pct))}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 8, color, fontWeight: 600, whiteSpace: 'nowrap' }}>
        {met}/{total} תנאים
      </span>
    </div>
  );
}

/** רצועת-שלבים S2 — כל מלבן = שלב-בדיקה אמיתי (הבדיקה נקטעת בכשל הראשון, לכן
 *  מלבן אדום אחרון = השלב שבו נעצרה; אין מכנה מומצא ואין אחוז). */
function DetStrip({ steps, passed, fullPass }: { steps: Component[]; passed: number; fullPass: boolean }) {
  if (!steps.length) return null;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <div style={{ display: 'flex', gap: 2, flex: 1 }}>
        {steps.map((c, i) => (
          <div
            key={`${c.key}-${i}`}
            title={c.key}
            style={{
              flex: 1, height: 5, borderRadius: 2,
              background: c.present ? '#3fb950' : '#da3633',
            }}
          />
        ))}
      </div>
      <span style={{ fontSize: 8, color: fullPass ? '#3fb950' : COLORS.textTertiary, whiteSpace: 'nowrap' }}>
        {fullPass ? 'כל השלבים ✓' : `עבר ${passed}`}
      </span>
    </div>
  );
}

/** שורת-החלטה קומפקטית: מה קרה בניסיון-הירי ולמה (שם-השער בעברית מ-GATE_HE). */
function DecisionMark({ d, dim }: { d: GatewayDecision; dim?: boolean }) {
  const t = d.t_il ? d.t_il.slice(0, 5) : '';
  if (d.blocked_by) {
    const g = gateHe(d.blocked_by);
    const why = blockWhy(d);
    return (
      <div style={{ fontSize: 9.5, color: dim ? COLORS.textTertiary : '#f0883e', lineHeight: 1.45 }}>
        ⛔ {t} נחסם — <b>{g.name}</b>
        {!dim && <span style={{ color: COLORS.textSecondary }}> · {why}</span>}
      </div>
    );
  }
  if (d.outcome === 'live' || d.outcome === 'demo') {
    return (
      <div style={{ fontSize: 9.5, color: '#3fb950', lineHeight: 1.45 }}>
        🔫 {t} ירה ({d.outcome === 'live' ? 'לייב' : 'דמו'}{d.trade_id ? ` #${d.trade_id}` : ''})
      </div>
    );
  }
  return (
    <div style={{ fontSize: 9.5, color: '#8b949e', lineHeight: 1.45 }}>
      👁 {t} עבר את כל השערים — צל בלבד
    </div>
  );
}

/** תנאי-נוסחה S4 בהרחבה — ✓/✗ + נדרש/בפועל (formula מ-woodies_inspector.py:573-590). */
function FormulaLine({ f }: { f: FormulaCondition }) {
  return (
    <div style={{ display: 'flex', gap: 4, fontSize: 9, padding: '1px 0', alignItems: 'baseline',
                  color: f.met ? COLORS.textSecondary : COLORS.textTertiary }}>
      <span style={{ width: 10, textAlign: 'center', color: f.met ? '#3fb950' : '#f85149' }}>
        {f.met ? '✓' : '✗'}
      </span>
      <span style={{ flex: 1 }}>{f.label}</span>
      <span dir="ltr" style={{ color: COLORS.textTertiary, maxWidth: 70, overflow: 'hidden',
                               textOverflow: 'ellipsis', whiteSpace: 'nowrap', unicodeBidi: 'plaintext' }}>
        {f.actual ?? '—'}
      </span>
    </div>
  );
}

/** שלב-בדיקה S2 בהרחבה — ✓/✗ + השם בעברית + המדידה הגולמית. */
function StepLine({ c }: { c: Component }) {
  return (
    <div style={{ display: 'flex', gap: 4, fontSize: 9, padding: '1px 0', alignItems: 'baseline',
                  color: c.present ? COLORS.textSecondary : COLORS.textTertiary }}>
      <span style={{ width: 10, textAlign: 'center', color: c.present ? '#3fb950' : '#f85149' }}>
        {c.present ? '✓' : '✗'}
      </span>
      <span style={{ flex: 1 }}>{COMPONENT_KEY_HE[c.key] || c.key}</span>
    </div>
  );
}

function PatternRow({ r, open, onToggle }: { r: RowModel; open: boolean; onToggle: () => void }) {
  const { p, info } = r;
  const sys = SYS_CHIP[r.sysId];
  const st = STATUS_HE[p.status] || STATUS_HE.unknown;
  const tierColor = TIER_META[info.tier].color;
  const help = PATTERN_HELP[p.id];
  const compact = info.tier === 'idle';
  const hot = info.hotDec;
  // רמז "מה חסם" גם כשהניסיון כבר לא בחלון-החם (ההחלטה האחרונה מאז עליית-הבקאנד)
  const staleBlockHint = !hot && info.lastDec?.blocked_by ? info.lastDec : null;

  return (
    <div style={{
      borderRadius: 5, marginBottom: 3, overflow: 'hidden',
      border: `1px solid ${info.tier === 'fire' ? tierColor : COLORS.borderFaint}`,
      background: info.tier === 'fire' ? `${tierColor}14` : COLORS.bgSurface2,
    }}>
      {/* שורה ראשית — לחיצה פותחת פירוט */}
      <div onClick={onToggle}
           style={{ display: 'flex', alignItems: 'center', gap: 4, padding: compact ? '2px 5px' : '3px 5px',
                    cursor: 'pointer' }}>
        <span style={{ fontSize: 7, color: COLORS.textTertiary }}>{open ? '▼' : '◀'}</span>
        <span style={{ fontSize: 8, fontWeight: 700, color: sys?.color ?? COLORS.textTertiary,
                       border: `1px solid ${sys?.color ?? COLORS.borderSecondary}44`,
                       borderRadius: 2, padding: '0 3px', flexShrink: 0 }}>
          {sys?.label ?? r.sysId}
        </span>
        <span style={{
          fontSize: compact ? 9.5 : 10.5, fontWeight: info.tier === 'fire' || info.tier === 'close' ? 700 : 400,
          color: compact ? COLORS.textSecondary : COLORS.textPrimary,
          flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {p.name}
        </span>
        {p.fired_today && p.status !== 'fired' && (
          <span style={{ fontSize: 8, color: '#3fb950', whiteSpace: 'nowrap' }}>✓ ירה היום</span>
        )}
        <span style={{ fontSize: 8.5, color: st.color, whiteSpace: 'nowrap' }}>{st.he}</span>
      </div>

      {/* התקדמות חיה — רק לשורות שאינן "סורק" (החיסכון במקום קריטי ב-240px) */}
      {!compact && (
        <div style={{ padding: '0 6px 3px 6px' }}>
          {info.buildPct !== null && p.formula ? (
            <BuildBar pct={info.buildPct} met={p.formula.filter((f) => f.met).length} total={p.formula.length} />
          ) : (
            <DetStrip steps={info.detSteps} passed={info.detPassed} fullPass={info.detFullPass} />
          )}
        </div>
      )}

      {/* מה חסר עכשיו / למה חסום */}
      {info.tier === 'blocked' ? (
        <div style={{ padding: '0 6px 3px 6px', fontSize: 9, color: '#f85149', lineHeight: 1.4 }}>
          {planReasonHe(p.reason) || 'חסום'}
        </div>
      ) : !compact && info.missingNow ? (
        <div style={{ padding: '0 6px 3px 6px', fontSize: 9, lineHeight: 1.4 }}>
          <span style={{ color: '#d29922' }}>חסר עכשיו: </span>
          <span style={{ color: COLORS.textSecondary }}>{info.missingNow}</span>
        </div>
      ) : null}

      {/* S4 מנותב ברגע-זה (state.ready_to_route) — גם בלי שורת-החלטה עדיין */}
      {info.routingNow && !hot && (
        <div style={{ padding: '0 6px 3px 6px', fontSize: 9.5, color: '#3fb950' }}>
          🚀 מנותב עכשיו לשער (ready_to_route)
        </div>
      )}
      {/* ניסיון-הירי האחרון: בולט בחלון-החם, רמז-חסימה מוקטן אחרת */}
      {hot && (
        <div style={{ padding: '0 6px 4px 6px' }}>
          <DecisionMark d={hot} />
        </div>
      )}
      {!hot && staleBlockHint && !compact && (
        <div style={{ padding: '0 6px 3px 6px' }}>
          <DecisionMark d={staleBlockHint} dim />
        </div>
      )}

      {/* הרחבה — פירוט מלא + ההסבר הסטטי (משני למידע-החי) */}
      {open && (
        <div style={{ padding: '3px 8px 5px', background: COLORS.bgSurface1,
                      borderTop: `1px solid ${COLORS.borderFaint}` }}>
          {p.formula && p.formula.length > 0 && p.formula.map((f, i) => <FormulaLine key={i} f={f} />)}
          {(!p.formula || p.formula.length === 0) && info.detSteps.map((c, i) => <StepLine key={i} c={c} />)}
          {compact && info.missingNow && (
            <div style={{ fontSize: 9, marginTop: 2 }}>
              <span style={{ color: '#d29922' }}>חסר עכשיו: </span>
              <span style={{ color: COLORS.textSecondary }}>{info.missingNow}</span>
            </div>
          )}
          {info.lastDec && !hot && (
            <div style={{ marginTop: 3 }}>
              <span style={{ fontSize: 8.5, color: COLORS.textTertiary }}>ניסיון-ירי אחרון: </span>
              <DecisionMark d={info.lastDec} />
            </div>
          )}
          {help && (
            <div style={{ fontSize: 9, lineHeight: 1.55, color: COLORS.textSecondary, marginTop: 4,
                          borderTop: `1px dashed ${COLORS.borderFaint}`, paddingTop: 3 }}>
              <div><span style={{ color: COLORS.textTertiary }}>ההסבר: </span>{help.explain}</div>
              <div style={{ marginTop: 2 }}>
                <span style={{ color: COLORS.textTertiary }}>מבנה גאומטרי: </span>{help.structure}
              </div>
              <div style={{ marginTop: 2 }}>
                <span style={{ color: '#d29922' }}>כמה נרות: </span>{help.candles}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function PatternsTab() {
  const { build, decisions, error, lastFetchedAt, refresh } = usePatternFeed();
  const { ageS, stale, nowMs } = useFeedAge(lastFetchedAt);
  const [openIds, setOpenIds] = useState<Record<string, boolean>>({});

  const systems: SystemBlock[] = build?.systems ?? [];
  const dayType = systems.find((s) => s.id === 'day_type');
  const decList = decisions?.decisions ?? [];

  // בניית כל השורות (S2 + S4) + חישוב-שכבה — ממוין-חי: הסדר מתעדכן בכל פול
  const rows: RowModel[] = [];
  for (const sysId of ['five_min', 'woodies'] as const) {
    const sys = systems.find((s) => s.id === sysId);
    if (!sys) continue;
    const sysDecs = decList.filter((d) => d.system === SYS_CHIP[sysId].system);
    for (const p of sys.patterns) {
      rows.push({ p, sysId, info: computeRow(p, sysDecs, nowMs) });
    }
  }
  const groups = TIER_ORDER
    .map((tier) => ({
      tier,
      rows: rows.filter((r) => r.info.tier === tier).sort((a, b) => b.info.score - a.info.score),
    }))
    .filter((g) => g.rows.length > 0);
  const nHotOrClose = rows.filter((r) => r.info.tier === 'fire' || r.info.tier === 'close').length;

  // פס-חסימות יומי (מהשדה today של פיד-ההחלטות — gateway_routes.py:82-85)
  const today = decisions?.today;
  const topGate = today && Object.keys(today.by_gate || {}).length
    ? Object.entries(today.by_gate).sort((a, b) => b[1] - a[1])[0]
    : null;

  // טריות-פיד לפי מערכת (data_freshness מהבקאנד — לא מומצא)
  const feedWarnings = (['five_min', 'woodies'] as const).flatMap((id) => {
    const s = systems.find((x) => x.id === id);
    if (!s || s.data_freshness?.fresh !== false) return [];
    const lag = s.data_freshness?.lag_seconds;
    return [`פיד ${SYS_CHIP[id].label} מפגר${lag != null ? ` (${Math.round(lag)}s)` : ''}`];
  });

  const dotColor = !lastFetchedAt ? COLORS.textTertiary : stale ? '#f85149' : '#3fb950';

  return (
    <div style={{ fontSize: 11, fontFamily: 'ui-monospace, monospace',
                  direction: 'rtl', textAlign: 'right', unicodeBidi: 'plaintext' }}>
      {/* כותרת + מחוון-טריות (עודכן-לפני + ↻ ידני; הפולינג האוטומטי 15s ברקע) */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontWeight: 700, color: COLORS.textPrimary }}>תבניות · זמן-אמת</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 6, height: 6, borderRadius: 3, background: dotColor, display: 'inline-block' }} />
          <span style={{ fontSize: 8, color: stale ? '#f85149' : COLORS.textTertiary }}>
            {ageS == null ? '…' : `${ageS}s`}
          </span>
          <button onClick={refresh}
            style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, border: 'none',
                     background: COLORS.bgSurface3, color: COLORS.textSecondary, cursor: 'pointer' }}>
            ↻
          </button>
        </span>
      </div>

      {stale && (
        <div style={{ padding: '3px 6px', borderRadius: 4, marginBottom: 4, fontSize: 9,
                      border: '1px solid #f8514955', background: '#f8514912', color: '#f85149' }}>
          ⚠ נתונים ישנים — עדכון אחרון לפני {ageS}s
        </div>
      )}
      {feedWarnings.map((w) => (
        <div key={w} style={{ padding: '2px 6px', borderRadius: 4, marginBottom: 4, fontSize: 9,
                              border: '1px solid #f0883e55', background: '#f0883e12', color: '#f0883e' }}>
          ⚠ {w} — התבניות מחושבות על הבר האחרון שהתקבל
        </div>
      ))}

      {/* הקשר-יום (S1) — שורה דחוסה; סוג-היום קובע SKIP/הרשאות לתבניות */}
      {dayType && (dayType.interpretations?.length ?? 0) > 0 && (
        <div style={{ fontSize: 8.5, color: COLORS.textSecondary, marginBottom: 4, lineHeight: 1.5 }}>
          <span style={{ color: '#a78bfa', fontWeight: 700 }}>S1 יום: </span>
          {(dayType.interpretations ?? []).map((i, idx) => (
            <span key={idx}>
              {idx > 0 ? ' · ' : ''}
              <span style={{ color: COLORS.textTertiary }}>{i.key}:</span>{i.value ?? '—'}
            </span>
          ))}
        </div>
      )}

      {/* סיכום-יום מהשער: כמה ירו / כמה נחסמו ומי החוסם העיקרי */}
      {today && (today.fired > 0 || today.blocked > 0) && (
        <div style={{ fontSize: 9, color: COLORS.textSecondary, marginBottom: 4 }}>
          היום: <b style={{ color: '#3fb950' }}>🔫 {today.fired}</b>
          {' · '}<b style={{ color: '#f0883e' }}>⛔ {today.blocked}</b>
          {topGate && <span> · חוסם עיקרי: {gateHe(topGate[0]).name} ×{topGate[1]}</span>}
        </div>
      )}

      {error && !build && (
        <div style={{ fontSize: 10, color: '#f85149' }}>שגיאת-חיבור: {error}</div>
      )}
      {!build && !error && (
        <div style={{ fontSize: 10, color: COLORS.textSecondary }}>טוען נתוני-תבניות…</div>
      )}
      {build && rows.length === 0 && (
        <div style={{ fontSize: 10, color: COLORS.textSecondary }}>
          אין נתוני-תבניות מהבקאנד (pattern-status ריק) — ממתין לרענון הבא.
        </div>
      )}

      {/* אין-חם: שהסוחר יידע במבט שאין כרגע כלום על הכוונת */}
      {rows.length > 0 && nHotOrClose === 0 && (
        <div style={{ fontSize: 9.5, color: COLORS.textTertiary, marginBottom: 4 }}>
          אין תבנית קרובה לירי כרגע — הכול בהתהוות/סריקה.
        </div>
      )}

      {/* השכבות — ממוין מהחם לקר, מתעדכן ומסתדר-מחדש בכל פול */}
      <div style={{ opacity: stale ? 0.55 : 1, filter: stale ? 'grayscale(0.5)' : undefined }}>
        {groups.map((g) => {
          const meta = TIER_META[g.tier];
          return (
            <div key={g.tier} style={{ marginBottom: 6 }}>
              <div title={meta.desc}
                   style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '2px 2px',
                            borderBottom: `1px solid ${meta.color}44`, marginBottom: 3 }}>
                <span style={{ fontSize: 11 }}>{meta.icon}</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: meta.color }}>{meta.he}</span>
                <span style={{ fontSize: 9, color: COLORS.textTertiary }}>({g.rows.length})</span>
              </div>
              {g.rows.map((r) => {
                const key = `${r.sysId}:${r.p.id}`;
                return (
                  <PatternRow
                    key={key}
                    r={r}
                    open={!!openIds[key]}
                    onToggle={() => setOpenIds((o) => ({ ...o, [key]: !o[key] }))}
                  />
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
