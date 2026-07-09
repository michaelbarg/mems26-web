# CC — ‏DLL rebuild + דריל-ניהול מלא מול סיירה (07-09, לפני 16:00)

**רקע:** דריל-הבוקר הוכיח place→bracket→fills→exit→slot, אבל חשף: ‏(א) ה-DLL הפרוס מחזיר
ack קצר **בלי** ‏parent/target/stop ids (המקור כבר כותב אותם) → המיפוי-המוקדם ואישור-הסטופ
של ה-reconcile לא עובדים (NAKED_STOP false-positive); ‏(ב) פסיקת מייקל: הדריל חייב לתרגל
**ניהול** — הזזות סטופ, סגירה חלקית, סגירה-ופתיחה — לא רק כניסה-יציאה. ‏Rule 5 על הכל;
ראיות ל-`docs/reports/evidence_2026-07-09/`.

## שלב 0 — 🔴 תיקון קוד לפני הדריל: exit חייב לשטח את סיירה (ממצא חי 07-09 ‏11:45)
מייקל סגר-מערכת את עסקת-הדריל 318 → הרשומה נסגרה וה-slot שוחרר, **אבל הפוזיציה נשארה
חיה בסיירה** (המראה של תקלת-אתמול). השורש: ‏`/api/v9/trades/{id}/exit` (trades.py:144+)
קורא ‏close_trade + משחרר slot אך **לא שולח EXIT/CANCEL לסיירה**.
**תקן:** לפני ‏close_trade — אם ‏mode∈(demo,live) והעסקה עם ‏sierra_order_id: שלח
‏`write_exit` (כל החוזים הנותרים) + ‏CANCEL לבראקטים, המתן ל-ack (timeout קצר), רק אז
סגור רשומה; אם אין ‏ack — אל תסגור, צעק ‏CRITICAL. טסט אנטי-טאוטולוגי (exit על עסקה עם
ids → ‏write_exit נקרא; בלי ids → ‏CRITICAL). זה על נתיב-הכסף — עדיפות ראשונה.

## שלב 1 — ‏DLL rebuild + deploy (זה הזמן, פסיקת מייקל)
1. ודא שהמקור מכיל את כתיבת ה-ids ב-ack (‏sc_study/MES_AI_DataExport.cpp ‏~:1058) — אם חסר
   משהו לפי הצורך של ה-reconcile (סטטוס STOP_CONFIRMED?), הוסף **מינימלית**: ה-ack של
   ‏ORDER_SUBMITTED חייב לכלול ‏parent_id/target_id/stop_id (כבר במקור) — ורצוי גם ‏trade_id
   ‏echo מהפקודה (סוגר את ההיוריסטיקה most-recent-PENDING).
2. `./scripts/build_monolithic_cpp.sh --deploy` (עושה snapshot אוטומטי) → ‏Sierra ‏Remote
   Build → reload study — לפי `docs/runbooks/SIERRA_DLL_OPS.md`.
3. אימות: ירי SIM קצר → ‏trade_result.json מכיל ‏parent_id — הדבק את הקובץ.

## שלב 2 — דריל ניהול מלא (סיירה ב-Sim Mode, בתיאום מייקל)
עם עסקת SIM ‏3 חוזים פתוחה, בצע ותעד כל צעד (לוג backend + ‏Sierra Trade Activity + עיניים
של מייקל על המסך):
1. **בראקט:** ‏3 יעדים + 3 סטופים מוצמדים — צילום/‏activity log.
2. **הזזת סטופ מהמערכת:** קרא ‏POST ‏`/api/v9/trades/{id}/move_stop` אם קיים, אחרת דרך
   ‏TM ‏(`_emit_modify_stop`) — **הדבק את שורת ‏sc.ModifyOrder מלוג-ההודעות של סיירה
   ואשר שהסטופ זז על המסך** (ההוכחה החסרה של L2!).
3. **הזזת יעד:** ‏MODIFY_TARGET → אותה ראיה.
4. **סגירה חלקית:** ‏EXIT של חוזה אחד → פוזיציה 3→2 בסיירה + ‏fill נכתב + המוניטור "1/3".
5. **סימולציית T1:** תן ליעד הקרוב להתמלא (או הזז אותו אל המחיר) → ‏smart-BE/מבנה נשלח
   אוטומטית → ‏sc.ModifyOrder שני + ‏STOP-STRUCT anchor בלוג (`structure-trail anchor`).
6. **סגירה מלאה + פתיחה הפוכה:** ‏flatten → ‏SHORT ‏3ח חדש → בראקט חדש → ‏flatten סופי.
7. **‏NAKED_STOP שקט:** אחרי ה-rebuild — אפס ‏false-positives בזמן שהבראקט חי.
8. ניקוי: כל עסקאות ה-SIM סגורות עם ‏reason ברור, ‏slots פנויים, מייקל מחזיר ‏Sim ‏Off.

## שלב 3 — הזנת TradeActivityLog אוטומטית
ה-parse הידני של 310 עבד; הפוך לקבוע: תהליך/סקריפט שמזין את קובץ היום ללדג'ר בכל דקה
(או בכל poll) — כך שסגירות/הזזות ידניות של מייקל מזוהות בזמן-אמת, לא בדיעבד.

## דיווח
טבלת צעד→ראיה→PASS/FAIL. כשל כלשהו = עצירה + דיווח למייקל ולצ'אט-הפיקוח. בסיום עדכן
‏task_board (‏CONTRACTS-3 → verified · ‏L2 → verified אם שלב 2.2 עבר) + היומן.
