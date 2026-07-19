# רשימת-משימות לקורסור — חוכמת-התבניות + תקינות פר-סוג-יום + השלמת מערכת-1

**פסיקת-מייקל 2026-07-19:** *"סים פעיל, מסחר ב-01:00. הרבה פיתוח + הרבה בדיקות לחוכמת-התבניות
ולתקינותן, וכן מערכת-1. לסיים את המשימות. קורסור מבצע, אני [cowork] מאמת."*

**מבצע: cursor-agent** (אינדקס-קודם — `CURSOR_WORKFLOW_INDEX_FIRST_2026-07-19.md`; קריאה/בדיקות/
דגל-OFF/תצוגה בלבד — **לא** משטח-מסחר, זה cc-macbook). **מאמת: cowork-dev (חוק-5).**
**בטיחות:** לפני כל ריצה שנוגעת-בביצוע — אמת `is_sim=1`. אין `.env` ON / RULED / op=PLACE בלי פסיקה.
**כל תוצר:** פקודה+פלט-גולמי ב-`LIVE_CHANNEL` + `git pull`/`commit`/`push`.

**סדר-עדיפויות:** T1→T2→T3 (חוכמת-התבניות, הלב) · T4→T5 (מערכת-1) · T6→T7 (כיסוי-בדיקות) · T8 (קוסמטי).

---

## חלק A — חוכמת-התבניות + תקינות פר-סוג-יום (הלב)

### T1 · מספרי against-Dalton (סוגר G-11 · Bible-U2)
הרץ על ה-Mac (DB חי): `BRIDGE_TOKEN=test python3 scripts/audit_pattern_miss.py --date 2026-07-1{5,6,7} --relax all`.
**תוצר:** לכל תבנית — כמה כניסות בפועל היו **נגד-דלתון** (CONT long ליד-VAH / short ליד-VAL),
מרחק-כניסה-ממוצע-מהקצה, ו-hit-rate C1/C2/C3. טבלה ל-`PATTERN_INTEL_NUMBERS_2026-07-19.md`.
זה **מספר-הבסיס** להשוואה אחרי D1. קריטריון: מספרים אמיתיים מ-DB, לא הערכה.

### T2 · מטריצת תקינות תבנית×סוג-יום מול מפת-D0
לכל 15 תבניות × 8 סוגי-יום, מ-`DIRECTION_AUTHORITY_MAP_2026-07-19.md` + `daytype_playbook.yaml` +
`sim_matrix.py`: **האם הכיוון/המשפחה שהתבנית מייצרת תואם את מפת-D0?** סמן 🟢 תואם / 🔴 סתירה
(למשל CONT-long-בתקרה ב-Normal שמפת-D0 חוסמת). הרץ `python3 scripts/sim_matrix.py` והצלב.
**תוצר:** מטריצה 15×8 עם 🟢/🔴 + `file:line` לכל 🔴. זה "לראות שהתבניות תקינות".

### T3 · גאומטריה: הצלבת Bible מול הקוד-החי (חוכמת-התבניות)
לכל תבנית, אמת שהגאומטריה ב-`PATTERN_BIBLE_2026-07-19.md` עדיין תואמת את הדטקטור בקוד
(`backend/v9/systems/woodies/patterns/*.py` · `five_min/patterns/*.py`) — במיוחד ספי-CCI/נפח/נרות.
סמן כל סטייה (SPEC_V2 שהחליף גרסה). **תוצר:** רשימת-סטיות + `file:line`.

---

## חלק B — השלמת מערכת-1

### T4 · S1 מקור-אחד — השלמת ה"לא-מוכרע" (G-13)
אמת מהלוג-החי (`docs/reports/OPS_LOG_*` / trend_state בפועל): **האם YELLOW בכלל מגיע מה-DLL?**
אם כמעט-אף-פעם → נעילת-YELLOW ב-`woodies_system.py:619` כמעט-inert (דווח). **תוצר:** ספירת
BLUE/RED/GRAY/YELLOW על 15/16/17 מה-DB (`v9_bars_5min_woodies.trend_state`).

### T5 · S1 מסווג נכון פר-סוג-יום (תקינות מערכת-1)
`classify_replay` על 15/16/17 + כל תאריך עם ראיה: האם המסווג מייצר את הרצף שמייקל קרא
(16/07: Normal→Neutral_Center→Neutral_Extreme)? הצלב מול `v9_day_type_history`. **תוצר:** טבלת
תאריך→סוג-יום-שסווג→האם-תואם-דוקטרינה + כל אי-התאמה עם הקריטריון מ-`daytype_classifier.py`.

---

## חלק C — כיסוי-בדיקות (להוכיח תקינות)

### T6 · טסטי מפת-כיוון (D0) — מוכנים ל-D1
כתוב טסטים **טהורים** לפונקציית-הכיוון הצפויה `allowed_direction(day_type, zone, poc_dir)` לפי
מפת-D0 (Normal: long-מתחת-POC+mig-UP · short-מעל+mig-DOWN · FLAT→REV · Trend→עם-המגמה-POC-לא-שער ·
#372-trap רק-רוטציה). **אנטי-טאוטולוגי.** הטסטים ימתינו ל-D1 (cc-macbook) — כך הבדיקה מוכנה מראש.
**תוצר:** `tests/v9/regression/test_direction_authority_map.py` (xfail/skip עד D1) + פלט.

### T7 · טסט אנטי-טאוטולוגי לכל דטקטור-תבנית (כיוון)
לכל תבנית, טסט שמוודא שהיא בוחרת כיוון **נכון** מ-CCI/מבנה (לא הפוך) — ומקרה-שלילי (לא-יורה כשאין
תנאי). **תוצר:** טסטים + `N passed`.

---

## חלק D — קוסמטי (cursor, סיכון-אפס)

### T8 · TopBar tooltip
`TopBar.tsx:71` עדיין כתוב "classify_replay" בעוד הערך כבר override-aware (P0-2). עדכן לטקסט
"get_live_day_type (override-aware)". tsc + render-check. **תוצר:** diff + tsc נקי.

---

## מה נשאר ל-cc-macbook (לא-cursor — משטח-מסחר, אחרי פסיקת-מייקל)
G2+G3 (זיהוי-S2 על live-daytype) · G6 (ביטול-fallback-מת) · D1 (הדלקת position_gate + POC-migration).
כל אחד: פסיקת-"לתקן" + דגל-OFF + אימות-סים.

## תוצר-כולל
כל T# → פלט-גולמי ב-`LIVE_CHANNEL` + מסמך-תוצר. cowork מאמת כל אחד (חוק-5). מסמכי-מספרים:
`PATTERN_INTEL_NUMBERS_2026-07-19.md` + מטריצת-T2 + טבלאות-S1.
