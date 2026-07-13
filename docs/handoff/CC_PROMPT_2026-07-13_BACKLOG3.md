# CC — שלוש משימות-הבקלוג שבבעלותך (מייקל 07-13: "לבצע את כל אלה")

**חוזה:** ‏docs/handoff/CC_HANDOFF_CONTRACT.md מחייב — טסטים אנטי-טאוטולוגיים, ראיות
פקודה+פלט-גולמי (Rule 5), וסעיף **NOT-DONE** מפורש בסוף. עבודה על מק-הפיתוח בלבד
(git הוא ערוץ-הקידום היחיד ל-iMac). אין ריסטארט בזמן עסקה פתוחה; היום יום-מסחר —
פריסות רק לפני 15:55 IL או אחרי סגירה.

## 1 · DEV-5 (P2) — הידרציה מלאה בבוט

**מה:** בריסטארט באמצע-סשן המערכת משחזרת היום ‏daily_pnl, עסקאות-פתוחות, ובאפרי-ברים
(BOOT_HYDRATION_V1) — אבל **שלב-S1** (opening_type/committed-provisional/IB-lock)
ו**צוברי-S2** (מוני-רצפים, cooldowns פנימיים) מתאפסים. ביום כמו 07-09 (ריסטארט 21:06)
זה אומר סיווג-חדש-מאפס באמצע-RTH.

**דרישות:**
- שחזור שלב-S1: להריץ ‏classify_session על ברי-היום-עד-עכשיו בעליית-בוט (הקוד קיים —
  ‏backend/v9/systems/day_type/classifier_core.py) ולזרוע את ‏day_type_machine כולל
  ‏committed-provisional ו-IB-lock; לא להמציא מצב — מה שלא נגזר מברים = ריק והוגן.
- שחזור צוברי-S2 מ-DB (עסקאות-היום + אירועים) — לתעד אילו צוברים כן/לא ניתנים-לשחזור.
- **טבלת-HYDRATION בלוג-הבוט:** שורה פר-רכיב: ‏restored/empty/failed + המקור.
- טסט: kill+restart מדומה באמצע-סשן-סינתטי → הסיווג ממשיך מאותה נקודה (לא FORMING).

## 2 · DEV-6 (P2) — LaunchAgent לפרונטאנד

**מה:** הפרונט רץ ב-screen — נופל בריבוט. הניסיון הקודם נתקע על TCC/launchd
(‏npm לא ב-PATH של launchd + ‏getcwd ב-~/Downloads).

**כיוונים מותרים (לבחירתך, לתעד את הנימוק):**
- ‏wrapper-script עם ‏PATH מלא + ‏cd מפורש ל-repo + ‏`next start` על בילד-פרודקשן
  (עדיף על ‏dev-mode ל-launchd), או
- ‏LaunchAgent שמריץ ‏screen עצמו (ההוכחה-שעובדת היום) — פתרון-ביניים לגיטימי.
- לבדוק hypothesis: הבעיה היא TCC על ~/Downloads — אם כן, ‏build-dir מחוץ ל-Downloads.

**קריטריון:** ריבוט-מדומה (kickstart) מעלה פרונט חי על ‏:3000 בלי יד-אדם; ‏plist עם
‏KeepAlive=SuccessfulExit=false כמו הבקאנד; סנאפשוט לפני שינוי LaunchAgents
(scripts/mems26_snapshot.sh).

## 3 · DEV-11 (P3) — ‏7 פיקסטורות-טסט ישנות של structural_targets

**מה:** ‏7 טסטים נופלים-ותיקים (רשימה: הרץ
`BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression/test_engine_promotion_parity.py -q`
— ‏11 נופלים, מתוכם המשפחה הזו). דריפט-ספק: הפיקסטורות הוקלטו מול קוד ישן.

**דרישות:** לכל פיקסטורה — להכריע האם (א) הקוד-החדש צודק → לברך-מחדש עם הערת-סמכות
(כמו שנעשה ל-06-08/06-10 תחת FIX-14), או (ב) רגרסיה אמיתית → לתקן קוד. אסור ברכה
עיוורת: כל re-bless מחייב שורת-נימוק דוקטרינרית. יעד: ‏0 נופלים בחבילה.

## דיווח

בסיום: עדכן ‏docs/plans/STATUS_BOARD.md (שורש+תיקון+ראיה פר-משימה) + ‏DEV_BACKLOG.md
(להזיז ל-טבלה-3/4) + הרץ ‏`python3 scripts/gen_task_board.py` + קומיט+פוש. ‏NOT-DONE
מפורש על כל מה שנשאר.
