# CC — W8 v3: סטופ + יעדים על פוזיציה קיימת (**התיקון: זה כן אפשרי**)

**פסיקת-מייקל 07-28:** *"המערכת כן תוכל לנהל עסקה שאני מבצע ולהוסיף לה סטופ ונקודות מימוש"*
**בעלים:** `cc-macbook` · **מאמת:** `cowork-dev` + `cursor-agent`
⚠️ **מייקל בפוזיציה חיה ומתחת-למרג'ין. אל תיגע בפוזיציה. כל אימות בסים בלבד.**

---

## 0. תיקון — מה שחסם את זה 8 ימים היה שגוי

בגוף ה-DLL יושבת הערה מ-2026-07-20:

> *"ACSIL cannot place a resting STOP order (Exit=MARKET-only, Entry+STOP=r=-1, SubmitOrder doesn't exist)."*

**‏cowork קיבל אותה כעובדה ובנה עליה ספק שגוי (‏W8 v2). מייקל חלק — וצדק.**
בדיקה של ה-API הממשי ב-`~/SierraChart/ACS_Source/`:

| הטענה מ-07-20 | מה שנמצא בפועל |
|---|---|
| "SubmitOrder doesn't exist" | ✅ **נכון.** ‏0 הגדרות ציבוריות (רק `InternalSubmitOrder`, מצביע פרטי) |
| "Exit = MARKET-only" | 🔴 **לא מתועד בשום מקום בהדר.** אין הגבלה כזאת ליד `InternalSellExit`/`InternalBuyExit` |
| "אי-אפשר להניח סטופ" | 🔴 **קיים `SCT_ORDERTYPE_OCO_LIMIT_STOP = 15`** — צמד LIMIT+STOP ב-OCO. **זה בדיוק "סטופ + נקודת-מימוש"** |

**וההוכחה החזקה ביותר — הקוד שלנו כבר עושה את זה:** `_merged.cpp:2895-2897` מציב
`Target1Price` + `AttachedOrderTarget1Type=LIMIT` + `Stop1Price` בכניסה. הבראקטים
של מייקל **נראים ברגע זה** ב-`sierra_state.json.orders[]`. המנגנון עובד — רק
מעולם לא הופעל על פוזיציה **קיימת**.

---

## 1. מסלול A (ראשי) — `OCO_LIMIT_STOP` דרך משפחת-Exit

```cpp
// Protective bracket on an EXISTING position: one OCO pair = target + stop.
// Michael 07-28. NOT op=EXIT (the broken partial-exit path) — a different
// OrderType on the same, proven Exit call.
s_SCNewOrder o;
o.OrderQuantity = clamped_qty;                    // reduce-only, ≤ abs(position)
o.OrderType     = SCT_ORDERTYPE_OCO_LIMIT_STOP;   // = 15
o.Price1        = target_price;                   // the LIMIT leg
o.Price2        = stop_price;                     // the STOP leg
o.TimeInForce   = SCT_TIF_DAY;
o.TradeAccount  = sc.SelectedTradeAccount;        // never from JSON
double r = (actual_pos > 0) ? sc.SellExit(o) : sc.BuyExit(o);
```

**‏`sc.SubmitOCOOrder` לא מתאים** — הוא דוחה כל טיפוס מלבד 17/18/19 (‏OCO דו-כיווניים
לכניסת-פריצה) ומחזיר `SCTRADING_NOT_OCO_ORDER_TYPE`. טיפוס 15 עובר דרך Exit.

**‏`double`, לא `int`.** כל פונקציות-ההזמנה מחזירות `double` — ‏v2 השים ל-`int r`.

## 2. מסלול B (גיבוי) — `sc.SetAttachedOrders`

```cpp
void (SCDLLCALL* SetAttachedOrders)(const s_SCNewOrder& AttachedOrdersConfiguration);
```
קובע את **תצורת-הבראקט** שסיירה תצרף. אם מסלול A מחזיר שגיאה — הגדר תצורה
(‏`Target1Price`/`Stop1Price`/`AttachedOrderStop1Type`) ובדוק אם סיירה מצרפת אותה
לפוזיציה. בדוק גם `GetNearestStopOrder`/`GetTargetOrderInOCOGroupNumber` —
עצם קיומן מעיד שה-API מצפה שתנהל סטופים/יעדים קיימים.

