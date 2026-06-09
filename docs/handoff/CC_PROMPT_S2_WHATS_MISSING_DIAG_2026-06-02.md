# CC Prompt — S2 "מה חוסר": אבחון host-only (read-only) · 2026-06-02

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**מאת:** Cowork diagnostic (read-only) → **אל:** Claude Code
**סוג:** אבחון בלבד — **אפס שינוי קוד/DB/דגל/שירות.** כל תיקון הוא strategic-stop לאישור Michael.
**הקשר:** Cowork מיפה את חוסמי S2 (REACTIVE + INITIATIVE) מ-DB+קוד, אבל **גייט-0 (COT/AMT)
והדגל/endpoint החיים לא ניתנים לאימות מה-sandbox** (אין גישה ל-`~/SierraChart_Data/` ולא
ל-env של התהליך). מטרת הפרומפט: לסגור בדיוק את הנעלמים האלה על ה-host. משלים את
`CC_PROMPT_S2_REACTIVE_CANFIRE_2026-06-02.md` (המימוש) — **זהו הצעד diagnose-first שלפניו.**

> משמעת Pre-LIVE (CLAUDE.md): diagnose-first · read-current-code · Rule 5 (command + raw
> output, לא assertion) · no silent failures · NOT-DONE section חובה · אל תפעיל שירות אם כבר
> רץ; אם ה-backend כבוי ואתה מעלה לבדיקה — 127.0.0.1 בלבד, בדוק listeners קודם, וכבה אחרי.

עובדות מאומתות (Cowork, raw) שאתה מאשש מחדש, לא מקבל על אמון:
- `v9_five_min_setups` = 0 rows all-time. הגייט החי ל-REACTIVE = `b2_vol ≤ b1_vol*0.10`
  (`five_min_system.py:515`); הדגל `S2_VSA_VOLUME` כבוי בקונפיג האתחול (`:498,512`).
- שתי התבניות מתות מיד אם `COT/AMT=None` (`:488` REACTIVE, `:597` INITIATIVE).
  מקור: `cot_amt.py` → `/Users/michael/SierraChart_Data/v9_export/cumulative_delta.json`.
- funnel היום (Cowork): REACTIVE נחסם ב-`b2_drop`; INITIATIVE נחסם ב-`b1_expansion`
  (רצועה 1.5–2.0×ATR); `lookback_quiet` co-blocker כש-b2 מורפה.
- נפחי close מנופחים 15:15–16:15 (`v9_bars_5min`): 980001/960000/950000…, `is_synthetic=0`,
  all-time MAX=980001.

---

## Phase 0 · גייט-0: COT/AMT — הנעלם הקריטי (host-only)
**שאלה:** האם `cumulative_delta.json` קיים, טרי, מתפרסר, ומחזיר COT/AMT **לא-None** עכשיו?
אם לא — S2 מת לפני כל לוגיקת בר, וכל כיול סף חסר משמעות.
- בדוק קיום+טריות הקובץ: `ls -l ~/SierraChart_Data/v9_export/cumulative_delta.json` +
  גיל mtime מול עכשיו.
- הרץ את קוד-הייצור עצמו (לא העתק): ייבא `from backend.v9.systems.five_min.cot_amt import
  read_cumulative_delta, compute_cot, compute_amt` והדפס `read_cumulative_delta()` (keys, len
  של `points`/`bars`), `compute_cot(pts)`, `compute_amt(pts)`.
- בדוק את ה-fallback: כש-footprint מושבת (`FOOTPRINT_DISABLED`), האם `_footprint_state()`
  מחזיר cot/amt או ריק? כלומר — אם הקובץ חסר, האם יש בכלל מקור?
- **Acceptance (בינארי):** קובע `COT/AMT resolvable = True/False` עם raw. אם False → 🔴 זה
  ה"מה חוסר" המרכזי; strategic-stop לפני כל המשך (bridge/export fix נפרד).
- **פקודת אימות:** הדבק את פלט ה-`read_cumulative_delta()` + compute_cot/amt.

## Phase 1 · הדגל החי + env של התהליך
- `S2_VSA_VOLUME` בתהליך ה-backend החי: בדוק את env של ה-PID (`ps eww <pid>` /
  `/proc`-equivalent ב-mac: `ps -E -p <pid>`), או דרך endpoint debug אם קיים. קבע אם הגייט
  החי בפועל = 0.10 או VSA.
- **Acceptance:** קובע ערך `S2_VSA_VOLUME` אפקטיבי ב-runtime (לא רק בקונפיג). raw של ה-env.

## Phase 2 · pattern-status חי ל-S2 (אם backend למעלה)
- `curl -s 'http://localhost:8000/api/v9/build/pattern-status?systems=five_min'` → לכל
  pattern של S2: `status`, `reason`, `blockers[]`, `fired_today`, `data_freshness`.
- **Acceptance:** הדבק את ה-JSON של `five_min`. אם backend כבוי → "NOT-DONE: backend down"
  (אל תעלה רק בשביל זה אלא אם נדרש ל-Phase 0/3).

## Phase 3 · funnel דרך גלאי הייצור (anti-tautological, B1)
- ייבא והרץ את `_detect_reactive` / `_detect_initiative` האמיתיים (לא העתק) על ברי
  `v9_bars_5min` של היום (read-only), עם COT/AMT/belly **אמיתיים** (מ-Phase 0). ספור
  terminated_at לכל גייט, לשני הכיוונים (LONG+SHORT) ולשתי התבניות.
- אשש/הפרך: REACTIVE binding=`b2_drop`, INITIATIVE binding=`b1_expansion`, ו-`lookback_quiet`
  co-blocker. ציין כמה כניסות היו נוצרות **עם COT/AMT אמיתי** (Cowork הניח pass-through).
- **Acceptance:** טבלת funnel per-pattern/direction + מספר כניסות אמיתי. *"if reverted →
  RED because ___"* אם מחליפים את הקריאה לקוד-ייצור בהעתק.

## Phase 4 · מקור הנפחים המנופחים (Source-of-Truth)
- הצלב את נפחי 15:15–16:15 ב-`v9_bars_5min` מול `~/SierraChart_Data/v9_export/` — אמיתיים
  מה-DLL או תוצר אגרגציה/ingestion? `bar_aggregator_5min.py:155` חוסם tick ל-10000, אז ערכי
  ~1M מגיעים מנתיב אחר — אתר אותו.
- **Acceptance:** קביעה "ground-truth = X" עם raw, או "NOT-DONE: אין גישה". אם סינתזה →
  strategic-stop (CLAUDE.md §Source-of-Truth).

---

## תבנית דוח חובה (חלק C)
1. טבלת phases: `Phase · Status (DONE/PARTIAL/NOT-DONE) · Evidence (command+raw output) · Deviation`.
2. *"if reverted → RED because ___"* לכל טסט/funnel שמייבא קוד-ייצור.
3. סעיף **NOT DONE / DEVIATIONS** (גם אם "none").
4. **VERDICT — "מה חוסר ל-S2"**: רשימה ממוספרת לפי סדר עוצר, כל פריט עם raw, ועם תיוג
   strategic-stop / blocker-נתונים / observability. (העיקר: האם גייט-0 COT/AMT עובר — כן/לא.)

## אסור לגעת
- אפס שינוי בקוד/דגל/DB/threshold. אפס נגיעה ב-DB write-path (`safe_writer`). footprint נשאר
  מושבת. אם נדרש backend לבדיקה — 127.0.0.1, בדוק listeners, כבה אחרי. אבחון בלבד.
