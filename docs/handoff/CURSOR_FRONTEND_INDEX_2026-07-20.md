# cursor — אינדקס-פרונטאנד מלא + סיבת-מחסום מדויקת בכל סעיף (מייקל 2026-07-20)

**מייקל:** *"לעבור על כל הפרונטאנד, לסדר אותו, ולשים אינדקס על כל סעיף — כדי שבכל תיקון עתידי נעדכן
מיד את הפרונטאנד, ושאדע בדיוק מה הסיבה לכל מחסום שמתקיים."*
**מבצע: cursor. תצוגה/דוקומנטציה בלבד — אפס שינוי-מסחר. חוק-5.** בונה על `FRONTEND_MAP_2026-07-19.md`
+ `CURSOR_PRECISE_BLOCK_REASON` (block-reason כבר החל).

## תוצר 1 — `docs/handoff/FRONTEND_INDEX.md` (אינדקס-סמנטי, לא רק רשימת-קבצים)
טבלה לכל **סעיף/רכיב מוצג-למשתמש**, עם:
| רכיב (file:line) | מה מציג | מקור-נתונים (endpoint + שדה) | סוג-יום/כיוון/סטופ/יעד/מחסום? | הערות |

כסה את כל המשפחות: TopBar · Switcher · DirectionStrip · KeyLevelsStrip · Layer0Strip · WoodiesCciPanel ·
DayType* · BuildTree · SystemsPanel · Setups/Decisions/Patterns tabs · plan lens (planHelp/planFireDiagnosis/
systemPlanLive) · TradeReview/Details · Chart. לכל רכיב: **מאיזה endpoint+שדה הוא קורא** ומה בדיוק מוצג.

## תוצר 2 — ⭐ סיבת-מחסום מדויקת לכל שער (הלב של הבקשה)
טבלת **כל** `blocked_by` (מ-`trading_gateway.py`) → הסיבה-המדויקת שתוצג:
| blocked_by | reason מהמנוע (`result["reason"]`) | תרגום-תצוגה מדויק | file:line במיפוי (planHelp) |
- **וודא ש-`result["reason"]` מוגדר בכל נקודת-חסימה ב-gateway** (לא רק daytype_playbook — גם location_gate,
  rr_entry_gate, cont_trend_filter, entry_not_confirmed, opening_type_gate, וכו'). אם חסר — הוסף (העברת-הסיבה-
  המחושבת בלבד, אפס-שינוי-החלטה) + טסט שההחלטה-החסומה מכילה reason לא-ריק.
- **planHelp: הצג את `reason` המדויק** (דרך regex-המיפוי), fallback לגנרי רק כשאין. הוסף תרגומים לכל דפוס-סיבה
  (responsive not at VAH / counter-trend / dir_sustained / R:R<min / no confirm bar / past cutoff / STOP-DAY / ...).
- **מטרת-מייקל:** בכל מחסום שמופיע במסך → **הסיבה-המדויקת** (למשל "שורט-fade לא בתקרה VAH · below_value"),
  לא "סוג-היום מסמן SKIP" גנרי.

## תוצר 3 — סדר + ניקוי
- סמן דפי/רכיבי-מת (orphans מ-gen_index — ~26 FE) → מועמדי-מחיקה (פסיקה בלבד, אל תמחק בלי אישור).
- ודא כל רכיב-חי מחובר לנתונים-חיים (לא endpoint מת). הצלב מול SoT.

## תוצר 4 — פרוטוקול-עדכון-עתידי (כדי ש"תיקון→עדכון-מיד")
בראש `FRONTEND_INDEX.md`: **כלל** — כל שינוי-backend שמוסיף/משנה שער/סיבה/שדה חייב לעדכן את השורה המתאימה
באינדקס + את מיפוי-התרגום ב-planHelp, באותו קומיט. כך הפרונטאנד לא מפגר אחרי המנוע.

## אימות (חוק-5)
`tsc --noEmit` נקי (0 חדשות) · `:3000` `/board` `/build` = 200 · החלטה-חסומה בדפדפן מציגה את הסיבה-המדויקת
(דוגמה חיה). commit+push + שורת-LOG. **cowork מאמת.** אם צריך `result["reason"]` ב-gateway (backend) —
זה display-transparency אפס-סיכון-מסחר, אבל דגל-OFF אם משנה התנהגות + טסט.
