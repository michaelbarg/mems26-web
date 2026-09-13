# T-350 · מפקד-אתרי-קריאה של נתיב-הכתיבה ל-`v9_trades.pnl_sierra`

**מי:** `cc-night(cowork-subagent)` · **מתי:** 2026-09-13 23:21-23:35 IL (יום א', שוק סגור,
‏MES נפתח `01:00 IL`). **אפס נגיעה:** אפס דגל · אפס `.env` · אפס קוד · אפס ריסטארט ·
אפס נגיעה בפוזיציה/סלוט/תור-פקודות; `~/SierraChart*` קריאה-בלבד. `--write` **לא הורץ**.

## השאלה (מ-`CC_EVENING_PROMPT_2026-09-13.md` §1)

| # | השערה | הכרעה |
|---|-------|-------|
| א | כתיבה **אוטומטית בסגירת-עסקה** שנשברה ב-`09-10` | **נכונה חלקית** — קיים נתיב אוטומטי, אך הוא מסביר `1` מ-`9` השורות בלבד |
| ב | **כלי-אצווה** שפשוט לא הורץ ([[T-192]]) | **✅ שורדת כמנגנון-הרוב** |

## 🔴 תיקון-עצמי #1 — המפקד שהתבקש היה צר מדי, והצר החמיץ את הנתיב האוטומטי

המפקד שהתבקש הוא "מי קורא ל-`sierra_pnl_reconcile`". הרצתי אותו (מפקד B למטה) והוא
החזיר **אפס קוראי-ייצור** — ואז כמעט דיווחתי "אפס קוראים ⇒ השערה ב'". **זו הייתה טעות.**
המפקד הנכון הוא על **העמודה**, לא על המודול: `pnl_sierra` נכתבת גם ממודול אחר לגמרי
(`fill_poller.py`) שאינו מייבא את `sierra_pnl_reconcile` כלל. מפקד-המודול **עיוור לו**.
המפריד: `grep` על `\.pnl_sierra *=` במקום על שם-המודול.

## מפקד A — `write_pnl_sierra` בכל הריפו

```
$ grep -rn "write_pnl_sierra" . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__
rc_A=0   count_A=8
./backend/v9/services/sierra_pnl_reconcile.py:242:def write_pnl_sierra(db, findings: List[dict]) -> int:
./scripts/sierra_activity_join.py:266:def write_pnl_sierra(dsn: str, rows: list[dict]) -> int:
./scripts/sierra_activity_join.py:373:        n = write_pnl_sierra(DSN, rows)
   (4 ההתאמות הנותרות: frontend/readiness.html · render_mobile_relay/readiness.html ·
    STATUS_BOARD.md · TASK_LOG.md · MONDAY_READINESS.html — תיעוד, לא קוד)
```

**ממצא:** יש **שתי** פונקציות נפרדות באותו שם ובחתימות שונות.
`backend/.../sierra_pnl_reconcile.py:242` — **אפס קוראים בכל הריפו** (הגדרה בלבד; גם
המבחן `tests/v9/regression/test_sierra_pnl_reconcile.py` אינו קורא לה) ⇒ **קוד-מת**.

## מפקד B — מי מייבא את המודול `sierra_pnl_reconcile` (קוד בלבד)

```
$ grep -rn "sierra_pnl_reconcile" backend/ scripts/ bridge/ tests/ \
    --include=*.py --include=*.sh --include=*.command --include=*.plist --include=*.yaml --include=*.yml
rc_B=0   count_B=5
backend/v9/services/daily_pnl.py:83:    ... (הערה)
backend/v9/services/daily_pnl.py:120:        from backend.v9.services.sierra_pnl_reconcile import (
backend/v9/services/exit_verifier.py:266:            # T-193 1א: ... (הערה בלבד)
scripts/pnl_reconcile.py:30:from backend.v9.services.sierra_pnl_reconcile import (  # noqa: E402
tests/v9/regression/test_sierra_pnl_reconcile.py:8:from backend.v9.services.sierra_pnl_reconcile import (
```

**מה כל אחד מייבא בפועל — ואף אחד לא את הכותב:**
* `daily_pnl.py:120` ⇒ `divergence_summary, load_journal` — **קריאה-בלבד**.
* `scripts/pnl_reconcile.py:30` ⇒ `DEFAULT_JOURNAL, divergence_summary, load_journal, reconcile`
  — **אינו מייבא `write_pnl_sierra`**; יש לו כותב משלו (`write_back` ב-`:57`).
