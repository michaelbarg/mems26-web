# Cowork Handoff — Continuation | 2026-06-03 (EOD)

**למי שקורא (Cowork chat הבא):** אתה ה-orchestrator + ה-verifier הבלתי-תלוי של MEMS26. CC (Claude Code, על ה-Mac) מבצע; אתה כותב פרומפטים, מצליב בלתי-תלוי, ומעדכן בורדים. אתה **לא** יכול לשלוט ב-backend/launchctl/Sierra של ה-Mac מה-sandbox — רק קבצים + bash מבודד (אין `sqlite3` CLI; השתמש ב-`python3`; ה-DB ב-`data/mems26_local.db`).

## 0 · הנחיות-על (לקרוא קודם)
- `CLAUDE.md` (במיוחד §DB Write-Safety שעודכן היום, §Pre-LIVE Discipline, §Source-of-Truth).
- `docs/handoff/CC_HANDOFF_CONTRACT.md` — כל פרומפט CC מפנה אליו; טסטים אנטי-טאוטולוגיים + Rule 5 (ראיה גולמית, לא טענה) + סעיף NOT-DONE חובה.
- זיכרון: roadmap auto-update אחרי כל משימה · אין present_files לקבצי-מעקב (אישור בטקסט) · wire-full-pipeline (לא partial) · **work-by-system-needs** (אמת data-flow per S1/S2/S3/S4) · don't re-add get_db lock · integrity רק backend-כבוי · Sierra=SoT (לא לסנתז study fields).

## 1 · איפה אנחנו (2026-06-03)
**✅ נסגר ואומת (commits):**
- **DB root fix** — השורש היה כתיבות ORM/raw לא-מסורלות (טענת 2/6 "get_db lock" הייתה שגויה — בוטל, deadlock). תיקון: כל כותב חם→`safe_writer` (`d38444d`) · raw→mode=ro (`edab3c0`) · rebuild + **soak 600ש'/21,726 דחיפות/0 שגיאות → integrity backend-כבוי=ok** (`9255bfa`). Cowork אימת: ההשחתה 325707 נעלמה. tick_reversal מושבת.
- **B1** — bypass lookback ב-**שני** האתרים + 4 טסטים (`825972f`).
- **session filter נרות** → ET (`361e5bd`).
- **sc_study v9.4.5-wc-fix** — committed (`816dd1a`): SWI local-computed, TrendUp SG4, bars-from-chart12 (מבטל frozen-tail). חי מאז 2/6. אומת Cowork מול קוד.
- **CLAUDE.md §DB Write-Safety** — תוקן doc-drift (Cowork).

**🔄 בתהליך:** **B4 fix** (`CC_PROMPT_B4_FIX_2026-06-03.md`) — נשלח ל-CC, **ממתין לדוח**. כולל: טבלה אחת=RTH (time-gate 09:30-16:00 ET) · CVD גם מ-RTH (מיושר, פותר C2) · is_synthetic לברים מנופחים · **אימות חיבור שדות-הסטאדי per-system** (Sierra export ID:10 Inputs) · בדיקת פער-גרסה v9.4.3-name מול v9.4.5.

**🔴 לא קרה היום:** יום SHADOW לא נאסף — RTH (09:30 ET) נפתח לפני ש-B4 הסתיים, **וה-feed תקוע** (בר אחרון 07:15 UTC/03:15 ET, ~6h ישן → backend/bridge לא קולט). אין מסחר אמיתי בכלל (Pipeline 5 לא נבנה — SHADOW/paper בלבד).

