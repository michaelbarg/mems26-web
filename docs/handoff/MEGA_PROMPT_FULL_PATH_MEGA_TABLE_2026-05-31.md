# מגה-פרומפט — טבלת-על: נתיב מלא end-to-end (כל המערכות) · קוד מול אפיון

> להדבקה בצ'אט **קוד** (Claude Code / Cursor) עם גישה ל-repo `mems26_web_git`.
> **קרא קודם `CLAUDE.md` ו-`.cursor/rules/mems26-pre-live-protocol.mdc`.**
> **READ-ONLY** — אפס שינוי קוד. התוצר הוא דוח טבלת-על + רשימת אי-התאמות.

---

## הקשר (מה כבר נעול — אל תשנה, רק תעד)
MEMS26 = מערכת מסחר אוטונומית ל-MES, 6 מערכות (S1-S6), כרגע **SHADOW בלבד**.
- Gateway קנוני = **MERGE** (בסיס Legacy `backend/v9/gateway/trading_gateway.py` + 5 שערי סיכון; RiskValidator יחולץ מ-New).
- bracket = `sc.BuyEntry/SellEntry`+Attached. modify = `sc.ModifyOrder`. Heartbeat = alert-only.
- חשבון = IronBeam `37138283` (sim/live = global toggle). אין Apex.
- **5 דגלי סיווג דלוקים ב-SHADOW** (`S2_ATR_RELATIVE`, `S3_RELATIVE`, `S1_CVD_OPENING`,
  `S1_IB_WIDTH_ATR`, `S1_DAYTYPE_STAGING`) — לכן תעד **גם** את הנתיב flag-OFF (ספים
  מוחלטים) **וגם** flag-ON (ATR-relative/CVD/staging) היכן שהם שונים.

## המשימה
לבנות **טבלת-על אחת** שעוקבת אחרי **הנתיב המלא של עסקה** — מזיהוי הפתיחה → סוג
היום (לכל מערכת) → החישוב → ירי → גודל פוזיציה → ביצוע → ניהול → סגירה — ולהצליב
**קוד מול אפיון** (spec/decisions), ולסמן כל אי-התאמה.

## מקורות לקרוא

**קוד (המימוש):**
- S1 day_type: `backend/v9/systems/day_type/` (`state_machine`, `detector`,
  `decision_matrix`, `schemas`, `consumer`, `neutral_classifier`, `zohar_rules`, `extensions`)
- S2 five_min: `backend/v9/systems/five_min/` (`five_min_system`, `setup_emitter`,
  `quality_tier`, `adaptive_stop`, `sr_proximity`, `patterns/`, `contract_split`,
  `time_stop_mapper`, `output_schema`)
- S3 footprint: `backend/v9/systems/footprint/` (`footprint_system`, `detectors`, `signals/`)
- S4 woodies: `backend/v9/systems/woodies/` (`woodies_system`, `decision_tree`, `execution_bridge`)
- S5 tpo: `backend/v9/systems/tpo/` · S6 killzone: `backend/v9/systems/killzone/`
- משותף: `backend/v9/shared/pre_fire_validator.py`, `backend/v9/shared/atr.py`,
  `backend/v9/services/sierra_command.py`
- Gateway (קנוני MERGE): `backend/v9/gateway/trading_gateway.py` + `risk_checks`,
  `cooldown`, `suffering_side_veto`
- ניהול עסקה: `backend/v9/services/trade_manager/manager.py`, `bar_level_detector`
- התמדה→UI: `backend/v9/db/models/`, `backend/v9/api/v9/trades.py`, `frontend/v9/.../trades/`

**אפיון (spec/characterization — אתר את הקנוניים):**
`docs/decisions/` (D-091 S2 · D-092 S4 · D-093 routing) · Master Index V2 ·
3-Mode Spec V3 · Constitution V3 · `docs/reports/SYSTEM_REVIEW_2026-05-29.md` ·
`MEMS26_SYSTEMS_DECISIONS_REGISTRY` · spec ה-day_type. אם יש מסמך אפיון מרכזי
("האפיון") — אתר וקרא אותו.

## מבנה טבלת-העל (שורה לכל שלב בנתיב)