* `exit_verifier.py:266` — **הערה**. הוא כותב שורת-`FLATTEN` ל-**יומן-ה-JSONL**, לא לעמודה.

## 🔑 מפקד E — מפקד-העמודה (זה שהכריע). מכנה: `103` התאמות ב-`backend/ scripts/ *.py`

```
$ grep -rn "pnl_sierra" backend/ scripts/ --include=*.py   ⇒  TOTAL=103
$ grep -n "\.pnl_sierra *= *[^=]"  ⇒  n_attr=4
  backend/v9/tests/test_w2_exit_tracking.py:101:    t.pnl_sierra = None          ← מבחן
  backend/v9/services/sierra_pnl_reconcile.py:257:  t.pnl_sierra = f["pnl_sierra"]  ← קוד-מת (אפס קוראים)
  backend/v9/services/fill_poller.py:558:  trade.pnl_sierra = float(sierra_pnl)   ← 🔴 אוטומטי
  backend/v9/services/fill_poller.py:579:  trade.pnl_sierra = float(sierra_pnl)   ← 🔴 אוטומטי (fallback)
$ grep -in "SET pnl_sierra"  ⇒  n_sql=5
  scripts/pnl_reconcile.py:70        UPDATE v9_trades SET pnl_sierra = %s ...   ← אצווה
  scripts/sierra_activity_join.py:277 UPDATE v9_trades SET pnl_sierra = %s ...  ← אצווה
  (3 הנותרות: docstrings עם `SET pnl_sierra = NULL` כהוראת-גלגול-אחורה)
```

⇒ **שלושה נתיבי-כתיבה אמיתיים**, לא אחד.

## שלושת נתיבי-הכתיבה, ומה כל אחד מהם מסביר

| # | `file:line` | סוג | תנאי-הפעלה | מה הוא כותב |
|---|---|---|---|---|
| 1 | `backend/v9/services/fill_poller.py:558` (+`:579` fallback) | **אוטומטי, בתהליך** | רק במסלול-הנפילה `CLOSED_TRADE_PNL` מ-`TradeActivityLog` | `pnl_usd = pnl_sierra = float(sierra_pnl)` **וגם** `exit_reason="BRACKET_EXIT_ACTIVITY"` |
| 2 | `scripts/pnl_reconcile.py:57 write_back()` | **אצווה, CLI** | `--write` **+** `--i-have-michaels-ruling` (שומר-[[T-227]]) | מחושב מ-`trade_fills_journal.jsonl` |
| 3 | `scripts/sierra_activity_join.py:266 write_pnl_sierra()` | **אצווה, CLI** | `--write` | מחושב מ-`Closed Trade P/L` ב-`TradeActivityLog` (סמכות גבוהה יותר) |

**המפריד הלוגי:** נתיב 1 מציב `pnl_usd` ו-`pnl_sierra` ל**אותו ערך**. ⇒ **כל שורה שבה
השניים חולקים לא יכולה להיכתב על-ידיו.**

## הראיה מה-DB — `exit_reason` הוא הדיסקרימינטור

```
$ psql -c "SELECT id, entry_ts::date d, mode, state, outcome, exit_reason, pnl_usd, pnl_sierra
           FROM v9_trades WHERE mode='live' AND state='CLOSED' AND entry_ts>='2026-09-07' ORDER BY id;"
rc=0
  id  |     d      | mode | state  | outcome  |      exit_reason      | pnl_usd | pnl_sierra
 1191 | 2026-09-07 | live | CLOSED | WIN      | BRACKET_EXIT_ACTIVITY |     2.5 |        2.5
 1224 | 2026-09-08 | live | CLOSED | LOSS     | STOP_HIT              |     -50 |      -42.5
 1231 | 2026-09-08 | live | CLOSED | LOSS     | STOP_HIT              | -103.75 |     -86.25
 1262 | 2026-09-08 | live | CLOSED | LOSS     | STOP_HIT              |   -52.5 |      -52.5
 1328 | 2026-09-09 | live | CLOSED | LOSS     | STOP_HIT              |     -40 |        -40
 1343 | 2026-09-09 | live | CLOSED | LOSS     | STOP_HIT              | -131.25 |     -137.5
 1409 | 2026-09-10 | live | CLOSED | LOSS     | STOP_HIT              |  -33.75 |
 1498 | 2026-09-11 | live | CLOSED | UNPRICED | phantom_reconcile     |         |
 1512 | 2026-09-11 | live | CLOSED | WIN      | STOP_HIT              |   38.75 |
(9 rows)
```

