// dayType.ts — single UI source for day-type colors, short codes and the
// trader-meaning legend (P-UI day-type round, 2026-07-02).
//
// COLORS follow the existing in-app convention — the identical DT_COLOR maps in
// DayTypeLabelTab.tsx and build_status/DayTypeConditionsTable.tsx (the labeler and
// the Build-Status table already teach the trader these colors). Aliases cover the
// classifier spelling (Normal_Variation), the playbook/old-engine spelling
// (Variation, Neutral) and the not-yet/unknown states.
//
// Canonical 7-type source: GET /api/v9/day_type/classify_replay
// (docs/spec_authority/S1_ACTIVE_CANONICAL.md + docs/SOURCE_OF_TRUTH.md §Day-type).
// Legend one-liners: Michael's ratified playbook — config/daytype_playbook.yaml
// (daytype_style.*.bias/note). Display-only; no trading logic here.

export const DAY_TYPE_COLOR: Record<string, string> = {
  Trend_Normal: '#56d364',
  Trend_DD: '#3fb950',
  Normal_Variation: '#bfae3b',
  Variation: '#bfae3b', // playbook / old-engine alias of Normal_Variation
  Normal: '#d2a106',
  Neutral_Center: '#58a6ff',
  Neutral_Extreme: '#bc8cff',
  Neutral: '#58a6ff', // generic alias
  Nontrend: '#a85751',
  FORMING: '#8b949e',
  UNKNOWN: '#6e7681', // muted
};

/** Color for a day-type label; tolerant to space/underscore spelling; muted fallback. */
export function dayTypeColor(dt: string | null | undefined): string {
  if (!dt) return DAY_TYPE_COLOR.UNKNOWN;
  return (
    DAY_TYPE_COLOR[dt] ??
    DAY_TYPE_COLOR[dt.replace(/\s+/g, '_')] ??
    DAY_TYPE_COLOR.UNKNOWN
  );
}

/** Compact chip codes for tight surfaces (trade lists, side-panel rows) —
 *  same code family the S1 DayTypePill already teaches (DayTypePill.tsx ABBREV).
 *  Added in UI round 2 (2026-07-02); additive only. */
export const DAY_TYPE_ABBREV: Record<string, string> = {
  UNKNOWN: 'UNKN', FORMING: 'FORM', Trend_Normal: 'TREND', Trend_DD: 'TDD',
  Variation: 'VAR', Normal_Variation: 'VAR', Normal: 'NORM',
  Neutral: 'NEUT', Neutral_Center: 'NEUC', Neutral_Extreme: 'NEUX', Nontrend: 'NONT',
};

/** Short chip code for a day-type label; tolerant to space/underscore; '—' when missing. */
export function dayTypeAbbrev(dt: string | null | undefined): string {
  if (!dt) return '—';
  return (
    DAY_TYPE_ABBREV[dt] ??
    DAY_TYPE_ABBREV[dt.replace(/\s+/g, '_')] ??
    dt.slice(0, 5)
  );
}

/** classifier `direction` stances (config/daytype_trading_plan.yaml:76) → trader text. */
export const DAY_TYPE_DIRECTION_HE: Record<string, string> = {
  none: 'אין כיוון — לא לסחור',
  fade_both: 'פייד משני הצדדים',
  with_extension: 'עם ההרחבה',
  with_trend: 'עם המגמה — לא לפייד',
  winner_side: 'לכיוון הקצה המנצח',
};

/** The 7 terminal types in playbook order + the trader meaning one-liner.
 *  Trend=go-with · Normal/Neutral=fade edges · Variation=with expansion · Nontrend=no trade. */
export const DAY_TYPE_LEGEND: Array<{ type: string; label: string; meaning: string }> = [
  { type: 'Trend_Normal',    label: 'Trend Normal',    meaning: 'ללכת עם המגמה מהפתיחה; תוספות בפולבקים רדודים; ראנר עד הסגירה' },
  { type: 'Trend_DD',        label: 'Trend DD',        meaning: 'המשך עם הפריצה מ-single-print / דיסטריביושן שני; טרייל מאחורי סטרוקטורה' },
  { type: 'Normal_Variation', label: 'Variation',      meaning: 'עם הרחבת ה-IB בלבד (המשך, לא פייד); כניסה בפולבק לקצה שנפרץ' },
  { type: 'Normal',          label: 'Normal',          meaning: 'פייד על קצוות ה-VA: שורט רק ליד VAH · לונג רק ליד VAL' },
  { type: 'Neutral_Center',  label: 'Neutral Center',  meaning: 'פייד משני הקצוות אל המרכז (POC) — יציאה במרכז, בלי ראנר' },
  { type: 'Neutral_Extreme', label: 'Neutral Extreme', meaning: 'פייד קצוות VA אל POC; ראנר לכיוון הקצה המנצח' },
  { type: 'Nontrend',        label: 'Nontrend',        meaning: 'אין משתתפים — לא לסחור (לכל היותר סקאלפ קצה→POC)' },
];
