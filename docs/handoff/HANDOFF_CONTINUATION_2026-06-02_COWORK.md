# Handoff — Cowork Agent Continuation · 2026-06-02

**מטרה:** שצ'אט Cowork חדש ימשיך **בדיוק מכאן** בלי לאבד הקשר. קרא את זה ראשון.

## מי אתה ומה התפקיד
אתה סוכן בקרת מערכת ל-MEMS26 (מסחר אוטונומי, מצב SHADOW). אתה **לא** כותב את הקוד — **Claude Code (CC)** מממש; אתה מאבחן, כותב פרומפטים ל-CC, ו**מאמת בלתי-תלוי** את עבודתו לפני שמסמנים "בוצע". משתמש = Michael.

## חוקי עבודה (חובה)
1. **כל פרומפט CC פותח ב:** "פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`". (אנטי-טסט-מזויף + Rule 5 + סעיף NOT-DONE חובה.)
2. **verify-before-trust:** אל תאמין לדוחות CC. הצלב מול git/קוד/DB. דרך טובה: הרץ את **פונקציית הייצור ישירות** ב-bash (sandbox: `pip install ... --break-system-packages`; חסר sqlalchemy → להריץ פונקציות בודדות, לא pytest מלא).
3. **תוויות החלטה:** כל פריט נושא `D-XXX` ומתועד ב-`docs/plans/DECISION_LEDGER.md` (תווית · החלטה · סיבה · נקודת-החלטה). זה מקור-האמת להחלטות.
4. **roadmap auto-update:** אחרי כל שינוי-מצב — עדכן `docs/plans/STATUS_BOARD.md` (root→fix→verification) + `docs/plans/ROADMAP_TO_LIVE.html`. **אל** תציג present_files לקבצי-מעקב (ledger/status/roadmap/CLAUDE.md) — אשר בטקסט. כן הצג present_files לפרומפטים/דוחות חדשים.
5. **shadow-first:** observers/דגלים לפני נגיעה ב-live; strategic-stop + אישור Michael לפני כל שינוי שמשפיע על ירי live/risk.

## מצב ההחלטות (מ-DECISION_LEDGER)
- **D-WDIAG** (Woodies relabel) — 🟢 מומש+מאומת בקוד/טסט (`trend_relabel.py`, נקרא ב-`woodies_system.py:279`, טסט אמיתי דרך `evaluate_bar`, commit `c43acc6`). דגל `S4_EXTREME_TREND_RELABEL` **ON ב-shadow runtime** (אומת ב-flag audit). **🟡 הפריט החי עכשיו:** כדי להשוות A/B חסר שדה `trend_original` (CC הציע שורה אחת ב-`trend_relabel.py` — ממתין אישור Michael + בדיקת schema של `WoodiesBar`). + ממתין לבר ±200 ב-RTH להוכחת shadow חיה. Stage "להדליק live קבוע" = אישור נפרד.
- **D-S1DYN** (סוג-יום דינמי) — 🟢 IMPLEMENTED-SHADOW (Phase 0-2, `caeb984`/`df16d03`/`9d8ff30`). דגל `S1_DYNAMIC_RECLASS`. ממתין: אימות יום-trend מלא ב-RTH (אתמול הגיע רק ל-Variation). Stage 3 (חיווט ל-Auth Table live) = אישור נפרד, דורש ~10 ימי shadow.
- **D-RVX** (Reactive) — ✅ אושר, ❌ **לא בוצע**. הכי דחוף פונקציונלית: S2 לא הפיק פלט אי-פעם (0 setups all-time). פרומפט מוכן: `CC_MEGA_PROMPT_REACTIVE_CHECK_FIX_DISPLAY_2026-06-01.md` (Phase 0 = אבחון למה S2 מת → 3 וריאציות observers → תצוגת build_status אור-ירוק + טריידר).
- **D-OBS** (Build Status observability) — 🟢 בוצע (`691c99b`), read-only.
- **D-RDY** (readiness gate) — ✅ אושר (הרחבת build_status), משתלב ב-D-OBS.
- **D-S3MUTE** — ✅ אושר: להשתיק S3 עד ש-1/2/4 יציבים. מנגנון: דגל `S3_MUTE=1` ב-plist. **פעולה ל-CC להחיל.**

## משימות פתוחות (task list)
- **#14** סוכן אבחון אוטומטי כל 30 דק' ב-RTH (16:30–23:00 IL) — להפעיל **אחרי** ש-D-OBS חי. scheduled task, read-only diagnostics ("למה כל תבנית לא ירתה").
- **#15** סוכן בדיקת סוף-יום (זרימת מידע) — אחרי הקודמים.

## הצעד הבא המיידי
Michael שאל "האם זה נכנס לירי ונוכל להשוות". התשובה: הדגל ON ב-shadow, HFE ייכנס כ-shadow trade, **אבל** בלי `trend_original` אי-אפשר לדעת אילו fires נבעו מה-relabel. → **להחליט עם Michael:** לאשר את שורת `trend_original` (+schema check) כדי לאפשר השוואה A/B. אם מאשר → פרומפט CC קצר (לפי החוזה, עם טסט שמוכיח שהשדה מגיע ל-cross_context).

## קבצים מרכזיים
- החלטות: `docs/plans/DECISION_LEDGER.md` · מצב: `docs/plans/STATUS_BOARD.md` · roadmap: `docs/plans/ROADMAP_TO_LIVE.html`
- חוזה CC: `docs/handoff/CC_HANDOFF_CONTRACT.md`
- דוחות CC אחרונים: `D_WDIAG_RELABEL_FLAG_AUDIT_2026-06-02.md` · `D_WDIAG_WOODIES_AUDIT_2026-06-01.md` · `D_S1DYN_SHADOW_RECLASS_2026-06-01.md` · `INDEPENDENT_VERIFICATION_2026-06-02.md`
- קוד מפתח: `backend/v9/systems/woodies/{woodies_system.py,trend_relabel.py,decision_tree.py}` · `backend/v9/systems/day_type/{state_machine.py,shadow_reclass.py}` · `backend/v9/systems/five_min/five_min_system.py` · `backend/v9/systems/build_status/`