**מה שזה מוכיח:** רק `1191` נושאת `BRACKET_EXIT_ACTIVITY` ⇒ **רק היא** יכולה להיות פרי
הנתיב האוטומטי. `8` הנותרות נסגרו ב-`STOP_HIT`/`phantom_reconcile` — מסלולים ש**אינם
כותבים את העמודה כלל**. ⇒ **השערה (א) בצורתה "נשבר ב-09-10" מופרכת:** הנתיב האוטומטי
לא כתב את `1224..1343` מלכתחילה, ולכן לא היה מה שיישבר.

## הרצה קריאה-בלבד של הרקונסיילר (‏`--write` לא הועבר)

```
$ python3 scripts/pnl_reconcile.py --mode live --since 2026-09-07   ;  rc=1
journal: /Users/michael/SierraChart_Data/v9_export/trade_fills_journal.jsonl  (535 fill lines)
trades:  11 CLOSED mode=live since=2026-09-07 · correlated by Sierra order id: 9
 trade mode         books     sierra     delta    cov  status
  1191 live         +2.50          —         —  0/2   incomplete
  1224 live        -50.00     -50.00     +0.00  2/2   MATCH
  1231 live       -103.75    -103.75     +0.00  2/2   MATCH
  1262 live        -52.50     -52.50     +0.00  2/2   MATCH
  1328 live        -40.00     -40.00     +0.00  2/2   MATCH
  1343 live       -131.25    -131.25     +0.00  5/5   MATCH
  1409 live        -33.75     -33.75     +0.00  4/4   MATCH
  1498 live             —          —         —  2/4   incomplete
  1512 live        +38.75     +38.75     +0.00  2/2   MATCH
matched 7 · DIVERGENT 0 · incomplete 2 · books -372.50 vs sierra -372.50 → net book error +0.00
(dry-run: nothing was written — pnl_sierra untouched)
```

**שתי מסקנות חדות:**
1. **`1409` (`4/4`) ו-`1512` (`2/2`) ניתנות-לחישוב *עכשיו*, `MATCH`.** הערך קיים ביומן;
   העמודה ריקה **רק משום שאיש לא הריץ `--write`**. ⇒ זו **לא** רגרסיה.
   `1498` = `incomplete 2/4` ⇒ `NULL` **נכון** (כישלון-כן, Rule-1) — המכנה האפקטיבי `2` ולא `3`.
2. **`1191` היא `incomplete 0/2` ⇒ כלי-האצווה *לא יכול* היה לכתוב אותה.** ובכל זאת יש לה
   ערך. ⇒ **הוכחה-בדרך-השלילה** שהוא הגיע מ-`fill_poller` (והיא היחידה עם `BRACKET_EXIT_ACTIVITY`).

## 🔴 ממצא-לוואי: העמודה **אינה בעלת-בעלים-יחיד** — שני כלים, שני מספרים שונים

הרקונסיילר מחשב `1224 = -50.00`, אך ב-DB יושב `-42.50`. ⇒ **לא הוא כתב אותה.** אישוש:

```
$ python3 scripts/sierra_activity_join.py --date 2026-09-08   ;  rc=0
# source: /Users/michael/SierraChart/TradeActivityLogs/TradeActivityLog_2026-09-08_UTC.37138283.data
 trade dir    books_pnl broker_pnl      recon  ok       Δ$
  1224 SHORT     -50.00     -42.50     -42.50  OK    -7.50
  1231 SHORT    -103.75     -86.25     -86.25  OK   -17.50
  1262 LONG      -52.50    -105.00     -52.50  !!   +52.50
DRY-RUN — would set pnl_sierra on 0 rows: []
```

`-42.50` ו-`-86.25` **משוחזרים בדיוק** ⇒ `1224/1231/1343` נכתבו ע"י
`sierra_activity_join.py --write` (‏T-256), ולא ע"י `pnl_reconcile.py`.
⇒ **שני כלים כותבים את אותה עמודה ממקורות שונים ומקבלים מספרים שונים לאותה עסקה**
(‏`-50.00` מול `-42.50`). זו הפרת "בעל אחד לכל תפקיד" של [[LEARNING_DOCTRINE]] ⇒ **[[T-351]]**.

