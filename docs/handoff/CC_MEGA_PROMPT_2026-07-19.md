# MEGA PROMPT — cc-macbook · השלמות + תיקונים (2026-07-19 ליל-סים)

**החלטת-מייקל:** לבנות מחדש את `PLACE_STOP` עם `sc.SubmitOrder` (לא Exit-family), ולהמשיך את כל
תור-המשטח-מסחר. `is_sim=1` מאומת (אמת שוב לפני כל ריצה). cowork מאמת כל תוצר (חוק-5).

## חוקי-ברזל (על כל משימה)
1. **snapshot לפני כל נגיעה ב-DLL/.env/LaunchAgent:** `scripts/mems26_snapshot.sh "<label>"`.
2. **Remote Build רק אחרי שהקוד קיים** (grep מוכיח) — לא RB על-ריק.
3. **דגל חדש = default OFF בקוד** + RULED + `flag_guard` + restart. **הדלקה ל-ON = פסיקת-מייקל + סים-הוכחה.**
4. **אין op=EXIT** (שבור). יציאות: OCO / MODIFY_STOP / MODIFY_TARGET / FLATTEN_ACCOUNT / PLACE_STOP(החדש).
5. **טסט אנטי-טאוטולוגי לכל שינוי** + דגל-OFF byte-identical. פלט-גולמי ל-`LIVE_CHANNEL`.
6. **`is_sim=1` לפני כל הצבה בסים.** אם r=-1 על מקרה-נקי → **עצור+דווח** (כמו שעשית — נכון).
7. `git pull` לפני · `commit`+`push` אחרי · אל תמחק רשומת-אחר.

---

## משימה 1 · ⭐ בנה מחדש PLACE_STOP עם `sc.SubmitOrder` (חוסם ORPHAN)
**קובץ:** `sc_study/MES_AI_DataExport.cpp:1389-1423`. **שנה:** `sc.SellExit(o)/sc.BuyExit(o)` →
`sc.SubmitOrder(o)` עם `o.OrderType = SCT_ORDERTYPE_STOP` (standalone, לא Exit-family — תומך STOP).

**🔴 שומר-בטיחות reduce-only-by-construction (חובה — standalone לא reduce-only מטבעו):**
- קרא את הפוזיציה-הנוכחית (`sc.GetTradePosition` → `PositionQuantity`) **ברגע-ההצבה**.
- אם `PositionQuantity == 0` → **אל תציב** (אין מה להגן) → `PLACE_STOP_NO_POSITION`.
- `qty = min(requested_qty, abs(PositionQuantity))` — **לעולם לא יותר מגודל-הפוזיציה** (יכול רק לשטח, לא להפוך).
- צד: פוזיציה SHORT(<0) → **BUY-STOP מעל**; LONG(>0) → **SELL-STOP מתחת**. אמת שהצד תואם את סימן-הפוזיציה.
- `o.OrderQuantity=qty` · `o.OrderType=SCT_ORDERTYPE_STOP` · `o.Price1=<stop>` · `o.TimeInForce=SCT_TIF_DAY` ·
  `o.TradeAccount` מהפקודה. `result_status = (r>=0)?"PLACE_STOP_OK":"PLACE_STOP_FAIL"`.
- **0 קריאות Entry בתוך ה-handler** (reduce-only). אם `sc.SubmitOrder` דורש דגל-סביבה
  (`sc.SendOrdersToTradeService`/AutoTrading) — טפל, אבל אל תשנה מצב-לייב.

**אז:** snapshot → עריכה → grep מוכיח `SubmitOrder` + השומר → **Remote Build** → reload study → **re-sim A1.6:**
יתום-2 בסים → `ORPHAN_AUTO_STOP_V1=1` (סביבת-סים) → **הוכח:** `PLACE_STOP_OK` · `working_orders` 0→1 ·
סטופ בצד/מחיר נכונים · **הפוזיציה נשטחה/לא-גדלה** · מקרה-מראה LONG. אם r=-1 שוב → עצור+דווח.
**cowork מאמת → ORPHAN_AUTO_STOP_V1 → RULED=1.**

