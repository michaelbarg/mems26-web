# CC — W8: `op=PLACE_STOP` ב-DLL (החוסם של הגנת-הפוזיציה)

**פסיקת-מייקל:** 07-25 (‏W8) + 07-28 (‏S6 מציב סטופ אוטומטית ללא אישור).
**סטטוס:** פסיקה **קיימת** → בונים → מאמתים (טסטים + סים) → **מדליקים בלי אישור שני**
(‏CLAUDE.md § "פסיקות הן חד-פעמיות וקבועות"). רשום את ההפניה ב-`config/RULED_FLAGS.yaml` באותו קומיט.
**בעלים:** `cc-macbook` · **מאמת:** `cowork-dev` + `cursor-agent`

---

## למה זה החוסם

מייקל הפסיד יותר מחצי תיק ב-07-27 על פוזיציה ידנית **בלי סטופ**. ההגנה שנבנתה
(`MANUAL_GUARD_AUTOPROTECT_V1`) מציבה **סטופ וירטואלי**: ה-backend מנטר מחיר ושולח
`FLATTEN_ACCOUNT` בפריצה.

**מה שוירטואלי לא מגן מפניו:** ‏backend שנפל · ריסטארט · קפיאת-פייתון · **גאפ** (הפריצה
קורית בין שני טיקים ואין למי לשלוח) · לילה. סטופ אמיתי יושב בבורסה ועובד בלי אף אחד מאיתנו.

**‏`op=EXIT` שבור ואסור** (‏CLAUDE.md) — זה **op חדש ונפרד**. אל תיגע ב-`_emit_exit`/`write_exit`.

---

## A. צד ה-DLL

**קובץ: `sc_study/MES_AI_DataExport_merged.cpp`** — ⚠️ **המונוליט הוא המקור המתוחזק-ביד.**
הקבצים המודולריים תקועים ב-07-22 וחסרים בהם כל תיקוני-ה-DLL מאז. הסקריפט **מסרב**
לייצר-מחדש (שומר חדש, 07-28). ערוך את המונוליט. פריסה: `./scripts/build_monolithic_cpp.sh --deploy`
→ **Remote Build ע"י מייקל בלבד**.

### הפקודה

```json
{"op":"PLACE_STOP","qty":6,"price":7369.50,"side":"SELL","id":"<uuid>"}
```

### המימוש

```cpp
// PLACE_STOP (Michael 07-25 + 07-28) — a REAL resting stop on Sierra's book.
// NOT op=EXIT: that path is broken (per-contract attached OCO leaves no free
// contract) and is forbidden. This is a standalone protective order.
s_SCNewOrder o;
o.OrderQuantity = qty;
o.OrderType     = SCT_ORDERTYPE_STOP;
o.Price1        = price;
// The 07-27 root cause of EVERY r=-1: the account was hard-coded while Sierra
// sat on a different one. ALWAYS route to the account Sierra has selected.
o.TradeAccount  = sc.SelectedTradeAccount;
int r = (side == "SELL") ? sc.SellExit(o) : sc.BuyExit(o);
```

**חובה:**
1. `o.TradeAccount = sc.SelectedTradeAccount` — **לא** env, **לא** קבוע.
2. **בדיקת-צד לפני שליחה:** לונג → `SELL` וגם `price < LastTradePrice`; שורט → `BUY` וגם
   `price > LastTradePrice`. צד/מחיר הפוכים = **דחייה + `PLACE_STOP_REJECT_WRONG_SIDE`**, לא שליחה.
   סטופ בצד הלא-נכון הופך למרקט מיידי — זו יציאה כפויה, לא הגנה.
3. `qty` חייב `1..abs(PositionQuantity)`. גדול מהפוזיציה → דחייה.
4. תוצאה ל-`trade_result.json`:
   `{"op":"PLACE_STOP","status":"PLACE_STOP_OK|PLACE_STOP_FAIL","r":<code>,"order_id":<id>,"ts":...}`
   כולל מפת-קודים (‏‎-1 GENERAL/NOT_ENABLED · ‎-3 EXCEEDED_MAX_POSITION · ‎-6 WORKING_ORDERS_EXIST).
5. הסטופ **חייב להופיע ב-`orders[]`** של `sierra_state.json` (‏`type` 2/3) — זה מה
   ש-`_has_protective_stop` קורא, וזו הראיה שההגנה קיימת.

**‏`op=PLACE_LIMIT`** — אותו דפוס, `SCT_ORDERTYPE_LIMIT`. בנה יחד, השאר **מנוטרל** (אין פסיקה ליעדים אוטומטיים).

---

## B. צד ה-backend

`trading_gateway.py` — `place_stop(qty, price, side)` לצד ה-PLACE הקיים; **חייב** להשתמש
ב-`_sierra_route_account()` (קיים). `sierra_position_reconciler._place_orphan_stop()` —
החלף את הסטופ-הווירטואלי בקריאה האמיתית, **והשאר את הווירטואלי כ-fallback** אם ה-op מחזיר כשל.

