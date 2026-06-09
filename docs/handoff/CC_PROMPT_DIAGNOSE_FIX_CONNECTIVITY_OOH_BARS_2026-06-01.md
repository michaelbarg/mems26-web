# CC PROMPT — אבחון ותיקון: חיבור + גשר + נרות מחוץ ל-RTH

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael — אבחן ותקן את המערכת) · **מצב:** SHADOW בלבד
**משמעת:** diagnose-first · Rule 5 (פלט גולמי לכל קביעה) · smallest correct change · regression לכל תיקון.

## ראיות מהדאשבורד (Cowork צילם 2026-06-01 ~10:58 IL / ~03:58 ET)
- **DISCONNECTED** משמאל-למעלה (WS) **וגם** מימין-למעלה. Woodies CCI panel: "Disconnected — retrying…". → ה-frontend עולה ומרונדר, אבל **לא מצליח להגיע ל-backend**.
- **CLOSED · pre-open** — מחוץ ל-RTH (Globex אולי פתוח, אך המערכת מסמנת CLOSED).
- **Y IB dll_missing** — ה-DLL לא מייצא.
- **SHADOW 0t · $0 · 0 trades · Day 1/30** — DB ריק.
- Badge **"1 Issue"** משמאל-למטה.

## המטרות של Michael (שורה תחתונה)
1. **אפס באגים** — לאבחן ולתקן את ה-DISCONNECTED + dll_missing + ה-Issue.
2. **לקבל נרות גם מחוץ לשעות מסחר** — fallback מטבלת DB (נרות אמיתיים שמורים).
3. **לוודא שהגשר עובד ומקבל מהכל** (כל ה-streams).

---

## משימה A · אבחון + תיקון חיבור (diagnose-first)
1. בדוק האם ה-backend רץ: `curl -s localhost:8000/health` + `lsof -i :8000` + `lsof -i :3000`. הדבק פלט. (CLAUDE.md: בדוק listeners לפני הפעלה; אל תכפיל instances.)
2. אם ה-backend לא רץ → זו כנראה סיבת ה-DISCONNECTED. דווח, ואז העלה דרך `scripts/start_all.sh` (Michael ביקש לתקן). אם רץ אך ה-WS מנותק → אבחן את ה-WS endpoint (URL/CORS/handler) ב-frontend↔backend. הדבק ראיה.
3. אבחן את **"1 Issue"** (פאנל ה-issue / קונסול / `/tmp/backend.log`) ואת **dll_missing** (DLL לא טעון/לא מייצא? בדוק `~/SierraChart_Data/v9_export/` — האם יש קבצי JSON טריים? מתי עודכנו?).
4. תקן את הבאג(ים) שמונעים את החיבור. smallest correct change + regression. אל תיגע ב-polling floors (CLAUDE.md).

## משימה B · גשר מקצה-לקצה
1. אמת שה-bridge רץ ודוחף ל-`localhost:8000` עבור **כל** ה-streams: `5min`, `woodies_5min`, footprint (`tick_reversal_15/12`). הדבק health/לוג per-stream (FRESH/STALE/DEAD) — `scripts/sot_health.py --strict` או ה-bridge inspector.
2. לכל stream שלא מגיע → אבחן (DLL? מנוי? path? export dir?) ותקן.
3. ודא **local-only** (CLAUDE.md): ה-bridge דוחף רק ל-localhost — אם יש `API push FAILED to https://...` עצור ודווח.

## משימה C · נרות מחוץ ל-RTH (display fallback מ-DB)
היום, מחוץ ל-RTH / כשאין feed, התצוגה ריקה. הוסף **נתיב תצוגה** בלבד:
1. כשאין נרות חיים טריים, endpoints של הצ'ארט/levels יחזירו את ה-**session האחרון השמור** מ-DB (`v9_bars_5min` + woodies + footprint), עם **badge ברור "LAST SESSION · <תאריך>"** והתצוגה read-only.
2. ⚠️ **קריטי — בטיחות + source-of-truth:**
   - זה **תצוגה בלבד**. **אסור** שנרות היסטוריים/stale יזינו את מערכות הירי או את `BarLevelDetector` כאילו חיים. הירי נשאר gated על נתון חי/RTH.
   - **אל תסנתז** נרות. רק להציג נרות אמיתיים שמורים, מסומנים כהיסטוריים (CLAUDE.md §Honest failure).
   - הצג בבירור מאיזה תאריך/שעה ה-session, כדי שלא יתבלבל עם חי.
3. אם תרצה — דגל `OOH_DB_FALLBACK` (default ON לתצוגה) כדי שניתן יהיה לכבות.

---

## פלט מצופה
`docs/reports/DIAGNOSE_FIX_CONNECTIVITY_OOH_2026-06-01.md`: לכל משימה — פקודות + פלט גולמי (health, lsof, bridge log), אבחנת שורש לכל בעיה, diff התיקון, פלט regression. עדכן `STATUS_BOARD.md` (finding→fix→evidence, Rule 5).

**שערים:** diagnose-first — דווח שורש לפני תיקון. נרות היסטוריים = תצוגה בלבד, לא מזינים ירי (strategic-stop אם המימוש עלול להפעיל ירי על stale). אפס שינוי order/risk/sizing. אל תיגע ב-threads האחרים (calibration wiring / Auth V2 / D-094). אם נדרשת הפעלת שירותים — בדוק listeners קודם, ודווח.
