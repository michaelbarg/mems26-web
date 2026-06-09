# Handoff — Cowork Agent Continuation · 2026-06-02 PM

מטרה: שצ'אט Cowork חדש ימשיך מכאן בלי לאבד הקשר. קרא ראשון.

## מי אתה
סוכן בקרת-מערכת ל-MEMS26 (מסחר אוטונומי, מצב SHADOW). אתה **לא** כותב קוד — Claude Code (CC)
מממש; אתה מאבחן, כותב פרומפטים ל-CC, ו**מאמת בלתי-תלוי** (verify-before-trust) לפני "בוצע". משתמש = Michael.

## חוקי עבודה (חובה)
1. כל פרומפט CC פותח ב: "פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`".
2. **verify-before-trust:** אל תאמין לדוחות CC — הצלב מול git/קוד/DB (הרץ `sqlite3`/python על `data/mems26_local.db`, grep, git log). היום זה תפס 3 דוחות "GO" שגויים.
3. תוויות החלטה ב-`docs/plans/DECISION_LEDGER.md`. roadmap auto-update: אחרי כל שינוי-מצב עדכן `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` (root→fix→verification). אל תציג present_files לקבצי-מעקב.
4. shadow-first; strategic-stop + אישור Michael לפני שינוי שמשפיע על ירי/risk.

## ✅ ההישג הגדול היום: ה-DB corruption נסגר מהשורש
- **שורש אמיתי (אחרי כל היום):** כתיבות **SQLAlchemy ORM** עקפו את ה-write-lock (לא רק חיבורי `sqlite3.connect` גולמיים). 
- **fix:** `get_db()` מקבל את `_write_lock` (`f5568a2`) → צומצם ל-commit-only + `RLock` (`ec9fe97`, פתר deadlock/חניקה). + footprint **מושבת זמנית** (`FOOTPRINT_DISABLED`) + `safe_writer.py` (writer מסורל) + VACUUM שניקה carried-over B-tree corruption מהגיבוי.
- **אומת (Cowork בלתי-תלוי):** integrity backend-כבוי=ok + קריאות נקיות תחת כתיבה חיה ב-16:57/17:03/17:05 + latency health 45-55ms. **GO.**
- ⚠️ הדוח `docs/reports/CC_DB_WRITE_SAFETY_REPORT_2026-06-02.md` היה **מיושן** (commit 0afe147, soak 89 שניות שהופרך) — אם עדיין לא עודכן, התעלם ממנו.

## החלטות Michael היום
- **footprint מושבת זמנית** עד כמה ימים נקיים של 1/2/4. (thread נפרד אחר כך.)
- **S2:** שלוש הווריאציות (A_VSA / B_RVOL / C_STRICT) יורות חי בשדואו, **כל fire מתויג** variant (+ ב-dedup key) להפרדה.
- **S1:** סיווג-מחדש חי (`S1_LIVE_RECLASS`) — **לא משנה את ה-Auth Table**, רק מעדכן day_type והבחירה נעשית **מהטבלה הקיימת** (select-from-existing). +Michael ביקש שה-Auth Table הפעילה **תוצג בעמוד** (Build Status) ותודגש כשמשתנה.

## מצב המערכת עכשיו (17:08, RTH פתוח עד 23:00 IL)
- ✅ **S4 (Woodies)** — יורה (3 trades/9 signals היום). תקין.
- ❌ **S2** — עדיין **0** (`five_min_setups/state=0`) למרות הדגל → **באג פתוח באבחון** (האם הדגל ON ב-runtime? אף וריאציה לא עוברת? ברים מגיעים?).
- ⚠️ **imbalance** — `MAX(ts)` תקוע על 04:40 גם ב-RTH פתוח → **נתיב כתיבה שבור** (באג פתוח).
- 🟡 **S1** — `S1_LIVE_RECLASS` מחווט; צריך לאמת שבאמת מחליף day_type חי.
- 🔇 **S3** — מושתק (footprint off).

## פרומפטים שמחכים / פתוחים
- **תיקון הבאגים (נשלח ל-CC):** S2 לא יורה + imbalance תקוע + אימות S1 reclass + S3 לא חדש. (diagnose-first, לא לגעת ב-DB write-path.)
- **`CC_PROMPT_DB_TRUE_ROOT_FIX_2026-06-02.md`** — נסגר (השורש תוקן); נשאר Phase C (בידוד footprint/tpo/tick ל-store נפרד FIFO) **נדחה** — בטוח כרגע כי הכל מסורל.
- **Trades UX redesign** — פרומפט מוכן ומאומת (כל השדות חוזרים מה-endpoint); להריץ ב-**CC שני** במקביל (frontend-only). מקור עיצוב: `UX_AUDIT_TRADES_BUILD_2026-06-02.md` + `UX_UI_LAYOUT_SPEC_TRADES_BUILDSTATUS_2026-06-02.md`.
- **Build Status** — global_gates + readiness banner נחתו (`0240cab`). נשאר: פאנל Auth Table פעילה (בקשת Michael).
- **MEGA phases פתוחים:** #19 streams (imbalance/tpo/cumulative) · #20 S2 חי · #21 S1 חי · #22 S4 אימות · #17 backfill היסטוריה מ-Sierra · #23 readiness→READY.

## סוכן מעקב (אני מנהל)
- `mems26-rth-monitor` — scheduled, כל ~30 דק' ב-RTH (16:30-23:00 IL, ימים א-ה), read-only: בריאות DB, מה ירה, day-type, וריאציות S2, טריות streams, חריגות. (לאמת/לכוון קצב cron אחרי ריצה ראשונה.)

## קבצים מרכזיים
- ledger: `docs/plans/DECISION_LEDGER.md` · status: `docs/plans/STATUS_BOARD.md` · roadmap: `docs/plans/ROADMAP_TO_LIVE.html` · חוזה: `docs/handoff/CC_HANDOFF_CONTRACT.md`
- DB: `data/mems26_local.db` (הצלב מולו תמיד) · safe_writer: `backend/v9/db/safe_writer.py` + `session.py:get_db()`
- commits מפתח היום: `f5568a2`+`ec9fe97` (DB root fix) · `1c28df7` (S3MUTE) · `401d526` (S4) · `3e2f785`+`0240cab` (D-RDY+frontend) · `1e077fa` (trend_original) · `6b0f401`+`fc93317` (S2 3-variant+tags) · `e5ad951`+`f65f6d7` (footprint off + S1 reclass)
