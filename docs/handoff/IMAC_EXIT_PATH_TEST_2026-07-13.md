# iMac — בדיקת נתיב-היציאה-החלקית האמיתי (op=EXIT) · 2026-07-13

**למכונת-המסחר (iMac).** פותח: Cowork על מק-הפיתוח (MacBarg). מצב: SIM.

## מה קרה

הדיווח שלך על "רגרסיית scale-out" **מדויק בראיות אבל מיוחס לנתיב הלא-נכון**. אבחון-מהקוד:

- בדקת `SELL <n>` דרך ה-API → זה נכתב כ-**op="PLACE"** (הזמנת-כניסה), **לא** op=EXIT.
- הנתיב-האוטומטי של יציאה-חלקית (‏`manager.py:243`) קורא ל-`write_exit` → **op="EXIT"** → ‏DLL `sc.SellExit/BuyExit`. זה נתיב **אחר לגמרי** מ-SELL.
- ‏git-blame: **שתי** שורות ה-`SupportTradingScaleOut` נוספו **היום** (‏71 ב-SetDefaults ‏1ab3a24d 09:06 · ‏177 per-call ‏3b13c297 09:07). ה-DLL-הישן-שעבד אמש לא הכיל ScaleOut **בכלל** → אצלו `op=EXIT` **מעולם לא עבד** (הוכחת-הסים שלי בבוקר: `sc.SellExit=-1`). ה-"SELL עבד באמת" שראית = נטו-הפחתה של op=PLACE, נתיב שהדלקת-ScaleOut משנה בצדק.
- **למה זה לא נבדק:** ה-API **דחה** ‏action=EXIT (‏HTTP 400) — אז נתיב-ה-EXIT (זה שהתיקון תיקן) לא היה בר-בדיקה מקצה-לקצה. נפלת ל-SELL כי לזה לא הייתה ברירה.

## התיקון (בקאנד בלבד — כבר בגיט, ‏0077bfd)

‏action=EXIT מנותב עכשיו ל-`write_exit` (op=EXIT). אומת על מק-הפיתוח: ‏action=EXIT → ‏ACK (במקום 400) → קובץ-הפקודה מראה `op=EXIT contracts=1 dir=LONG`. ‏**ה-DLL לא נגעתי** (משטח-סיכון-מסחר; דורש פסיקת מייקל).

## מה לעשות אצלך (iMac, SIM, is_sim=1)

1. **משוך את התיקון:** כפתור-העדכון (‏`MEMS26_UPDATE.command` / ‏CONTROL אופציה 5). ודא HEAD כולל ‏`0077bfd`, ריסטארט-בקאנד, ‏flag_guard PASS.
2. **בדוק את הנתיב האמיתי (op=EXIT, לא SELL):**
   ```
   BUY 2                          → ודא qty=2, working=4 (OCO)
   POST action=EXIT contracts=1   → זה הנתיב האוטומטי!
        (sierra_bracket_id = order_id של הכניסה, direction=LONG)
   ```
   המתן ~7ש' וקרא:
   - ‏`sierra_state.json`: **qty 2→1** = ✅ התיקון עובד.
   - ‏`trade_result.json`: **EXIT_OK** (או ‏EXIT_FAIL עם קוד — ה-DLL כותב result על שני המצבים, שורה 1343).
3. **הכרעה:**
   - ‏qty 2→1 + EXIT_OK → **אין רגרסיה**; התיקון של הבוקר הצליח, פשוט לא היה בר-בדיקה. סוגרים.
   - ‏qty נשאר 2 / EXIT_FAIL → אז יש בעיה אמיתית ב-`sc.SellExit`; דווח את קוד-ה-r מ-trade_result, ואז נשקול (א) rollback-DLL, או (ב) שינוי-DLL עם פסיקת מייקל.

## אל תעשה

- אל תשפוט מ-`SELL <n>` — זה op=PLACE, לא נתיב-היציאה. רק ‏action=EXIT.
- אל תיגע ב-DLL בלי פסיקת מייקל (משטח-סיכון). ‏rollback-DLL זמין (snapshot `20260713T114612Z_pre-dll-deploy`) אם EXIT גם נכשל.
