# CC — שכתוב op=EXIT: יציאה-חלקית על פוזיציה מבורקטת-מלאה · לביצוע 2026-07-14

**חוזה מחייב:** ‏docs/handoff/CC_HANDOFF_CONTRACT.md — טסטים אנטי-טאוטולוגיים, ראיות
פקודה+פלט-גולמי (Rule 5), סעיף **NOT-DONE** בסוף. עבודה על **מק-הפיתוח בלבד**; git הוא
ערוץ-הקידום; פריסת-DLL ל-iMac = משיכה שם + ‏Remote Build ע"י מייקל. **אין פריסה בזמן
עסקה פתוחה; רק לפני 15:55 IL או אחרי סגירה.** ‏snapshot לפני כל שינוי-DLL
(`scripts/mems26_snapshot.sh`, ‏`build_monolithic_cpp.sh --deploy` עושה אוטומטית).

## שלב 0 — הקשר (לקרוא לפני שורת-קוד אחת)

1. ‏`docs/handoff/IMAC_EXIT_PATH_TEST_2026-07-13.md` — האבחון המלא.
2. ‏STATUS_BOARD שורות ‏07-13 (‏"EXIT op r=-1 — ROOT CONFIRMED").
3. ‏`docs/runbooks/SIERRA_DLL_OPS.md` + ‏`docs/SYSTEM_MANIFEST.md` (משטחי-DLL).
4. הקוד: ‏`sc_study/MES_AI_DataExport.cpp` — נתיב-PLACE (‏~1013–1100, מבנה ה-3-OCO),
   מטפל-EXIT (‏~1301–1363), טבלת-השגיאות, וסלוטי-ה-persistent (מיפוי order-ids 1–7).

## הבעיה (מאומתת, לא לשחזר את האבחון)

‏PLACE מצמיד לכל חוזה קבוצת-OCO עצמאית (‏OCOGroup1/2/3, כ"א ‏Quantity=1 עם target+stop).
לכן **כל** חוזה "מחויב" לברקט, ו-`sc.SellExit/BuyExit` מחזיר ‏r=-1 — אין חוזה חופשי.
אומת ב-iMac (‏PID 20495): ‏EXIT_FAIL ‏r=-1 גם עם ‏ScaleOut (SetDefaults+per-call) וגם עם
‏TIF=DAY. ה-DLL הישן נכשל זהה — הנתיב מעולם לא עבד. אין קוראים חיים ל-`_emit_exit`
(‏manager.py:229) — אז אין שבר-חי; זו בנייה-קדימה לפיצ'רים הכבויים (‏STALL_EXIT,
‏S6-AUTOCORRECT, ‏OPPOSITE_EXIT) ולסגירה-ידנית-חלקית עתידית.

## הדרישה — op=EXIT v2 (cancel-then-exit)

שכתב את מטפל-ה-EXIT (‏cpp ‏~1305) ללוגיקה הבאה, **בלי לגעת בנתיב-PLACE**:

1. **בחירת החוזה-היוצא (דטרמיניסטי):** קבוצת-ה-OCO הפעילה עם ה-target ה**רחוק** ביותר
   מהמחיר (C3 קודם, אז C2, אז C1) — "חותכים את הראנר", שומרים את הקרוב-למימוש.
   אם ‏order_id ספציפי הגיע בפקודה (‏sierra_bracket_id) — הוא גובר.
2. **ביטול-הברקט של החוזה הזה בלבד:** ‏`sc.CancelOrder` על ה-target שלו (ה-OCO מפיל
   את אח-הסטופ אוטומטית — לאמת מול ‏ACSIL: אם לא, לבטל את שניהם מפורשות).
3. **יציאת-שוק מיידית:** עכשיו יש חוזה חופשי → ‏`sc.SellExit/BuyExit` עם ‏Quantity=1,
   ‏TIF=DAY (או market הפוך ישיר — לבחור את היציב, לתעד למה).
4. **רשת-ביטחון NEVER-NAKED:** אם צעד-3 נכשל (‏r<0) אחרי שהברקט כבר בוטל —
   **להחזיר מיד סטופ-מגן** לחוזה (re-place stop במחיר-הסטופ המקורי מהסלוטים) ולכתוב
   ‏`EXIT_FAIL_RESTORED`. בשום תרחיש לא נשאר חוזה בלי סטופ.
5. **result עשיר תמיד:** ‏`EXIT_OK` עם ‏{exited_group, cancelled_ids, exit_order_id} ·
   ‏`EXIT_FAIL`/`EXIT_FAIL_RESTORED` עם ‏r ושלב-הכשל. עדכון סלוטי-persistent בהתאם
   (הקבוצה שיצאה = 0). ‏fills-journal מקבל שורת-EXIT אמיתית (‏order_id של היציאה, לא r).
6. ‏`contracts>1` = לולאה על צעדים 1–5 (קבוצה-אחר-קבוצה, עצירה בכשל הראשון).

**אסור:** לשנות את מבנה-ה-PLACE/OCO · ‏FlattenAndCancelAllOrders בתוך EXIT (זה CANCEL) ·
"תיקונים אגביים". השינוי הקטן-הנכון בלבד.