### חיווט S6 (הפסיקה מ-07-28)

`system6_supervisor.diagnose_trade` — `NAKED_POSITION` לדרג **AUTO** שפולט `PLACE_STOP`
(**לעולם לא `EXIT`**). מפעיל: `_has_protective_stop() is False` במשך `S6_AUTOSTOP_GRACE_S`
(‏45). `None` (לא-ידוע) → **התראה בלבד, בלי הצבה** (חוק 1).

**המבנה:** סווינג 5-דק' → נר-קודם → קיצון-סשן (‏IB) → ‏ATR fallback. חוצץ
`S6_AUTOSTOP_BUFFER_TICKS`(4) · מרחק-מינימום 6 טיקים · תקרת-סיכון
`S6_AUTOSTOP_MAX_RISK_USD`(250) → אחרת קיצוץ + `CLAMPED_TO_RISK_CAP`.
**השתמש ב-`StopResolver`/`stop_anchors` הקיימים — אל תבנה מנוע-רמות שני** (ביקורת-לפני-בנייה).

חל על פוזיציה **של המערכת וגם ידנית** — הבעלות קובעת רק את שורת-הלוג, לא אם מגנים.
**פוזיציה עם סטופ — לא נוגעים לעולם** (פסיקת-בעלות 12:20).

אידמפוטנטיות: מעקב `(qty, avg_price)`; אחרי `PLACE_STOP_OK` לא מציבים שוב לאותו אפיזוד.
ביטול-ידני → אפיזוד חדש, עד `S6_AUTOSTOP_MAX_PER_EPISODE`(3).

---

## C. דגלים

| דגל | ברירת-מחדל | הערה |
|---|---|---|
| `PLACE_STOP_OP_V1` | **1 אחרי אימות-סים** | ה-op עצמו |
| `S6_AUTOSTOP_V1` | **1 אחרי אימות-סים** | הצבה-אוטומטית (פסיקת 07-28) |
| `S6_AUTOSTOP_GRACE_S` / `_BUFFER_TICKS` / `_MAX_RISK_USD` / `_MAX_PER_EPISODE` | 45 / 4 / 250 / 3 | |
| `PLACE_LIMIT_OP_V1` | **0** | אין פסיקה |

---

## D. טסטים (כולם לפני הדלקה)

1. לונג עירום → סטופ מתחת לסווינג ‎− חוצץ
2. שורט עירום → סטופ מעל הסווינג ‎+ חוצץ
3. **פוזיציה מוגנת → אפס קריאות** (פסיקת 12:20 — מקובע)
4. `_has_protective_stop` → `None` → התראה בלבד
5. מבנה רחוק מהתקרה → קיצוץ + `CLAMPED_TO_RISK_CAP`
6. **צד שגוי → נדחה, לא נשלח**
7. בתוך grace → כלום; אחרי → הצבה **אחת**
8. `PLACE_STOP_OK` → אין הצבה שנייה באותו אפיזוד
9. אפיזוד חדש אחרי ביטול → מציב; ה-4 → נחסם
10. `qty` > פוזיציה → נדחה
11. דגל כבוי → no-op זהה-בייט
12. **‏assert ברמת-המקור: אף פעם לא `op=EXIT`**
13. **אנטי-mock:** אסור ל-fixture להזריק סמל שהמודול לא מגדיר (מחלקת ה-`_t`)

---

## E. אימות (חוק 5 — פקודה + פלט-גולמי)

**סים, ירי-אמיתי.** פתח פוזיציה עירומה בסים → תוך ‎~45 שניות **סטופ אמיתי ב-`orders[]`**
בצד/כמות/מחיר הנכונים, ו-`_has_protective_stop` → `True`.

**הדבק `orders[]` לפני ואחרי.** חבילת-טסטים ירוקה **אינה** ראיה מספקת כאן — זה
בדיוק המסלול שכשל ב-07-27, ובדיוק המסלול שבו טסט עם mock הסתיר `NameError` לאורך שעות.

---

## F. סדר

1. ‏DLL + backend + טסטים → commit → `--deploy` → **בקש מ-מייקל Remote Build**
2. אחרי הבילד: אימות-סים (‏E) → הדלקת שני הדגלים + `RULED_FLAGS` → LOG ב-`LIVE_CHANNEL`
3. `cowork` + `cursor` מאמתים — **לא סוגר משימה של עצמך**

⚠️ **מייקל בפוזיציה חיה** (‎+6, מרג'ין תופס 92% מהחשבון). **אל תיגע בפוזיציה ובפקודות שלו.**
כל עבודת-הסים אחרי שהוא מעביר את סיירה לסים — **מעבר סים/לייב הוא של מייקל בלבד**.
