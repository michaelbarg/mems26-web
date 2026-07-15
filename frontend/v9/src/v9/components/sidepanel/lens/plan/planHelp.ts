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


/** "איך מתגבשת" — מבנה / מפעיל / מבטל, בעברית פשוטה, קבוע פר-תבנית.
 *  מקורות: מפרטי-הרכיבים החיים מ-/api/v9/build/pattern-status (S2) +
 *  outputs/WOODIES_S4_FIRE_CONDITIONS_2026-06-24.md (S4). מפתח = pattern id. */
export const PATTERN_HELP: Record<
  string,
  { nick: string; structure: string; trigger: string; cancel: string }
> = {
  // ── S2 · תבניות 5-דקות (10) ──
  REACTIVE_LONG: {
    nick: 'ריאקטיב · לונג-היפוך',
    structure: 'תשישות-מכירה בתחתית (COT>AMT) — כניסת-היפוך מעלה',
    trigger: 'בר-מוכרים (סגירה<פתיחה, נפח>0) ואז חזרה מעלה',
    cancel: 'יום ללא-מגמה, תא-הרשאה SKIP, או R:R ליעד-1 קטן מ-1',
  },
  REACTIVE_SHORT: {
    nick: 'ריאקטיב · שורט-היפוך',
    structure: 'תשישות-קנייה בפסגה (COT>AMT) — כניסת-היפוך מטה',
    trigger: 'בר-קונים (סגירה>פתיחה, נפח>0) ואז חזרה מטה',
    cancel: 'יום ללא-מגמה, תא-הרשאה SKIP, או R:R ליעד-1 קטן מ-1',
  },
  INITIATIVE_LONG: {
    nick: 'יוזמה · לונג-המשך',
    structure: 'התרחבות בכיוון המגמה (COT<AMT) — הצטרפות למהלך',
    trigger: 'בר-התרחבות בטווח 3.2–6.1 נק׳ כלפי מעלה',
    cancel: 'בר צר מדי או מחוץ לטווח-ההתרחבות',
  },
  INITIATIVE_SHORT: {
    nick: 'יוזמה · שורט-המשך',
    structure: 'התרחבות בכיוון המגמה (COT<AMT) — הצטרפות למהלך מטה',
    trigger: 'בר-התרחבות בטווח 3.2–6.1 נק׳ כלפי מטה',
    cancel: 'בר צר מדי או מחוץ לטווח-ההתרחבות',
  },
  INVERSE_HNS_LONG: {
    nick: 'ראש-וכתפיים הפוך · לונג',
    structure: '3 שפלים — האמצעי (הראש) הנמוך ביותר, כתפיים סימטריות',
    trigger: 'פריצת קו-הצוואר מעלה עם ≥3 שפלי-סווינג',
    cancel: 'פחות מ-3 שפלים או מבנה לא-סימטרי',
  },
  HNS_TOP_SHORT: {
    nick: 'ראש-וכתפיים · שורט',
    structure: '3 שיאים — האמצעי (הראש) הגבוה ביותר, כתפיים סימטריות',
    trigger: 'שבירת קו-הצוואר מטה עם ≥3 שיאי-סווינג',
    cancel: 'אין טריפלט תקין (ראש לא-הכי-גבוה / כתפיים לא-סימטריות)',
  },
  DOUBLE_BOTTOM_EE_LONG: {
    nick: 'תחתית-כפולה (Eve+Eve) · לונג',
    structure: '2 שפלים בהפרש ≤3%, תחתיות מעוגלות (Eve)',
    trigger: 'זוג-שפלים מאושר ואז חזרה מעלה',
    cancel: 'אין זוג-שפלים בטווח, או צורה חדה (לא Eve)',
  },
  DOUBLE_TOP_AA_SHORT: {
    nick: 'פסגה-כפולה (Adam+Adam) · שורט',
    structure: '2 שיאים בהפרש ≤3%, פסגות חדות (Adam, ≤2 ברים)',
    trigger: 'זוג-שיאים חד מאושר ואז חזרה מטה',
    cancel: 'רוחב-פסגה מעל 2 ברים (לא Adam), או ללא זוג',
  },
  BULL_FLAG_LONG: {
    nick: 'דגל-שורי · לונג',
    structure: 'מוט (≥5 ברים, ≥4 נק׳) ואז דגל-דחיסה 3–8 ברים, תיקון ≤50%',
    trigger: 'פריצה מעל שיא-הדגל (+0.25 נק׳)',
    cancel: 'אין מוט, דגל ארוך מדי, או תיקון מעל 50%',
  },
  BEAR_FLAG_SHORT: {
    nick: 'דגל-דובי · שורט',
    structure: 'מוט-ירידה (≥5 ברים דוביים, ≥4 נק׳) ואז דגל 3–8 ברים',
    trigger: 'שבירה מתחת שפל-הדגל',
    cancel: 'אין מוט תקין או תיקון עמוק מדי',
  },
  // ── S4 · Woodies CCI (9) ──
  ZLR: {
    nick: 'דחיית קו-אפס · המשך',
    structure: 'קיצון CCI ≥+100 ב-~12 ברים ואז תיקון אל 100≥CCI>−100 (בלי לחצות −100)',
    trigger: 'CCI חוזר לעלות (גדול מהקודם, בין 0 ל-200)',
    cancel: 'חציית −100 (איבוד המבנה), או CCI שטוח (טווח<50)',
  },
  TLB: {
    nick: 'שבירת קו-מגמה · המשך',
    structure: 'קו-רגרסיה על 10 ערכי CCI (שיפוע<−2)',
    trigger: 'CCI חוצה מעל הקו-החזוי (+10) ומעל הקודם',
    cancel: 'ללא קיצון ±200 ב-12 ברים או שותף-כיוון (כש-SPEC_V2 דולק)',
  },
  TT: {
    nick: 'טורבו-טרנד · המשך',
    structure: 'מגמה BLUE ו-CCI(14) חיובי',
    trigger: 'TCCI(6) נגע ב-CCI-14 (≤+5) וקפץ מעליו (+5), אחרי שהיה ≥+10 מעל',
    cancel: 'מגמה לא-כחולה או פער-TCCI קטן מ-5',
  },
  GB100: {
    nick: 'גוסט-בר ב-±100 · המשך',
    structure: 'מגמה BLUE, חציית +100 טרייה',
    trigger: 'הנוכחי>100 והקודם≤100 ולפני-כן<100',
    cancel: 'מגמה YELLOW, או תיקון עמוק (>6 ברים) לפני החצייה',
  },
  Vegas: {
    nick: 'וגאס · דיברגנס (היפוך)',
    structure: 'דיברגנס מחיר↔CCI על 2 סווינגים (מחיר שפל-נמוך / CCI שפל-גבוה = לונג)',
    trigger: 'אישור הדיברגנס עם סווינגים ≥5 ברים זה מזה',
    cancel: 'סווינגים צמודים מדי או ללא דיברגנס',
  },
  Ghost: {
    nick: 'גוסט · ראש-וכתפיים ב-CCI (היפוך)',
    structure: '3 שיאים/שפלים ב-CCI, האמצעי קיצוני',
    trigger: 'שבירת קו-הצוואר (הנוכחי חוצה את הכתף)',
    cancel: 'אין מבנה 3-נקודות תקין',
  },
  FaMir: {
    nick: 'פאמיר · כשל ב-±200 (היפוך)',
    structure: 'CCI התקרב ל-±200 (170–210) אך נכשל',
    trigger: 'היפוך ≥20 נק׳ מהקיצון (עולה מעל הקודם והמינימום+20)',
    cancel: 'LSMA בצד הלא-נכון (AP9), או שהקיצון נפרץ',
  },
  HTLB: {
    nick: 'שבירת קו-אופקי (היפוך)',
    structure: 'קו-CCI אופקי שנגע ≥2 פעמים',
    trigger: 'פריצה מעל התנגדות / שבירה מתחת תמיכה (≥5 נק׳)',
    cancel: 'פחות מ-2 נגיעות, או תבנית נגד ה-bias המערכתי',
  },
  HFE: {
    nick: 'וו-מקיצון (היפוך)',
    structure: 'קיצון CCI (±200) לפני 2–12 ברים — מוכרע ע״י ה-DLL',
    trigger: 'שדה hfe_detected מה-DLL + כיוון',
    cancel: 'הקיצון מחוץ לחלון 2–12 ברים (AP5), או CCI שטוח',
  },
};

