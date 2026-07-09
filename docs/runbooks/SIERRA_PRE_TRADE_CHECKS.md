# בדיקות סיירה לפני חימוש — הרשימה שנולדה מ-07-08 (עדכון 2026-07-09)

כל שורה = תקלה אמיתית שקרתה. מסומן מי מבצע: 🖥 CC · 👤 מייקל (בסיירה עצמה).

| # | בדיקה | למה (התקלה שקרתה) | איך |
|---|-------|---------------------|-----|
| 1 | 👤 חימוש: ‏Trading Enabled + חשבון 37138283 + ‏Sim-Mode תואם | ‏BLOCKER-1 ‏(GENERAL_ERROR) · "עבד-ואז-נשבר" 07-07 | ‏Trade menu; ה-DLL עושה auto-match אבל העין שלך מאשרת |
| 2 | 🖥 ‏DLL פרוס == repo | פריסות ישנות | `scripts/mems26_verify.sh` (DLL↔repo) |
| 3 | 🖥 ‏export כותב + feed טרי | קפאון 06-25 | ‏live_price ‏age<2s · ‏Sierra writing=true |
| 4 | 🖥 ירי SIM ‏3ח מלא: ‏PLACE→‏ORDER_SUBMITTED error=0 + ‏parent/target/stop ids → **fills נכתבים** → flatten → ‏CANCEL_OK | הסיבוב-fill עדיין לא הוכח (partial 07-08) · מפת ה-id | ‏debug_gateway_fire מחוץ ל-RTH |
| 5 | 👤 בראקט נראה בסיירה: **3 יעדים + 3 סטופים** מוצמדים אחרי כניסה | ‏naked-bracket 07-08 (‏NAKED_STOP צרח 10 דק') | ‏Trade Window אחרי הכניסה הראשונה |
| 6 | 🖥 ‏TradeActivityLog של היום נגיש ונטען | הסגירה הידנית שלך הייתה בלתי-נראית | הפידר קורא את קובץ היום |
| 7 | 🖥 ‏reconcile נקי בדקות הראשונות: פוזיציית סיירה == המערכת, אפס ‏NAKED/ORPHAN | היתומה 308/310 | לוג + ‏System6 |
| 8 | 🖥 אפס אזהרות "no auth cell" ל-S2 · ‏effective contracts==3 | עקיפת הטבלה · המעבר ל-3 | לוג + ‏fire_drill |
| 9 | 👤 ‏DTC מחובר, אין delay/gaps בדאטה | ריקונקטים ליליים (תקין) — לוודא שהתייצב | ‏Sierra message log נקי מ-errors מתמשכים |
| 10 | 🖥 ‏flag_guard ‏32/32 + ‏fire_drill ‏🟢 + ‏flat | הכל | אוטומטי 15:55 |

**כלל:** כל ✗ → ‏DEMO עד תיקון. אין "זה בטח בסדר".