## מפקד המתזמנים — LaunchAgents · crontab · סקריפט-ה-EOD

```
$ ls -1 ~/Library/LaunchAgents/*.plist                                   ⇒  n_plists=13
$ grep -l "pnl_reconcile\|sierra_activity_join\|pnl_sierra\|sierra_pnl_reconcile" \
      ~/Library/LaunchAgents/*.plist                                     ⇒  rc=1  hits=0
$ grep -l "Program" ~/Library/LaunchAgents/*.plist   [ביקורת-חיובית]     ⇒  control_hits=11
$ crontab -l                                          ⇒  rc=1  "crontab: no crontab for michael"
$ grep -n "pnl_reconcile\|sierra_activity_join\|pnl_sierra" scripts/eod_data_handoff.sh
      73:       exit_ts::text, exit_price, exit_reason, pnl_usd, pnl_sierra,   ← SELECT בלבד
$ grep -c "python3" scripts/eod_data_handoff.sh       [ביקורת-חיובית]    ⇒  9
```

**האפס מגובה בביקורת-חיובית דרך אותה צורת-פקודה** (`11` ו-`9` התאמות) ⇒ אינו עיוורון-grep.
`com.mems26.eod_handoff` רץ `23:05` א'-ו' ומריץ `scripts/eod_data_handoff.sh`, שרק **קורא**
את העמודה. **אין ולו מתזמן אחד שמריץ `--write`.**

מפקד-סופי של כל אזכור לשני הכלים (‏`*.sh|*.py|*.command|*.plist|*.yaml|*.yml`) ⇒ `13` שורות,
**כולן** docstrings/usage/הערות/טעינת-מודול-במבחן. **אפס הפעלות.** והמובהקת שבהן — המערכת
מורה ל**אדם** להריץ ידנית:

```
scripts/live_pnl.py:145:  print("      python3 scripts/sierra_activity_join.py --date <d> --write")
scripts/live_pnl.py:14:   `pnl_sierra` is written by `sierra_activity_join.py`, which ...
```

## ✅ ההכרעה

**השערה (ב) שורדת.** `pnl_sierra` מתמלאת בעיקרה ע"י **כלי-אצווה ידני** שאינו מחובר לשום
מתזמן, ולא הורץ מאז `09-09`. זו **חזרה מדויקת** על מה ש-[[T-192]] כבר חזה ב-05.09
(*"כלי שרץ פעם אחת ידנית יחזור להיות NULL"*) — הפעם עם מנגנון מוכח ולא משוער.

**השערה (א) אינה מתה לגמרי, אבל היא לא מסבירה את הפער:** קיים נתיב אוטומטי אמיתי
(`fill_poller.py:558`), אך הוא מותנה במסלול-`CLOSED_TRADE_PNL` ומסביר **`1/9`** שורות.
**אין ענף שנשבר ב-`09-10`** — לא נמצא, ולא נטען שיש.

**לא תוקן דבר.** לא הורץ `--write`. לא נוגע קוד. `T-350` יורד ל-🟠 (מנגנון מוכח), **ואינו נסגר**.

### מה שבמפורש אינו נטען (NOT-DONE)
1. **לא נמדד מתי בדיוק הורץ הכלי לאחרונה** — אין חותמת-הרצה; ההסקה היא מהנתונים בלבד.
2. **לא הוכרע מי משני הכלים הוא הבעלים הנכון** של העמודה ⇒ [[T-351]], דורש פסיקת-מייקל.
3. **`1262` מסומנת `!!`** ע"י `sierra_activity_join` (‏`-105.00` ברוקר מול `-52.50` recon)
   ו-`COVERAGE ... INCOMPLETE (residual +697.50)` ⇒ **מיפוי-הברוקר ל-`09-08` אינו מלא**;
   לא נחקר הלילה.
4. **לא הורץ backfill** ל-`1409`/`1512` — `--write` חסום מאחורי `--i-have-michaels-ruling`
   (שומר-[[T-227]], פסיקת 02.09) ⇒ **מעבר-לסמכות תור-הלילה**.
