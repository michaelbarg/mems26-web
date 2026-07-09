/** Fire / no-fire diagnosis for Plan tab (Hebrew copy for traders). */

import type { FireRowStatus, PlanLifecycle } from './planHelp';

export type TreeSituation =
  | 'NO_SETUP'
  | 'PATTERN_WAIT'
  | 'TREE_FAIL'
  | 'TREE_PENDING'
  | 'TREE_READY'
  | 'ROUTED_SHADOW'
  | 'ROUTED_DEMO'
  | 'ROUTED_LIVE'
  | 'GATEWAY_BLOCK'
  | 'NO_GATEWAY';

export interface FireDiagnosis {
  situation: TreeSituation;
  badgeLabel: string;
  setupLine: string;
  identifiedLine: string;
  treeLine: string;
  whyNotFire: string[];
  wouldFireWhen: string[];
  primaryStage?: string;
}

export interface GatewaySnap {
  shadow_active_count?: number;
  demo_slot?: string | null;
  demo_slot_system?: number | null;
  live_slot?: string | null;
  live_slot_system?: number | null;
  cooldown?: { blocked?: boolean };
  cluster_guard?: { blocked?: boolean };
  ssv?: { blocked_directions?: string[] };
}

const GATEWAY_BLOCK_HE: Record<string, string> = {
  cooldown: 'קירור אחרי 2 סטופים רצופים (cooldown)',
  cluster_guard: 'מגן קלאסטר — יותר מדי ניסיונות בפרק זמן קצר',
  suffering_side_veto: 'SSV — כיוון העסקה הוא "צד סובל"',
  chop_searching: 'Layer 0 במצב SEARCHING (שוק צופף)',
};

function stageMessage(
  pre: Array<Record<string, unknown>> | undefined,
  stageId: string,
): string {
  if (!pre) return '';
  const row = pre.find((r) => r.stage_id === stageId);
  return String(row?.message ?? '');
}

function formatSetup(patterns: Array<Record<string, unknown>> | undefined): {
  line: string;
  id: string | null;
  direction: string | null;
  confidence: number | null;
} {
  if (!patterns?.length) {
    return { line: 'אין סטאפ פעיל — לא זוהתה תבנית CCI בבר האחרון', id: null, direction: null, confidence: null };
  }
  const best = patterns.reduce((a, b) =>
    Number(b.confidence ?? 0) > Number(a.confidence ?? 0) ? b : a,
  );
  const id = String(best.pattern_id ?? '—');
  const dir = String(best.direction ?? '—');
  const conf = best.confidence != null ? Number(best.confidence) : null;
  return {
    line: `סטאפ: ${id} ${dir}${conf != null ? ` · ביטחון ${(conf * 100).toFixed(0)}%` : ''}`,
    id,
    direction: dir,
    confidence: conf,
  };
}

function gatewayWhyNot(
  gw: GatewaySnap | null,
  systemId: number,
  direction: string | null,
): string[] {
  if (!gw) return ['Gateway לא זמין — לא ניתן לנתב עסקה'];
  const out: string[] = [];
  if (gw.cooldown?.blocked) out.push(GATEWAY_BLOCK_HE.cooldown);
  if (gw.cluster_guard?.blocked) out.push(GATEWAY_BLOCK_HE.cluster_guard);
  if (direction && gw.ssv?.blocked_directions?.includes(direction)) {
    out.push(GATEWAY_BLOCK_HE.suffering_side_veto);
  }
  if (gw.demo_slot && gw.demo_slot_system != null && gw.demo_slot_system !== systemId) {
    out.push(`סלוט DEMO תפוס ע״י S${gw.demo_slot_system} (${gw.demo_slot})`);
  }
  if (gw.live_slot && gw.live_slot_system != null && gw.live_slot_system !== systemId) {
    out.push(`סלוט LIVE תפוס ע״י S${gw.live_slot_system} (${gw.live_slot})`);
  }
  if (gw.shadow_active_count != null && gw.shadow_active_count > 0) {
    out.push(
      `SHADOW: ${gw.shadow_active_count} רשומות היום — זה לא חוסם, רק מידע`,
    );
  }
  return out;
}

function explainFailStage(stageId: string, msg: string): string {
  if (stageId === 'A5' && msg.includes('reject')) {
    return 'A5 גודל פוזיציה = reject — התבנית זוהתה אבל sizing לא מאשר כניסה';
  }
  if (stageId === 'A1') {
    return 'A1 שער מגמה — trend אפור או ביטחון נמוך מדי';
  }
  if (stageId === 'A3') {
    return 'A3 אין תבנית בבר הזה (SKIP) — לא אומר שאין סטאפ בהיסטוריה';
  }
  if (stageId === 'A7') {
    return 'A7 pre_fire/gateway — בדיקות אוניברסליות רק בזמן route_setup';
  }
  return `${stageId}: ${msg || 'נכשל'}`;
}

