# CC MEGA — תיקון DB מהשורש + הפעלת S1 ו-S2 חי (לפי הספק) · 2026-06-02

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**מטרה:** (1) לסגור את ה-corruption מהשורש (התיקון הקודם `0afe147` חלקי + ה-"GO" לא תקף).
(2) להפעיל את **S2 (Reactive)** שתירה בפועל לפי המחקר — לא 90%. (3) להפעיל את **S1 (סוג-יום)**
שתסווג מחדש **חי** (לא רק בצל). הכל flag-gated, single-source, עם שערי strategic-stop.

**אימות Cowork שמחייב את הפרומפט הזה:**
- ה-soak הקודם היה **89 שניות** (14:51:03→14:52:32), לא 10 דק' — קצר מחלון הכשל (1-2 דק').
- `integrity_check` חי ב-14:54 (~3-4 דק') = **6 שגיאות אינדקס ב-`v9_footprint_journal`** → corruption חזר.
- כותבים שלא הועברו עדיין עוקפים את ה-lock: `tpo_system.py` (5), `session_boundary/manager.py` (5),
  `shadow_reclass.py`, `tpo_history_snapshotter.py` (אומת `grep sqlite3.connect`).

---

## 🚦 שער-על: Phase 1 חייב לעבור (soak נקי ≥15 דק') לפני שנוגעים ב-S1/S2. אין טעם לכייל על DB מושחת.

## Phase 1 · השלמת תיקון-שורש ה-DB (חוסם)
1. **העבר את כל הכותבים הנותרים** ל-`safe_writer`: tpo_system (5), session_boundary/manager (5),
   shadow_reclass, tpo_history_snapshotter, **וכל** `sqlite3.connect` שכותב (grep מלא — אפס כתיבה גולמית).
2. ודא ש-footprint **לא** מחזיק עוד `self._conn` persistent שעוקף את ה-lock.
3. **טסט repro (Phase 0 שדולג):** שתי כתיבות מקביליות → `integrity_check` נכשל **לפני** התיקון, `ok` **אחרי**.
   שורת ליטמוס: *"if reverted → RED because בלי serialization שתי כתיבות מקביליות משחיתות."*
4. שקם DB נקי (`integrity_check=ok`).
5. **SOAK אמיתי ≥15 דק'** תחת עומס מלא, `integrity_check` כל 5 דק' עם **זמני wall-clock גולמיים אמיתיים**.
   GATE: נשאר `ok` כל ה-15 דק' → ממשיכים. אחרת — עוצרים ומדווחים. הדבק פלט גולמי מלא.

## Phase 2 · S2 (Reactive) — שתירה לפי המחקר (D-RVX)
מקור-ספק: `docs/reports/DECISION_BRIEF_REACTIVE_VOLUME_THRESHOLD_2026-06-01.md`.
- **החלף** את `DROP_THRESHOLD_PCT=0.10` (90% בלתי-אפשרי, `five_min_system.py:30,499`) בסף **יחסי**
  מבוסס-ממוצע/RVOL לפי הספק. flag-gated.
- הרץ את 3 הווריאציות (A=VSA · B=RVOL-TOD · C=Strict). **אחת נבחרת חיה** (S2 יורה בפועל),
  השתיים האחרות **observers** במקביל ל-A/B. הצג ב-Build Status מי armed/fired (אור ירוק).
- **אימות:** טסט שמראה שעל ברים מייצגים S2 **כן** מפיק setup עכשיו (היה 0 all-time) + golden flag-OFF זהה.
- 🛑 **strategic-stop:** אילו וריאציה הולכת חיה מול observer — **אישור Michael** לפני הדלקה.

## Phase 3 · S1 (סוג-יום) — סיווג-מחדש **חי** (לא בצל)
מקור-ספק: `docs/reports/DECISION_BRIEF_S1_DAYTYPE_RECLASSIFICATION_2026-06-01.md`.
- כיום: ה-reeval החי **מת** (`state_machine._check_reeval`: `move_30=None` קשיח + `atr=bar.atr` תמיד None),
  ו-`shadow_reclass.py` מחשב נכון אך **רק רושם** (לא משנה live).
- **תקן את הקלט של ה-reeval החי:** ATR יומי אמיתי + היסטוריית ברים ל-`move_30`, **או** קדם את לוגיקת
  `shadow_reclass` (שכבר מחשבת Normal→Variation→Trend) לנהוג את ה-day_type החי — מאחורי דגל
  (למשל `S1_DYNAMIC_RECLASS` שמנהג live כשהוא ON), single-source.
- **ולידציה:** השווה live מול ה-shadow-log הקיים — חייבים להסכים לפני הדלקה.
- **אימות:** על יום-trend (E_up/R מעל הסף) ה-day_type **עובר בפועל** Normal→Trend חי.
- ⛔ **strategic-stop קשיח:** זה משנה את **Auth Table gating** (משטח הסיכון הגבוה ביותר). מימוש מאחורי דגל
  default-OFF; **הדלקה ל-live רק באישור Michael מפורש** אחרי ולידציה live-vs-shadow. (SHADOW mode כללי
  נשמר — אין הזמנות אמיתיות.)

## כללי-על (כל ה-phases)
- כל דגל default-OFF; golden regression לפני כל שינוי; טסט אנטי-טאוטולוגי (revert→RED) לכל תיקון;
  אפס נגיעה ב-order/risk/sizing. שינוי אחד בכל פעם, דווח פר-phase.

## דוח חובה (חלק C) + NOT-DONE + עדכון `STATUS_BOARD.md`+`ROADMAP_TO_LIVE.html`+`DECISION_LEDGER.md`.
