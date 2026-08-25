# ביקורת-cowork · פקודת-העבודה T-103 (לפני ביצוע)

**מאת:** cowork-dev · **אל:** cursor-agent + cc-macbook · **תאריך:** 2026-08-25 10:05 IL
**מעמד:** ביקורת-קדם. **לא בניתי, לא הדלקתי דגל, לא ריסטארטתי.**
**נבדק:** `CC_WORKORDER_T103_LEDGER_2026-08-25.md` · `COWORK_VERIFY_T103_LEDGER_2026-08-25.md` ·
`CANDIDATE_LEDGER_CONTRACT.md` · `candidate_ledger.py` · `024_candidate_ledger_columns.py` · DB חי

---

## פסק

**המסגרת מקצועית — הטובה ביותר שקיבלנו. הביצוע עוד לא בשל.**
**7 ליקויים · 3 חוסמים · 2 מהם יזיקו היום אם CC ירוץ כלשונו.**

---

## חוסם 1 · עובדה שגויה בפקודת-העבודה — `is_synthetic`

פקודת-העבודה §2: *"`is_synthetic` שחסר במודל S2 (019 כבר ב-DB)"*.

```
$ psql postgresql://localhost/mems26 -tAc "SELECT table_name||'.'||column_name
  FROM information_schema.columns WHERE table_name IN
  ('v9_five_min_setups','v9_woodies_signals') AND column_name='is_synthetic';"
v9_woodies_signals.is_synthetic
```

**`v9_five_min_setups.is_synthetic` לא קיים ב-DB.** 019 הוסיף אותו ל-woodies בלבד.

CC יוסיף את השדה למודל S2 כהוראה → כל persist של S2 ייפול ב-`UndefinedColumn` →
הנתיב warning-only (חוזה §5) → **אינדקס-הזיהוי של S2 ייכבה בשקט.** בדיוק הנתון
שהליגר קיים כדי ללכוד.

**תיקון:** להסיר מ-§2, או להוסיף `is_synthetic BOOLEAN` nullable ל-024.

---

## חוסם 2 · DDL בלי `lock_timeout` ביום-מסחר — ושלושה סשנים תלויים כרגע

```
$ ... "SELECT pid,state,now()-xact_start FROM pg_stat_activity
       WHERE datname='mems26' AND state<>'idle';"
44556 | idle in transaction | 00:00:53.17 | SELECT v9_trades...
45100 | idle in transaction | 00:00:00.01 | SELECT v9_bars_5min...
45237 | idle in transaction | -00:00:00.00 | UPDATE v9_bars_5min SET poc_vol...
```

`ALTER TABLE` דורש ACCESS EXCLUSIVE. בלי `lock_timeout` הוא **ממתין ללא-גבול**,
וכל קורא שמגיע אחריו **נתקע בתור מאחוריו**. זה בדיוק הטריז של 07-22
(PID 28917, 35 דקות, backend מת).

הטבלאות זעירות — הבנייה עצמה אינה הסיכון:

```
v9_five_min_setups | 939 rows  | 280 kB
v9_woodies_signals | 2355 rows | 736 kB
```

הסיכון הוא **100% תפיסת-הנעילה**. לכן `SET lock_timeout='3s'` פותר אותו במלואו.

**תיקון:** `lock_timeout` לפני כל DDL · בדיקת `pg_stat_activity` מקדימה ·
rollback כתוב מראש (`ALTER TABLE … DROP COLUMN`) · בדיקת-חיוּת ל-backend אחרי.
`mems26_snapshot.sh` מצלם DLL/.env/LaunchAgents — **לא סכימת-DB.** אין היום נקודת-חזרה.

---

## חוסם 3 · `CREATE UNIQUE INDEX` הופך תצפית למשבשת-כתיבה

```python
# 024_candidate_ledger_columns.py:74
f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_candidate_id ..."
```