/** תרגום מלא של מפתחות-רכיבים לעברית — מכסה את כל המפתחות מ-/api/v9/build/pattern-status
 *  (S2 + S4). מחליף את המפה החלקית שהייתה מוטבעת ב-AllPatternsPlan. */
export const COMPONENT_KEY_HE: Record<string, string> = {
  five_min_bar_recency: 'בר 5-דק׳ טרי (עד 6 דק׳)',
  '5min_bar_recency': 'בר 5-דק׳ טרי (עד 6 דק׳)',
  cci_14_history: 'היסטוריית CCI(14): ≥14 ברים',
  cci_14_present: 'CCI(14) זמין',
  tcci_present: 'TCCI(6) זמין',
  day_type_known: 'סוג-היום ידוע (שורת-היום סווגה)',
  day_type_assigned: 'סוג-יום סווג',
  day_type_gate: 'סוג-יום סווג (למטריצת וודיז)',
  day_type_matrix: 'מטריצת-הרשאה: סוג-יום × תבנית',
  auth_table_cell: 'תא-הרשאה לסוג-היום (לא SKIP)',
  nt_skip: 'לא יום ללא-מגמה',
  mode_context: 'הקשר-מצב (שעה-ראשונה / תוך-יומי)',
  fhb_eligible: 'שעה-ראשונה: לא בצבירה (בר 4+)',
  choppiness_ok: 'מדד-גליוּת (השער מושבת)',
  min_bars: 'מינימום ברים במאגר (≥7)',
  buffer_size: 'מאגר ≥5 ברים לזיהוי',
  bars_today: 'עובדו ברים היום',
  b1_sellers: 'בר-טריגר מוכרים (סגירה<פתיחה)',
  b1_buyers: 'בר-טריגר קונים (סגירה>פתיחה)',
  b1_expansion: 'בר-התרחבות (טווח 3.2–6.1 נק׳)',
  breakout: 'פריצה מעל שיא-הדגל',
  pole_found: 'זוהה מוט (≥5 ברים, ≥16 טיקים)',
  flag_length: 'אורך-דגל תקין (3–8 ברים)',
  flag_retrace: 'תיקון-דגל ≤50%',
  swing_highs_found: '≥3 שיאי-סווינג',
  swing_lows_found: '≥3 שפלי-סווינג',
  hns_structure: 'מבנה ראש-וכתפיים (כתף-ראש-כתף סימטרי)',
  peak_pair: 'זוג-שיאים (הפרש ≤3%)',
  adam_variant: 'פסגות חדות (וריאנט Adam, ≤2 ברים)',
  r_t1_gate: 'יחס-סיכון ליעד-1 ≥ 1.0',
  stop_price: 'מחיר-סטופ (אדפטיבי)',
  targets: 'יעדים (לפי סוג-יום)',
  sizing_time_stop: 'גודל-פוזיציה + סטופ-זמן',
  strategic_gate: 'שער אסטרטגי (מגמה BLUE/RED)',
  rth_gate: 'שעות-מסחר ראשיות (RTH)',
  pattern_specific: 'התבנית זוהתה כפעילה',
  ready_to_route: 'מוכן לניתוב',
  ib_locked: 'טווח שעה-ראשונה נעול',
  ib_range_pts: 'טווח שעה-ראשונה (נק׳)',
  not_developing: 'סיווג יציב (לא-מתפתח)',
  directional_certainty: 'ודאות-כיוון מעל סף',
  probability_above_threshold: 'הסתברות ≥ 0.55',
  trading_confidence: 'ביטחון-מסחר נקבע',
  opening_type_set: 'סוג-פתיחה נקבע',
  opening_run_detected: 'זוהתה ריצת-פתיחה',
  opening_reasoning: 'נימוק סוג-הפתיחה',
  zohar_rules_evaluated: 'כללי זוהר הוערכו',
};