/** Woodies S4 — full why / why-not from snapshot raw + gateway. */
export function diagnoseWoodies(
  raw: Record<string, unknown>,
  gateway: GatewaySnap | null,
  killzoneOpen: boolean | null,
): FireDiagnosis {
  const dt = (raw.decision_tree ?? {}) as Record<string, unknown>;
  const pre = dt.pre_fire as Array<Record<string, unknown>> | undefined;
  const failed = (raw.failed_stages ?? dt.failed_stages) as string[] | undefined;
  const pending = (raw.pending_stages ?? dt.pending_stages) as string[] | undefined;
  const patterns = raw.active_patterns as Array<Record<string, unknown>> | undefined;
  const setup = formatSetup(patterns);
  const classification = String(raw.classification ?? 'NO_SETUP');
  const entrySpec = raw.entry_classification_spec as string | undefined;
  const ready = raw.ready_to_route === true;
  const lastRoute = raw.last_route as Record<string, unknown> | undefined;

  const identified = [
    setup.line,
    classification !== 'NO_SETUP' ? `סיווג: ${classification}` : null,
    entrySpec ? `סוג כניסה (A6): ${entrySpec}` : null,
    `אות אחרון בראש: ${raw.signal ?? 'NEUTRAL'} / ${raw.direction ?? '—'}`,
  ]
    .filter(Boolean)
    .join('\n');

  const whyNot: string[] = [];
  const wouldFire: string[] = [];
  let situation: TreeSituation = 'NO_SETUP';
  let badgeLabel = 'אין תבנית';
  let treeLine = 'מיקום בעץ: לפני A3 — אין תבנית בבר הנוכחי';
  const primaryStage = failed?.[0] ?? pending?.[0];

  if (!patterns?.length && classification === 'NO_SETUP') {
    situation = 'NO_SETUP';
    badgeLabel = 'אין תבנית';
    whyNot.push('לא זוהתה תבנית CCI (ZLR, HFE, VEGAS, …) בבר האחרון.');
    wouldFire.push('כש-A3 יחזיר PASS עם pattern_id ב-active_patterns.');
  } else if ((failed?.length ?? 0) > 0) {
    situation = 'TREE_FAIL';
    const sid = failed![0];
    const msg = stageMessage(pre, sid);
    badgeLabel = `חסום · ${sid}`;
    treeLine = `מיקום בעץ: ${explainFailStage(sid, msg)}`;
    whyNot.push(treeLine.replace('מיקום בעץ: ', ''));
    for (const s of failed!.slice(1)) {
      whyNot.push(explainFailStage(s, stageMessage(pre, s)));
    }
    if (sid === 'A5') {
      wouldFire.push('כש-sizing יחזיר full או half (לא reject).');
    }
  } else if ((pending?.length ?? 0) > 0) {
    situation = 'TREE_PENDING';
    badgeLabel = `ממתין · ${pending![0]}`;
    treeLine = `מיקום בעץ: שלב ${pending![0]} עדיין PENDING (למשל touch-points HTTP).`;
    whyNot.push('שלבי עץ לא הושלמו — זה לא אישור/דחייה ידנית.');
    wouldFire.push('כשכל שלבי A1–A7 יהיו PASS (ללא PENDING/FAIL).');
  } else if (ready) {
    situation = 'TREE_READY';
    badgeLabel = 'מוכן לניתוב';
    treeLine = 'מיקום בעץ: A1–A7 עברו — ready_to_route=true';
    wouldFire.push('העץ מאשר — הבא: TradingGateway (SHADOW רושם, LIVE שולח הוראה).');

    if (!gateway) {
      situation = 'NO_GATEWAY';
      badgeLabel = 'אין Gateway';
      whyNot.push('העץ מוכן אבל TradingGateway לא מחובר ל-WoodiesSystem.');
    } else {
      const gwBlocks = gatewayWhyNot(gateway, 4, setup.direction);
      const routeBlocked = lastRoute?.blocked_by as string | undefined;
      if (routeBlocked) {
        situation = 'GATEWAY_BLOCK';
        badgeLabel = `Gateway · ${routeBlocked}`;
        whyNot.push(GATEWAY_BLOCK_HE[routeBlocked] ?? `Gateway חסם: ${routeBlocked}`);
      } else if (gwBlocks.length > 0) {
        const hard = gwBlocks.filter((x) => !x.includes('לא חוסם'));
        if (hard.length) {
          situation = 'GATEWAY_BLOCK';
          badgeLabel = 'Gateway חסום';
          whyNot.push(...hard);
        }
      }
      if (lastRoute?.shadow) {
        situation = 'ROUTED_SHADOW';
        badgeLabel = 'נרשם SHADOW';
        treeLine = `מיקום בעץ: ירי SHADOW — trade ${lastRoute.shadow}`;
        whyNot.length = 0;
        whyNot.push('ב-SHADOW אין הוראה לברוקר — רק רישום לבדיקה.');
      } else if (ready && !lastRoute && !routeBlocked) {
        whyNot.push('עדיין לא נקלט last_route — ייתכן שהבר הנוכחי עבר לפני חיבור gateway.');
      }
    }
    if (killzoneOpen === false) {
      whyNot.push('Killzone סגור — שעות מחוץ ל-Cash Hours חוסמות ירי.');
    }
  } else {
    situation = 'PATTERN_WAIT';
    badgeLabel = 'בונה סטאפ';
    treeLine = 'מיקום בעץ: תבנית מזוהה — שלבי עץ עדיין לא סגורים';
    const skips = (pre ?? []).filter((r) => String(r.status).toUpperCase() === 'SKIP');
    if (skips.length) {
      whyNot.push(
        `${skips.length} שלבים ב-SKIP בבר הזה (נורמלי כשאין תנאי לשלב) — בדוק FAIL אדום.`,
      );
    }
    wouldFire.push('כשלא יהיו FAIL/PENDING ו-ready_to_route יהפוך ל-true.');
  }

  return {
    situation,
    badgeLabel,
    setupLine: setup.line,
    identifiedLine: identified,
    treeLine,
    whyNotFire: whyNot,
    wouldFireWhen: wouldFire,
    primaryStage,
  };
}