`candidate_id` הוא hash דטרמיניסטי של (system, pattern, direction, בר-5-דק', variant) —
**ללא pid וללא זמן-קליטה** (חוזה §3, בכוונה). לכן re-push על אותו בר, ריסטארט, או replay
מייצרים אותו מזהה בדיוק → `IntegrityError` על ה-INSERT השני → ב-`_persist_pattern` של S4
זה יושב על session משותף ויכול להרעיל את הטרנזקציה.

חוזה §Behavior: *"Ledger failure must never alter detection."*
**אילוץ UNIQUE הוא חוסם-כתיבה, לא תצפית.**

**תיקון:** אינדקס רגיל, לא unique. הדדופ שייך לקורא — חוזה §3 כבר אומר
*"Readers deduplicate by event_id"*.

---

## 4 · הדגל אינו רשום ב-`RULED_FLAGS.yaml`

```
$ grep -c "CANDIDATE_LEDGER_V1" config/RULED_FLAGS.yaml
0
$ python3 scripts/flag_guard.py | tail -1
FLAG-GUARD: PASS — all 199 ruled flags match.
```

דגל לא-שמור = אין שמירה על סחיפה לשני הכיוונים. לפי כללי-הממשל הוא נכנס
ל-`RULED_FLAGS.yaml` **באותו commit**.

---

## 5 · סתירת-תיעוד: `GATE_DECISION → ROUTED`

חוזה §2 מתאר שני שלבים עוקבים. הקוד מתייג **שורה אחת, בלעדית**:

```python
# trading_gateway.py:793
_dec["event_type"] = "GATE_DECISION" if bb else "ROUTED"
```

הקוד נכון (אין ספירה-כפולה); **החוזה הוא השגוי.** מי שיבנה משפך לפי §2 יקבל
"0% routed" ויסיק שהמערכת לא סוחרת. לתקן את הניסוח.

---

## 6 · `_code_commit()` — subprocess עצל בתוך הנתיב-החם

```python
# candidate_ledger.py:224
subprocess.check_output(["git","rev-parse","HEAD"], timeout=2)
```

רץ באירוע-הליגר הראשון של היום — **בתוך `process_bar`**. אם CC עושה commit באותו רגע
(`.git/index.lock`), זו השהיה של עד 2 שניות על זיהוי S2 חי. לפתור ב-import/boot.

## 7 · `_seen_event_ids` — לא-חסום ותהליכי

גדל ללא גבול לאורך חיי-התהליך, ומתאפס בריסטארט. מבחני-קבלה 6 ו-7 מתקיימים
**רק בתוך תהליך אחד**. הדוח חייב לומר זאת במפורש ולא להצהיר "דדופ מוחלט".

---

## מה כן טוב (ולא מובן-מאליו)

חוזה-לפני-קוד עם 13 מבחני-קבלה · דגל OFF שעוטף **כתיבות בלבד** ולא זיהוי/ניתוב ·
איסור מפורש על מקור-אמת שלישי · רשימת-אסור מפורשת · `_jsonl_path()` מחזיר `None`
תחת pytest על נתיב חי · הכותב לעולם לא זורק · חוק-5 נדרש פר-שלב ·
והפרדה נקייה בין בונה למאמת. זו עבודת-ניהול טובה.

---

## המלצה — לפצל את התזמון

המיגרציה היא **החלק היחיד עם סיכון-מסחר היום**. שאר T-103 (ORM · EOD resolver · טסטים)
הוא אפס-סיכון.

**והמפתח: הדגל כבוי — אף `candidate_id` לא ייכתב היום גם אם העמודות קיימות.**
כלומר **שום דבר ב-T-103 לא זקוק ל-024 לפני הסגירה.**

| מתי | מה |
|---|---|
| עכשיו → 15:00 | שלבים 2·3·4 — ORM (בלי `is_synthetic` ל-S2), EOD RESOLVED, טסטים. אפס DDL. |
| 15:45 | שער-אימות + ריסטארט (קו-אדום 16:10) |
| 16:30 | פתיחה · 4 חוזים |
| אחרי הסגירה | 024 מתוקן: אינדקס רגיל · `lock_timeout='3s'` · rollback כתוב · בדיקת-חיוּת |

מסיר 100% מסיכון-המסחר של היום בלי לעכב את ההתקדמות בכלום.

---

## הוספה למסמך-האימות שלי

מעבר ל-9 הפריטים שקורסור כתב, אאמת גם:

10. `v9_five_min_setups.is_synthetic` — לא נוסף למודל בלי עמודה ב-DB
11. ל-DDL היה `lock_timeout`, ו-`pg_isready` + החלטה חיה אחרי ה-024
12. `uq_*_candidate_id` — **לא** unique
13. `CANDIDATE_LEDGER_V1` רשום ב-`RULED_FLAGS.yaml` ו-`flag_guard` עובר 200
