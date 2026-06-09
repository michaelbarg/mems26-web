# Design Proposal — Externalize Auth-Matrix + Targets/Stop tables for calibration | 2026-06-03

## דרישת Michael (2026-06-04): שלושתם גמישים — stop, יציאות, וכמות חוזים
Michael רוצה שלושה דברים ניתנים-לכיול בלי שינוי-קוד: (1) **כמות חוזים (sizing)**, (2) **יציאות (T1–T5)**, (3) **ה-stop**.
לא משנה עכשיו, אבל סביר שישנה → להבטיח שכל השלושה ב-config.

## הבעיה היום
**שלוש** קבוצות-risk-surface הן **dict/קוד קשיח ב-Python**:
- `auth_table_v1.py::_AUTH_TABLE_V1` — 70 תאים (pattern × day-type × tier → verdict + **חוזים/sizing**). spec **LOCKED**. → דרישה (1).
- `targets_table.py::_TARGETS` — פר day-type, T1/T2/T3 ב-R-multiples + **time-stop**. "Constitution V3". → דרישה (2) + חלק מ-(3).
- `five_min/adaptive_stop.py` (+ מודל ה-stop השכבתי של S4) — פרמטרי **ה-stop**: structural-anchor offsets, ATR-cap multipliers, floor ticks. → דרישה (3). **טרם כלול בתכנון — להוסיף.**

כל שינוי = עריכת `.py` → commit → **restart backend**. לא runtime, לא UI, לא DB. מטרת SHADOW היא **כיול** —
ולכן מחזור edit→commit→restart על כל שינוי-מספר הוא חיכוך גדול בדיוק בשלב שבו צריך לכייל הרבה.

## מה הגמישות תאפשר (קונקרטי)
1. **כיול בלי redeploy** — לשנות מספר-חוזים/R-multiple ולראות אפקט בסשן הבא, בלי dev-cycle.
2. **איטרציה מהירה ב-SHADOW/DEMO** — הליבה של soak: לכוונן→לצפות→לכוונן.
3. **גרסאות + A/B** — להחזיק V1/V2 ולהשוות בצל (SHADOW) לפני נעילה.
4. **עריכה מהדאשבורד** — `BuildTreeView` כבר מציג placeholder "ממתין ל-backend" ל-TARGETS/STOP ול-Day-Type Matrix → אפשר להפוך לעריכה מבוקרת.
5. **audit-trail** — כל שינוי נרשם (מי/מתי/ישן→חדש), ממשל טוב יותר מ-git-only.
6. **הפרדת config מקוד** — אתה מכייל בלי לגעת ב-Python.

## ⚠️ הסיכון שחייב guardrails
טבלאות אלו הן **risk-surface**. לעשות אותן editable-בזמן-ריצה בלי בקרות = לפתוח דלת ל-blow-up סיכון בעריכה אחת.
לכן כל אופציה חייבת לכלול: **schema-validation** בטעינה · **תקרות קשיחות** (חוזים ≤ global max-contracts; R-multiples בטווח שפוי) ·
**דגל approval/lock** (ערך פעיל מול "מאושר") · **audit-trail** · ושמירת ה-spec ה-LOCKED כ-baseline-מאושר.

## האופציות

**Option A — YAML config (file-backed) · המלצה לשלב 1**
הטבלאות עוברות ל-`config/auth_matrix.yaml` + `config/targets.yaml`, נטענות באתחול (+ endpoint reload אופציונלי).
- גמישות: עריכת קובץ → reload/restart, בלי שינוי-קוד. git עוקב (diff/PR) = ממשל מובנה.
- מאמץ: נמוך. סיכון: נמוך. **הצעד הראשון הנכון** — נותן 80% מהגמישות מיד.

**Option B — DB table + admin UI · שלב 2 (post-SHADOW)**
הטבלאות הופכות לשורות-DB (`v9_auth_matrix`, `v9_targets`) + טבלת `v9_config_audit`, נערכות דרך endpoint/פאנל מבוקר.
- גמישות: עריכה בזמן-ריצה, בלי restart, מהדאשבורד, audit-trail מלא.
- מאמץ: גבוה (UI + governance). מתחבר ל-placeholders הקיימים ב-`BuildTreeView`.

**Option C — Hybrid (מומלץ כיעד-קצה)**
DB מחזיק את הערכים ה**פעילים** (כולל כיול); YAML/spec ה-LOCKED הוא ה-baseline המאושר; דגל lock + audit-trail;
fallback ל-const dict אם DB/קובץ ריק. נותן גמישות מלאה **בלי** לאבד את ה-LOCKED-spec כמקור-אמת מאושר.

## מסלול לא-הרסני
1. הוצא את ה-dicts לשכבת-loader עם **fallback לערכים הנוכחיים** (אם config חסר → const dict) → אפס שבירה.
2. שלב 1 = Option A (YAML + schema-validation + תקרות). מכייל מיד ב-SHADOW.
3. שלב 2 (אם צריך עריכת-runtime/UI) = Option B/C: DB + פאנל ב-`BuildTreeView` + audit-trail + approval-gate.
4. ה-spec ה-LOCKED (`S2_AUTH_TABLE_V1.md`) נשאר baseline; שינוי-כיול = גרסה חדשה עם אישור Michael, לא דריסה שקטה.

## המלצה
**שלב 1 = Option A** (YAML, low-risk, git-governed) לכיול מיידי ב-SHADOW; **שלב 2 = Option C** אחרי SHADOW אם תרצה עריכת-runtime/UI.
שינוי risk-logic נשאר תחת strategic-stop + אישורך. prompt ל-CC ייכתב אחרי שתבחר אופציה.
**הרחבת-scope (Michael 2026-06-04):** ה-prompt הקיים `CC_PROMPT_CONFIG_YAML_AUTH_TARGETS` מכסה auth(חוזים)+targets(יציאות).
להוסיף **קבוצה שלישית — פרמטרי ה-stop** (`adaptive_stop.py` + S4 layered-stop) ל-YAML, כדי ש-3 הדרישות (stop/יציאות/חוזים) גמישות. מתחבר ל-stop-anchor design ול-P0-2 (חשיפת r_t1/1R).
