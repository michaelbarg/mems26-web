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


/** "איך מתגבשת" — הסבר / מבנה-גאומטרי / כמה-נרות / מפעיל / מבטל, פר-תבנית.
 *  מקור-אמת (מייקל 07-17): חוּלץ מקוד-הדטקטורים החי — לא מדוקטרינה. ליד כל תבנית
 *  מצוטט קובץ:שורות של הדטקטור לביקורת עתידית. מפתח = pattern id
 *  מ-/api/v9/build/pattern-status. מצבי-דגלים (docs/FLAG_INDEX.md, 07-17):
 *  ZLR_SPEC_V2=ON · TLB_SPEC_V2=ON · VEGAS_SPEC_V2=ON (ספל-וידית, לא דיברגנס) ·
 *  HFE_DISABLED=ON · S2_VSA_VOLUME=ON (variant UNION) · S2_CVD_DETECTION_V1=ON ·
 *  S2_REQUIRE_COT_AMT=OFF (S2 ⟂ S3). */
export interface PatternHelp {
  nick: string;       // כינוי קצר
  explain: string;    // ההסבר — מה התבנית סוחרת ולמה
  structure: string;  // המבנה הגאומטרי המזוהה — התנאים כפי שהדטקטור בודק אותם
  candles: string;    // כמה נרות — חלון-הסריקה והמינימום מהקוד
  trigger: string;    // מה מפעיל את הירי
  cancel: string;     // מה מבטל/חוסם
}

