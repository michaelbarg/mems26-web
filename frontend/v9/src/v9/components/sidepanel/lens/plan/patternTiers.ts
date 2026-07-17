// patternTiers — לוגיקת השכבות/מיון/"מה חסר עכשיו" של פאנל-התבניות בזמן-אמת
// (מייקל 2026-07-17). גזירת-תצוגה טהורה משדות-בקאנד אמיתיים בלבד — אסור להמציא מספרים:
//   · S4: build_pct + formula (woodies_inspector.py:573-590) · רכיבי detection/ready_to_route
//     (woodies_inspector.py:382-394, :500-512)
//   · S2: רכיבי stage="detection" — בדיקה סדרתית עם קטיעה-בכשל-ראשון
//     (s2_pattern_probe.py; סטטוסים: s2_inspector.py:455-497) ⇒ "כל הרכיבים present"
//     שקול למעבר-מלא; רכיב אחרון אדום = השלב שבו נעצרה הבדיקה. אין אחוז מומצא ל-S2.
//   · פיד-החלטות: /api/v9/gateway/decisions (trading_gateway.py:366-385).
import type { Pattern, Component } from '../../../build_status/types';
import type { GatewayDecision } from '../../../../hooks/usePatternFeed';
import { COMPONENT_KEY_HE } from './planHelp';

export type Tier = 'fire' | 'close' | 'building' | 'idle' | 'blocked';

export const TIER_ORDER: Tier[] = ['fire', 'close', 'building', 'idle', 'blocked'];

export const TIER_META: Record<Tier, { icon: string; he: string; desc: string; color: string }> = {
  fire: {
    icon: '🔥', he: 'ירי עכשיו',
    desc: 'ניסיון-ירי ב-5 הדקות האחרונות, או סטאפ מנותב ברגע זה',
    color: '#ff7b72',
  },
  close: {
    icon: '🟠', he: 'קרוב לירי',
    desc: 'המבנה כמעט שלם — ממתין לנר-הטריגר / לאישור המנוע',
    color: '#f0883e',
  },
  building: {
    icon: '🟡', he: 'בהתהוות',
    desc: 'חלק מתנאי-התבנית כבר מתקיימים בברים האחרונים',
    color: '#d29922',
  },
  idle: {
    icon: '⚪', he: 'סורק',
    desc: 'אין מבנה מתגבש כרגע',
    color: '#8b949e',
  },
  blocked: {
    icon: '🚫', he: 'חסום / וטו',
    desc: 'לא יירה במצב הנוכחי — וטו-מגמה, SKIP לסוג-היום או נתונים חסרים',
    color: '#f85149',
  },
};

/** חלון-ה"חם": החלטת-gateway מ-5 הדקות האחרונות = התבנית בשכבת 🔥. */
export const HOT_WINDOW_MS = 5 * 60_000;

const norm = (s?: string | null) => (s || '').toUpperCase().replace(/[^A-Z0-9]/g, '');

/** ההחלטה האחרונה של ה-gateway עבור תבנית זו (התאמת-שם גמישה + התאמת-כיוון).
 *  הועבר מ-AllPatternsPlan למודול משותף (07-17). תוספת: שורת CONFLUENCE_RI_ZLR
 *  ("CONFLUENCERIZLR" מכיל "ZLR") לא תוצג עוד כהחלטה של שורת ה-ZLR ההורה. */
export function lastDecisionFor(
  p: { id: string; name: string },
  decs: GatewayDecision[],
): GatewayDecision | null {
  const pid = norm(p.id), pname = norm(p.name);
  const rowDir = pid.endsWith('LONG') ? 'LONG' : pid.endsWith('SHORT') ? 'SHORT' : null;
  for (const d of decs) { // decs מגיע חדש-ראשון מהשרת
    const gp = norm(d.pattern);
    if (!gp) continue;
    if (gp.startsWith('CONFLUENCE') && !pid.startsWith('CONFLUENCE')) continue;
    if (!(gp.includes(pid) || pid.includes(gp) || gp.includes(pname) || pname.includes(gp))) continue;
    const dDir = (d.direction || '').toUpperCase();
    if (rowDir && dDir && dDir !== rowDir) continue; // כיוון-ההחלטה סותר את כיוון-השורה
    return d;
  }
  return null;
}

/** האם ההחלטה בתוך חלון-החם (ts מהשרת הוא ISO-UTC עם אופסט — אין ניחוש TZ). */
export function isHotDecision(d: GatewayDecision, nowMs: number): boolean {
  const t = Date.parse(d.ts);
  return Number.isFinite(t) && nowMs - t <= HOT_WINDOW_MS && nowMs - t >= -60_000;
}

/** שלבי-הטריגר הסופיים של בדיקות-S2 — "הכול עבר חוץ מנר-הטריגר" = קרוב-לירי. */
const TRIGGER_KEYS = new Set(['b4_confirm', 'b4_test', 'breakout', 'neckline_breakout']);

