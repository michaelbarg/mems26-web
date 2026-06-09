# Cowork Handoff — צ'אט הבא (2026-06-08 ערב)

אתה (Cowork הבא): orchestrator + verifier בלתי-תלוי של MEMS26. CC מבצע על ה-Mac;
אתה כותב פרומפטים, מצליב (Rule 5: פקודה+פלט גולמי), מעדכן בורדים, ומתקן ישירות.
**קרא קודם `CLAUDE.md` (§Index קודם! `backend/main.py`≠`backend/v9/main.py`) + הזיכרון.**

## 0 · מקור-אמת + פרוטוקולים
`CLAUDE.md` · `CC_HANDOFF_CONTRACT.md` · `CC_VERIFICATION_PROTOCOL.md`.
בורדים: `docs/plans/STATUS_BOARD.md` (source-of-record) · `ROADMAP_TO_LIVE.html` ·
`docs/reports/MEMS26_ISSUES_REGISTER.md`. ה-SPEC: `MEMS26_MASTER_TRADE_SPEC_ONE_TABLE.xlsx`.

## 1 · מה נסגר היום (אומת חי, Rule 5)
- **תיקון-T3** (4d79a2d+0be56ab+56a6a9c) — חי, מאומת.
- **אכיפת-דגלים** (bcdf43e) — `env_loader` טוען `.env` בכל דרך-אתחול (באג-שישי). 10 דגלים ON.
- **חשד-SQLite** — `DATABASE_URL` ב-`.env`, אומת Postgres בתהליך.
- **SPEC סטופים/T1/גדלים נעול** ל-14 תבניות (Michael+מחקר) → `STOP_ANCHOR_DECISIONS_DRAFT` + xlsx.
- **מימוש Stop-Anchor V2 מלא ומאומת** (00aa717→0a82128): YAML+resolver+מנועי-V2+14 תבניות+
  sizing(min(סולם,auth,מצב))+T1-ladder+מסווג-מצב. **Cowork-verifier תפס+תיקן באג offset 4T→3T.**
  **דלוק ב-SHADOW** (`STOP_ANCHORS_V2=1`).
- **day_type endpoint מת תוקן** (bebea27) — `status` קורא `app.state.day_type_machine` החי
  (לא ה-`_get_engine()` המת). day_type מציג עכשיו נכון (Trend_Normal/LOCKED).
- **build-inspector stream-names** (ccfa625) — `bars_5min`/`tpo`/`tick_reversal_15`.
- **דגלי-reclass דינמיים** — `S1_DYNAMIC_RECLASS`+`S1_LIVE_RECLASS`=true (סיווג-יום מתמשך).
  ⚠️ Cowork טעה קודם וקרא להם "קוד-מת" — הם בשימוש (main.py:283/310). תוקן.
- **repo נדחף ל-GitHub** (origin מעודכן, 222 commits). מעבר-מחשב: חלק-B מוכן `CC_NEW_MACHINE_SETUP.md`.

## 2 · 🔴 הפתוח (RTH 06-08, verdict=BLOCKED, 0 armed)
- **I-16 · choppiness_ok חסר** → Reactive/Initiative (S2) חסומים. תלוי ב-`tick_reversal_15`+`tpo`
  שאינם טריים. **Michael: tick_reversal_15 קיים/זורם · tpo מ-Chart 3 · footprint מנוטרל
  (`S3_MUTE=1`) עד הודעה חדשה.** פעולת-Michael: Chart 1 + Chart 3 לפוקוס. ⚠️ ודא ש-choppiness
  לא תלוי ב-footprint-המושתק (אם כן — חיווט-לתיקון).
- **REV ב-Trend_Normal = SKIP** — 🟢 תקין (דוקטרינה), לא באג.
- **I-22 · pnl_r מנופח ~50×** — מחושב מול stop-שהוזז-ל-BE ולא stop-התחלתי (task פתוח, Cowork).
- **I-20/I-18 · TZ mask** (`bridge_inspector._parse_ts` ET/+00:00) — load-bearing, דורש דגימת-ts
  פר-stream + תיקון `_parse_ts` פר-קונבנציה. אובחן, לא תוקן (לא-עיוור).
- **I-11 · footprint ingest-break** — מנוטרל בכוונה כרגע.
- **audit-תבניות**: `CC_AGENT_PATTERN_ARMING_AUDIT_2026-06-08.md` (מה חסר לכל 19 תבניות).

## 3 · הצעד הראשון בצ'אט הבא
1. קרא `CLAUDE.md` + הזיכרון. הצלב את `PATTERN_ARMING_AUDIT` (אם CC הריץ) מול ה-SPEC.
2. אמת חי: choppiness_ok נפתר אחרי Chart 1+3? תבניות-S2 דורכות? עסקאות-SHADOW עם V2
   מקבלות סטופ-מבני/T1-סולם/חוזים נכונים (הצלב מול xlsx).
3. אם choppiness תלוי ב-footprint-המושתק → תקן חיווט שיבוא מ-5min/woodies.
4. המשך soak: השוואת V2 מול legacy יום-יום; כיול YAML לפי MFE.

## 4 · לקחים מחייבים (היום)
1. **אינדקס קודם** (חוק #1) — Cowork טעה על "קוד-מת" כי לא בדק באינדקס; Michael תפס.
2. §7a — אל תיגע ב-market-data route בלי אימות-Sierra חי (Cowork נמנע נכון; Michael תיקן Sierra).
3. הצלב כל טענת-CC (Rule 5) — Cowork תפס באג-offset שטסטי-CC פספסו.
4. None>0.0 כ-sentinel (T3) · דגל-gated + SHADOW לפני LIVE · "מוכן-לירי" דורש ברים+armed, לא רק דגלים.