const REASON_PHRASES: Array<[RegExp, string]> = [
  [/Awaiting:\s*/g, 'ממתין ל: '],
  [/Missing:\s*/g, 'חסר: '],
  [/\bneed\b/gi, 'צריך'],
  [/\brange\b/gi, 'טווח'],
  [/\bclose\b/gi, 'סגירה'],
  [/\bgap\b/gi, 'פער'],
  [/\bretrace\b/gi, 'תיקון'],
  [/\btrend\b/gi, 'מגמה'],
  [/\bno valid\b/gi, 'אין תקין'],
  [/Data ready/gi, 'נתונים מוכנים'],
  [/not yet detected/gi, 'טרם זוהתה'],
  [/swing lows/gi, 'שפלי-סווינג'],
  [/swing highs/gi, 'שיאי-סווינג'],
  [/\bfound\b/gi, 'נמצאו'],
  [/in last (\d+) bars/gi, 'ב-$1 ברים אחרונים'],
  [/\bb\d+_sellers\b/gi, 'בר-מוכרים'],
  [/\bb\d+_buyers\b/gi, 'בר-קונים'],
  [/\bb\d+_expansion\b/gi, 'בר-התרחבות'],
  [/\bbars\b/gi, 'ברים'],
];

/** מתרגם מחרוזת-סיבה גולמית מה-API לעברית קריאה ("מה חסר עכשיו"). */
export function planReasonHe(reason?: string | null): string {
  if (!reason) return '';
  let r = reason;
  const keys = Object.keys(COMPONENT_KEY_HE).sort((a, b) => b.length - a.length);
  for (const k of keys) {
    r = r.split(`data.${k}`).join(COMPONENT_KEY_HE[k]).split(k).join(COMPONENT_KEY_HE[k]);
  }
  for (const [re, he] of REASON_PHRASES) r = r.replace(re, he);
  return r;
}

