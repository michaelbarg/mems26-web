# מה נשאר לפתח + משימות-המשך לקורסור (בדיקות + פרונטאנד בכל שלב)

**פסיקת-מייקל 2026-07-19:** *"מה עוד צריך לפתח; מה שאי-אפשר בלי סים — נבצע ונבדוק ונתקן; להכין
לקורסור המשך-עבודה; **הפרונטאנד חייב מעודכן בכל השלבים**; להכין לקורסור בדיקות — שלא נגיע מחר ונגלה
פערי-פיתוח."*

**עיקרון-על:** לכל שינוי-מנוע יש **3 מרכיבים חובה יחד**: (1) קוד + טסט אנטי-טאוטולוגי, (2) **פרונטאנד
שמשקף אותו**, (3) אימות-סים. פריט לא "נגמר" בלי שלושתם. cursor מכין (1-חלקי)+(2)+בדיקות; cc-macbook
בונה קוד-מסחר; cowork מאמת; מייקל פוסק+סים.

---

## חלק 1 — מה נשאר לפתח (רשימת-אב)
| # | פריט | מבצע-קוד | דגל | צריך-סים? | פרונטאנד שחייב לשקף |
|---|---|---|---|---|---|
| G2+G3 | זיהוי-S2 + Flag-T2 על `get_live_day_type` | cc-macbook | `S2_DETECTION_LIVE_DAYTYPE_V1` OFF | כן (הדלקה) | תווית-סוג-יום כבר override-aware ✅ (לאמת) |
| G6 | ביטול נסיגה למקור-מת ב-S4 | cc-macbook | חדש OFF | כן | — (מקור-יום; כבר מוצג override-aware) |
| **D1** | אימוץ+הדלקת `daytype_position_gate` + POC-migration | cc-macbook | `DIRECTION_AUTHORITY_V1`/`DAYTYPE_POSITION_GATE` OFF | כן (הלב) | **DirectionStrip `dir_sustained` · Switcher "setup≠allowed" · BuildTree "הסכמת-כיוון" · why-blocked** |
| G4 | honest-prelock הדלקה | cowork+מייקל | `DAYTYPE_HONEST_PRELOCK_V1` | כן | תווית פרה-IB (כבר live-aware) |
| G7 | FIXED_4 ↔ REDUCED | cc-macbook | פסיקת-מייקל | כן | תצוגת-גודל/חוזים פר-עסקה |
| G8 | דוקטרינת Neutral/escalation | cowork | — (spec) | לא | — |
| B1 | ORPHAN_AUTO_STOP_V1 | (בנוי) | OFF | **כן — סים בלבד** | חיווי-הגנת-יתום (אופציונלי) |
| B2 | STOP_WIDEN_TO_FLOOR | (בנוי) | OFF | **כן — סים בלבד** | — |

---

## חלק 2 — משימות-המשך לקורסור (בדיקות מוכנות-לפני-בנייה + פרונטאנד)
**המטרה: כשה-cc-macbook יבנה, הטסט + ה-UI כבר קיימים — אפס פער-פיתוח מחר.**

### T9 · טסטים מוכנים ל-G2/G3 (לפני הבנייה)
כתוב טסטי-רגרסיה ל-`S2_DETECTION_LIVE_DAYTYPE_V1` (xfail/skip עד cc-macbook בונה):
דגל-OFF → byte-identical (אותן החלטות NT-skip/chart כמו היום) · ON + override=Variation בזמן
hydrate=Nontrend → לא-NT-skip · **אנטי-טאוטולוגי:** ON + override=Nontrend → עדיין-skip.
**תוצר:** `tests/.../test_s2_detection_live_daytype.py` + פלט.

### T10 · טסטים מוכנים ל-G6 (fallback-מת)
דגל-ON + כל-live-None → מחזיר `None` (לא `"Normal"`, לא קריאת-`v9_day_type_state`) · OFF → שרשרת-ישנה ·
אנטי-טאוטולוגי: ערך-חי אמיתי עדיין זורם. **תוצר:** טסט + פלט.

