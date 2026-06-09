# NEXT CHAT — MEMS26 Pre-LIVE · המשך מ-2026-05-30

הדבק את הקובץ הזה בתחילת צ'אט חדש. הוא מסכם איפה אנחנו ואיך להמשיך.

## מי אתה ומה הכללים
אתה עוזר ל-Michael להביא את MEMS26 (מערכת מסחר אוטונומית, MES futures) ל-LIVE.
המערכת רצה כ-**SHADOW/paper בלבד** — אין עדיין נתיב הזמנה אמיתי לברוקר.
**כללי-על (CLAUDE.md):** diagnose-first (אמת מול DB/קוד לפני תיקון — הקוד זז הרבה,
אל תתקן מה שכבר תוקן); smallest correct change + regression test; "תוקן"=פקודה+פלט;
מקור-אמת = Sierra (אסור לסנתז/להמציא placeholder); שינוי לוגיקת-מסחר (gate/סף) → אישור Michael.
**Cowork אין לו** API/לוגים/Sierra/venv/commit (נעילת git) → תיקוני קוד שדורשים הרצה/קומיט
נמסרים ל-Claude Code (CC) דרך מגה-פרומפט.

## כלל auto-update (חובה אחרי כל משימה)
עדכן `docs/plans/ROADMAP_TO_LIVE.html` + `docs/plans/STATUS_BOARD.md`: סמן שהושלם, הוסף
פריטים חדשים, רשומת לוג מתוארכת עם finding+fix+ראיה. (גם ב-CLAUDE.md §Reporting Workflow.)

## המסמכים החיים
- `docs/plans/ROADMAP_TO_LIVE.html` — גאנט + צ'קליסט. כל פריט ממוספר (1.1..) ועם **שני סימונים:
  סוכן (Claude) + מיכאל (אישור)**. ביטול סימון "סוכן" = לא תקין.
- `docs/plans/STATUS_BOARD.md` — מקור-האמת (OPEN FOR SUNDAY + לוג מתוארך).

## איפה אנחנו (סעיף 1 — חוסמים)
**מתוקן/אומת (Cowork/CC):** 1.5 TIME_STOP (floor 5min), 1.6 T1 detection (woodies_5min),
1.7 footprint dedup, 1.9 bars_5min TZ (0 future rows), 1.11 TZ/DST (כבר תוקן),
1.13 day_type IB-lock = **fixture drift** (תוקן `test_day_type_ib_live.py`; הקוד תקין — אל
תיגע ב-A4!), 1.3 pre_fire (אומת שנקרא ב-S2/S3/S4), 1.14 status enum (מיפוי קיים).
**⚠️ כל תיקוני CC עדיין UNCOMMITTED (נעילת git).**

**החלטות שננעלו 30/5:**
- §1.8 @5900: שורש = `gateway/trading_gateway.py:25` נתיב DB קשיח → טסטים כותבים ל-DB החי.
  אושר: לסמן rows 844-846 `is_synthetic=1` (גיבוי, לא מחיקה) + תיקון נתיב DB. דוח: `FAKE_5900_SOURCE_2026-05-30.md`.
- §1.15 restart: אושר backfill ברי 5min + load-from-DB ל-opening_type (שורש `day_type_seed.py:111`
  כופה INDETERMINATE). בלי replay/כלל-13:00. תוכנית: `RESTART_RECOVERY_PLAN_2026-05-30.md` v2.

**פתוח — דורש החלטת Michael:**
- §1.2 Gateway canonical (D-093.Q1): המלצה = **New** (`services/trading_gateway/`, W11+W14 RiskValidator).
- §1.16 S2 ספים קבוע→יחסי (ATR): שינוי לוגיקת-מסחר.
- Pipeline 5 (שליחת פקודות לסיארה): **מוקפא לבקשת Michael** — לא לגעת.

## הצעד הבא המיידי
שלח ל-CC את `docs/handoff/CC_MEGA_PROMPT_BLOCKER_SWEEP_R2_2026-05-30.md`, החל מ-R2-1
(commit — פתור נעילת git). R2 מכיל: commit, regression tests, ISO-ts, fixture של
test_day_type.py, api conftest, TPO TZ, CST test, R2-8 (@5900 + נתיב DB), R2-9 (restart recovery).
diagnose-first; הדבק פלט pytest גולמי; עדכן roadmap+status אחרי כל משימה.

## ממתין לשוק חי (ראשון RTH)
1.1 DLL frozen-tail (Phase B, `CC_MEGA_PROMPT_SYSTEM_READINESS_CHECK_2026-05-29_v2.md`),
ואימות חי של תיקוני T1/T2/T6.

## נושא פתוח שנדון: טיפול בחדשות
קיים לוח סטטי קשיח: `backend/v9/services/risk_validator/news_calendar.py` (FOMC/CPI/NFP 2026,
±10min) + `bridge/news_guard.py` + S4 B6NewsWindow (NEWS_EXIT). אפשרויות: A סטטי (קיים),
B feed חיצוני, C מ-Sierra (אם חושפת לוח — לאמת), D היברידי (סטטי כ-fail-safe + השלמה).
המלצה: D. **פתוח:** לאמת ש-S2/S3 מכבדים `is_news_blocked` (כרגע רק S4 ודאי); להחליט חלונות
לפי דרגה (FOMC רחב); להחליט block מול flatten. לאמת אם Sierra חושפת לוח כלכלי.

## אחרי שכל סעיף 1 ירוק → שער SHADOW (P-S0)
UAT 4 צירים על `/cockpit/systems-snapshot` (Quality/Recency/Cardinality/Latency), דוחות אימות
S1/S3, 60 דק' ירוק, sign-off → SHADOW soak ≥10 ימים → DEMO → LIVE.
