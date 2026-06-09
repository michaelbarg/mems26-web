# CC — למה אף תבנית S2+S4 לא ירתה היום + counterfactual על העסקאות שפוספסו

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.**

**מטרה אחת:** לקבוע *למה לא נורתה אף תבנית של S2 (Five-Min) ו-S4 (Woodies) היום
(2026-06-08)* למרות שהיו תנועות/עסקאות מצוינות בשוק (הערת Michael), ולכמת את
הפספוסים ב-counterfactual. **דיאגנוסטיקה — קריאה/אבחון; שום שינוי fire/threshold
ל-live בלי strategic-stop + אישור Michael (B5).**

> **אנטי-רגרסיה:** אל תניח שה-gateway חסם. כבר אומת ב-Cowork: ב-`trading_gateway.py`
> route-path אין veto על dead-streams/readiness; Layer-0 chop **מושבת** (:124–125);
> cooldown/cluster/SSV היו inactive. ⇒ ה-gateway **לא** השורש. השורש הוא ש-`route_setup`
> **לא נקרא כלל** כי **לא היה detection**.

---

## ראיות חיות (snapshot 2026-06-08 ~11:43–11:55 CT)

- **S2:** `fired_today=0`, `last_pattern=None`, `last_classification=None`,
  `patterns_detected=0`, `setups_published=0`, buffer 49, mode DAY_TYPE_MODE,
  opening_type OPEN_DRIVE, day_type_gate Trend_Normal.
- **S4:** `fired_today=0`, `active_patterns=[]`, `NO_SETUP`, `cci_14=-164.37`,
  trend RED (היום התנדנד RED/GRAY/BLUE — I-15).
- **trades/recent:** רק 3 עסקאות **משישי**; **0 היום**.
- **gateway:** `trades_today=0`, demo_enabled=[2,4], live=[], כל ה-guards inactive.

**מסקנת-ביניים:** אפס fires = אפס detections (לא veto). השאלה: **למה ה-detectors
לא זיהו כלום למרות תנועות אמיתיות?** 4 חשודים מצטברים — לכמת כל אחד מול הברים בפועל.

---

## Phases (אטומיים)

### Phase 0 — לאשר 0-fires/0-detections מה-DB (לא מה-endpoint)
- `SELECT count(*),max(ts) FROM v9_trades WHERE date(ts)=<today ET>` (צפי 0).
- ספירת detections היום מ-`v9_system_signals` / state של S2/S4.
- **AC:** מספרים גולמיים + פקודה. *fires=0 ו-detections=0 מאומתים מ-DB.*

### Phase 1 — לשלוף את רשימת-הפספוסים (כלי קיים!)
- `MissedTradeDetector` (`backend/v9/systems/build_status/missed_trade_detector.py`)
  כבר רושם `blocked_signal` + `uncaptured_move` (תנועה נקייה ≥סף בלי תבנית) →
  `persist_daily()` כותב ל-`v9_system_signals` (system_id=0, `MISSED_*`).
- שלוף את כל ה-`MISSED_*` של היום. **אבל אמת שתיים:** (a) `persist_daily()` בכלל
  רץ היום? (b) `on_bar()` הואכל בכל בר-RTH — או שיש פערים (אם ערוץ 5דק' נתקע →
  לדטקטור עצמו יש חורים, והפספוסים לא נרשמו). 
- **AC:** טבלת candidates (ts_ct, type, pattern, system, direction, why_not,
  hypothetical_r) + הוכחה ש-on_bar קיבל רצף ברים מלא (או רשימת הפערים).

### Phase 2 — ציר-זמן של ערוצי-הנתונים היום (חשוד-שורש #1: I-21)
- שחזר זמינות פר-בר ל-`woodies_5min`/`5min_bars`/`footprint`/`tick_reversal_15`
  מ-`~/SierraChart_Data/v9_export/` (mtimes + last-bar ts) + פערי-ברים ב-DB.
- עוגנים ידועים: ערוץ 5דק' עלה **~09:00 CT** (~30דק' אחרי פתיחת 08:30) ⇒ שעת-הפתיחה
  לא כוסתה; `tick_reversal_15` **DEAD כל היום** (מ-שישי); הקפאות-CCI לסירוגין.