## 2 · מה צריך לבדוק (אימותים פתוחים — חלק D)
1. **דוח B4 של CC** כשיחזור — הצלב: time-gate עובד (push מחוץ ל-RTH לא נכתב), `MAX(volume) WHERE is_synthetic=0` שפוי (לא 1M), VSA rolling_avg מסנן is_synthetic, סטאדי לא נשברו, טסט אנטי-טאוטולוגי litmus.
2. **פער-גרסה** — שם study בצ'ארט="v9.4.3-chart5" מול V9_VERSION="v9.4.5". לוודא איזה build באמת רץ על צ'ארט המסחר (אם v9.4.3 ישן → S4/SWI/trend על מיפוי שגוי). סביר literal מיושן, אבל לאמת.
3. **🔴 feed תקוע** (task #10) — backend חי? bridge דוחף? Sierra מחובר? נתונים מתקדמים? תנאי מקדים ל-SHADOW.
4. **woodies_5min ts=2025-01-01** (task #9) — תוצר rebuild? שלא מבלבל S4.

## 3 · החלטות שנעולות (אל תפתח מחדש)
- DB: safe_writer-only, **get_db לא נועל** (deadlock — אל תחזיר). journals-isolation דחוי (Phase 3).
- נרות **היום**: טבלה אחת = RTH, time-gated; CVD גם מ-RTH. **טבלה רציפה 24h = משימה עתידית** (#11).
- sc_study v9.4.5 = אומץ (committed). B2/B3 **ללא שינוי**. B1 = bypass lookback כש-VSA.
- B4 = A+D + is_synthetic (אושר). תיקון-שורש מלא על פני מהיר (העדפת Michael).
- עיקרון: **עובדים לפי המערכות והצרכים שלהן** (אמת per-system).

## 4 · המשימות הבאות (task list #1-#11)
- **נתיב ליום SHADOW נקי:** #10 לוודא feed/backend/bridge קולטים (חוסם) → #2 רענון פרומפט SHADOW → #3 pre-trade verify (readiness=READY, S2 יורה בשני נתיבים, integrity חי) → #4 הרצה+ניטור → #5 EOD+integrity.
- **ניקוי (לא חוסם):** #6 ~5 כותבי-ORM תדר-נמוך→safe_writer · #7 Phase 3 journals · #8 D1 ~9 דגלים קפואים · #9 woodies ts.
- **עתידי:** #11 טבלה רציפה 24h · **Pipeline 5 / Sierra order routing = חוסם-LIVE אמיתי** (בלי זה אין מסחר אמיתי).

## 5 · החלטות פתוחות ל-Michael
- D1: להשלים המרת ~9 הדגלים או לקבל PARTIAL (latent, plist מציל).
- האם VAL כ-target מפורש ל-S2 (כרגע target=day-type R-multiples/POC, לא VAL ישיר — שאלת Michael על "VAH short→VAL").

## 6 · S2 — תקציר ירי SHORT (לשאלת Michael "VAH short→VAL")
S2 יורה SHORT דרך REACTIVE (היפוך בהתנגדות) / INITIATIVE (פריצה). "מ-VAH"=גייט sr_proximity (VAH מבין PDH/VAH/IBH). "ל-VAL"=**לא target ישיר**; target מ-targets_table לפי day-type (T1=1R, T2=POC/extreme/2.5R...). REACTIVE SHORT gates: b1 עולה+vol>0 · b2_drop (VSA) · b3 יורד+belly · b4 סוגר<b3.low · COT<AMT · lookback_quiet (bypass כש-VSA) · belly_ratio_ok · קרבה ל-VAH. +quality/cot_amt/chop/pre_fire/RTH/readiness.

## 7 · פרומפטים שנוצרו היום (docs/handoff/)
`CC_PROMPT_B4_FIX` (פעיל) · `CC_PROMPT_B4_VOLUME_ROOT_DIAGNOSE` · `CC_PROMPT_SCSTUDY_V945_DIAGNOSE` · `CC_PROMPT_DB_ROOT_FIX_FULL` · `CC_PROMPT_SHADOW_DAY_OPS` (חלקית מיושן — שער DB כבר עבר) · round2/round3 fixes · `CC_PROMPT_DESKTOP_WORKLIST_FIXES`. דוח: `docs/reports/CC_DB_ROOT_FIX_AND_SCSTUDY_DIAGNOSE_2026-06-03.md`. מקורות: `docs/plans/STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html`.