export const PATTERN_HELP: Record<string, PatternHelp> = {
  // ── S2 · תבניות 5-דקות (10) ──
  // REACTIVE — backend/v9/systems/five_min/five_min_system.py:617-815
  // (קבועים :30-37 · סף-אישור :88-95 · VSA :654-681 · CVD :726-743 · S2⟂S3 :640-648)
  // variant נפח: UNION (config/s2_firing.yaml)
  REACTIVE_LONG: {
    nick: 'ריאקטיב · לונג-היפוך',
    explain: 'עסקת-היפוך על תשישות-מוכרים: אחרי בר-מכירה חזק הנפח קורס, הקונים משתלטים, ונר-אישור סוגר מעל שיא נר-הקונים — כניסה לונג נגד הלחץ שהתרוקן.',
    structure: 'B1 בר-מוכרים (סגירה<פתיחה, נפח>0) → B2 קריסת-נפח (UNION: נמוך מ-2 הקודמים ו-≤0.7× ממוצע-20, או ≤0.5× הממוצע, או גם טווח-צר) → B3 בר-קונים → B4 אישור: סגירה מעל שיא-B3 (ביום-תנודתי: מעל 75% מטווח-B3) + אישור-CVD (דלתא-קנייה בנר-הכניסה או דיברגנס מחיר-CVD). ‏COT/AMT לא נדרש (S2 ⟂ S3).',
    candles: '7 נרות מינימום: 4 נרות-תבנית (B1–B4) + 3 נרות-רקע; ממוצע-הנפח על 20 נרות; משטר-תנודתי נמדד על 14',
    trigger: 'B4 סוגר מעל שיא-B3 — הירי על סגירת נר-האישור',
    cancel: 'אין קריסת-נפח ב-B2, אין אישור-CVD, יום ללא-מגמה / תא-הרשאה SKIP, או R:R ליעד-1 קטן מ-1',
  },
  REACTIVE_SHORT: {
    nick: 'ריאקטיב · שורט-היפוך',
    explain: 'עסקת-היפוך על תשישות-קונים: אחרי בר-קנייה חזק הנפח קורס, המוכרים משתלטים, ונר-אישור סוגר מתחת לשפל נר-המוכרים — כניסה שורט נגד הלחץ שהתרוקן.',
    structure: 'B1 בר-קונים (סגירה>פתיחה, נפח>0) → B2 קריסת-נפח (UNION כמו בלונג) → B3 בר-מוכרים → B4 אישור: סגירה מתחת לשפל-B3 (ביום-תנודתי: מתחת 75% מהטווח) + אישור-CVD (דלתא-מכירה / נטו-מכירה / דיברגנס). ‏COT/AMT לא נדרש (S2 ⟂ S3).',
    candles: '7 נרות מינימום: 4 נרות-תבנית (B1–B4) + 3 נרות-רקע; ממוצע-הנפח על 20 נרות',
    trigger: 'B4 סוגר מתחת לשפל-B3 — הירי על סגירת נר-האישור',
    cancel: 'אין קריסת-נפח ב-B2, אין אישור-CVD, יום ללא-מגמה / תא-הרשאה SKIP, או R:R ליעד-1 קטן מ-1',
  },
  // INITIATIVE — backend/v9/systems/five_min/five_min_system.py:817-934
  // (טווח-התרחבות דינמי :44-46 + :115-129 · POC-סובלנות :132-144 · CVD :888-895)
  INITIATIVE_LONG: {
    nick: 'יוזמה · לונג-המשך',
    explain: 'עסקת-המשך עם הזרם: בר-התרחבות פותח מהלך, מבחן שומר שפל-עולה (או חוזר ל-POC), נר-הצטרפות מרחיב את המהלך, ונר-הכניסה פורץ מעל שיא בר-הפתיחה — הצטרפות ליוזמת-הקונים.',
    structure: 'B1 בר-שורי מתרחב: טווח בין 1.3× ל-2.5× מהטווח-הממוצע של 14 הנרות האחרונים (ביום-תנודתי הרצפה נחתכת ב-8 נק׳) → B2 מבחן: שפל גבוה משפל-B1 או חזרה ל-POC (±0.2× טווח-ממוצע) → B3 הצטרפות: טווח גדול מטווח-B1 → B4 מבחן-שני (שפל ≥ שפל-B2) וסגירה מעל שיא-B1 + CVD נטו לא-שלילי בחלון.',
    candles: '7 נרות מינימום: 4 נרות-תבנית + 3 נרות-רקע; ההתרחבות נמדדת מול ממוצע 14 נרות',
    trigger: 'B4 סוגר מעל שיא-B1 (פריצת בר-הפתיחה)',
    cancel: 'B1 צר/רחב מדי (מחוץ ל-1.3×–2.5×), אין מבחן-B2, או CVD נטו-מוכר נגד הפריצה',
  },
  INITIATIVE_SHORT: {
    nick: 'יוזמה · שורט-המשך',
    explain: 'עסקת-המשך עם הזרם מטה: בר-התרחבות דובי, מבחן שומר שיא-יורד (או חוזר ל-POC), נר-הצטרפות מרחיב, ונר-הכניסה שובר מתחת לשפל בר-הפתיחה — הצטרפות ליוזמת-המוכרים.',
    structure: 'B1 בר-דובי מתרחב (1.3×–2.5× מהממוצע של 14 נרות) → B2 מבחן: שיא נמוך משיא-B1 או חזרה ל-POC → B3 הצטרפות: טווח גדול מטווח-B1 → B4 מבחן-שני (שיא ≤ שיא-B2) וסגירה מתחת לשפל-B1 + CVD נטו לא-חיובי.',
    candles: '7 נרות מינימום: 4 נרות-תבנית + 3 נרות-רקע; ההתרחבות נמדדת מול ממוצע 14 נרות',
    trigger: 'B4 סוגר מתחת לשפל-B1 (שבירת בר-הפתיחה)',
    cancel: 'B1 מחוץ לטווח-ההתרחבות, אין מבחן-B2, או CVD נטו-קונה נגד השבירה',
  },
  // H&S — backend/v9/systems/five_min/patterns/head_shoulders.py:26-31 (קבועים),
  // :141-208 (הפוך) · :211-277 (רגיל); פיבוט 2-מכל-צד :63-90; סימטריה ≤5% :93-103
  INVERSE_HNS_LONG: {
    nick: 'ראש-וכתפיים הפוך · לונג',
    explain: 'היפוך-עלייה קלאסי: שלושה שפלים שהאמצעי (הראש) עמוק מהכתפיים — המוכרים כשלו פעמיים לשבור נמוך יותר; פריצת קו-הצוואר מאשרת מעבר-שליטה לקונים.',
    structure: '3 שפלי-פיבוט (פיבוט = נמוך מ-2 נרות מכל צד): כתף-ראש-כתף, הראש נמוך משתי הכתפיים ב-≥2 טיקים, סימטריית-כתפיים ≤5% ממרחק ראש-כתפיים; קו-צוואר = שיא-הביניים בין הכתפיים; ירי: סגירה מעל קו-הצוואר +1 טיק.',
    candles: 'מינימום 12 נרות; נסרק על 30 הנרות האחרונים; כל פיבוט דורש 2 נרות מכל צד',
    trigger: 'נר-הסגירה האחרון מעל קו-הצוואר +1 טיק',
    cancel: 'ראש לא-הכי-נמוך, כתפיים לא-סימטריות (>5%), או ראש שלא בולט ≥2 טיקים',
  },
  HNS_TOP_SHORT: {
    nick: 'ראש-וכתפיים · שורט',
    explain: 'היפוך-ירידה קלאסי: שלושה שיאים שהאמצעי (הראש) גבוה מהכתפיים — הקונים כשלו פעמיים לפרוץ גבוה יותר; שבירת קו-הצוואר מאשרת מעבר-שליטה למוכרים.',
    structure: '3 שיאי-פיבוט (פיבוט = גבוה מ-2 נרות מכל צד): כתף-ראש-כתף, הראש גבוה משתי הכתפיים ב-≥2 טיקים, סימטריה ≤5%; קו-צוואר = שפל-הביניים; ירי: סגירה מתחת קו-הצוואר −1 טיק.',
    candles: 'מינימום 12 נרות; נסרק על 30 הנרות האחרונים; כל פיבוט דורש 2 נרות מכל צד',
    trigger: 'נר-הסגירה האחרון מתחת קו-הצוואר −1 טיק',
    cancel: 'ראש לא-הכי-גבוה, כתפיים לא-סימטריות (>5%), או ראש שלא בולט ≥2 טיקים',
  },
  // Double Bottom/Top — backend/v9/systems/five_min/patterns/double_bt.py:30-37 (קבועים),
  // :167-230 (תחתית) · :233-295 (פסגה); רוחב-Eve/Adam ‏:96-129; סימטריה ≤3% :132-137
  DOUBLE_BOTTOM_EE_LONG: {
    nick: 'תחתית-כפולה (Eve+Eve) · לונג',
    explain: 'היפוך-עלייה: שתי תחתיות מעוגלות כמעט באותו מחיר — המוכרים נעצרו פעמיים באותה רצפה בלי כוח לשבור; פריצת קו-הצוואר מעלה מאשרת את ההיפוך.',
    structure: '2 שפלי-פיבוט בהפרש ≤3%, שניהם מעוגלים (Eve): ≥3 נרות ברוחב ±2 טיקים סביב כל שפל; קו-צוואר = השיא שבין השפלים, גובה-התבנית ≥0.1% מהמחיר; ירי: סגירה מעל קו-הצוואר +1 טיק.',
    candles: 'מינימום 10 נרות; נסרק על 30 האחרונים; כל תחתית רחבה ≥3 נרות',
    trigger: 'נר-הסגירה האחרון מעל קו-הצוואר +1 טיק',
    cancel: 'הפרש-שפלים >3%, תחתית חדה (<3 נרות רוחב — לא Eve), או תבנית שטוחה מדי',
  },
  DOUBLE_TOP_AA_SHORT: {
    nick: 'פסגה-כפולה (Adam+Adam) · שורט',
    explain: 'היפוך-ירידה: שתי פסגות חדות כמעט באותו מחיר — הקונים ננעצו פעמיים באותה תקרה ונדחו מהר; שבירת קו-הצוואר מטה מאשרת את ההיפוך.',
    structure: '2 שיאי-פיבוט בהפרש ≤3%, שניהם חדים (Adam): ≤2 נרות ברוחב ±2 טיקים סביב כל שיא; קו-צוואר = השפל שבין השיאים, גובה-התבנית ≥0.1% מהמחיר; ירי: סגירה מתחת קו-הצוואר −1 טיק.',
    candles: 'מינימום 10 נרות; נסרק על 30 האחרונים; כל פסגה חדה ≤2 נרות',
    trigger: 'נר-הסגירה האחרון מתחת קו-הצוואר −1 טיק',
    cancel: 'הפרש-שיאים >3%, פסגה רחבה (>2 נרות — לא Adam), או תבנית שטוחה מדי',
  },
  // Flags — backend/v9/systems/five_min/patterns/flags.py:32-41 (קבועים),
  // מוט :75-138 · דגל+פריצה :141-259
  BULL_FLAG_LONG: {
    nick: 'דגל-שורי · לונג',
    explain: 'המשך-מגמה: מוט-עלייה חד ואז דגל-דחיסה רדוד — הקונים נחים בלי לוותר על השטח שנכבש; פריצה מעל תקרת-הדגל מחדשת את המהלך במלוא הכוח.',
    structure: 'מוט: 5–15 נרות בגובה ≥16 טיקים (4 נק׳) שבו ≥60% מהנרות סוגרים מעלה → דגל: 3–8 נרות דחיסה, תיקון ≤50% מגובה-המוט, אף נר-דגל לא סוגר מעל ראש-המוט → פריצה: סגירה מעל שיא-הדגל +1 טיק.',
    candles: 'מוט 5–15 נרות + דגל 3–8 נרות + נר-פריצה; נסרק על 30 האחרונים (מינימום 10)',
    trigger: 'נר-הסגירה האחרון מעל שיא-הדגל +1 טיק',
    cancel: 'אין מוט תקין (קצר/נמוך/לא-חד-כיווני), דגל ארוך מ-8 נרות, או תיקון מעל 50%',
  },
  BEAR_FLAG_SHORT: {
    nick: 'דגל-דובי · שורט',
    explain: 'המשך-מגמה מטה: מוט-ירידה חד ואז דגל-דחיסה רדוד — המוכרים נחים בלי לוותר; שבירה מתחת לרצפת-הדגל מחדשת את הירידה.',
    structure: 'מוט-ירידה: 5–15 נרות בגובה ≥16 טיקים (4 נק׳) שבו ≥60% מהנרות סוגרים מטה → דגל: 3–8 נרות, תיקון ≤50% מהמוט, אף נר-דגל לא סוגר מתחת לתחתית-המוט → שבירה: סגירה מתחת לשפל-הדגל −1 טיק.',
    candles: 'מוט 5–15 נרות + דגל 3–8 נרות + נר-שבירה; נסרק על 30 האחרונים (מינימום 10)',
    trigger: 'נר-הסגירה האחרון מתחת לשפל-הדגל −1 טיק',
    cancel: 'אין מוט תקין, דגל ארוך מ-8 נרות, או תיקון מעל 50%',
  },
  // ── S4 · Woodies CCI (9) ──
  // ZLR — backend/v9/systems/woodies/patterns/zlr.py:32 (LOOKBACK=12) · :180 (מינ׳ 13) ·
  // :200-209 (שלבים) · :64-129 (SPEC_V2) · anti_patterns.py:44-82 (AP1) · :197-229 (AP8)
  ZLR: {
    nick: 'דחיית קו-אפס · המשך',
    explain: 'תבנית-ההמשך המרכזית של ווּדיז: במגמה מבוססת ה-CCI נסוג לאזור קו-האפס, נדחה ממנו וחוזר לכיוון-המגמה — כניסה על חידוש-המומנטום, לא על היפוך.',
    structure: 'קיצון CCI ≥ +100 בתוך 12 הנרות האחרונים → תיקון לאזור (−100,‏+100] בלי לחצות −100 → פנייה מעלה (CCI גדול מהקודם, בין 0 ל-200). עם SPEC_V2 (דולק): ≥6 נרות מגמה כחולה מהקיצון, SWI צהוב/ירוק, 3 סגירות אחרונות מעל EMA-34, קפיצת-CCI ≥15, כניסה ≤120, CZI ציאן 3 נרות (מראה הפוכה לשורט).',
    candles: 'מינימום 13 נרות; הקיצון בתוך 12 האחרונים; ≥6 נרות-מגמה; אישורי-הכניסה על 3 הנרות האחרונים',
    trigger: 'CCI חוזר לעלות/לרדת בכיוון-המגמה בקפיצה ≥15, בין 0 ל-±200',
    cancel: 'חציית הקו-הנגדי (±100 ההפוך — איבוד-המבנה), תיקון >12 נרות מהקיצון (AP1), או CCI שטוח <50 על 3 נרות (AP8)',
  },
  // TLB — backend/v9/systems/woodies/patterns/tlb.py:16 (LOOKBACK=10) · :127-137 (רגרסיה+שבירה) ·
  // :28-37 + :84-112 (SPEC_V2: קיצון ±200 ב-12 + שותף-המשך)
  TLB: {
    nick: 'שבירת קו-מגמה · המשך',
    explain: 'שבירת קו-מגמה על ה-CCI עצמו: קו-רגרסיה יורד על ערכי-ה-CCI נשבר מעלה — התיקון נגמר והמגמה חוזרת. לפי המקור כמעט אף-פעם לא עומדת לבד — נדרש שותף-המשך מאשר.',
    structure: 'רגרסיה-לינארית על 10 ערכי-ה-CCI האחרונים: שיפוע < −2 וה-CCI הנוכחי מעל הקו-החזוי +10 וגם מעל הקודם (מראה הפוכה לשורט). עם SPEC_V2 (דולק): נדרש גם קיצון ±200 בתוך 12 הנרות האחרונים + תבנית-המשך שותפה (GB100/ZLR/TT) באותו כיוון.',
    candles: '10 נרות לקו-הרגרסיה (מינימום 10); הקיצון ±200 בתוך 12 האחרונים',
    trigger: 'CCI חוצה מעל/מתחת הקו-החזוי ב-≥10 נק׳ ובכיוון-השבירה',
    cancel: 'אין קיצון ±200 ב-12 נרות או אין שותף-המשך (SPEC_V2), או CCI שטוח (AP8)',
  },
  // TT — backend/v9/systems/woodies/patterns/tt.py:52-85 (3 נרות: היה-מעל→מגע→ניתור) ·
  // anti_patterns.py:175-194 (AP7 פער ≥5)
  TT: {
    nick: 'טורבו-טרנד · המשך',
    explain: 'ריענון-מומנטום מהיר בתוך מגמה: ה-TCCI המהיר (CCI-6) יורד לגעת ב-CCI-14 האיטי וניתר ממנו חזרה לכיוון-המגמה — הכניסה על הניתור.',
    structure: 'מגמה BLUE ו-CCI-14 חיובי; לפני 2 נרות TCCI היה ≥10 מעל CCI-14 → בנר הקודם ירד לגעת בו (≤+5) → בנר הנוכחי ניתר חזרה (≥+5 מעל CCI-14 ועולה); פער-TCCI בכניסה ≥5 (AP7). מראה הפוכה לשורט במגמה RED עם CCI-14 שלילי.',
    candles: 'נבחנים 3 הנרות האחרונים בלבד (היה-מעל → מגע → ניתור); מינימום 3 נרות',
    trigger: 'ניתור ה-TCCI חזרה מעל/מתחת ל-CCI-14 בכיוון-המגמה',
    cancel: 'מגמה לא כחולה/אדומה, פער-TCCI <5 (AP7), או CCI שטוח (AP8)',
  },
  // GB100 — backend/v9/systems/woodies/patterns/gb100.py:52-91 (חצייה טרייה על 3 נרות) ·
  // :69-82 + anti_patterns.py:155-172 (AP6 עומק-תיקון ≤6) · :85-109 (AP2 צהוב)
  GB100: {
    nick: 'גוסט-בר ב-±100 · המשך',
    explain: 'חצייה טרייה של קו-ה-100 בכיוון מגמה קיימת — הרגע שבו תיקון רדוד נגמר והמומנטום חוזר לצד-המגמה בכוח מלא.',
    structure: 'מגמה BLUE וחצייה טרייה של +100 על פני 3 נרות: הנוכחי >100, הקודם ≤100, שלפניו <100; התיקון שקדם לחצייה החזיק ≤6 נרות בצד-הנגדי של קו-האפס (AP6); נחסם במגמה YELLOW (AP2). מראה הפוכה לשורט (RED / −100).',
    candles: 'החצייה נבחנת על 3 נרות; עומק-התיקון נסרק אחורה — עד 6 נרות מותרים מעבר לקו-האפס',
    trigger: 'הנוכחי>100 והקודם≤100 ולפני-כן<100 (חצייה טרייה, לא שהייה)',
    cancel: 'מגמה YELLOW (AP2), תיקון >6 נרות מעבר לקו-האפס (AP6), או CCI שטוח (AP8)',
  },
  // VEGAS — backend/v9/systems/woodies/patterns/vegas.py:20 (חלון 20) · :75-190 (ספל-וידית,
  // SPEC_V2=ON חי); מצב-הדיברגנס הישן (:259-407) כבוי
  Vegas: {
    nick: 'וגאס · ספל-וידית ב-CCI (היפוך)',
    explain: 'היפוך אסטרטגי: ספל-וידית על ה-CCI — צלילה לקיצון עמוק, התאוששות עד השפה, ידית רדודה שמחזיקה, ופריצת-השפה. מסמן סוף-מגמה וסיכוי גבוה למגמה חדשה בכיוון ההפוך. נדיר בכוונה.',
    structure: 'לונג: CCI צולל מתחת −200 (תחתית-הספל) → מתאושש וחוצה −100; שיא-ההתאוששות = השפה → ידית: ≥2 נרות של שפל-גבוה מעל הספל שמחזירים <50% מהתאוששות ספל→שפה → כניסה בחצייה טרייה מעל השפה. מראה הפוכה לשורט (+200/+100).',
    candles: 'חלון-סריקה 20 נרות (מינימום 20); הידית ≥2 נרות',
    trigger: 'חצייה טרייה מעל/מתחת שפת-הספל (הנוכחי חוצה, הקודם עוד לא)',
    cancel: 'ידית עמוקה (>50% החזר — סכין נופלת), ידית שחוזרת לעומק-הספל, או CCI שטוח (AP8)',
  },
  // GHOST — backend/v9/systems/woodies/patterns/ghost.py:16 (חלון 20) · :53-63 (קיצון מקומי) ·
  // :80-86 + :140-146 (3 דחיפות, אמצעית קיצונית, שבירת כתף-3)
  Ghost: {
    nick: 'גוסט · ראש-וכתפיים ב-CCI (היפוך)',
    explain: 'ראש-וכתפיים על ה-CCI (לא על המחיר): שלוש דחיפות-מומנטום שהאמצעית הקיצונית והשלישית כבר חלשה — המומנטום דועך מדחיפה לדחיפה; שבירת הכתף-השלישית = היפוך.',
    structure: 'בחלון של 20 נרות: 3 פסגות-CCI מקומיות (פסגה = גבוהה מ-2 הנרות שלפניה ומהנר שאחריה), האמצעית (הראש) הגבוהה מכולן והימנית נמוכה מהשמאלית; ירי-שורט כשה-CCI הנוכחי יורד מתחת לכתף-הימנית. מראה הפוכה על שפלים ללונג.',
    candles: 'חלון-סריקה 20 נרות (מינימום 20); כל קיצון-מקומי נבנה מ-3–4 נרות',
    trigger: 'ה-CCI הנוכחי חוצה את ערך הכתף-השלישית בכיוון-ההיפוך',
    cancel: 'אין 3 קיצונים תקינים (ראש לא-קיצוני / כתף-ימין לא-חלשה), או CCI שטוח (AP8)',
  },
  // FAMIR — backend/v9/systems/woodies/patterns/famir.py:15-16 (170–210) · :53-73 + :134-136
  // (5 נרות, היפוך ≥20) · anti_patterns.py:231-269 (AP9 LSMA)
  FaMir: {
    nick: 'פאמיר · כשל ב-±200 (היפוך)',
    explain: 'כשל-בקיצון: ה-CCI מטפס לעבר +200 אך לא מגיע ומתהפך — הדחיפה האחרונה של המגמה נכשלה מול ההתנגדות הגדולה; כניסה נגד-המגמה על הכשל, בגיבוי צד-ה-LSMA.',
    structure: 'ב-5 הנרות האחרונים: שיא-CCI בטווח 170–210 (התקרב ל-+200 אך כשל) → הנוכחי יורד מהקודם וכבר ≥20 נק׳ מתחת לשיא; תנאי-LSMA: לשורט המחיר מתחת ל-LSMA, ללונג מעליו (AP9). מראה הפוכה ללונג (−170 עד −210).',
    candles: 'נסרקים 5 הנרות האחרונים בלבד (מינימום 5)',
    trigger: 'היפוך ≥20 נק׳-CCI מהקיצון-שנכשל, בהמשך לירידה/עלייה מהנר הקודם',
    cancel: 'LSMA בצד הלא-נכון (AP9), קיצון שעבר את 210 (הצליח — לא כשל), או CCI שטוח (AP8)',
  },
  // HTLB — backend/v9/systems/woodies/patterns/htlb.py:16-18 (חלון 15, ≥2 נגיעות ±15) ·
  // :60-82 (הקו) · :124-125/:188-189 (שבירה ±5) · :85-104 (bias אזורי, דגל ON)
  HTLB: {
    nick: 'שבירת קו-אופקי ב-CCI (היפוך)',
    explain: 'שבירת רמה אופקית על ה-CCI: רמה שה-CCI כיבד בנגיעות חוזרות נשברת — שחרור-לחץ לכיוון-השבירה. בתצורה האזורית (דולקת) קובעת גם bias-כיוון לכל תבניות-ווּדיז.',
    structure: 'בחלון של 15 נרות: קו-אופקי מקיצונים מקומיים עם ≥2 נגיעות בסטייה ≤15 נק׳-CCI; שבירה: הנר הקודם ≤ הקו והנוכחי > הקו +5 → לונג (מראה הפוכה לשורט). bias אזורי: התנגדות ב-[−200,−100] שנשברה מעלה = UP; תמיכה ב-[+100,+200] שנשברה מטה = DOWN.',
    candles: 'חלון-סריקה 15 נרות (מינימום 15); הקו דורש ≥2 נגיעות',
    trigger: 'פריצה/שבירה של הקו ב-≥5 נק׳-CCI אחרי נר שעוד כיבד אותו',
    cancel: 'פחות מ-2 נגיעות בקו (AP4), או CCI שטוח (AP8)',
  },
  // HFE — backend/v9/systems/woodies/patterns/hfe.py:32-34 (חלון 12, וו ≥50) · :239-243 (AP5
  // ‏2–12) · :214-225 (DLL-בלבד); מושבת: HFE_DISABLED=1 (woodies_system.py:454, מייקל 06-24)
  HFE: {
    nick: 'וו-מקיצון (מושבת)',
    explain: 'וו-חזרה מקיצון ±200 לכיוון קו-האפס. מושבתת קבוע (HFE_DISABLED=1, מייקל 06-24: "לא התבנית שלי"; המפסידה הגדולה בנתונים). הזיהוי הקובע הוא ב-DLL של סיירה; הפייתון רץ לביקורת בלבד.',
    structure: 'קיצון CCI ±200 שאירע לפני 2–12 נרות (AP5) ומאז וו-חזרה ≥50 נק׳-CCI לכיוון קו-האפס, כשהנר הנוכחי ממשיך את הוו; ההכרעה משדה hfe_detected של ה-DLL בלבד.',
    candles: 'הקיצון בתוך 12 הנרות האחרונים, 2–12 נרות אחורה (מינימום 4)',
    trigger: 'שדה hfe_detected מה-DLL + כיוון — כשהדגל יופעל מחדש',
    cancel: 'מושבת גלובלית (HFE_DISABLED=1); קיצון מחוץ לחלון 2–12 (AP5); CCI שטוח (AP8)',
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
  // 07-17: השלמת כל מפתחות-ה-detection של S2 (s2_pattern_probe.py) — היו חסרים
  // ולכן "מה חסר עכשיו" הציג מפתח-אנגלי גולמי.
  b1_bull: 'B1 בר-שורי (סגירה>פתיחה)',
  b1_bear: 'B1 בר-דובי (סגירה<פתיחה)',
  b2_volume_drop: 'B2 קריסת-נפח',
  b2_test: 'B2 מבחן — שפל/שיא נשמר או חזרה ל-POC',
  b3_buyers: 'B3 בר-קונים',
  b3_sellers: 'B3 בר-מוכרים',
  b3_joining: 'B3 הצטרפות (טווח גדול מ-B1)',
  b4_confirm: 'B4 נר-אישור (סגירה מעבר לקצה B3)',
  b4_test: 'B4 מבחן-שני + סגירה מעבר ל-B1',
  lookback_quiet: 'רקע שקט (נפח-העבר נמוך מ-B1)',
  belly_cot_amt: 'COT/AMT + בטן (פוטפרינט — לא נבדק כאן)',
  cot_amt: 'COT/AMT (פוטפרינט — לא נבדק כאן)',
  neckline_breakout: 'פריצת קו-הצוואר (±1 טיק)',
  trough_pair: 'זוג-תחתיות (הפרש ≤3%)',
  eve_variant: 'תחתיות מעוגלות (Eve — רוחב ≥3 נרות)',
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
  // 07-17 (זמן-אמת בתבניות): משפטי-הסטטוס המלאים של ה-inspectors —
  // s2_inspector.py:460-497 · woodies_inspector.py:522-571 — כדי ש"מה חסר"/"למה
  // חסום" ייקראו עברית שלמה ולא חצי-אנגלית.
  [/Nontrend day type — global NO_TRADE gate \(D-091\)/g, 'יום ללא-מגמה — שער NO_TRADE גלובלי (אין עסקאות S2 היום)'],
  [/Auth Table SKIP for\s*/g, 'טבלת-ההרשאה: SKIP עבור '],
  [/Stage A1 veto: trend_state=/g, 'וטו-מגמה (A1): מצב='],
  [/\(GREY\/YELLOW\/INDETERMINATE — Woodies WSI rule\)/g, '(אפור/צהוב — עומדים בצד לפי חוק-המגמה של ווּדיז)'],
  [/CCI-14 not computed — insufficient bar history/g, 'CCI-14 טרם חושב — חסרה היסטוריית-ברים'],
  [/All conditions met — awaiting trigger signal/g, 'כל התנאים מתקיימים — ממתין לנר-הטריגר'],
  [/Awaiting trigger/g, 'ממתין לטריגר'],
  [/pattern detected · awaiting decision tree approval/g, 'התבנית זוהתה — ממתין לאישור עץ-ההחלטה'],
  [/fired earlier today at/g, 'ירה מוקדם-יותר היום ב-'],
  [/Setup fired today at/g, 'הסטאפ ירה היום ב-'],
  [/firing now/gi, 'יורה עכשיו'],
  [/not initialized/g, 'לא אותחל'],
  [/Insufficient data/g, 'אין מספיק נתונים'],
  [/Missing data/g, 'חסרים נתונים'],
  [/day_type unknown — cannot evaluate/g, 'סוג-היום עוד לא סווג — אי-אפשר להעריך'],
  // 07-20: precise gateway block reasons (daytype_playbook / location) — not generic SKIP
  [/responsive SHORT not at VAH/g, 'שורט-fade לא בתקרה (VAH) — מיקום שגוי'],
  [/responsive LONG not at VAL/g, 'לונג-fade לא ברצפה (VAL) — מיקום שגוי'],
  [/\(below_value\)/g, '(מתחת לערך)'],
  [/\(above_value\)/g, '(מעל הערך)'],
  [/\(near_val\)/g, '(ליד VAL)'],
  [/\(near_vah\)/g, '(ליד VAH)'],
  [/\(mid_value\)/g, '(אמצע הערך)'],
  [/counter-day-direction on /g, 'נגד כיוון-היום ב-'],
  [/counter-trend on /g, 'נגד מגמה-רגעית ב-'],
  [/ on Variation/g, ' ביום-Variation'],
  [/ on Trend_Normal/g, ' ביום-Trend_Normal'],
  [/ on Trend_DD/g, ' ביום-Trend_DD'],
  // 07-20 FRONTEND_INDEX: precise reasons for EVERY gateway blocked_by
  [/outside firing window 08:30–15:00 CT/g, 'מחוץ לחלון-ירי 08:30–15:00 CT'],
  [/past EOD entry cutoff/g, 'אחרי חיתוך כניסת-סוף-יום'],
  [/min before 15:00 CT close/g, 'דק׳ לפני סגירת 15:00 CT'],
  [/2-stop cooldown active/g, 'צינון אחרי 2-סטופים פעיל'],
  [/is suffering side \(SSV D-049\)/g, 'הוא צד-סובל (SSV D-049)'],
  [/Layer-0 chop_state=SEARCHING \(high chop\)/g, 'Layer-0 במצב חיפוש (שוק-קופצני)'],
  [/canonical feed stale/g, 'פיד-קנוני תקוע'],
  [/kill switch engaged/g, 'מתג-חירום מופעל'],
  [/duplicate S(\d+) /g, 'ירי-כפול S$1 '],
  [/ within 30s/g, ' בתוך 30 שנ׳'],
  [/setup (UP|DOWN) vs day-context (UP|DOWN)/g, 'סטאפ $1 מול הקשר-יום $2'],
  [/vs sustained /g, 'מול מגמה-מתמשכת '],
  [/\(CONT\) setup /g, '(המשך) סטאפ '],
  [/\|LSMA slope /g, '|שיפוע-LSMA '],
  [/pts\/bar \(flat LSMA, scope=/g, 'נק׳/בר (LSMA שטוח, היקף='],
  [/news blackout: /g, 'חלון-חדשות: '],
  [/ against (UP|DOWN) expansion on /g, ' נגד התרחבות-$1 ב-'],
  [/\(no halt-proof\)/g, '(אין הוכחת-עצירת-מגמה)'],
  [/ on wrong side of entry=/g, ' בצד הלא-נכון של כניסה='],
  [/T1_dist=/g, 'מרחק-T1='],
  [/stop_dist=/g, 'מרחק-סטופ='],
  [/ × min=/g, ' × מינ׳='],
  [/\(R:R=/g, '(יחס='],
  [/confluence avg_dist=/g, 'ממוצע-מרחק confluence='],
  [/adverse drift /g, 'סטייה-נגדית '],
  [/ > max /g, ' > מקס '],
  [/signal age /g, 'גיל-איתות '],
  [/daily pnl \$/g, 'P&L יומי $'],
  [/ \(STOP DAY\)/g, ' (עצירת-יום)'],
  [/ consecutive losses >= /g, ' הפסדים-רצופים ≥ '],
  [/cluster guard D-037 \(too many fires in cluster window\)/g, 'שומר-צבירה D-037 (יותר מדי יריות בחלון)'],
  [/pattern_loss_breaker:/g, 'שובר-הפסדים-לתבנית:'],
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
  daytype_playbook: { name: 'פלייבוק סוג-יום', why: 'פלייבוק דחה — ראה סיבה מדויקת מהשרת' },
  trend_direction_gate: { name: 'שער כיוון-מגמה', why: 'נגד מגמה — ראה סיבה מדויקת מהשרת' },
  reactive_location: { name: 'מיקום ריאקטיבי', why: 'מיקום fade שגוי — ראה סיבה מדויקת מהשרת' },
  location_gate: { name: 'שער-מיקום (דלתון)', why: 'מיקום מול VAH/VAL שגוי — ראה סיבה מדויקת מהשרת' },
  daytype_position_gate: { name: 'שער משפחה×סוג-יום', why: 'משפחה×סוג-יום — ראה סיבה מדויקת מהשרת' },
  cont_trend_filter: { name: 'המשך-עם-מגמה', why: 'המשך נגד מגמה-מתמשכת — ראה סיבה מדויקת מהשרת' },
  direction_context: { name: 'הקשר-כיוון יומי', why: 'נגד הקשר-יום — ראה סיבה מדויקת מהשרת' },
  lsma_flat: { name: 'LSMA שטוח', why: 'שיפוע-LSMA שטוח — ראה סיבה מדויקת מהשרת' },
  news_blackout: { name: 'חלון-חדשות', why: 'חלון-חדשות — ראה אירוע מדויק מהשרת' },
  day_direction_doctrine: { name: 'דוקטרינת כיוון-יום', why: 'נגד התרחבות-יום — ראה סיבה מדויקת מהשרת' },
  entry_not_confirmed: { name: 'אין אישור-כניסה', why: 'אין אישור-כניסה — ראה סיבה מדויקת מהשרת' },
  t1_wrong_side: { name: 'T1 בצד הלא-נכון', why: 'T1 בצד הלא-נכון — ראה סיבה מדויקת מהשרת' },
  rr_entry_gate: { name: 'שער סיכון:סיכוי', why: 'R:R מתחת לסף — ראה מספרים מדויקים מהשרת' },
  daily_loss_halt: { name: 'עצירת הפסד-יומי', why: 'תקרת ההפסד היומי (−$400) נפרצה — אין ירי עד מחר' },
  consecutive_loss_halt: { name: 'עצירת הפסדים-רצופים', why: 'רצף הפסדים — עצירה מחויבת' },
  s4_risk_cap: { name: 'תקרת-סיכון S4', why: 'הסיכון בנקודות/דולרים מעל התקרה לעסקת S4' },
  cluster_guard: { name: 'שומר-צבירה', why: 'יותר מדי עסקאות באותו אזור-מחיר/זמן' },
  // 07-17: השלמת אוצר-המילים מול trading_gateway.py (ביקורת מלאה של כל blocked_by):
  // pattern_loss_breaker פוצל מ-s4_risk_cap ב-P5 (trading_gateway.py:1457-1464).
  pattern_loss_breaker: { name: 'שובר-הפסדים לתבנית', why: 'התבנית הזו כבר הפסידה פעמיים היום — חסומה עד סוף-היום' },
  // שמור-מראש ל-N3 (ZONE_LIMIT_ENTRY_V1 — עוד לא בבקאנד): תרגום מוכן ליום שהשער יעלה.
  zone_limit_late_entry: { name: 'כניסה מאוחרת', why: 'כניסה מאוחרת (סטייה/גיל) — ראה סיבה מדויקת מהשרת' },
};

export function gateHe(key?: string | null): { name: string; why: string } {
  if (!key) return { name: '', why: '' };
  return GATE_HE[key] || { name: key, why: 'שער ללא-תרגום — ראה לוג' };
}

/** 07-20: prefer precise API reason over generic GATE_HE.why (Michael: don't show misleading SKIP). */
export function blockWhy(d: { blocked_by?: string | null; reason?: string | null }): string {
  const precise = planReasonHe(d.reason);
  if (precise) return precise;
  return gateHe(d.blocked_by).why;
}
