# פרומפט CC — audit TZ מערכתי (diagnose only)

> להדבקה ב-Claude Code. **קרא קודם `CLAUDE.md` (Rule 4 TZ · No silent failures).**
> ⚠️ **DIAGNOSE ONLY — אפס שינוי קוד.** מטרה: למפות את **כל המחלקה** של באג ה-TZ
> שהתגלה ב-`bar_level_detector` (naive מ-DB מול aware), לא רק האתר הבודד.

---

## הרקע
`DIAGNOSE_T1_TZ_2026-05-31.md` מצא: **SQLite מחזיר datetime כ-naive** (מפשיט tzinfo),
ובהשוואה מול datetime **aware** (מ-`_market_now_utc()` / `_parse_ts()` / ts מהגשר
עם `+00:00`) נזרק `TypeError: can't compare offset-naive and offset-aware`. ב-
bar_level_detector זה אף נבלע ב-except שקט → כשל סמוי. השורש **מערכתי** — כל מקום
שעושה את זה עלול להיות שבור באותו אופן.

## מה לאבחן (read-only, עם ראיות)

1. **מקורות naive (DB):** מפה אילו מודלים/עמודות `DateTime` נקראים ומוחזרים naive
   (SQLite). `rg` למודלים ב-`backend/v9/db/models/` עם `DateTime`.
2. **מקורות aware:** `_market_now_utc`, `_parse_ts`, `datetime.now(timezone.utc)`,
   ts מהגשר (`+00:00`/`Z`). `rg` לכולם.
3. **אתרי סיכון:** מצא כל מקום ש**משווה / מחסר / min / max / sorts** datetime
   שמקורו DB מול datetime ממקור aware. (`rg` ל-`< `/`> `/`-`/`min(`/`max(` סביב
   datetime, ובמיוחד `entry_ts`/`exit_ts`/`ts`/`created_at`/`last_updated_at`.)
4. **סיווג כל אתר:** **SAFE** (שני הצדדים naive או שניהם aware) · **AT-RISK** (מעורב,
   עלול לזרוק) · **CONFIRMED-BUG** (כמו bar_level_detector). הצג קוד+נימוק.
5. **excepts שקטים:** `rg` ל-`except Exception`/`except:` ליד פעולות datetime —
   מקומות נוספים שעלולים **לבלוע** את אותו TypeError בשקט (כמו ש-bar_level_detector בלע).
6. **הצעת נרמול-גבול:** הערך פתרון שורש אחד — TypeDecorator על עמודות `DateTime`
   שמחזיר UTC-aware בקריאה, **או** helper מרכזי שכל קריאת datetime עוברת דרכו.
   ציין **blast radius** (כמה נתיבי קריאה מושפעים, אילו מהם מסחר) ואת ההמלצה.

## תוצר
`docs/reports/TZ_SYSTEMIC_AUDIT_2026-05-31.md`:
- טבלת אתרים: קובץ:שורה · מקור כל צד (naive/aware) · סיווג (SAFE/AT-RISK/BUG) · ראיה.
- רשימת excepts שקטים סביב datetime.
- הצעת נרמול-גבול + blast radius + המלצה (boundary fix מול per-site).
- **כל זה כהצעה — לא מיושם.** עצור ודווח → המתן להחלטת Michael על ההיקף.

## אסור
שינוי קוד · תיקון · refactor. אבחון בלבד. (התיקון הצר של bar_level_detector מטופל
בנפרד ב-`CC_PROMPT_FIX_T1_TZ` — אל תיגע בו כאן.)
