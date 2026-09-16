# שער-הבטיחות על עבודת cc-macbook — cowork-dev, 2026-09-16 לילה

מאמת את 5 הקומיטים של cc מ-16:37–17:14 (T-396 · T-390 · T-391 · T-389 · T-392).
כל טענה כאן מלווה בפקודה + פלט גולמי (Rule 5). הריצות בוצעו אחרי סגירת-RTH, ללא ריסטארט.

---

## א1 · טסטים — PASS (98 עברו, rc=0)

```
$ set -a; . ./.env; set +a
$ python3 -m pytest tests/v9/regression/test_shadow_session_close.py \
    tests/v9/regression/test_situation_vector.py \
    tests/v9/regression/test_condition_expr.py \
    tests/v9/regression/test_dalton_playbook_identity.py \
    tests/v9/regression/test_gap_analysis.py \
    tests/v9/regression/test_dalton_tree.py -q
rc=0
98 passed, 2 warnings in 1.51s
```

ספירה לפי קובץ (כל קובץ הורץ בנפרד):

```
test_shadow_session_close      : 6 passed
test_situation_vector          : 24 passed
test_condition_expr            : 28 passed
test_dalton_playbook_identity  : 3 passed
test_gap_analysis              : 24 passed
test_dalton_tree               : 13 passed
```

**כל 5 המספרים ש-cc טען אומתו בדיוק** (6/24/28/24/13). אפס פער בין הספירה שלי לטענת-cc.

### 🔴 ממצא א1 — טענת-טסט של cc שאינה ניתנת לאימות

`tests/v9/regression/test_dalton_playbook.py` **אינו קיים, ומעולם לא היה קיים**:

```
$ python3 -m pytest ... tests/v9/regression/test_dalton_playbook.py ... -q
rc=4
ERROR: file or directory not found: tests/v9/regression/test_dalton_playbook.py

$ git log --all --oneline -- "tests/v9/regression/test_dalton_playbook.py"
(ריק — הקובץ מעולם לא היה מעוקב בשום קומיט)
```

**זו אינה שגיאת-ההזמנה בלבד.** `TASK_LOG.md:20`, בשורת-cc של T-391, טוען מפורשות:

> *"Test `test_condition_expr.py` 28/28 PASS + existing `test_dalton_playbook.py`
> **32/32 PASS (backward compat)**"*

