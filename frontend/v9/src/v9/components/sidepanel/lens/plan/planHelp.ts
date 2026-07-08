export type PlanLifecycle = 'SCANNING' | 'APPROACHING' | 'BLOCKED' | 'READY' | 'FIRING';
export type FireRowStatus = 'ok' | 'wait' | 'block';

/** What each lifecycle badge means — not approve/disapprove, derived from live checks. */
export const LIFECYCLE_HELP: Record<PlanLifecycle, { title: string; measures: string; meaning: string }> = {
  SCANNING: {
    title: 'SCANNING',
    measures: 'האם יש בכלל setup פעיל לבדיקה (תבנית, buffer, session).',
    meaning: 'אין עדיין תבנית מזוהה, או שהמערכת מחכה לנתונים / לחלון מסחר.',
  },
  APPROACHING: {
    title: 'APPROACHING',
    measures: 'האם משהו מתגבש (תבנית, IB, סיווג) אבל עדיין לא עבר את כל השלבים.',
    meaning: 'יש סיגנל חלקי — עדיין חסרים שלבי pre-fire או אישורים.',
  },
  BLOCKED: {
    title: 'BLOCKED',
    measures: 'האם שלב pre-fire נכשל (FAIL), gate סגור, או feed שבור.',
    meaning: 'לא יורה עד שהשורה האדומה ב-TO FIRE תתוקן. זה לא "דחייה ידנית" — זה חסימה לוגית.',
  },
  READY: {
    title: 'READY',
    measures: 'האם כל שלבי pre-fire עברו ו-ready_to_route=true (Woodies) או pattern מוכן (S2).',
    meaning: 'מוכן לניתוב — ה-setup יישלח ל-gateway בסגירת הבר. המצב האמיתי (live/shadow) נקבע לפי live_enabled_systems ב-gateway, לא בכיתוב הזה.',
  },
  FIRING: {
    title: 'FIRING',
    measures: 'מצב ירי פעיל / ניתוב אחרון.',
    meaning: 'המערכת שלחה או מנסה לשלוח setup ל-gateway.',
  },
};

export const SECTION_HELP = {
  state: {
    title: 'STATE',
    measures: 'סיכום מצב אחד: scanning → approaching → blocked/ready.',
    meaning: 'נגזר מ-health + decision tree + failed_stages. לחץ על ה-badge לפירוט.',
  },
  building: {
    title: 'BUILDING',
    measures: 'מה המערכת בונה עכשיו (תבנית, IB, zone) + % התקדמות (buffer / letters).',
    meaning: 'פס ההתקדמות = כמה נתונים יש מול המינימום הנדרש (למשל 14 ברים CCI).',
  },
  toFire: {
    title: 'TO FIRE',
    measures: 'כל שורה = בדיקה אחת לפני ירי. ✓ עבר | ⚠ ממתין | ● נכשל/חוסם.',
    meaning: 'לחץ שורה לראות מה נמדד, הערך בפועל, ולמה הסטטוס כזה.',
  },
  health: {
    title: 'DATA HEALTH',
    measures: 'האם snapshot מ-/cockpit/systems-snapshot מגיע בזמן + health endpoint.',
    meaning: 'אדום = נתונים עלולים להיות ישנים; לא אומר שהתבנית "רעה".',
  },
};

export const STATUS_HELP: Record<FireRowStatus, string> = {
  ok: '✓ עבר — התנאי מתקיים עכשיו לפי הנתונים הגולמיים.',
  wait: '⚠ ממתין — עדיין לא הושלם; לא בהכרח חוסם.',
  block: '● חוסם — שלב נכשל או נתון חסר; מונע ירי.',
};

/** RTL panel for Hebrew copy (detail popup, hints). */
export const PLAN_RTL_STYLE = {
  direction: 'rtl' as const,
  textAlign: 'right' as const,
  unicodeBidi: 'plaintext' as const,
};

/** Woodies A1–A7 — מה כל שלב בודק (מ-decision_tree.py). */
export const WOODIES_STAGE_HELP: Record<string, { measures: string; pass: string; fail: string }> = {
  A1: {
    measures: 'SWI / trend_state מול ביטחון בתבנית (לא לירות ב-GRAY עם conf נמוך).',
    pass: 'מגמה לא אפורה, או conf מספיק גבוה על התבנית המובילה.',
    fail: 'trend GRAY + confidence < 0.55 על התבנית הטובה ביותר.',
  },
  A2: {
    measures: 'שכל 11 המחקרים (CCI14, TCCI, EMA34, LSMA, SWI, CZI, …) קיימים בבר האחרון.',
    pass: 'אין study חסר ב-studies.',
    fail: 'רשימת missing studies ב-message.',
  },
  A3: {
    measures: 'האם זוהתה לפחות תבנית CCI (ZLR, TLB, …) בבר הנוכחי.',
    pass: 'patterns=[…] בפלט השלב.',
    fail: 'SKIP אם אין תבניות — לא חוסם אם אין setup.',
  },
  A4: {
    measures: 'הקשר consultative מ-S1 Day Type, S5 TPO, S6 Killzone, Layer0, veto (HTTP).',
    pass: 'נקראו endpoints; advisories נרשמו — לא חייב לאשר, רק לתעד.',
    fail: 'בדרך כלל לא FAIL; degraded אם endpoint לא זמין.',
  },
  A5: {
    measures: 'יישור עזר: SWI, CZI, TCCI, LSMA, EMA עם כיוון התבנית.',
    pass: 'עזרים תואמים כיוון / לא סותרים.',
    fail: 'סתירה בין כיוון תבנית לבין מחקרים.',
  },
  A6: {
    measures: 'סיווג כניסה REACTIVE מול INITIATIVE לפי spec.',
    pass: 'spec_classification ב-details.',
    fail: 'לא עומד בכללי סיווג הכניסה.',
  },
  A7: {
    measures: 'pre_fire_validator + gateway checks (גודל, stop, session).',
    pass: 'pre_fire OK כשיש fire_setup.',
    fail: 'fail_reason מ-validator — למשל gate, cooldown, SSV.',
  },
};

export function woodiesStageId(label: string): string | null {
  const m = label.match(/^([AB]\d+)/);
  return m ? m[1] : null;
}

export function rowHelpForWoodiesStage(stageId: string, status: FireRowStatus, message: string): string {
  const h = WOODIES_STAGE_HELP[stageId];
  if (!h) return message || STATUS_HELP[status];
  const outcome = status === 'ok' ? h.pass : status === 'block' ? h.fail : 'ממתין להערכה בבר הבא.';
  const now = message ? `מה קורה עכשיו:\n${message}` : '';
  return [h.measures, now, `משמעות:\n${outcome}`].filter(Boolean).join('\n\n');
}