### T11 · טסטים מוכנים ל-D1 (הרחבת T6 לגייט האמיתי)
הרחב את `test_direction_authority_map.py` לגייט `daytype_position_gate` בפועל (כשיודלק): Normal
CONT-long מעל-POC → חסום · CONT-long מתחת-POC+mig-UP → מותר · Trend → POC-לא-שער · #372 רק-רוטציה.
**תוצר:** טסטים (xfail עד D1) + פלט.

### T12 · פרונטאנד לכיוון (P1 מאודיט-ה-UI — חובה עם D1)
כשD1 יגייט כיוון, ה-UI חייב **להראות** את הכיוון-המותר ולמה-נחסם:
- **DirectionStrip:** להוסיף `dir_sustained` (ה-API כבר מחזיר; `DirectionStrip.tsx:28-65`) — chip/אזהרה כש-`dir≠dir_sustained`.
- **Switcher/WoodiesLens:** להבדיל "כיוון-תבנית (setup)" מ-"כיוון-מותר (allowed)" + `blocked_by` מהפיד.
- **BuildTree "הסכמת-כיוון":** לקשור ל-`direction_now`/`dir_sustained`, לא הצבעה-עצמאית.
**תוצר:** diff + tsc נקי + render-check :3000 (screenshot) — **פרונטאנד מעודכן, לא מפגר אחרי הקוד.**

### T13 · Preflight "אפס פערי-פיתוח מחר" (הכי חשוב למייקל)
סקריפט/צ'קליסט שעובר על **כל** דגל-פתוח (G2/G3/G6/D1/G4/G7/ORPHAN/STOP_WIDEN) ומוודא לכל אחד:
(א) קיים טסט · (ב) קיים ביטוי-פרונטאנד (או "לא-רלוונטי") · (ג) קיים קריטריון-אימות-סים. **כל RED =
פער לסגור הערב.** **תוצר:** `PREFLIGHT_NO_DEV_GAPS_2026-07-19.md` — טבלת דגל × [טסט/UI/סים] × 🟢/🔴.

### T14 · השלמת שאר-🔴 מאודיט-ה-UI (תצוגה=מנוע בכל מקום)
System4Panel `woodiesBars` מת → למחוק/לחבר ל-`/woodies/current` · KeyLevelsStrip/DayTypeConditions
עדיין `classify_replay` → live-aware · DayTypeLabelTab לסמן "display≠gate" היכן רלוונטי.
**תוצר:** diff + render-check + עדכון `UI_CONSISTENCY_AUDIT`.

---

## חלק 3 — מה שאי-אפשר בלי סים (נבצע+נבדוק+נתקן בחלון-הסים)
| פריט | קריטריון-אימות-סים | אם נכשל |
|---|---|---|
| ORPHAN_AUTO_STOP_V1 | יתום-2 → PLACE_STOP סטופ בצד/מחיר · `working` 0→1 · פוזיציה לא-גדלה | לתקן+לחזור; RULED→1 רק אחרי ✅ |
| STOP_WIDEN | הרחבה-לרצפה בדחייה + SIZE_CAP_CUT תקין | לתקן+לחזור |
| מטריצת-E2E מלאה | כל תבנית×סוג-יום: כניסה→סולם→MODIFY_STOP→יעד→BE→S6→סגירה · 0 כשלים | כל ❌ = תיקון+ריצה-חוזרת |
| D1 (כשיודלק בסים) | against-Dalton צונח מול בסיס-T1 · 0 חסימות-שווא | לכייל+לחזור |
| G2/G3/G6 (הדלקה) | sim_matrix + E2E ירוקים תחת הדגל | byte-identical כש-OFF |

**חוק-בטיחות:** `is_sim=1` לפני כל ריצת-ביצוע · אין op=PLACE על לייב · בסוף — Sierra חזרה-ללייב + `is_sim=0`.

## תוצר-כולל
כל T# → פלט-גולמי ב-`LIVE_CHANNEL` + commit/push. cowork מאמת. **המדד: בבוקר, T13 (preflight) כולו 🟢 →
אין פערי-פיתוח; מה שנשאר = הדלקות-סים-מאומתות + פסיקות-מייקל בלבד.**
