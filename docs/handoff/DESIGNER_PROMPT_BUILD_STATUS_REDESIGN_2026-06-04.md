# Designer Prompt (צ'אט חדש) — מעצב עמוד Build-Status: הדמיה + הכנה ליישום · 2026-06-04

**התפקיד שלך:** אתה **המעצב** של עמוד ה-Build-Status ב-MEMS26 (מערכת מסחר אוטונומית). מטרה: לעבור על מה שקיים,
ולהפיק **הדמיה (mockup) + מפרט מוכן-ליישום** לעמוד Build-Status חדש שיהיה ברור לעבודה חכמה ולהסקת-מסקנות.
**אתה לא מממש קוד-פרודקשן ולא נוגע ב-backend/risk-logic** — אתה מעצב ומכין ליישום.

## מה זה Build-Status (ההקשר)
עמוד שמראה, לכל מערכת-מסחר (S1–S6), את **עץ-ההחלטה** שלה בזמן-אמת: למה תבנית "armed/blocked/fired", ומה חוסם.
השלבים הקנוניים פר-מערכת: **SOURCE → INPUT → GATE → DETECTION → TARGETS/STOP**, + שערים גלובליים + readiness.
המערכות: S1 Day-Type (observer) · S2 5-Min Patterns (firing) · S3 Footprint (firing, מושבת) · S4 Woodies CCI (firing) ·
S5 TPO (observer) · S6 Killzone (gate).

## מה כבר קיים (סקור קודם — read-only)
**שני משטחים:**
- **חדש (התחל מכאן):** `frontend/v9/src/v9/components/build_tree/BuildTreeView.tsx` (route `/build`, `app/build/page.tsx`) — עיצוב-מחדש כעץ-החלטה.
- **ישן (מועמד להחלפה):** `frontend/v9/src/v9/components/build_status/BuildStatusTab.tsx` (+ `SystemSection`, `ReadinessHeader`) — מותקן בדאשבורד.
- **רכיבים משותפים (נשמרים):** `PatternRow`, `ComponentTable`, `StatusPill`, `types.ts` בתיקיית `build_status/`.

**מסמכי-עיצוב קיימים (קרא לפני שמתחילים):**
- `docs/plans/BUILD_STATUS_REDESIGN_MOCKUP.html` — ה-mockup הנוכחי של העיצוב-מחדש.
- `docs/plans/BUILD_STATUS_COMPONENT_AUDIT.md` — **אודיט מלא: לכל מערכת, מה האפיון דורש מול מה שמוצג ומה חסר.** זה מפת-הדרך שלך.

**נתונים + שפה-עיצובית:**
- Hook: `frontend/v9/src/v9/hooks/useBuildStatus.ts` · Endpoint: `GET /api/v9/build/pattern-status` (`backend/v9/api/v9/build_status_routes.py`).
- inspectors: `backend/v9/systems/build_status/` (day_type/woodies/s2/bridge/aggregator — קוראים מ-Postgres).
- Tokens: `frontend/v9/src/v9/design/tokens.ts` (השתמש בהם לעקביות).

## הפערים שהאודיט מצא (תכנן את העיצוב לפתור אותם)
- **P0:** 2 שערים גלובליים חסרים מהתצוגה — `pre_fire_validator` (7 בדיקות) ו-`risk_checks` (תקרות LIVE: $250/יום, 5 עסקאות, 2 חוזים, חיתוך 14:30 ET, עצירה אחרי 2 הפסדים). + **שלב TARGETS/STOP חסר ב-S2/S4/S3** (stop/1R/T1-T3/חוזים/time-stop). + **Day-Type Matrix verdict** ל-S4 (תבנית ❌ ליום נראית כמו ✅).
- **P1:** S6 Killzone כשער אמיתי · S/R+COT/AMT כשערים אמיתיים ל-S2 · anti-patterns+A7 ל-S4 · freshness ל-3 קבצי Sierra.
- **P2:** חיווט S5 TPO · pre-open context ל-S1 · באנר "מושבת" ל-S3.
(פירוט מלא + ציטוטי קוד ב-`BUILD_STATUS_COMPONENT_AUDIT.md`.)

## עיקרון-ברזל (source-of-truth, CLAUDE.md Rule 1)
עצב כך שהעמוד יציג **רק שדות שה-backend פולט**. שדה שה-backend עדיין לא מספק (TARGETS/STOP, Day-Type Matrix, S5/S6,
שערים גלובליים) → **placeholder "ממתין ל-backend", לעולם לא לסנתז ב-frontend.** סמן בבירור מה "חי" מול "ממתין ל-backend".

## תוצרים (deliverables)
1. **הדמיה (mockup):** קובץ HTML עצמאי בסגנון `BUILD_STATUS_REDESIGN_MOCKUP.html` (ו/או הדמיה אינטראקטיבית inline) שמראה את
   העמוד החדש — עץ-החלטה פר-מערכת עם 5 השלבים + שערים גלובליים + readiness, כולל מצבי armed/blocked/fired/disabled.
2. **מפרט מוכן-ליישום** `docs/plans/BUILD_STATUS_REDESIGN_SPEC_2026-06-04.md`: מבנה-קומפוננטות, מה כל פאנל מציג, אילו שדות
   כבר קיימים (מ-`/api/v9/build/pattern-status`) מול אילו **חסרים ב-backend**, ומיפוי שלב→שדה.
3. **gap-list ל-backend:** רשימה מסודרת של מה ש-inspectors/endpoint צריכים לחשוף בנוסף (P0→P2) — כקלט לפרומפט-מימוש backend.
4. **המלצת cull:** אם העיצוב-מחדש מחליף את הישן — אילו קבצים למחוק (`BuildStatusTab`/`SystemSection`/`ReadinessHeader`),
   מה לשמר (למשל אם רוצים את ה-ReadinessHeader), והאם Build יחיה ב-`/build` בלבד או מורכב בדאשבורד.

## Invariants
read-only · **לא לממש קוד-פרודקשן ולא לגעת ב-backend/risk-logic** · source-of-truth (חסר = "ממתין ל-backend", לא סינתזה) ·
localhost · עקביות עם `design/tokens`. Michael מאשר את ההדמיה לפני מימוש. כל שינוי backend = פרומפט נפרד לאישור.