| # | שלב | מערכת/רכיב | תפקיד (observer/firing) | קלט | חישוב/לוגיקה | פלט | מזין ל | מיקום בקוד | מקור באפיון | תואם קוד↔אפיון? |
|---|-----|-----------|------------------------|-----|--------------|-----|--------|------------|--------------|------------------|

שורות הנתיב (לכל הפחות):
1. קליטת נתונים (bars 5min / footprint / CVD / woodies)
2. S1·A1 הקשר טרום-פתיחה (gap — מוחלט מול `gap/ATR14` flag-ON)
3. S1·A2 זיהוי סוג פתיחה (מחיר; + CVD/PE shadow אם flag-ON)
4. S1·A3-A4 מעקב+נעילת IB + רוחב (15/25pt מול ATR-tiers flag-ON)
5. S1·B1 DECISION_MATRIX (opening × ib_width → day_type) — כולל EXTREME אם flag-ON
6. S1·B-C התפתחות + staging (60% עד נעילת IB; C-period re-diagnose אם flag-ON) + נעילה
7. S1·C3 playbook (strategy / sizing / time_stop לכל סוג יום)
8. S2 זיהוי setup (patterns + expansion — מוחלט מול ATR flag-ON)
9. S3 footprint signals (+ relative אם flag-ON)
10. S4 woodies decision_tree
11. S5 TPO / S6 Killzone (observers — מה הם תורמים)
12. setup_emitter — Auth Table (pattern × day_type × quality_tier → SKIP/sizing) + NT gate
13. quality_tier + sizing_contracts
14. adaptive_stop (floor — מוחלט מול ATR flag-ON)
15. pre_fire_validator (7 בדיקות)
16. gateway.route_setup — 5 שערי סיכון (cooldown/SSV/cluster/chop/strict)
17. trade_manager.accept_setup → V9Trade row (mode) + cross_context
18. on_fill → FILLED
19. ניהול: TIME_STOP, T1/T2/T3, Smart BE, trail, bar_level_detector
20. סגירה → exit_reason, pnl_usd, pnl_r, outcome
21. התמדה (`v9_trades`) → API → עמוד הטריידס

## אימות כללים תפעוליים (חובה — מול האפיון)
שני כללים שמיכאל ציין שנמצאים באפיון — אמת **במפורש** שהקוד תואם, ודגל פער:
- **גודל פוזיציה:** האם מיפוי ה-sizing (playbook AGGRESSIVE/STANDARD/HALF/MIN +
  Auth Table) → מספר חוזים בפועל **תואם לאפיון**? צטט אפיון + קוד.
- **מי יורה (קריטי):** האפיון אומר "המערכת עם **יחס הרווח הגבוה** יורה". בדוק אם
  ה-`gateway.route_setup` / `setup_emitter` באמת **בוחר לפי יחס‑רווח**, או עושה
  **first-wins / slot יחיד / all-shadow**. ⚠️ חשד מקדים: הקוד נראה first-wins, לא
  בחירת יחס‑רווח. אם פער — סמן N + תאר בדיוק.

## דרישות אימות
- לכל שורה: **מיקום בקוד מדויק** (קובץ:שורה) + **מקור באפיון** (מסמך:סעיף).
- עמודת "תואם": **Y** אם הקוד תואם לאפיון, **N + הערה** אם לא.
- בסוף: סעיף **"אי-התאמות קוד↔אפיון"** — רשימת כל ה-N עם תיאור הפער (זה התוצר המרכזי).
- כל טענה מאומתת מהקוד/המסמך בפועל (Rule 2 — verify before trust). אל תמציא.
- היכן שדגל משנה התנהגות — שתי שורות/תת-שורות (flag-OFF מול flag-ON).

## תוצר
`docs/reports/FULL_PATH_MEGA_TABLE_2026-05-31.md` — טבלת-העל המלאה + סעיף אי-התאמות
+ סיכום (כמה שלבים, כמה תואמים, כמה פערים). READ-ONLY, אפס שינוי קוד.

> STATUS: audit read-only · קוד מול אפיון · נתיב מלא · אי-התאמות מסומנות לטיפול.