export interface PatternRowInfo {
  tier: Tier;
  /** מיון בתוך שכבה — גבוה=ראשון. */
  score: number;
  /** החלטת-gateway בתוך 5 הדקות האחרונות (אם יש). */
  hotDec: GatewayDecision | null;
  /** ההחלטה האחרונה בכלל (מאז עליית-הבקאנד), לרמז "מה יחסום". */
  lastDec: GatewayDecision | null;
  /** S4 בלבד — build_pct אמיתי מהבקאנד (met/total של הנוסחה). null ב-S2. */
  buildPct: number | null;
  /** שלבי-detection של S2 (רשימה סדרתית, ייתכן קטועה בשלב-הכשל). */
  detSteps: Component[];
  detPassed: number;
  /** true ⇔ הבדיקה עברה עד הסוף (בגלל הקטיעה-בכשל, all-present = מעבר-מלא). */
  detFullPass: boolean;
  /** השלב הנכשל (בגלל הקטיעה — לכל-היותר אחד, תמיד האחרון ברשימה). */
  failingStep: Component | null;
  /** "מה חסר עכשיו" בעברית — התנאי הלא-מתקיים הראשון, משדות אמיתיים. */
  missingNow: string | null;
  /** S4: state.ready_to_route — הסטאפ מנותב ל-gateway ברגע זה. */
  routingNow: boolean;
  /** S4: התבנית ב-active_patterns של המנוע עכשיו. */
  detectedNow: boolean;
}

export function computeRow(
  p: Pattern,
  decs: GatewayDecision[],
  nowMs: number,
): PatternRowInfo {
  const lastDec = lastDecisionFor(p, decs);
  const hotDec = lastDec && isHotDecision(lastDec, nowMs) ? lastDec : null;

  const comps = p.components || [];
  const detSteps = comps.filter((c) => c.stage === 'detection');
  const detPassed = detSteps.filter((c) => c.present).length;
  const detFullPass = detSteps.length > 0 && detPassed === detSteps.length;
  const failingStep = detSteps.find((c) => !c.present) || null;
  // שלבי-מבנה שעברו, בלי min_bars (מעבר-min_bars לבדו אינו "התהוות")
  const structPassed = detSteps.filter((c) => c.present && c.key !== 'min_bars').length;
  const buildPct = typeof p.build_pct === 'number' ? p.build_pct : null;
  const routingNow = comps.some((c) => c.key === 'ready_to_route' && c.present);
  const detectedNow = comps.some((c) => c.key === 'pattern_specific' && c.present);

  let tier: Tier;
  if (hotDec || routingNow) {
    tier = 'fire';
  } else if (p.status === 'vetoed' || p.status === 'blocked') {
    tier = 'blocked';
  } else if (p.status === 'unknown' || p.status === 'not_applicable') {
    tier = 'idle';
  } else if (
    detectedNow ||
    detFullPass ||
    (failingStep !== null && TRIGGER_KEYS.has(failingStep.key)) ||
    (buildPct !== null && buildPct >= 75)
  ) {
    tier = 'close';
  } else if (structPassed >= 2 || (buildPct !== null && buildPct >= 45)) {
    tier = 'building';
  } else {
    tier = 'idle';
  }

  let score = 0;
  if (tier === 'fire') {
    score = hotDec ? Date.parse(hotDec.ts) || 0 : nowMs; // מנותב-עכשיו לפני חם-ישן
  } else if (buildPct !== null) {
    score = detectedNow ? 100 + buildPct : buildPct;
  } else if (detSteps.length) {
    score = detFullPass
      ? 100
      : failingStep && TRIGGER_KEYS.has(failingStep.key)
        ? 90
        : structPassed * 10;
  }

  // "מה חסר עכשיו" — התנאי הלא-מתקיים הראשון. ל-blocked/vetoed/unknown השורה
  // מציגה את reason של הבקאנד (מתורגם ב-planReasonHe) במקום.
  let missingNow: string | null = null;
  if (tier !== 'fire' && tier !== 'blocked' && p.status !== 'unknown') {
    if (p.formula && p.formula.length) {
      const unmet = p.formula.find((f) => !f.met);
      if (unmet) {
        missingNow = `${unmet.label} — צריך ${unmet.needed}${unmet.actual ? ` · בפועל ${unmet.actual}` : ''}`;
      } else if (!detectedNow) {
        missingNow = 'תנאי-הנוסחה מתקיימים — ממתין לזיהוי המנוע ולעץ-ההחלטה';
      }
    } else if (failingStep) {
      missingNow = COMPONENT_KEY_HE[failingStep.key] || failingStep.key;
    } else if (detFullPass) {
      missingNow = 'כל שלבי-הזיהוי עברו — ממתין לנר-הטריגר';
    }
  }

  return {
    tier, score, hotDec, lastDec, buildPct,
    detSteps, detPassed, detFullPass, failingStep,
    missingNow, routingNow, detectedNow,
  };
}