## 3. שני שערי-בטיחות — v2 עשה חצי

1. **צד מול סימן-הפוזיציה** — ‏v2 עשה ✅ (שמור).
2. **מחיר מול שוק** — ‏v2 **לא עשה** 🔴 **חובה**:
   - לונג → `stop < LastTradePrice < target`
   - שורט → `target < LastTradePrice < stop`
   הפרה → `PLACE_BRACKET_REJECT_WRONG_SIDE`, **בלי לשלוח**.
   סטופ בצד הלא-נכון = מרקט מיידי — יציאה כפויה במסווה של הגנה.
3. **reduce-only:** `qty = min(requested, abs(pos))`; ‏`pos==0` → סירוב. (‏v2 ✅)
4. **בלי לגעת בקיים:** אם `_has_protective_stop()` כבר `True` — **אל תציב** (פסיקת-בעלות 12:20).

## 4. פקודה ותוצאה

```json
{"op":"PLACE_BRACKET","qty":6,"stop":7416.00,"target":7504.00,"side":"LONG"}
```
```json
{"op":"PLACE_BRACKET","status":"PLACE_BRACKET_OK|_FAIL|_REJECT_WRONG_SIDE|_NO_POSITION",
 "r":<double>,"route":"OCO_LIMIT_STOP|SET_ATTACHED","ts":...}
```
`target` אופציונלי — בלעדיו `SCT_ORDERTYPE_STOP` בלבד (הגנה קודמת לרווח).

## 5. דגלים

`PLACE_BRACKET_OP_V1` · `S6_AUTOSTOP_V1` — **1 אחרי אימות-סים** (פסיקה קיימת →
בונים→מאמתים→מדליקים בלי אישור שני). ‏`S6_AUTOSTOP_GRACE_S`=45 ·
`_BUFFER_TICKS`=4 · `_MAX_RISK_USD`=250 · `_MAX_PER_EPISODE`=3.
**רשום ב-`config/RULED_FLAGS.yaml` באותו קומיט** — ‏v2 לא רשם, והדגלים לא היו בשום מקום.

## 6. חיווט S6 (לא מומש ב-v2 בכלל)

`system6_supervisor.diagnose_trade` → `NAKED_POSITION` בדרג **AUTO** → `PLACE_BRACKET`.
מפעיל: `_has_protective_stop() is False` במשך `S6_AUTOSTOP_GRACE_S`. `None` → **התראה בלבד**.
מבנה: סווינג-5דק' → נר-קודם → קיצון-סשן → ‏ATR. **השתמש ב-`StopResolver`/`stop_anchors` הקיימים.**
חל על פוזיציה של המערכת **וגם ידנית** — הבעלות קובעת רק את שורת-הלוג.

## 7. טסטים — 13, ‏**v2 מסר 0**

צד-נכון · צד-הפוך-נדחה · **מחיר-בצד-הלא-נכון-נדחה** · מוגן→אפס-קריאות ·
`None`→התראה-בלבד · clamp · flat→סירוב · grace · אידמפוטנטיות · אפיזוד-חדש ·
תקרת-סיכון · דגל-כבוי=no-op · **assert: אפס `op=EXIT`** · **אנטי-mock**.

## 8. אימות (חוק 5) — התנאי להדלקה

**סים.** פוזיציה עירומה → תוך ‎~45 שניות **סטופ אמיתי + יעד ב-`orders[]`**
(‏`type` 2/3 ו-1), ‏`_has_protective_stop` → `True`.
**הדבק `orders[]` לפני ואחרי + את ה-`r` הגולמי.**

⚠️ **‏cowork לא הריץ את זה — זו ראיה מ-API, לא מריצה חיה.** אם מסלול A מחזיר
שגיאה, **תעד את קוד-השגיאה המדויק** ועבור ל-B. אל תכריז "בלתי-אפשרי" בלי קוד-שגיאה
גולמי מריצה בסים — **בדיוק הטעות שעלתה לנו 8 ימים.**

## 9. לפני הכל

`_merged.cpp:3389` קורא ל-`sc.SubmitOrder(o)` — **לא מתקמפל, הסר.**
הקובץ הפרוס נקי (0 קריאות) ולכן ה-DLL הרץ בטוח; `mems26_verify` מסמן drift — זה נכון.
