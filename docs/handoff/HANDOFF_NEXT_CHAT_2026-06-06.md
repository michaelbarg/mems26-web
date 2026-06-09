# Cowork Handoff — צ'אט הבא (2026-06-06) — T3 תוקן מהשורש · מחקר-footprint הושלם · הכנה למעבר-מחשב

**אתה (Cowork הבא):** orchestrator + verifier בלתי-תלוי של MEMS26. CC מבצע על ה-Mac; אתה כותב פרומפטים,
מצליב (**Rule 5: פקודה+פלט גולמי**), מעדכן בורדים, מריץ agents, ומתקן frontend ישירות (Next hot-reload).

## 0 · מקור-אמת + פרוטוקולים
`CLAUDE.md` (§Index קודם! `backend/main.py`≠`backend/v9/main.py`) · `CC_HANDOFF_CONTRACT.md` · `CC_VERIFICATION_PROTOCOL.md`.
בורדים: `docs/plans/STATUS_BOARD.md` (source-of-record) · `ROADMAP_TO_LIVE.html` · `docs/reports/MEMS26_ISSUES_REGISTER.md`.
**מעבר-מחשב:** `docs/runbooks/MIGRATION_TO_NEW_MACHINE.md` (נכתב היום — המחשב החדש = סביבת-הפיתוח).

## 1 · מה נסגר בסשן הזה (אומת)
- **תיקון-T3 מהשורש (I-22+I-23)** — שורש: `t3=0.0` במקום `None` גרם ל-`active_trade_manager/monitor.py:104` לטפל ב-T3-לא-קיים כיעד-פנטום על C3.
  - Backend: S2 חולץ ל-`build_s2_gateway_setup()` (מעביר `t1_setup.t3_price`); S4 `woodies_system.py:504` + S3 `footprint_system.py:565` `0.0`→`None`; API `trades.py` חושף `t3_label`/`trail_after_t2`. טסט אנטי-טאוטולוגי `tests/v9/regression/test_s2_gateway_t3_passthrough.py`.
  - Frontend: `tradeMath.ts rLevels` הוסיף `t3R`+guard; `SelectedTradePanel` מציג price·R + שורת T3; `TradeDetailsModal/PriceTimeAxis` guard `t3>0`.
  - אומת: sandbox (`t3` passthrough), tsc 0-חדש, UI חי (#13: `T1 7410.50·+1.0R · T2 7404.88·+2.5R · T3 —`). **⚠️ uncommitted + צריך restart + LIVE-gate.**
- **רוד-מאפ** — סומנו 8 פריטי-פאזה-0 בוצע (I-1/B-11/B-13-residual/I-2/I-22/I-23/Trades-Phase1/BuildStatus-P0), עם ראיית-commit. השאר פתוח ביושר.
- **מחקר-footprint** — `FOOTPRINT_CONFIRMATION_FILLED_2026-06-06.md`: טבלת 19-תבניות × footprint (כניסה+יציאה+stop+veto+יום), הוצלב מול מחקר-עצמאי. **כל S4 = INFERENCE; עמודת EXIT הכי-פחות-מתועדת.**

## 2 · המשימות הפתוחות (לפי דחיפות)
**🔴 מיידי (uncommitted/לא-חי):** commit תיקון-T3 → restart SHADOW → אישור-LIVE (משנה ניהול C3 בימי-Trend).
**🔴 חוסם #1 (CC+Mac+session-חי):** **I-21** stall יצוא Sierra 5-דק'/study (אובחן בלבד). **I-11** footprint 0-ברים נופל איתו. תנאי-מקדים למחקר-footprint.
**🟡 כיול (soak):** K=0.75 · `MOVE_THRESHOLD=15` · I-3 ZLR · I-13 sizing aux<2 · עוגני-סטופ · **החלטת-T3 ב-Variation (trail מול קבוע)**.
**🟡 housekeeping:** I-9 (cron — כנראה טופל, אמת) · B-14 (כפילות-נרות, פרומפט מוכן) · טסט נכשל `test_bear_flag_skipped_on_first_hour_mode` · Phase-5 (CC דילג על אבחון-I-21).
**🟢 footprint→יישום:** עמודות `footprint_entry_gate`/`exit_rule`/`veto` ב-`stop_target_placement_table` (YAML). חסום על I-21 + שער-LIVE.
**⏳ פאזות:** SHADOW soak ≥10 ימי-RTH/≥20 עסקאות (יום-1) → DEMO (Pipeline 5) → LIVE.

## 3 · הצעד הראשון בצ'אט הבא
1. **commit + restart** של תיקון-T3 (8 קבצים: atr כבר committed; החדשים — five_min_system/woodies/footprint/trades.py + tradeMath/SelectedTradePanel/TradeDetailsModal/types + 2 טסטים). הצלב: pytest ירוק, flag חי, UI מציג מחירים.
2. **פרומפט I-21 ל-CC** (diagnose-first, read-only: mtimes ב-`~/SierraChart_Data/v9_export/` + `bridge.err.log` + `MAX(ts)` פר-טבלה + ה-mask של I-20/C-6).
3. אם המעבר-מחשב פעיל — לך לפי `MIGRATION_TO_NEW_MACHINE.md` והרץ `scripts/check_env.sh` על המכונה החדשה.

## 4 · לקחים מחייבים
1. **אינדקס קודם** · 2. **אל תאבחן מ-endpoint יחיד** · 3. **הצלב כל טענת-CC (Rule 5)** · 4. **visual=1:1** ·
5. **כשמשהו מאושר אל תעכב אותו** · 6. **שינוי trading-logic = flag-gated + soak + אישור Michael לפני LIVE** ·
7. **כשמתקנים — None > 0.0 כ-sentinel** (לקח-T3: 0.0 הופך ליעד-פנטום ב-aggregators).
