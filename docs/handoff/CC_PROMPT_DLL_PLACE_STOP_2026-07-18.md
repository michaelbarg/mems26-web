# CC משימה 1ב — op חדש ב-DLL: `PLACE_STOP` (סטופ-מגן לפוזיציה-יתומה)

**פסיקת-מייקל 2026-07-18: "לבצע עכשיו את משימה 1 בשלמותה."**
**מבצע: cc-macbook · מארגן/מעקב: cursor-agent · מאמת: cowork-dev · Remote Build: מייקל.**
**זה שינוי ב-C++ שמדבר עם הברוקר — הרמה הכי רגישה. אפס ניחושים.**

## למה
משימה 1א הושלמה: הגייטינג + 11 טסטים + 8 תנאי-בטיחות בנויים ואומתו (27 עוברים).
`_place_orphan_stop()` הוא stub שמחזיר `NO_DLL_PATH` — **כי אין op ב-DLL שמניח סטופ עצמאי.**
בלי ה-op הזה ההגנה לא פועלת. **המשימה: לבנות אותו.**

## מה שכבר אימתנו בקוד (אל תחזור על החקירה — התחל מכאן)
- **שרשרת-הדיספאץ':** `sc_study/MES_AI_DataExport.cpp` — שרשרת `else if (cmd_content.find("\"OPNAME\"") != npos)`.
  קיימים: `BUY/SELL` (‎:1025, ‎`sc.BuyEntry/SellEntry` עם ברקט מצורף) · `MODIFY_STOP` (‎:1260) ·
  `MODIFY_TARGET` (‎:1356) · `EXIT` (‎:1383) · `FLATTEN_ACCOUNT` (‎:1447) · `CANCEL` (‎:1462).
- **תבנית-הכתיבה:** `s_SCNewOrder o; o.OrderQuantity/OrderType/TimeInForce/TradeAccount` →
  קריאת-ACSIL → `result_status = "..._OK"/"..._FAIL"`.
- **פרסרים קיימים:** `parse_float("\"key\"")`, `parse_str("\"key\"", buf, size)` — השתמש בהם.
- **`account` מהפקודה** נקרא ל-`o.TradeAccount` — **זה מה ששולט SIM מול LIVE. חובה לשמר.**

## מה לבנות

### 1) DLL — op חדש `PLACE_STOP`
הוסף ענף לשרשרת (אחרי `MODIFY_TARGET`, לפני `EXIT`):
- **קלט:** `qty` (int, >0) · `price` (double, >0) · `side` = `"LONG"`/`"SHORT"` (צד ה**פוזיציה** להגן עליה) · `account`.
- **סוג-הוראה:** `SCT_ORDERTYPE_STOP`, `Price1 = price`, `OrderQuantity = qty`, `TimeInForce = SCT_TIF_DAY`.
- **כיוון (reduce-only — קריטי):**
  - פוזיציה **LONG** → סטופ-מכירה מתחת → `sc.SellExit(o)`
  - פוזיציה **SHORT** → סטופ-קנייה מעל → `sc.BuyExit(o)`
- **`result_status`:** `PLACE_STOP_OK` (r≥0) / `PLACE_STOP_FAIL` (אחרת) / `PLACE_STOP_BAD_INPUT` (qty≤0 או price≤0 או side לא-חוקי).
- **חובה: לעולם לא לפתוח פוזיציה חדשה.** רק משפחת-Exit (reduce-only). אם יש ספק שההוראה עלולה לפתוח — **עצור ודווח**.

### ⚠️ ההיסטוריה שחייבת להישקל (אל תתעלם)
`CLAUDE.md §op=EXIT` — `sc.SellExit/BuyExit` החזירו `r=-1` בעבר. **השורש היה:** לכל חוזה כבר היה
OCO-מצורף → לא נשאר חוזה חופשי לצאת איתו. **המקרה שלנו שונה:** יתום = `working_orders == 0`,
**אין OCO מצורף** → אין קונפליקט. **זו השערה מנומקת, לא עובדה — חובה להוכיח בסים.**
אם בסים זה מחזיר `-1` גם ליתום-נקי: **עצור, אל תעקוף, דווח.**