export function lifecycleFromDiagnosis(
  d: FireDiagnosis,
  health: string,
): PlanLifecycle {
  if (health === 'error') return 'BLOCKED';
  switch (d.situation) {
    case 'ROUTED_SHADOW':
    case 'ROUTED_DEMO':
    case 'ROUTED_LIVE':
      return 'FIRING';
    case 'TREE_READY':
      return 'READY';
    case 'TREE_FAIL':
    case 'GATEWAY_BLOCK':
    case 'NO_GATEWAY':
      return 'BLOCKED';
    case 'PATTERN_WAIT':
    case 'TREE_PENDING':
      return 'APPROACHING';
    default:
      return 'SCANNING';
  }
}

export function diagnoseFiringSystem(
  systemId: number,
  raw: Record<string, unknown>,
  gateway: GatewaySnap | null,
): FireDiagnosis {
  if (systemId === 4) {
    return diagnoseWoodies(raw, gateway, null);
  }

  if (systemId === 2) {
    const mode = String(raw.mode ?? '');
    if (mode === 'MAINTENANCE' || mode === 'WEEKEND' || mode === 'OVERNIGHT_MODE') {
      return {
        situation: 'GATEWAY_BLOCK',
        badgeLabel: `חסום · ${mode}`,
        setupLine: `מצב מערכת: ${mode}`,
        identifiedLine: String(raw.last_reasoning_notes ?? raw.opening_type ?? '—'),
        treeLine: 'מיקום בעץ: S2 לא פעילה — ממתינה לחלון מסחר / יום מסחר',
        whyNotFire: [`מצב ${mode} — אין זיהוי דפוסים ואין ירי.`],
        wouldFireWhen: ['כש-mode יחזור ל-FIRST_HOUR_TACTICAL או DAY_TYPE_MODE.'],
      };
    }
  }

  const pattern = raw.last_pattern ?? raw.combined_class ?? raw.last_classification;
  const failed = raw.last_fire as Record<string, unknown> | undefined;
  if (failed?.blocked_by) {
    const block = String(failed.blocked_by);
    return {
      situation: 'TREE_FAIL',
      badgeLabel: `חסום · ${block}`,
      setupLine: pattern ? `סטאפ: ${pattern}` : 'אין סטאפ מזוהה',
      identifiedLine: String(failed.route_reason ?? failed.blocked_by),
      treeLine: 'מיקום בעץ: ניסיון ירי אחרון נחסם ב-pre_fire / gateway',
      whyNotFire: [String(failed.route_reason ?? failed.blocked_by)],
      wouldFireWhen: ['כשהחסימה ב-last_fire תתנקה בבר הבא.'],
      primaryStage: block,
    };
  }

  return {
    situation: pattern ? 'PATTERN_WAIT' : 'NO_SETUP',
    badgeLabel: pattern ? String(pattern) : 'אין תבנית',
    setupLine: pattern ? `סטאפ: ${pattern}` : 'אין סטאפ מזוהה כרגע',
    identifiedLine: String(raw.last_reasoning_notes ?? raw.mode ?? '—'),
    treeLine: pattern
      ? 'התבנית זוהתה — ממתינה לסגירת בר 5-דק׳ ולשערי הכניסה'
      : 'המערכת סורקת כל בר — ראה למעלה אילו תבניות קרובות ומה חסר לכל אחת',
    whyNotFire: [pattern
      ? 'התבנית ממתינה: ירי נבחן רק על סגירת בר, ואז עובר את שערי הכניסה (R:R, בר-אישור, התאמה לסוג-היום)'
      : 'אף תבנית לא השלימה את תנאיה — הרשימה למעלה מראה בדיוק מה חסר לכל אחת'],
    wouldFireWhen: ['בר נסגר עם כל התנאים ירוקים + השערים מאשרים + אין עסקה פתוחה — ואז הפקודה נשלחת לסיירה אוטומטית'],
  };
}
