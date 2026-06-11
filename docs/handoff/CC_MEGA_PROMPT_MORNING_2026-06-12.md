# CC MEGA-PROMPT — הכנת המערכת לפתיחת המסחר 2026-06-12 (יום-תצפית עוגנים)

**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — Rule 5 (פקודה+פלט גולמי), טסטים
אנטי-טאוטולוגיים אמיתיים, NOT-DONE חובה. Standing Decisions נשארות OFF.
**החלטת Michael (00:30, 2026-06-12):** לבצע עכשיו את המלצת-העוגן לפי האפיון + יום-תצפית
נוסף; **לסמן את הקומיט כך שניתן לבטלו**; בסוף יום המחר מחליטים סופית איך נקבעים העוגנים.

**קרא קודם:** `FIX_2026-06-12_REPORT.md` (העבודה שלך הלילה + הערות-האימות של Cowork ב-STATUS_BOARD)
· `PATTERN_DAYTYPE_PLAYBOOK_RESEARCH_2026-06-11.md` חלק ו'+ז' · `INSIGHTS_UNIFIED_2026-06-11.md`.

---
## T1 — תיקון הטסטים הטאוטולוגיים (חובה לפני הכול)

ממצא Cowork (עדות גולמית ב-STATUS_BOARD): שני הטסטים החדשים ב-`test_g1_entry_context.py`
עוברים גם כשהתיקון ב-`trading_gateway.py` מוסר (stash→9 passed). שכתב אותם כך שיקראו
לנתיב האמיתי (בניית ה-tm_setup/trade-dict דרך הקוד של ה-gateway, או חילוץ הביטוי לפונקציה
`resolve_pattern_id(setup, g1)` שה-gateway קורא לה והטסט בודק אותה). הוכחת RED-on-revert:
הפוך את התיקון זמנית → הטסט חייב להיכשל → החזר. הדבק את שני הפלטים.

## T2 — תקרות-סיכון/עוגן לפי האפיון (`PATTERN_RISK_CAPS`) — ההמלצה לביצוע עכשיו

האפיון (`stop_anchors.yaml`): עוגן מבני + 3 טיקים, `risk_cap_points: 25` לחוזה,
וסולם-חוזים לפי סיכון. **הפרצה שנוצלה אתמול:** עוגן-קיצון (HFE/DB) נגרר רחוק מהכניסה
(עד 39 נק' בפועל, 73 נדחה) — בניגוד לרוח-האפיון. התיקון, flag `PATTERN_RISK_CAPS`
(default OFF בקוד):
1. שדה `max_risk_points` פר-תבנית ב-`stop_anchors.yaml` (ערכי-פתיחה מהפלייבוק, מסומנים
   🔬-לתצפית): HFE **20** · VEGAS 20 · GHOST 18 · HTLB 20 · FAMIR 12 · ZLR **15** ·
   TLB **15** · TT/GB100 15 · Reactive 15 · Initiative 12 · Double_BT **20** · HnS 20 · Flag 15.
2. אכיפה בנקודת פתרון-העוגן (לפני pre_fire): סיכון > תקרה ⇒ תבניות-המשך (CONT) →
   SIZE-DOWN לחוזה-1 עם סטופ בתקרה רק אם קיים עוגן-משנה מבני בתוך התקרה; אחרת —
   ו-תמיד בתבניות-היפוך (REV) → **SKIP** עם לוג `RISK_CAP_SKIP` (ה-עוגן רחוק = התבנית
   כבר ברחה, לא מגדילים סיכון). אין הזזת-סטופ-לתוך-נר (עיקרון structural_stop_always_wins).
3. רגרסיה אנטי-טאוטולוגית: תרחיש #49 (HFE, עוגן 39 נק') ⇒ flag=ON נחסם-עם-לוג,
   flag=OFF עובר; תרחיש ZLR-12נק' ⇒ עובר בשני המצבים. RED-on-revert מוכח.
4. `.env`: `PATTERN_RISK_CAPS=1` (SHADOW בלבד — יום-תצפית).

## T3 — מימוש הראנר T2/T3 (`RUNNER_TARGETS_V1`) — אושר ע"י Michael (11.06 ערב)

לפי העיצוב בדוח שלך + פלייבוק חלק ו': T2 = הקרוב מבין R-multiple (2.0 CONT / 1.5 REV)
↔ רמה מבנית לפי סוג-יום (`day_type_targets`) · T3 = trail (2-bar או chandelier 2.5×ATR)
בימי Trend בלבד · סטופ-אחרי-T1 = עוגן-משנה מבני (דגל נפרד `STOP_AFTER_T1_STRUCTURAL`,
**OFF מחר** — מפעילים רק את היעדים, לא משנים BE באותו יום-תצפית — משתנה אחד בכל פעם).
חיבור ל-BarLevelDetector/mgmt-log (T2_HIT/T3_HIT קיימים) + UI. רגרסיות לכל מסלול.
`.env`: `RUNNER_TARGETS_V1=1` (SHADOW).

## T4 — מכשירי-התצפית (log-only, ON)

`S2_DETECTION_LOG=1` + `S4_DETECTION_LOG=1` (שורה פר-בר: וקטור התנאים + ערכים; dedup
פר-ts, בלי ספאם) + `TRADE_CVD_SNAPSHOT=1` (cvd_at_entry/t1/exit, None אם אין — Rule 1).
אלה observability בלבד — מותר ON בלי שער.

## T5 — קומיט מסומן-לביטול + restart (הדרישה המפורשת של Michael)

1. קומיט אחד לכל עבודת-הקוד: `fix+feat(anchors+runner): PATTERN_RISK_CAPS + RUNNER_TARGETS_V1 + detection logs + real G1 tests [ANCHOR-TRIAL]`.
2. **תיוג**: `git tag pre-anchor-trial-2026-06-12 HEAD~1` + `git tag anchor-trial-2026-06-12 HEAD`.
   תעד בדוח את שורת-הביטול: `git revert <sha>` או rollback-מיידי בלי revert: כיבוי הדגלים
   ב-.env + restart (הדגלים default-OFF בקוד ⇒ כיבוי = התנהגות-אתמול בדיוק).
3. restart backend → אימות חי: הדגלים ב-`ps eww`/לוג-עלייה, health<100ms, ואז צ'קליסט
   `docs/runbooks/PRE_TRADE_PROTOCOL.md` מלא. הדבק פלטים.

## T6 — תוכנית סוף-היום (להכין את התשתית עכשיו)

דוח-נגד EOD אוטומטי (`scripts/eod_anchor_trial_report.py` או הרחבת ה-EOD הקיים — בדוק
קודם מה יש, אל תשכפל): לכל עסקה/דחייה מחר — העוגן שנבחר, הסיכון, האם נחסם/הוקטן ע"י
התקרה, וקאונטרפקטואל ("בלי תקרה היה X"); + ביצועי T2/T3 הראשונים. הפלט הוא הבסיס
להחלטת-העוגנים של Michael מחר בערב.

## NOT-DONE / מחוץ לתחום
COUNTER_PATTERN_VETO — עיצוב קיים, **ממתין לשער Michael** (לא להפעיל) · אין כיול
b2_vsa/b1_expansion · אין שינוי TIME_STOP · Standing Decisions OFF · §7a.

## דו"ח
`docs/reports/MORNING_PREP_2026-06-12.md` + עדכון לוחות. Cowork יאמת Rule-5 לפני הפתיחה.
