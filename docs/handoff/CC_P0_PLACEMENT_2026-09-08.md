# ‏🔴 P0 · 08.09 16:50 — החלטת-לייב שאינה מגיעה לברוקר, ואיש אינו שואל

**מאת:** cowork-dev · **אל:** cc-macbook · **פסיקת-מייקל 16:47: "מאשר".**
**עבודה אחרי 23:00 (סגירת-שוק). אין ריסטארט ב-RTH.**

---

## מה קרה היום, גולמי

```
16:40:08 [SierraCmd] T-214: PLACE rejected — t3=0.0 invalid on 3 contracts
16:40:08 [Gateway]   LIVE trade TM id=1220: SHORT OPENING_DRIVE t1=7691 t2=7666 t3=0.00
                     ← כאן נשלחה התראת-הטלפון למייקל
16:40:26 [Reconciler] SYS-3 DIVERGENCE: TM says -3 ['#1220(live,3c/assumed_open)'], Sierra says 0
16:40:29 [fill_poller] POSITION_TRUTH: Sierra FLAT 20s → closed 1220 + freed slot
```
`command_queue/` **ריקה**; `COMMAND QUEUED` האחרון הוא **#405 מאתמול 19:29**. ‏**אף פקודה לא נכתבה היום.**

## שלושה כשלים, שכבה אחר שכבה

**‏1 · צורת-החזרה השנייה.** ‏`sierra_command.py:903` מחזיר `{"rejected": True, "reason": "t3_missing"}`.
`trading_gateway.py:4843-4859` מטפל ב-`ValueError` (`place_refused`) — **ואינו בודק את המפתח `rejected`.**
אותו כשל, שתי צורות-החזרה, קורא אחד עודכן. ⇒ הגייטוויי רשם "LIVE trade", תפס סלוט, החזיר `PENDING`.

**‏2 · ההתראה מקדימה את הביצוע.** ‏`:4871` שולח `ntfy.on_fire` **מיד אחרי בניית-הפקודה**, לפני
כל אישור-כתיבה. ⇒ הסיגנל הרם ביותר במערכת אומר "ירינו" ברגע ה**החלטה**, לא ברגע ה**שליחה**.

**‏3 · ואין שום אזעקה על "הוחלט-לייב ולא נכתבה פקודה".** הרקונסיילר **כן** ראה
(`Records ≠ reality!`, `phantom-heal streak 1/3`) — ופירש זאת כ**רישום-מיושן לרפא**, לא ככשל-שליחה.
‏20 שניות ⇒ נסגר ⇒ נעלם. **שישה סשנים ככה.**

## ‏🔴 והשורש המבני: מסלול-הפתיחה כולו בלתי-ניתן-לשליחה

```
opening_entry.py:292-293    "t2": None,  "t3": None      ← כל setup של פתיחה, תמיד
T3_REQUIRED_V1=1            (פסיקת-מייקל 01.09) דוחה PLACE כש-t3<=0 ו-contracts>=3
RISK_MIN_CONTRACTS=3        ⇒ contracts תמיד >=3
⇒ 100% מעסקאות-הפתיחה נדחות מאז 02.09
```
**‏T-214 עצמו נכון** — מייקל פסק שכל חוזה נושא יעד. **מה שלא נעשה: לא נשאל אילו יַצְרָנים פולטים
`t3=None`.** החגורה נבדקה על עצמה (4 טסטים) ולא על האוכלוסייה שעליה היא חלה.

---

# מה לבנות — לפי הסדר

## ‏§1 · הגייטוויי מטפל ב-`rejected` (**באג טהור — אין פסיקה, בונה ומדליק**)

אחרי `command_from_setup`, לפני שורת-הלוג ולפני ה-ntfy:
```python
if isinstance(command, dict) and command.get("rejected"):
    self._last_live_abort = ("place_rejected", command.get("reason") or "?")
    logger.error("[Gateway] LIVE PLACE REJECTED (%s: %s) — cancelling trade %s, freeing slot",
                 command.get("reason"), command.get("detail"), trade_id)
    self._trade_manager.close_trade(trade_id, reason=str(command.get("reason") or "PLACE_REJECTED"),
                                    outcome_override="CANCELLED")
    self._trade_manager._db.commit()
    return None
```
**‏`return None` לפני ה-ntfy** ⇒ אין התראת-שווא. הסלוט משתחרר מיד ולא אחרי 20 שנ'.
**אותו טיפול ב-`_execute_demo`.** **טסט:** ‏setup עם `t3=None` ו-3 חוזים ⇒ `route_setup` מחזיר
`live_blocked_by="place_rejected"` · אפס קריאה ל-`on_fire` · הסלוט פנוי · העסקה `CANCELLED`.
**מוטציה:** הסרת הבדיקה ⇒ נכשל.

## ‏§2 · אינווריאנט-השליחה — **זה מה שסוגר את המחלקה, לא את הבאג**

**כל החלטת-לייב חייבת לייצר פקודה כתובה, או שזו אזעקה.** לאחר `_execute_live` מוצלח:
לרשום `trade_id → ts` ב-`app.state`; ‏`fill_poller` בודק בכל טיק: אם עברו **>5 שניות** ואין
`COMMAND QUEUED`/קובץ-תור לאותו `trade_id` ⇒ `logger.critical` + `on_emergency` + סגירת-העסקה
כ-`PLACEMENT_FAILED`. **‏🔴 לא "phantom-heal" — כשל.**
**קבלה:** להזריק דחייה ⇒ ‏CRITICAL אחד + עסקה `PLACEMENT_FAILED` + סלוט פנוי, תוך ≤5ש'.

## ‏§3 · ה-ntfy עובר אחרי האישור

‏`on_fire` נקרא **רק** אחרי שהפקודה נכתבה בפועל (החזרה מ-`_write_command` עם `seq`/נתיב).
טקסט ההתראה יישא את מספר-הפקודה. **התראה = פקודה שיצאה, לא החלטה שהתקבלה.**

## ‏§4 · ‏`opening_entry` חייב t2/t3 — **ממתין לפסיקת-מייקל, אל תנחש**

היום יש רק `T1 = 1.5R` (`T1_BANK_R=1.5`). **אל תמציא סולם.** להכין את הקוד כך שהסולם מגיע
מפרמטר, ולהמתין להכרעה. **עד שתגיע — מסלול-הפתיחה נשאר חסום, וזה עכשיו חסום בקול** (§1+§2).

---

## אימות שאני אריץ

`git status` ריק · `guard_tests` · `flag_guard` · **טסט-§1 עם מוטציה** · **הזרקת-דחייה מייצרת
CRITICAL תוך 5ש'** · ‏`grep -c "COMMAND QUEUED"` על סשן-סים אחרי הזרקה.

## אסור

ריסטארט לפני 23:00 · להמציא t2/t3 לפתיחה · לכבות `T3_REQUIRED_V1` (החגורה נכונה — הבעיה שהיצרן
לא בונה יעד) · להשאיר את `rejected` שקט · לגעת ב-`awaiting_release`/הסלוט.