הקובץ הזה אינו קיים בעץ-העבודה ולא בהיסטוריה ⇒ **הטענה אינה ניתנת לאימות**, ואיתה
נופל הביסוס לקריטריון-הקבלה של T-391 (*"כל ה-golden-ים הקיימים של הפלייבוק עוברים
ללא שינוי"*).

הקובץ הקרוב-ביותר שקיים — `test_dalton_playbook_identity.py` — **אינו** הגולדן הזה.
הוא 3 טסטים על מסלול-הדגל-**כבוי** בלבד:

```
$ python3 -m pytest tests/v9/regression/test_dalton_playbook_identity.py -q --collect-only
TestDaltonPlaybookOff::test_flag_off_is_default
TestDaltonPlaybookOff::test_flag_off_skips_dalton_block
TestDaltonPlaybookOff::test_old_gates_run_when_off
```

הוא אינו מעביר שורות-YAML קיימות דרך `_match_condition`, אינו נוגע ב-`expr:`, ואינו
נוגע ב-`vector`. יתרה מזו `DAYTYPE_PLAYBOOK=1` ב-`.env` — כלומר שלושת הטסטים מכסים
דווקא את המסלול ש**אינו** פעיל בייצור.

**⇒ קריטריון תאימות-האחורה של T-391 אינו מכוסה באף טסט-יחידה.**

### למה זה בכל-זאת אינו חוסם את הריסטארט

התכונה עצמה **אומתה אמפירית בא3, על נתונים אמיתיים, וזו ראיה חזקה יותר מטסט-היחידה
החסר:** שתי ריצות-הרנס מלאות עם ה-`.env` האמיתי (‏`DAYTYPE_PLAYBOOK=1`, כלומר מסלול-
הפלייבוק **פעיל**) החזירו `routes` זהים בית-בית לבסיס — 70/70 ו-78/78. אילו `_match_condition`
החדש היה משנה התאמה ולו בשורה אחת, ההבדל היה מופיע שם.

**סיכום א1:** 98 עברו, אפס נפלו. חמשת המספרים ש-cc טען על קבצים **קיימים** אומתו בדיוק
(6/24/28/24/13). הפער היחיד הוא הטענה השישית על קובץ-רפאים — **ממצא-תיעוד שמתוקן
ב-`TASK_LOG`, לא נסיגת-קוד.** הציפייה `≈127` שגויה; הנכון הוא **98**.

---

## א2 · Guards — PASS (rc נתפס ישירות, לא דרך `| tail`)

```
$ set -a; . ./.env; set +a; python3 scripts/flag_guard.py > …; echo "flag_guard rc=$?"
flag_guard rc=0
FLAG-GUARD: PASS — all 259 ruled flags match.
  ── LIVENESS REPORT: all ON flags have ≥1 production read-site ──

$ python3 scripts/task_log_guard.py > …; echo "task_log_guard rc=$?"
task_log_guard rc=0
task_log_guard — 381 items, last committed 0.1 days ago
✅ the task log is current, structured, and the only one
```

**אפס דגל דלוק חורג** ⇒ לא נדרשה שורת-🔴 לפסיקת-מייקל, ולא כובה/נוסף שום דגל.

---

## א3 · הרנס — PASS, `routes`/`would_write` זהים בית-בית

הבסיס `harness_out/t367/head_*.json` נוצר ב-10:58 (לפני קומיטי-cc מ-16:37+), באותו
`variant=head` / `push_mode=firstpush` / `oe_closed=false` כמו ריצות-הלילה. זו בדיוק
ההשוואה הנדרשת: לפני-cc מול אחרי-cc.

```
$ set -a; . ./.env; set +a
$ python3 scripts/fwd_harness.py --session 2026-09-15 --out harness_out/night_0916/head_2026-09-15.json
rc=0    Traceback=0    peak memory footprint 96,321,536

$ python3 scripts/fwd_harness.py --session 2026-09-11 --out harness_out/night_0916/head_2026-09-11.json
rc=0    Traceback=0
```

ההשוואה מפורשת על שני השדות בלבד (ולא checksum של הקובץ כולו — שדות-זמן היו שוברים
אותו בלי משמעות-החלטה). הכלי: `harness_out/night_0916/cmp_routes.py`.

```
$ python3 harness_out/night_0916/cmp_routes.py 2026-09-15 2026-09-11

===== session 2026-09-15 =====
routes: baseline_len=70 new_len=70 IDENTICAL=True
would_write: baseline_len=0 new_len=0 IDENTICAL=True

===== session 2026-09-11 =====
routes: baseline_len=78 new_len=78 IDENTICAL=True
would_write: baseline_len=0 new_len=0 IDENTICAL=True

==================================
A3 VERDICT: IDENTICAL (zero behaviour change)
CMP_EXIT=0
```

**קריטריון אפס-שינוי-התנהגות של T-390/T-391/T-392 מתקיים** — הווקטור מוסיף מידע,
`expr:` אפס שורות בפרודקשן, והעץ בצל-בלבד. אין ממצא-חוסם.

### ריצה נוספת — `--restart-at 18:29` (crash-check בלבד)

הורצה כי ההשוואה הבסיסית עברה ויש זיכרון. היא מפעילה את נתיב-ההידרציה-הקרה שהוא
בדיוק מה ש-T-396 סעיף-2 שינה, ולכן שווה בדיקה:

```
$ python3 scripts/fwd_harness.py --session 2026-09-15 --restart-at 18:29 --out …
rc=0    Traceback=0    routes: 67  would_write: 0
```

**זו אינה בדיקת-זהות.** ה-`cold_restart_*.json` שבריפו הם מעידן-קוד אחר ולא בסיס
בן-השוואה; 67 מול 70 הוא הפרש-צפוי של ריסטארט-באמצע-יום (ניקוי-מצב + re-seed), ולא
ממצא. מה שנבדק כאן ואומת: **הנתיב לא קורס ואינו זורק Traceback** אחרי שינוי-ההידרציה.

---

## פסיקה

**א1 PASS (עם ממצא-תיעוד) · א2 PASS · א3 PASS.**

אפס ממצא-חוסם ⇒ **הריסטארט של מחר-בבוקר ירוק** לטעינת T-390/T-391/T-396.
הקריטריון שההזמנה קבעה לריסטארט — `Traceback=0` על 15.09+11.09 — **התקיים** (0 ו-0),
וקריטריון אפס-שינוי-ההתנהגות אומת חזק ממנו: זהות בית-בית ב-`routes`/`would_write`.

**שני דברים פתוחים שאינם חוסמים את הריסטארט:**
1. 🔴 טענת-`test_dalton_playbook.py 32/32` ב-`TASK_LOG:20` — קובץ-רפאים; יש לתקן את
   השורה ולכתוב את גולדן-תאימות-האחורה האמיתי ל-T-391 (הסיכון עצמו מכוסה ע"י א3).
2. ⛔ [[T-389]] — `gap_analysis.py` קורס על כל סשן עם עסקאות; פירוט מלא ב-
   `docs/reports/GAP_ANALYSIS_2026-09-17.md`. **אינו נוגע לריסטארט** — סקריפט-ניתוח
   אופליין שאינו חלק מנתיב-המסחר ואינו נטען ע"י הבקאנד.