### 2) Backend — לחבר את ה-stub
`backend/v9/services/sierra_position_reconciler.py::_place_orphan_stop` — להחליף את
`NO_DLL_PATH` בכתיבת פקודת `PLACE_STOP` דרך הנתיב הקיים (`sierra_command.py`), ולהוסיף `PLACE_STOP`
לרשימת-ה-ops שהוא יודע לפלוט. לקרוא את `trade_result.json` ולהחזיר `(True, "PLACE_STOP_OK")` /
`(False, "<status>")`. **הדגל נשאר OFF.** כל 8 תנאי-הבטיחות שכבר נבנו נשארים בתוקף.

### 3) טסטים
- DLL: אין לנו הרנס ל-C++ — האימות הוא **סים** (סעיף 5).
- Backend: הרחב את `test_orphan_auto_stop.py` — `_place_orphan_stop` עם stub-כותב מדומה →
  מוודא שנכתבה פקודה עם `op=PLACE_STOP`, qty/price/side נכונים, ו-`account` נשמר;
  `PLACE_STOP_FAIL` → `(False, ...)` בלי קריסה. **11 הטסטים הקיימים חייבים להישאר ירוקים.**

## פרוטוקול-פריסה (חובה, לפי CLAUDE.md §Change-Safety)
1. **`./scripts/mems26_snapshot.sh "pre-dll-place-stop"` — לפני שנוגעים ב-DLL. חובה.**
2. עריכה ב-`sc_study/MES_AI_DataExport.cpp` בלבד.
3. `./scripts/build_monolithic_cpp.sh --deploy` → `~/SierraChart/ACS_Source/`.
4. **מייקל: Remote Build בסיירה + reload study.** (אתה לא עושה — זו פעולה שלו.)
5. `./scripts/mems26_verify.sh` — DLL-פרוס == ריפו.

## אימות-סים (חובה — בלעדיו הדגל לא נדלק)
**gate: `is_sim=1` מאומת מהאקספורט לפני כל פקודה. אפס PLACE_STOP על לייב.**
1. צור **יתום** בסים: כניסה ידנית בסיירה-סים בלי שהמערכת תדע (‎-2 חוזים).
2. אמת שהרקונסיילר מזהה: `Sierra says -2`, `working_orders=0`.
3. הדלק `ORPHAN_AUTO_STOP_V1=1` **בסביבת-הסים בלבד** (לא ב-.env של הלייב).
4. **הוכח:** הסטופ **נח בפועל** בסיירה, בצד הנכון (מעל, לשורט), במחיר הנכון, על כל הכמות;
   `working_orders` עבר מ-0 ל-1; **הפוזיציה לא גדלה** (עדיין ‎-2, לא ‎-4).
5. מקרה-מראה: יתום **LONG** → סטופ מתחת.
6. חד-פעמיות: מחזור-רקונסיילר נוסף → **לא** מניח שוב.
7. הדבק: שורות-לוג + `trade_result.json` + מצב-הסיירה לפני/אחרי.

## מה שאסור
- ❌ לא לגעת ב-`.env` ולא ב-`RULED_FLAGS.yaml` — ההדלקה היא פסיקה נפרדת של מייקל.
- ❌ לא לגעת ב-op=EXIT הקיים ולא ב-PLACE.
- ❌ לא לפרוס ללייב, לא לחמש.
- ❌ אם `sc.BuyExit/SellExit` מחזיר ‎-1 גם ליתום-נקי — **לא לעקוף בשום דרך**. לעצור, לדווח כאן.

## תוצר
שורה ב-`LIVE_CHANNEL.md` עם: diff-DLL (מה נוסף), פלט-טסטים גולמי, **ראיות-הסים המלאות**,
וסעיף **NOT-DONE** חובה. אני (cowork-dev) מאמת הכל עצמאית לפני שזה עולה לפסיקת-הדלקה של מייקל.
