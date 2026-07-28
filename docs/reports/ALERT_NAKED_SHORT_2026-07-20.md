# 🔴 דרוש מייקל — NAKED LIVE SHORT פעיל (07-20 09:49 ET)

**session-watch · MacBook (MacBarg.local) · ריצה ראשונה עם נראות-לייב אמיתית מאז ה-cutover ל-MacBook (07-17). Desktop Commander מחובר → כל 5 הבדיקות בוצעו על המערכת האמיתית.**

## שורה-תחתונה — פעולה נדרשת עכשיו
פוזיציית **שורט-3-חוזים עירומה על חשבון הלייב** (is_sim=0), **ללא סטופ וללא יעד**, לא-מנוהלת ע"י המערכת. ה-auto-heal של הרקונסיילר **נכשל** (phantom-heal 0/3, working_orders נשאר 0).

➡️ **FLATTEN_ACCOUNT ידני מיידי** (או הצב סטופ-מגן ידני ~7552.5). המערכת לא סוגרת את זה לבד. אני מאבחן ומתריע בלבד — איני מבצע עסקאות.

## הראיה (מקור-אמת נטיבי, טרי, גובר על לוגים)
sierra_state.json — 4 קריאות זהות ב-6 שניות (mtime 16:49:41→16:49:47 IDT):
```
{"ts":1784555387,"is_sim":0,"order_placement_armed":1,"send_orders_to_trade_service":1,"position_qty":-3,"avg_price":7542.50,"working_orders":0,"orders":[]}
```
- position_qty=-3 (שורט 3) · avg_price=7542.50 · **working_orders=0 · orders=[] → עירום.**
- `GET /api/v9/trades/active` = `null` → ה-TM/DB לא-מודע. **Records ≠ reality.**
- `GET /api/v9/live_price` = 7540.25 (age<1s) → כרגע ~+2.25נק' לטובת השורט, אבל **בלי סטופ = חשיפה בלתי-מוגבלת** (3×MES ≈ $15/נק').
- 0 רשומות ב-`v9_trades` היום (אחרונה = #400 לייב, 07-17). כלומר השורט הזה מעולם לא נרשם.

רקונסיילר (כל 30ש', src=state, טרי):
```
2026-07-20 16:48:59 / 16:49:29 [Reconciler] SYS-3 DIVERGENCE: TM says 0 contracts [], Sierra says -3 (src=state).
Records ≠ reality! [phantom-heal streak 0/3] 🔴 NAKED ORPHAN SHORT 3c @ 7542.5 → PLACE PROTECTIVE STOP @ 7552.5 (10pt).
```
→ המערכת *רוצה* להציב סטופ אך **לא מצליחה** — streak תקוע 0/3, working_orders נשאר 0. זה באג ה-heal הידוע.

## ציר-זמן היום (07-20)
1. **הפוזיציה עברה 0 → -3 בין 16:39:49 ל-16:48:57 IDT** (09:40→09:49 ET) — שורט חדש @7542.50. ב-16:39 sierra_state עוד הראה flat.
2. **בוקר ~07:00 ET** (13:53-14:04 IDT): אורפן-לונג-אמת — `ORPHAN FILL` ל-ord 9191 (1c ENTRY) + 9204 (4c ENTRY) @7500 + T3@7523; רקונסיילר: `NAKED ORPHAN LONG 4c→3c → PLACE PROTECTIVE STOP @7511.5`. **יצא בלי fills-יציאה מתועדים** ובלי רשומת-DB (יומן-המילויים נעצר ב-T3 14:00:46).
3. **09:06 ET** (16:06 IDT): התלקחות שקרית — הרקונסיילר נפל ל-**src=events** מהקובץ `trade_activity_events.jsonl` **שתקוע מ-07-17 17:46** והסיק false -3 (`avg_price unavailable; FLATTEN_ACCOUNT immediately`).
4. **668** שורות DIVERGENCE היום.

## מחלקה + שורש
זהה ל-07-14 ו-07-17: naked position מ-bracket-דלוף / reconciler-heal תקוע 0/3. **חוזר בפעם השלישית בשבוע על כסף-אמת.** שורש-פתוח (memory): C3 רקונסיילר-לא-משטח-לבד + ORPHAN_AUTO_STOP_V1/DLL op PLACE_STOP עדיין בתהליך.

## שאר הבדיקות
- **Check 1 (החלטות):** מועמדים 0 / ירי 0 ב-35 הדק' — אין אנומליית-חסימה. חסימות מבוזרות על 9 שערים (cont_trend 18, daytype 12, rr 10, location 6, s4_risk_cap 5...) = חתימה בריאה, לא שער-מורעל יחיד. 🟢
- **Check 4 (בריאות):** flag_guard **PASS 96/96** · live_price age<1s · trade_activity_feed יחיד (PID 33553) · 0 CRITICAL-חדש בחלון · woodies bar age ~3.5 דק'. 🟢
- **פגם-מעקב לתיקון:** `trade_activity_events.jsonl` תקוע מ-07-17 → מרעיל את הרקונסיילר (נפילה ל-src=events מעופש) ומאבד audit של POSITION_CHANGE. סביר שקשור לשורש ה-naked-tracking.

—
דוח אוטומטי ע"י session-watch (קריאה-בלבד). הצ'אט-הראשי/מייקל מטפלים בסגירה + תיקון-שורש.


---

## עדכון-מחזור [2026-07-20 18:47 IDT] — 🔴 האורפן חזר אחרי השיטוח של 18:13

לאחר שמייקל שיטח ידנית ב-~18:13, מחזור-האורפן **בנה מחדש** SHORT 5 חוזים:
- `sierra_state.json` (is_sim=0, armed): `position_qty=-5`, `avg_price=7520.50`, working buy-stop `#9240 @ 7525.75` (avg נדד 7503→7519.5→7520.5; order-id 9238→9240 — סטופ נגרר).
- backend `/trades/active`=null · DB 0-פתוחות · TM=0 → **records ≠ reality** נמשך.
- reconciler `phantom-heal streak 0/3` — מזהה, חסום-ריפוי על is_sim=0.
- הפעם **יש סטופ-מגן** (בניגוד לעירום-המוחלט של 18:02) אך הפוזיציה **לא-מנוטרת** ע"י המערכת.
- הכניסה נבנתה **אחרי 17:45** (העסקה-החיה האחרונה #424 נסגרה אז) → ללא רשומת `v9_trades`.

**דרוש:** אימות-חזותי + FLATTEN ידני; שקילת ביטול-חימוש עד סגירת שורש-המחזור. פרטים מלאים ב-`ALERTS_LIVE.md` (בלוק 18:47).

— session-watch (cowork-dev / MacBarg, קרא-בלבד)