## אימות (Rule 5 — פקודה+פלט, אנטי-טאוטולוגי)

בנה ‏`scripts/exit_op_drill.sh` (בסגנון ‏d1_exit_proof.sh) שמריץ על **SIM** (שער
‏is_sim=1 חובה לפני כל פקודה):

```
BUY 3 (stop+t1+t2+t3)  → qty=3, working=6 (3 targets+3 stops)
EXIT 1                  → qty=2 · working=4 · trade_result=EXIT_OK{exited_group=3}
                          ✔ אנטי-עירום: ה-orders שנותרו כוללים 2 סטופים!
EXIT 1                  → qty=1 · working=2 · exited_group=2
FLATTEN_ACCOUNT         → qty=0 · working=0
תרחיש-כשל (אופציונלי בסים): EXIT כשה-qty=0 → EXIT_FAIL נקי, בלי side-effects
```

ההוכחה המכרעת היא **‏qty יורד + הסטופים-הנותרים קיימים**. ‏result ריק/‏r כ-order_id
בפילים = כשל-הדיווח הישן — לוודא שנעלם.

## פריסה

1. מק-פיתוח: קוד → ‏`./scripts/build_monolithic_cpp.sh --deploy` (סנאפשוט אוטומטי) →
   קומיט+פוש (קוד + סקריפט-דריל + עדכוני-דוקס באותו קומיט).
2. ‏iMac: כפתור-עדכון (מזהה שינוי-sc_study ומריץ בילד) → **מייקל: ‏Remote Build + reload**
   → הרצת ‏exit_op_drill.sh שם על SIM → ראיות.
3. עדכן: ‏STATUS_BOARD (שורש+תיקון+ראיה) · ‏DEV_BACKLOG (+`gen_task_board.py`) ·
   ‏SIERRA_DLL_OPS.md · ‏NOT-DONE מפורש.

## חלק B — שני תיקונים נוספים באותו מחזור-DLL (דיווח iMac 07-13 pm)

מאחר שה-DLL נפתח ממילא, לבצע גם — שניהם ב-`sc.*` order-path של אותו סטאדי:

**B1 — כשל-שקט: ‏op=PLACE לא-מזוין לא כותב result (מפר "No silent failures").**
תסמין (iMac): ‏BUY עם ‏Input21=0 → הפקודה נצרכת אבל ‏trade_result.json נשאר ריק/ישן
(אין ‏ACK_SHADOW). ‏FLATTEN כן כותב → נתיב-הכתיבה תקין. אבחון-קוד (אומת Cowork-dev):
זרוע-ה-disarmed ב-`MES_AI_DataExport.cpp:1177-1178` קובעת `result_status="ACK_SHADOW"`,
והכותב-הגנרי ב-1403 מותנה ב-`!result_written` — אבל התוצאה ריקה, אז או ש-`result_written`
לא מתאפס פר-פקודה (בדוק את ההכרזה ב-~1010 מול לולאת-הפקודות) או שהזרוע לא מגיעה ל-1403.
**דרישה:** ‏op=PLACE לא-מזוין **תמיד** כותב ‏`{"status":"ACK_SHADOW",...}` (או `DISARMED`)
ל-result. לוודא ש-`result_written` מאותחל לכל פקודה.

**B2 — לחשוף את מצב-החימוש ב-heartbeat (עונה ישירות ל"איך יודעים שמחומש בפתיחה").**
ל-`sierra_state.json` (הבלוק שנכתב כל שנייה) להוסיף ‏`"order_placement_armed": 0|1` =
ערך `EnableOrderPlacement.GetInt()`. כך הסוכן קורא חימוש בלי לשלוח פקודת-בדיקה.
**בונוס (אם קל):** כשהחימוש 0 אחרי reload — שורת-אזהרה בלוג-סיירה ("DISARMED after
reload — re-arm Input 21"), כי ‏re-add מאפס ל-0 בשקט והשאיר את המערכת "אילמת+לא-מחומשת".

**אימות B (Rule 5):** ‏Input21=0 + BUY → ‏result=`ACK_SHADOW` (לא ריק) **וגם**
‏`order_placement_armed:0` ב-state · ‏Input21=1 + BUY → ‏`ORDER_SUBMITTED` qty→1 +
‏`order_placement_armed:1`. את שלושת התיקונים (A+B1+B2) לאמת בריצת-`exit_op_drill.sh` אחת.

## גבולות

זו עבודת-DLL בלוגיקת-מסחר — **מאושרת ע"י מייקל לביצוע (פסיקת 07-13/14)** בסים בלבד.
חיווט-קוראים ל-`_emit_exit` (הפעלת STALL/S6-autocorrect וכו') **לא** בסקופ — כל אחד מהם
פסיקת-הדלקה נפרדת. אם מתגלה שה-OCO-sibling לא מתבטל אוטומטית או כל הפתעת-ACSIL —
עצור, תעד, דווח; אל תאלתר נתיב-חלופי בלי אישור.