- **AC:** טבלת-ציר-זמן; מיפוי כל `uncaptured_move` (Phase 1) למצב-הערוץ באותו רגע
  (האם הפספוס נפל בחלון late-start/stall/dead-channel?).

### Phase 3 — אודיט ספי-detection (חשוד #2: ספים צרים-מדי)
- לכל חלון עם `uncaptured_move`, חשב את קלטי-ה-detection בפועל מול הסף הנדרש:
  - **S2:** `b1_expansion` range מול הבאנד (register צפה range=8.25 מול need
    [4.5,6.0] ⇒ expansion חזק **נדחה כרחב-מדי** — חשוד ישיר ל"עסקה מצוינת שפוספסה"),
    `b2_volume_drop`, `b1_buyers`, swing detection.
  - **S4:** `A3 pattern_specific` (ZLR LOOKBACK=12/AP1, TLB/TT/HFE…), `trend_state`.
- הצלב כל קלט מול Sierra `v9_export` (CCI-14/TCCI/OHLC). פער backend↔Sierra = ממצא.
- **AC:** טבלת measured-vs-required פר-חלון; סמן ספים שדחו setup תקין-לכאורה.
  *אם ספג b1_expansion חוסם תנועות חזקות → המלצת-כיול (flag-gated), לא הדלקה ל-live.*

### Phase 4 — אודיט שערים שדיכאו detection (חשודים #3+#4)
- **`data.choppiness_ok` (I-16/I-17):** בכמה סנאפ-שוטים **כל 10** תבניות-S2 נחסמו
  על choppiness_ok-Missing (score≠gate-flag). כמה זמן היום הדגל היה Missing? בכל
  חלון-פספוס — האם choppiness_ok חסם את כל S2 מלזהות?
- **S4 trend GRAY (I-15):** trend התנדנד; כש-GRAY → A1-veto לכל S4 **לפני** A3. כמה
  מהיום היה GRAY, והאם חפף לתנועות?
- **4 day-patterns:** auth×Trend_Normal — לאשר שזו חסימה לפי-אפיון (לא באג).
- **AC:** לכל חלון-פספוס — המדכא המדויק (choppiness Missing / trend GRAY / band /
  channel-dead), עם ראיה.

### Phase 5 — Counterfactual פר פספוס
- לכל setup שפוספס: entry/stop/T1/T2 לפי ספק-התבנית → שחזר את הברים שאחריו
  (`v9_bars_5min`/Sierra) → hit_T1/T2/stop/timeout → R ותוצאה. צבור ΣR + win-rate.
- **חסם ידוע:** `pnl_r` מנופח ~50× (I-22) — השתמש בנוסחת-R מתוקנת
  (risk=entry−stop_init פר-חוזה), לא ב-`pnl_r` הקיים.
- **AC:** טבלת counterfactual; מסקנה — האם הספים/הערוצים עלו לנו על עסקאות טובות.

### Phase 6 — דוח לפי חלק C של החוזה
טבלת phases (DONE/PARTIAL/NOT-DONE + Evidence command+output) · *"if reverted →
RED because ___"* לכל טסט · סעיף **NOT DONE / DEVIATIONS** · **Open**. עדכן
`MEMS26_ISSUES_REGISTER.md` (I-15/I-16/I-21/I-22) + `STATUS_BOARD.md`.

---

## אסור לגעת (risk surface)
- אין שינוי fire-path/gateway/risk; אין הרחבת ספי-detection ל-live בלי
  strategic-stop+אישור Michael; אל תדליק chop gates; אל תיגע ב-`FOOTPRINT_DISABLED`/
  Bridge-local-only/LaunchAgent. **Sierra `v9_export` = source-of-truth** לכל קלט.

## קבצים רלוונטיים
- `backend/v9/systems/five_min/five_min_system.py` + detectors · `setup_emitter`/`setup_wrapper`
- `backend/v9/systems/woodies/decision_tree.py` + `stages/` (A1–A7) + `zlr.py`
- `backend/v9/systems/build_status/missed_trade_detector.py` · `s2_pattern_probe.py`
- `backend/v9/gateway/trading_gateway.py` (route-path — לאישור אין-veto)
- DB: `v9_trades`, `v9_system_signals` (system_id=0 MISSED_*), `v9_bars_5min`
- `~/SierraChart_Data/v9_export/` (CCI/OHLC/study — הצלבה)
