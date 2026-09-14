# פריט 3 מתוך 8 — יעדים וסטופ של דלתון לכל כניסת-קצה ביום Normal/Neutral (לא רק לכפולות)
(פריט 2 אומת ומקובל — `efaaf833`; הגולדן 11.09 17:30:03 SHORT 7674.75 stop 7679 T1 7663.25 T2 7659.75 → ADMIT. פריט אחד, קומיט אחד, בלי שאלות.)

## למה
דוקטרינת 11.09 09:50: "ביום נורמלי סוחרים את ההיפוך ב-VAH/VAL **עד ל-POC, או כל עוד הוא ממשיך — עד הצד השני**." היום זה נכון רק ל-`CEILING_FLIP_TOUCH2` (פריט 2). כל כניסת-קצה אחרת שעוברת את כלל-המיקום (ZLR/REACTIVE/GB100/INITIATIVE ב-VAL/VAH) עדיין מקבלת יעדים מהסולם (`#68 structural`/`STEP_SCALED_LADDER`/`STRUCT_TARGETS_WIN`) וסטופ מה-resolver — T1 יכול ליפול קצר או להתפזר, וה-R:R מחושב על סולם שאינו הדוקטרינה. 11.09 18:55 REACTIVE_SHORT 7673.25 (העסקה הנכונה שנכתבה בהרנס) קיבל סולם, לא POC→VAL.

## מה לבנות (בדיוק זה)
1. בשער, אחרי שכלל-המיקום (T-319b-lite) **מאשר** setup בשורת Normal/Neutral (`_dp_location_checked=True`): להוסיף ל-setup `metadata.edge_fade_targets=True` ולחשב:
   - **T1 = POC** · **T2 = קצה-הערך הנגדי** (SHORT: VAL, LONG: VAH) · **T3 = קצה-ה-IB הנגדי**. אם POC בצד הלא-נכון או בתוך `0.65×stop` מהכניסה ⇒ T1 = קצה-הערך הנגדי, T2 = קצה-IB, T3 = None. שרשרת מונוטונית (T-335).
   - **סטופ = הקצה שממנו נכנסים + טיק** (SHORT: max(VAH, IB_high אם המחיר בין) + 0.25; LONG: המקביל) — `stop_is_structural=True` ⇒ הפטור של פריט 2 חל (resolver/floor/ladder לא נוגעים). אם ה-setup כבר הביא `structural_anchor` (כפולות) — העוגן גובר.
   - הגודל נגזר מהסטופ; n<3 ⇒ אין כניסה. runner=false ב-Normal/Neutral.
2. `STRUCT_TARGETS_WIN`/`#68 structural targets` **לא** דורסים setup עם `edge_fade_targets` (רק ECON-DIFF).
3. שורות Variation/Trend — **ללא שינוי** (הסולם נשאר שם; זה פריט אחר).
4. `mobile_monitor` dalton-block: `targets_source: dalton_edge|ladder`.

## golden (שורות גולמיות בדיווח)
- 11.09 `18:55:03 REACTIVE_SHORT 7673.25` ⇒ נשאר **WRITE** יחיד ב-11.09, עם `stop=7676.00–7676.25` (VAH 7675.75 + טיק), `T1=7667.75` (POC), `T2=7660.25` (VAL), `T3=7659.75` (IB-low), n נגזר.
- 11.09 `17:10:0x` ZLR LONG 7671–7674 ⇒ עדיין `location` (לא נוגעים בחסימות).
- 10.09 (Normal מ-17:35): `17:40:03 DOUBLE_BOTTOM_EE_LONG 7612.5` ⇒ עדיין `location near_vah`; אפס כתיבות.
- 08-03 · 08-04 · 09-09: **אפס שינוי** בכתיבות (אין שם שורת-Normal עם כניסת-קצה מאושרת — אם יש, להדביק את ההבדל).
- הרנס ×5 + `--restart-at 18:29` ירוק, 0 Traceback; `test_edge_fade_targets.py`: SHORT מ-VAH ⇒ T1=POC/T2=VAL/T3=IB-low; POC קרוב מדי ⇒ T1=VAL; מוטציה — setup בשורת Variation לא מקבל את היעדים האלה.

## דיווח
קומיט אחד, TASK_LOG+STATUS_BOARD באותו קומיט, LOG חתום עם השורות הגולמיות. **לעצור ולכתוב "סיים פריט 3".** אין ריסטארט (המתוזמן 15:45).
