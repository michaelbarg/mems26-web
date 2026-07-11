# CC — סופ"ש 11-12/07: השלמת התור לקראת שני (השוק סגור — חופש פעולה)

**חוזה:** CC_HANDOFF_CONTRACT.md. דוח חי: `docs/reports/CC_WEEKEND_REPORT_2026-07-11.md`
מתעדכן אחרי כל פריט (Rule 5: פקודה+פלט; NOT-DONE מפורש). ‏Cowork מבקר בשני 10:00
(ביקורת אוטומטית מתוזמנת מול docs/reports/MONDAY_CHECKLIST_2026-07-13.md).

## הקשר — חובה לקרוא לפני
1. `docs/handoff/CC_NIGHT_MEGA_2026-07-10.md` **כולל העדכונים 21:4x + 23:1x** — ליל-שישי לא רץ;
   רוב FIX-9..16 כבר בוצעו ע"י Cowork (מסומן שם, קומיטים 137be92 + I-62) — **אל תבנה כפול**.
2. `docs/reports/MONDAY_CHECKLIST_2026-07-13.md` — מה נבדק בשני בבוקר.
3. הריפו push-מעודכן ל-origin (9f74515). עבוד ודחוף — יש remote חי.

## התור (לפי סדר; פריט תקוע >45 דק' → NOT-DONE והלאה)
1. **hydration-PG** — להסיר את ה-SQLite-fallback מ-main.py (הבוט מדפיס
   "database disk image is malformed" בכל עלייה): ההידרציה כולה על PG דרך backend/v9/db/read.py
   + טסט. ‏DoD: בוט נקי מהשגיאה + daily_pnl משוחזר נכון.
2. **LaunchAgents** — ‏com.mems26.activity_feed (פידר **פר-חשבון**: קובץ-offset נפרד פר-account,
   ‏real+sim לפי המוד, KeepAlive-on-failure) · ‏com.mems26.frontend · ‏com.mems26.redis.
   עדכן SYSTEM_MANIFEST + snapshot לפני. ‏DoD: ריבוט-סימולציה (kickstart) מחזיר הכל.
3. **באג גרירת-יעד** — ‏MODIFY_STOP (סטופ 7604→7611.25) גרר בסיירה את יעד-8721 ‏7622→7629.25
   (Δ-אופסט זהה). צוד במונולית הפרוס (‏~/SierraChart/ACS_Source/MES_AI_DataExport.cpp הנוכחי =
   כבר כולל FLATTEN_ACCOUNT+sierra_state של Cowork) או ב-twconfig. היעד חייב להישאר במקומו.
   ‏DoD: טסט-סים אחרי reload: הזזת-סטופ ⇒ יעד לא זז.
4. **אינווריאנט S6 שבור** — ‏stop_wrong_side מתריע על סטופ-ברווח (LONG stop>entry אחרי T1 =
   רווח-נעול, לא שגיאה!). תקן: ‏wrong_side = הסטופ בצד-ההפסד של **המחיר** (LONG: stop>price).
   ‏SYSTEM6_SUPERVISOR=1 חי מאתמול — הצופה חייב להפסיק לזעוק על המצב הרצוי. + טסט.
5. **STALL_EXIT — בקטסט בלבד (flag-OFF, אין קוד-חי בלי פסיקה):** אחרי T1, מחיר נתקע ≥3 ברים
   בטווח ≤3 טיקים ליד קיצון-רגל/רמה + מומנטום דועך ⇒ מימוש-ראנר. הרץ על 30 ימי tp_audit:
   כמה ראנרים משתפרים/נפגעים, טבלה לפסיקת מייקל. הראיה: ראנר-350 דעך ממדף 7615-7617.5 לסטופ.
6. **2 endpoints ל-UX** — ‏GET /api/v9/s6/diagnose/{trade_id} · ‏GET /api/v9/trades/{id}/timeline
   (fills + stop_moves מ-cross_context + management-log + חסימות). הפרונט אצל צ'אט-המערכות.
7. **CERT test-debt** — פיקסטורות 21:00 האמיתיות (DOWN-גולמי→UP) + RED-סימטרי.
8. **t1=t2=t3 ladder-collapse** (337: שלושתם 7583.75) — אבחון+תיקון+טסט.
9. **NAKED_STOP_SUSPECT calibration** — לא לזעוק כשברקט-סטופ קיים ותקין (67 דק' אזעקה תקועה 07-10).
10. **decision_replay 2026-07-10** — עם הקוד החדש: היום חייב לצאת Neutral_Extreme; ‏07-09 נשאר
    Variation (צמד-הכיול של FIX-14). צרף diff מול הירי-בפועל.
11. **D1-EXIT הכנה** — ההוכחה האמיתית = write_exit_command פנימי על סים (ל-API אין action EXIT;
    דריל-ה-SELL פגע בנתיב PLACE). הכן תסריט-הוכחה מלא לריצה אחרי ה-reload של מייקל:
    BUY 2 → EXIT 1 → FLATTEN_ACCOUNT → ‏sierra_state.json מתעדכן ≤2ש'.
12. **ROADMAP_TO_LIVE.html + STATUS_BOARD** — עדכון מלא (חובת-פרוטוקול; נדחה פעמיים).

## שערים
- אסור לגעת בדגלים-פסוקים (47) בלי פסיקה. דגל חדש = default-OFF + REGISTRY+RULED.
- ‏.env/DLL/LaunchAgents = snapshot לפני (scripts/mems26_snapshot.sh). ‏flag_guard PASS אחרי.
- ‏Sierra reload = רק בתיאום מייקל (הוא עושה Remote Build+reload — 30 שניות).
- קובץ שנערך היום ע"י אחר (bar_level_detector, manager, structural_targets, relative_features,
  state_machine, fill_poller, sierra_position_reconciler, trade_commands, trade_activity_feed,
  sc_study/*) — משוך origin קודם והרץ את איחוד-הטסטים.
