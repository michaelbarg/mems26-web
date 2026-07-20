# cursor — הצג את הסיבה-המדויקת לחסימה (לא מחרוזת-גנרית מטעה) · מייקל 2026-07-20

**מייקל:** *"בפרונטאנד רשום 'סוג-היום אינו מאשר' — מטעה. לרשום בדיוק מה הסיבה לחסימה."*
דוגמה-חיה: 13:15 REACTIVE_SHORT נחסם — הסיבה-האמיתית **"responsive SHORT not at VAH (below_value)"** (מיקום),
אבל הפרונטאנד הראה "טבלת-המשחק של סוג-היום מסמנת SKIP" (גנרי, מטעה). **תצוגה בלבד — אפס שינוי-מסחר.**

## השורש (מאומת ע"י cowork)
1. **Backend** `trading_gateway.py:698` — החסימה עושה `logger.info("BLOCKED by day-type playbook: %s", _pb.reason)`
   אבל **לא** `result["reason"]=_pb.reason`. הסיבה-המדויקת קיימת (`_pb.reason`) אך לא מגיעה ל-API.
2. **Frontend** `planHelp.ts:457` — `daytype_playbook: {why: 'טבלת-המשחק... מסמנת SKIP'}` = **מחרוזת קשיחה**, מוצגת
   תמיד, מתעלמת מהסיבה-האמיתית.

## התיקון (2 חלקים, דגל-OFF אם משנה התנהגות; זו תצוגה — אפס-סיכון-מסחר)
1. **Backend (gateway):** בכל נקודת-חסימה שיש בה סיבה-מחושבת, הוסף `result["reason"] = <הסיבה>`:
   - `daytype_playbook` → `_pb.reason` · `location_gate` → `_lg_reason` · `rr_entry_gate` → הסיבה שלו ·
     `require_with_trend` → הסיבה · `entry_not_confirmed`/`cont_trend_filter` → מחרוזת-הסיבה שלהם.
   - זה **רק מעביר** את מה שכבר מחושב+נרשם-בלוג. אפס-שינוי-החלטה. טסט: החלטה-חסומה מכילה `reason` לא-ריק.
2. **Frontend (planHelp / block display):** כשקיים `decision.reason` — **הצג אותו** (מתורגם, דרך regex-המיפוי
   הקיים ב-planHelp:415-430), במקום ה-`why` הגנרי-פר-שער. הגנרי = fallback רק כשאין `reason`.
   - הוסף מיפויי-תרגום: `responsive SHORT not at VAH` → "שורט-fade לא בתקרה (VAH) — מיקום שגוי" ·
     `below_value/above_value` · `counter-trend on ...` וכו'. כך המשתמש רואה **בדיוק** למה.

## אימות (חוק-5)
- החלטה-חסומה של daytype_playbook/location מחזירה `reason` מדויק ב-API (curl decisions).
- בפרונטאנד: הבלוק מציג את הסיבה-המדויקת (לא הגנרי) — למשל "responsive SHORT לא ב-VAH" ולא "סוג-היום מסמן SKIP".
- byte-identical של לוגיקת-המסחר (רק display). `tsc` נקי.
תוצר: קוד + טסט + פלט גולמי ל-LIVE_CHANNEL. commit+push. cowork מאמת.