/** 07-15 (מייקל: "שיהיה ברור בכל רגע נתון למה לא ירה") — כל שער-חסימה של
 * ה-gateway בעברית: שם קצר + מה-זה-אומר. המפתחות = blocked_by מהבקאנד. */
export const GATE_HE: Record<string, { name: string; why: string }> = {
  kill_switch: { name: 'מתג-חירום', why: 'מתג-העצירה הכללי מופעל — שום ירי בשום מצב' },
  session_gate_closed: { name: 'מחוץ לחלון-מסחר', why: 'מחוץ ל-16:30–22:00 IL (08:30–15:00 CT)' },
  eod_entry_cutoff: { name: 'סוף-יום', why: 'אחרי שעת-הכניסה האחרונה — אין כניסות חדשות לקראת סגירה' },
  feed_watchdog: { name: 'פיד-נתונים תקוע', why: 'הנתונים מסיירה לא זורמים — אסור לירות על מידע ישן' },
  cooldown: { name: 'צינון אחרי עסקה', why: 'המתנה מחויבת אחרי עסקה קודמת לפני ירי חדש' },
  suffering_side_veto: { name: 'וטו צד-סובל (SSV)', why: 'הצד הזה הפסיד שוב-ושוב היום — נחסם זמנית' },
  duplicate_fire: { name: 'ירי-כפול', why: 'אותו איתות בדיוק כבר נורה הרגע — מניעת כפילות' },
  chop_searching: { name: 'שוק-קופצני (Layer-0)', why: 'מדד-הצ׳ופ במצב חיפוש — השוק ללא כיוון (כבוי כברירת-מחדל)' },
  opening_type_gate: { name: 'שער סוג-פתיחה', why: 'סוג-הפתיחה שזוהה לא מתיר את התבנית הזו' },
  daytype_playbook: { name: 'פלייבוק סוג-יום', why: 'טבלת-המשחק של סוג-היום מסמנת SKIP לתבנית זו היום' },
  trend_direction_gate: { name: 'שער כיוון-מגמה', why: 'הכיוון נגד המגמה המזוהה של היום' },
  reactive_location: { name: 'מיקום ריאקטיבי', why: 'עסקת-fade לא במיקום קצה תקין' },
  location_gate: { name: 'שער-מיקום (דלתון)', why: 'הכיוון לא מתאים למיקום מול VAH/VAL — לונג רק ברצפת-הערך, שורט רק בתקרה' },
  daytype_position_gate: { name: 'שער משפחה×סוג-יום', why: 'משפחת-התבנית (CONT/REV) לא מתאימה לסוג-היום' },
  cont_trend_filter: { name: 'המשך-עם-מגמה', why: 'עסקת-המשך נגד צבע/כיוון ה-LSMA' },
  direction_context: { name: 'הקשר-כיוון יומי', why: 'הכיוון נגד ההקשר הדומיננטי של היום (פטור ל-fade בימי-רוטציה)' },
  lsma_flat: { name: 'LSMA שטוח', why: 'אין שיפוע — אין ראיית-כיוון לעסקת-המשך' },
  news_blackout: { name: 'חלון-חדשות', why: 'אירוע-מאקרו קרוב — אין כניסות בחלון' },
  day_direction_doctrine: { name: 'דוקטרינת כיוון-יום', why: 'הדוקטרינה של סוג-היום אוסרת את הכיוון הזה' },
  entry_not_confirmed: { name: 'אין אישור-כניסה', why: 'בר-האישור (S4) עדיין לא התקבל' },
  t1_wrong_side: { name: 'T1 בצד הלא-נכון', why: 'היעד הראשון מתחת/מעל לכניסה בכיוון ההפוך — סטאפ פסול' },
  rr_entry_gate: { name: 'שער סיכון:סיכוי', why: 'R:R ל-T1 (לפני-ריאליזם) מתחת לסף' },
  daily_loss_halt: { name: 'עצירת הפסד-יומי', why: 'תקרת ההפסד היומי (−$400) נפרצה — אין ירי עד מחר' },
  consecutive_loss_halt: { name: 'עצירת הפסדים-רצופים', why: 'רצף הפסדים — עצירה מחויבת' },
  s4_risk_cap: { name: 'תקרת-סיכון S4', why: 'הסיכון בנקודות/דולרים מעל התקרה לעסקת S4' },
  cluster_guard: { name: 'שומר-צבירה', why: 'יותר מדי עסקאות באותו אזור-מחיר/זמן' },
};

export function gateHe(key?: string | null): { name: string; why: string } {
  if (!key) return { name: '', why: '' };
  return GATE_HE[key] || { name: key, why: 'שער ללא-תרגום — ראה לוג' };
}