## משימה 2 · STOP_WIDEN — אימות-סים → RULED
`STOP_WIDEN_TO_FLOOR_ON_REJECT_V1=1` (סים): סטופ-מבני צר-מרצפה בדחייה → נדחף-לרצפה · `SIZE_CAP_CUT`
מגיב נכון. byte-identical כש-OFF. **cowork מאמת → RULED=1.**

## משימה 3 · T16 — בנה `SYSTEM6_REVERSAL_TIGHTEN_V1` (default OFF)
W1 אישר: על היפוך-משמעותי (**trigger שמרני: CVD-adverse + ≥2 סגירות-עוינות אחרי T1, לפני יציאה**):
`MODIFY_STOP` הידוק + `MODIFY_TARGET` קירוב-היעד-הבא למחיר. **לא op=EXIT.** ה-caller מגדיר "היפוך" (לא
לסנתז ב-supervisor). טסט אנטי-טאוטולוגי: היפוך→`MODIFY_TARGET` קרוב-יותר-לכניסה; בלי-היפוך→byte-identical.
**דגל OFF — הדלקה=פסיקת-מייקל אחרי סים (W1 תומך).**

## משימה 4 · T17 — BE-אחרי-T1-האמיתי + 4-חוזים
**פסיקת-מייקל: BE אחרי T1-האמיתי, לא T0.** אמת ב-`trade_manager/manager.py` ש-`on_target_hit`
מפעיל `_apply_smart_be_after_t1` על **hit של T1** (C2), **לא** על T0 (C1/הסקאלפ). אם מופעל על T0 → תקן
(דגל-OFF אם משנה-התנהגות + טסט). + תקן `system6_routes` `expected_contracts` 3→4 (תצוגה) + טסט.
**E2E סים 4-חוזים:** PLACE 4 · מילוי C1(T0)→C2(T1)→C3(T2)→C4(T3) · `MODIFY_STOP` בכל שלב · **BE רק אחרי T1**.

## משימה 5–7 · שרשרת-הכיוון (הטסטים כבר מוכנים מ-cursor)
- **5 · G2+G3** `S2_DETECTION_LIVE_DAYTYPE_V1` (OFF): NT-skip + chart-gates + Flag-T2 על
  `get_live_day_type() or self.current_day_type`. OFF=byte-identical. (טסט: `test_s2_detection_live_daytype.py`.)
- **6 · G6** (דגל OFF): כשל-live → `None`+log, **לא** `v9_day_type_state` ולא `"Normal"`. (טסט:
  `test_s4_honest_daytype_fallback.py`.)
- **7 · D1** (אחרי G2/G6 + סים): אמץ+הדלק `daytype_position_gate` **לפי מפת-D0**
  (`DIRECTION_AUTHORITY_MAP_2026-07-19.md`) + **חווט POC-migration** (חלון-מתגלגל, `UP/DOWN/FLAT`); הרחב
  ל-CONT (לא רק REV); Normal-CONT = **חריג ל-PATTERN_AWARE** רק כש-mig בכיוון + צד-POC נכון; Trend=POC-לא-שער.
  (טסט: `test_direction_authority_map.py` — הרחב לגייט האמיתי.) **הדלקה=פסיקת-מייקל+סים; against-Dalton מול בסיס-W2.**

## סדר-ביצוע
`1 PLACE_STOP(RB+סים) → 2 STOP_WIDEN(סים) → 3 T16 build → 4 T17 → 5 G2+G3 → 6 G6 → 7 D1`.
עצור אחרי כל אחד עד ש-cowork מאמת. **הדלקות ל-ON (ORPHAN/STOP_WIDEN/D1) = פסיקת-מייקל אחרי סים-הוכחה בלבד.**
