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

### ממצא א1 (מדווח, לא מתוקן בשקט)

`tests/v9/regression/test_dalton_playbook.py` **אינו קיים**. הריצה הראשונה נפלה על כך:

```
$ python3 -m pytest ... tests/v9/regression/test_dalton_playbook.py ... -q
rc=4
ERROR: file or directory not found: tests/v9/regression/test_dalton_playbook.py
```

הקובץ הזה (וציפיית ה-32 טסטים שלו) הגיע מ**שורת-הציפייה של הזמנת-הערב**, לא מטבלת-הקומיטים
של cc — cc מעולם לא טען אותו. הגולדן של תאימות-אחורה לפלייבוק שנדרש ב-T-391
("כל ה-golden-ים הקיימים של הפלייבוק עוברים ללא שינוי") הוא
`tests/v9/regression/test_dalton_playbook_identity.py`, והוא עובר 3/3.
המסקנה: אין טסט חסר ואין נסיגה — הציפייה `≈127` הייתה שגויה; המספר הנכון הוא **98**.

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

**א1 PASS · א2 PASS · א3 PASS.** אפס ממצא-חוסם ⇒ **הריסטארט של מחר-בבוקר ירוק.**
