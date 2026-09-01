# פקודת-עבודה · שרשרת-המדידה — למה 57% מהעסקאות אין להן מספר-ברוקר

**מאת:** cowork-dev · **אל:** cc-macbook · **01.09** · **T-193 · T-88 · T-192ב**
**מצב:** מאובחן במלואו. **אל תחקור מחדש — בנה.**

---

## 🔴 קרא את זה קודם: הכותרת של הבוקר לא תקפה

הבוקר פורסם *"‏`pnl_sierra` = 44.9% · RR 1.00 · איזון 50.0% — **האמת**"*.
**גם המספר הזה מוטה.** ‏`sc_study/MES_AI_DataExport_merged.cpp:2866`:

```cpp
double entry_price = parse_float("\"price\"");   // ← מה-JSON שאנחנו שלחנו
```

**מחיר-הכניסה ביומן הוא המחיר שביקשנו, לא המחיר שסיירה מילאה.** רגלי-היציאה
משתמשות ב-`ti.AvgFillPrice` **אמיתי** — כלומר צד אחד של החישוב הוא ברוקר וצד שני
הוא כוונה. ⇒ **כל `pnl_sierra`, כולל 57 שורות ה-`MATCH`, שגוי ב-(החלקת-כניסה × חוזים × $5).**

זה סותר את ההצהרה בראש `sierra_pnl_reconcile.py:16` (*"Money is read from Sierra ONLY"*),
ותואם בדיוק את ראיית-T-88 על `#760` (יומן 7680.00, מילוי 7677.75 — **2.25 נק' = $11.25 לחוזה**).

**⇒ פריט 3 להלן הוא התיקון החשוב ביותר בפקודה הזו.** בלעדיו אין לנו מספר-אמת בכלל.

---

## הרקע במשפט

ל-**105 מתוך 183** עסקאות live/demo אין `pnl_sierra`. השורש **אחד**, ב-DLL.

---

# פריט 1 · 🔴 השורש — `FLATTEN` לא כותב מילוי, **ומשמיד את מי שהיה יכול**

`sc_study/MES_AI_DataExport_merged.cpp:3636-3644` — **כל המטפל:**

```cpp
else if (cmd_content.find("\"FLATTEN_ACCOUNT\"") != std::string::npos)
{
    int r = sc.FlattenAndCancelAllOrders();
    result_status = (r >= 0) ? "FLATTEN_ACCOUNT_OK" : "FLATTEN_ACCOUNT_FAIL";
    order_err = r;
    for (int ci = 1; ci <= 9; ci++) sc.GetPersistentInt64(ci) = 0;   // ← מוחק את המזהים
    sc.GetPersistentInt(103) = 1;                                    // ← exit_written
    sc.AddMessageToLog("MEMS26: FLATTEN_ACCOUNT executed (FIX-11)", 1);
}
```

**ל-DLL יש בדיוק 4 אתרי-כתיבה ל-`fills_path`** (`ENTRY` :2998 · `EXIT` :3613 · `T1-T4` :3728 ·
`STOP` :3751). **‏FLATTEN אינו אחד מהם.** ‏`AddMessageToLog` הולך ללוג-ההודעות של סיירה —
**קובץ שהיומן לא קורא.**

**והנזק השני חמור מהראשון:** ‏`GetPersistentInt(103) = 1` הוא `p5_exit_written`, ותנאי-השמירה
של המנטר הוא `p5_exit_written == 0` (`:3707`). ⇒ **כל רגל-ברקט שטרם נצפתה `FILLED` הופכת
בלתי-ניתנת-לדיווח לצמיתות.** ‏`FlattenAndCancelAllOrders()` **מבטל** את רגלי-ה-OCO
(סטטוס `CANCELED`, לא `FILLED`) ומגיש פקודות-שוק חדשות שמזהיהן מעולם לא נרשמו.

**אותו פגם ב-`:3650-3654` (CANCEL) וב-`:3327-3338` (FLATTEN_ORPHAN).**

## מה לבנות — **1א קודם, והוא backend בלבד**

**‏1א · אפס נגיעה ב-DLL.** ב-`exit_verifier.py:259-266`, ברגע-האישור לפני `p.on_confirmed()`,
לרשום **שורה אחת** ליומן:
```json
{"kind":"FLATTEN","ts":<now>,"order_id":<quality.sierra_order_id>,
 "price":<px>,"contracts":<p.contracts>,"source":"activity_log"}
```
‏`sierra_order_id` **כבר** ראשון ב-`_CHILD_ID_KEYS` (`sierra_pnl_reconcile.py:46`) ⇒ **אפס
שינוי במתאם.** ובנוסף להעביר את אותו `px` ל-`close_trade(..., exit_price=px)`
ב-`bar_level_detector.py:1196`, כדי ש-T-160 יפסיק לכתוב `UNPRICED`.

**🔴 שאלת-האמת שחייבת להיפתר לפני שכותבים שורת-קוד:** **מאיפה `px`?**
המקור היחיד שהוא באמת ברוקר הוא מנת-ה-`CLOSED_TRADE_PNL` ש-`fill_poller._check_activity_exits`
כבר מפרק (`fill_poller.py:459-497`). **אסור להשתמש ב-`LastTradePrice`** — זה מספר מסונתז,
בקובץ שהחוזה שלו הוא "סיירה בלבד". **אם אין `px` ברוקרי — לא לכתוב שורה.** ‏`UNPRICED`
כן הוא התשובה הנכונה (כלל 1). **תג `"source"` חובה** כדי שיהיה אפשר להבחין משורות-DLL.

**‏1ב · DLL, רק אחרי ש-1א חי.** לצלם `PositionQuantity` ו-`GetPersistentInt64(1)` **לפני**
ה-flatten · **למחוק את `GetPersistentInt(103) = 1;`** · לחמש בדיקה נדחית שכותבת
`kind:"FLATTEN"` כשהפוזיציה מגיעה ל-0. **‏SIM בלבד, snapshot לפני, אחרי 01:00.**

**‏1ג · שורה אחת, לעשות בכל מקרה.** ‏`sierra_pnl_reconcile.py:41` ו-`sierra_ledger.py:28`:
להוסיף **`"EXIT"`** ל-`EXIT_KINDS`. סוג-היציאה היחיד שה-DLL **כן** יודע לפלוט אינו
מוכר לאף אחד משני הקוראים.

---

# פריט 2 · 🟠 חלון-אובדן ב-`fill_poller` (TOCTOU)

`fill_poller.py:963-1015`:
```python
976    content = FILLS_PATH.read_text().strip()   # קורא
1004   with open(_journal, "a") as jf: ...        # מיומן
1013   FILLS_PATH.write_text("")                  # מוחק
```
**כל שורה שה-DLL מוסיף בין 977 ל-1013 נמחקת** — לא מעובדת, לא מיומנת, **בלי אזהרה**.
החלון מכיל `_process_fill` לכל מילוי (כתיבות-DB, פוש-ntfy, `set_sierra_order_ids`) ⇒
**אינו מיקרו-שניות**, ותחת Wine אין נעילת-קבצים.

**התיקון (5 שורות, אפס סיכון):** `os.rename(FILLS_PATH, ...".claimed")` **תחילה** — אטומי
באותה מערכת-קבצים — ואז לקרוא/ליומן/לעבד את הקובץ המשונה, ואז `unlink`. ה-`ofstream(app)`
הבא של ה-DLL ייצור את הקובץ מחדש.

**‏⚠️ לא הוכח שזה אי-פעם הפיל שורה.** אל תבנה מעבר ל-5 השורות.

---

# פריט 3 · 🔴🔴 מחיר-הכניסה ביומן הוא כוונה ולא מילוי

**זה הפריט שמכריע אם יש לנו בכלל מד-כסף.**

`cpp:2866` מפרסר `entry_price` מ-**פקודת-ה-JSON שלנו**, וכותב אותו ליומן (`:3019`).
רגלי-היציאה משתמשות ב-`AvgFillPrice` אמיתי.

**מה לבנות:** לקרוא את מחיר-הכניסה **מסיירה** אחרי המילוי — `sc.GetOrderByOrderID(parent)`
⇒ `ti.AvgFillPrice` — ולכתוב **אותו** ליומן. ‏DLL ⇒ SIM, snapshot, אחרי 01:00.

**עד שזה נוחת — חובה דיווחית:** כל דוח שמצטט `pnl_sierra` **חייב** לשאת את המשפט
*"מחיר-הכניסה הוא מחיר-הפקודה ולא מחיר-המילוי; המספר מוטה בהחלקת-הכניסה."*
**ולמדוד את הגודל:** ‏`AVG(|journal.entry_price − sierra fill price|)` על מה שאפשר לשחזר —
זה נותן את **תיקון-הביאס ל-44.9%**.

---

# פריט 4 · 🟠 הכשל שקורא כמו הצלחה

`sierra_pnl_reconcile.py:227` — ‏`net_error` מסכם רק `delta`, ו-`delta=None` בכל שורת
`incomplete`. ⇒ **הכסף שנעלם תורם 0.00 לאזעקה.** ‏T-88 תפס בדיוק את זה:
`DIVERGENT 0 · net book error +0.00` בזמן ש-$96.25 חסרים.

**התיקון:** להוסיף `unpriced_contracts` ליד `net_error`, ולעולם לא להדפיס `+0.00` כשיש
`incomplete>0`.

**ובנוסף — האינווריאנט היחיד שאינו תלוי בהתאמת-מזהים:** בדיקה יומית
`Σ ENTRY + Σ EXIT ביומן == sierra_state.daily_total_qty_filled`. **היא הייתה תופסת את
16+13≠32 ביום עצמו.** ‏`daily_total_qty_filled` **אינו נקרא היום ע"י שום קוד ב-backend.**

---

## סדר-ביצוע

**‏1ג ו-4 (דקות, אפס סיכון) → 2 (5 שורות) → 1א (backend, פותח את 53 העסקאות) →
1ב ו-3 (DLL, SIM, אחרי 01:00, snapshot).**

## אימות-סגירה — דו-כיווני, לכל פריט

| פריט | חייב לעבור | וחייב עדיין להיכשל |
|---|---|---|
| 1א | עסקת-FLATTEN ⇒ שורת-יומן + `pnl_sierra` לא-NULL | **אין `px` ברוקרי ⇒ `UNPRICED`, בלי מחיר מומצא** |
| 2 | שורה שנוספת תוך-כדי-קריאה **שורדת** | — |
| 3 | ‏`journal.entry_price == ti.AvgFillPrice` | — |
| 4 | ‏`incomplete>0` ⇒ הדוח **אינו** מדפיס `net_error=+0.00` | ‏0 incomplete ⇒ הדוח שקט |

**כלל 5 על כל שורה: פקודה + פלט גולמי. לא "עבר".**

---

## ‼️ לפני שאתה בונה — סתירה שלא הוכרעה

`fill_poller.py:344-351` טוען: *"‏The deployed DLL (v8.2.0) does NOT write exit fills
(T1/T2/T3/STOP) — only the undeployed `_merged.cpp` has Pipeline 5"*.
**אבל ראיית 31.08 סותרת** — 4 שורות `MATCH` עם `covered == contracts` ⇒ מילויי-יציאה
**כן** מגיעים. ⇒ **ההערה מיושנת או שהפריסה השתנתה. להכריע לפני שנוגעים ב-DLL** —
זה קובע אם ה-DLL בכלל בלולאה.

## אסור

‏DLL בלי `mems26_snapshot.sh` · ‏DLL לפני 01:00 · לגעת בחשבון החי · **להמציא `px`** ·
‏`logger.debug` על כשל-כתיבה · לכתוב שורת-יומן בלי `"source"`.
