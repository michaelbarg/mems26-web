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

## משימה 1 · ⭐ הגנת-יתום = ניטור-backend + יציאת-שוק (לא סטופ-רסטינג!) — תיקון-שורש
**עדכון קריטי (cowork, מהקוד):** 3 הגישות שלך נכשלו כי **ACSIL לא מאפשר סטופ-רסטינג עצמאי:**
Exit-family=MARKET-בלבד (`:1382`) · Entry+STOP=סמנטיקה-שגויה+r=-1 · **`sc.SubmitOrder` לא קיים** (צדקת).
ו-**`send_orders_to_trade_service=0` הוא הנכון בסים** (`:174` `sc.SendOrdersToTradeService =
!sc.GlobalTradeSimulationIsOn`) — **לא** השורש; **סיירה תקינה** (פסיקת-מייקל). **הפסק לנסות סטופ-רסטינג.**

**🔴 תיקון-תכן (פסיקת-מייקל 2026-07-20): לא לסגור מיד — סטופ-מבני שומר + תקרת-$200.**
מייקל: *"לא אישרתי לסגור — אישרתי לשים לו **סטופ במבנה שישמור עליו**, ורק אם נוצר **הפסד של $200**
אפשר לסגור."* כלומר היתום **מוחזק ומוגן**, לא מושטח-מיד. שני תנאי-סגירה בלבד:
1. **סטופ-מבני** (השומר) — חשב מ-`stop_resolver`/עוגן-מבני (swing/VA הרלוונטי) = הרמה שמגִנה על היתום.
   כשהמחיר **חוצה את הסטופ-המבני** → FLATTEN_ORPHAN.
2. **תקרת-הפסד קשיחה $200** — אם ההפסד-הלא-ממומש ≥ $200 (= `200 / (5 × qty)` נק') → FLATTEN_ORPHAN.
**אחרת — להחזיק** (לא לסגור על תנועה-קטנה / לא רק-כי-יתום). FLATTEN רק כש-(1) או (2).

**הארכיטקטורה — ניטור-backend → יציאת-שוק בשני-תנאים:**
- **backend (`ORPHAN_AUTO_STOP_V1`):** כשמזוהה יתום → חשב **סטופ-מבני** (`stop_resolver`) + חשב את
  רף-ה-$200. **נטר כל tick/bar.** שלח FLATTEN_ORPHAN **רק** כשהמחיר חוצה את הסטופ-המבני **או** הפסד≥$200.
  (סף-$200 ניתן-לכיוונון: `ORPHAN_MAX_LOSS_USD`, ברירת-מחדל 200.)
- **DLL op (החלף את PLACE_STOP השבור, `:1389-1423`):** `FLATTEN_ORPHAN` — יציאת-שוק דרך הנתיב
  שכן-עובד: `SellExit/BuyExit` עם **`SCT_ORDERTYPE_MARKET`** (כמו `:1487`, מוכח). **שומר reduce-only:**
  קרא `PositionQuantity` ברגע-הביצוע · `qty=min(req,abs(pos))` · pos==0→אל תבצע · צד-מגן תואם-סימן ·
  0 קריאות Entry. `result_status=(r>=0)?"FLATTEN_ORPHAN_OK":"..._FAIL"`.
- **למה זה נכון:** יתום = רשומות≠מציאות, פוזיציה-לא-רצויה; המטרה **לשטח אותה** כשהיא נגדך, לא לנהל
  אותה. יציאת-שוק-מנוטרת = op מוכח, אפס r=-1. פשרה: סליפג' של פולינג (~1-5ש') — קביל להגנת-רשת נדירה.

**אז:** snapshot → עריכת-DLL (`FLATTEN_ORPHAN` market-exit) + לוגיקת-ניטור ב-backend (דגל OFF) → grep
מוכיח → **Remote Build** → **re-sim A1.6:** יתום-2 בסים → `ORPHAN_AUTO_STOP_V1=1` → הזז מחיר-סים מעבר
לסטופ-הוירטואלי → **הוכח:** יציאת-שוק ירתה · `position_qty`→0 · לא-גדל. מקרה-מראה LONG. r=-1 → עצור+דווח.
**cowork מאמת → RULED=1.** (אם בכל-זאת תרצה סטופ-רסטינג-אמיתי: לוג את שגיאת-ה-ACSIL המדויקת דרך
`sc.GetOrderByOrderID`/last-error, לא רק r=-1 — אבל הנתיב-המנוטר הוא הפתרון-המאושר.)

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
