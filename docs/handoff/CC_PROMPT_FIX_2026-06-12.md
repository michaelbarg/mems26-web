# CC Prompt — הסבר + תיקון למחר (2026-06-12): #49 כיוון-הפוך · אובדן-זיהויים · הפעלת T2/T3

**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — Rule 5 (פקודה+פלט גולמי לכל טענה),
טסטים אנטי-טאוטולוגיים, NOT-DONE חובה. כל שינוי לוגיקת-מסחר flag-gated default-OFF +
שער-Michael לפני הפעלה. Standing Decisions נשארות OFF.

**קרא קודם (כל התובנות מהיום):** `S2_WHY_NOT_FIRED_REPLAY_2026-06-11.md` ·
`S2_PATTERNS_INVENTORY_2026-06-11.md` · `S2_DEEP_CHECKLIST_2026-06-11.md` ·
`TRADE_ANALYSIS_RECOMMENDATIONS_2026-06-11.md` · `TRADE_AUDIT_S2_S4_2026-06-11.md` ·
`PATTERN_DAYTYPE_PLAYBOOK_RESEARCH_2026-06-11.md` (חלק ה'+ו') · `TRADES_VISUAL_2026-06-11.html`.

---
## חלק 1 — מחקר/הסבר (לפני כל תיקון; דו"ח עם עדות גולמית)

### 1.1 הבאג המרכזי — #49: שורט HFE בתוך גיאומטריית LONG מובהקת (סטייה מהאפיון)
Michael (צילום-מסך #49): באזור 19:00–20:00 IL היו על הצ'ארט **רצפה-כפולה** וגם **דגל
עליון** — והמערכת ירתה HFE **SHORT** (id 49, ‑$585, סיכון 39 נק', עוגן משותף ל-6 עסקאות).
ה-replay של Cowork מאשר: `detect_double_bottom_ee` החזיר **LONG** ב-19:05/19:10/19:15
וב-20:25–20:55 על הברים האמיתיים. כלומר ברגע-הירי של שורט-49 הייתה תבנית-נגד LONG
שהדיטקטור עצמו מזהה. שאלות לענות עם קוד+דאטה:
1. למה זיהויי ה-DB-LONG של 19:05–19:15 **לא הגיעו בכלל ל-live** (אין ירי ואין דחיית
   pre_fire בלוג)? חשודים: dedup פר-kind · סדר-השרשרת (Reactive→Initiative→5a→5b→5c,
   מי "בולע" את מי) · באפר אחרי ה-hydration החוזר (14×, 16:35–16:56) · שער day_type.
   הוכח איזה מהם עם replay מול הלוג.
2. למה S4 רשאי לירות SHORT כשתבנית-נגד S2 פעילה באותו רגע? האם קיים בכלל צ'ק
   cross-system על תבנית-נגד לפני ירי (לא רק systems_agreement תצוגתי)? תעד את המצב.
3. אותו מנגנון: 17:50 REACTIVE_SHORT זוהה ב-replay ולא נסחר — באותה דקה S4 ירה ZLR
   (id 37). dedup? mutual exclusion? הוכח.
4. ⚠️ id 43: S2 ירה REACTIVE_LONG אבל ב-DB נרשם `pattern_id=VEGAS` — "נכנס לתבנית
   הלא-נכונה". מצא איפה ה-pattern_id מתערבב (gateway?) — זה אותו משפחת-באג.

### 1.2 אימות מלא של ממצאי ה-replay
הרץ את ה-replay של Cowork (התנאים ב-`S2_WHY_NOT_FIRED_REPLAY`) כסקריפט בדיקה עצמאי
(`scripts/replay_s2_conditions.py`, קריאה-בלבד) ואשר/הפרך: 12 near-miss של REACTIVE על
`b2_vsa`, 13 של INITIATIVE על `b1_expansion`, רצפי ה-DB-EE, אפס HnS/DT/Flags.

---
## חלק 2 — תיקונים (flag-gated; להציג diff למייקל לפני הפעלה ב-SHADOW)

### 2.1 תיקון "נכנס לתבנית הלא-נכונה / לא זיהתה תבניות"
לפי ממצאי 1.1: תקן את הצינור כך ש**זיהוי תקף של תבנית לא הולך לאיבוד** (dedup/שרשרת/
hydration — מה שיוכח) ואת ערבוב ה-pattern_id (1.1.4). רגרסיה: טסט שמזין את ברי 19:05
ומוודא שה-DB-LONG מגיע ל-pre_fire; טסט pattern_id=מה-שזוהה.

### 2.2 וטו תבנית-נגד (חדש — שער-Michael)
דגל `COUNTER_PATTERN_VETO` (default OFF): לפני ירי, אם דיטקטור פעיל אחר מחזיק זיהוי
בכיוון ההפוך מאותו חלון ברים (או ירי-נגדי ב-N≤3 ברים אחרונים) ⇒ חסום/סמן. עדות-בסיס:
13 זוגות-נגד היום, כמעט בכל זוג מפסיד גדול. טסט אנטי-טאוטולוגי: תרחיש #49 (HFE-SHORT
מול DB-LONG פעיל) ⇒ עם דגל=נחסם, בלי דגל=עובר.

### 2.3 הפעלת מימוש T2/T3 (הבקשה המרכזית של Michael)
הראנר חייב יעדים. לממש לפי `PATTERN_DAYTYPE_PLAYBOOK_RESEARCH` חלק ו':
- `RUNNER_TARGETS_V1` (default OFF): T2 = **הקרוב מבין** R-multiple (2.0 CONT / 1.5 REV)
  ↔ רמה מבנית (קצה-IB/POC/VA לפי סוג-יום מ-`day_type_targets`). T3 = trail (chandelier
  2.5×ATR או 2-bar) בימי Trend בלבד.
- סטופ-אחרי-T1 = עוגן-משנה מבני (בר-האות) במקום BE+טיק — לכבד את D-002. דגל נפרד
  `STOP_AFTER_T1_STRUCTURAL` כדי שמייקל יוכל להפעיל בנפרד.
- חיבור ל-mgmt log (T2_HIT/T3_HIT כבר קיימים) + ל-UI. רגרסיה לכל מסלול.
- **לא** לגעת ב-TIME_STOP בינתיים.

### 2.4 תקרות-סיכון פר-תבנית (הפסקת ה-39-נק'-על-HFE)
`stop_anchors.yaml`: שדה `max_risk_points` פר-תבנית (HFE 15–20 · DB 20 · ZLR/TLB 15 —
ערכי-פתיחה מהפלייבוק; מעבר לתקרה: CONT→SIZE-DOWN, REV→SKIP). דגל `PATTERN_RISK_CAPS`.

## NOT-DONE / מחוץ לתחום
אין שינוי לספי b2_vsa/b1_expansion (כיול = אחרי שבוע-התצפיות + המחקר החיצוני של Michael) ·
אין שינוי chop/COT-AMT · אין נגיעה ב-sc_study/bridge (§7a).

## דו"ח
`docs/reports/FIX_2026-06-12_REPORT.md` + עדכון לוחות. מחר: Michael בוחן את התיקון,
ואז משלבים את מסקנות המחקר החיצוני (ניהול סטופים) למסמך המלצות מאוחד.
