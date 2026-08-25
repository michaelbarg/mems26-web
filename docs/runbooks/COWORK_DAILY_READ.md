# MEMS26 · הקריאה-היומית של Cowork

**מה זה:** המסמך שסוכן-Cowork קורא בתחילת **כל** סשן — לפני שהוא עונה על שאלה
אחת על מצב-המערכת. הוא לא מחליף שום מקור-אמת; הוא אומר **באיזה סדר לקרוא אותם**,
**באילו פקודות מוציאים את אמת-היום**, ו**אילו מלכודות הופכות דוח לשקר**.

**מה זה לא:** לא רשימת-משימות (זה `TASK_LOG.md`, והוא היחיד — `task_log_guard`
נכשל על מרשם מתחרה). לא פרוטוקול-פתיחה (זה `PRE_OPEN_PROTOCOL_2026-08-16.md`).
לא מילון-תקלות (זה `PRE_TRADE_PROTOCOL.md`). לא אבחון "למה לא ירה"
(זה `FIRING_READINESS_PROTOCOL.md`).

**נגזר מ:** בדיקת ה-EOD של 18.08. כל מלכודת בסעיף §3 היא טעות שקרתה בפועל
באותה בדיקה, או שכמעט קרתה — לא רשימה תיאורטית.

---

## §0 · חוק-הברזל: הכל דרך Desktop Commander על ה-Mac

**סנדבוק-Cowork מנותק מה-DB, מהלוגים ומ-Sierra.** סקריפט שרץ שם יחזיר "תקין" על
מערכת מתה. זו מחלקת-כשל I-7, והיא חזרה 5 פעמים.

אם אין גישה למכונה — כותבים **"לא ניתן לקבוע"**. לא "תקין", לא "כנראה".

---

## §1 · סדר-הקריאה (3 דקות, בלי לרוץ לקוד)

| # | קובץ | מה מוציאים ממנו |
|---|---|---|
| 1 | `docs/plans/TASK_LOG.md` | מה פתוח · הסטטוס · **הצעד הבא** לכל פריט. בלוק "3 דברים למחר" בראש = סדר-העדיפויות |
| 2 | `docs/handoff/LIVE_CHANNEL.md` | הודעות מהסוכנים האחרים · פסיקות ממתינות |
| 3 | `docs/plans/STATUS_BOARD.md` — **הרשומה העליונה בלבד** | מה נמצא ואומת בסשן הקודם. הקובץ 2,000+ שורות — לעולם לא לקרוא במלואו, `head -c 3000` |
| 4 | `config/RULED_FLAGS.yaml` | מצב-דגל **נקבע כאן**, לא מהזיכרון ולא מ-`ps eww` |

`git pull` לפני. `commit`+`push` אחרי.

---

## §2 · אמת-היום — הפקודות (כל אחת אומתה 18.08)

```bash
PSQL=/Applications/Postgres.app/Contents/Versions/latest/bin/psql
DB=postgresql://localhost/mems26
# יום-המסחר האחרון שיש לו ברי-RTH — לא CURRENT_DATE (§3.3)
DAY=$($PSQL $DB -At -c "SELECT max((ts AT TIME ZONE 'America/New_York')::date)
  FROM v9_bars_5min_woodies
  WHERE (ts AT TIME ZONE 'America/New_York')::time >= time '09:30'
    AND (ts AT TIME ZONE 'America/New_York')::time <  time '16:00';")
echo "יום-המסחר הנבדק: $DAY"     # ← להדפיס ולוודא שזה היום שהתכוונת אליו
```

**א · עסקאות היום** — תמיד ב-ET, לעולם לא `entry_ts::date` גולמי (§3.3):

```bash
$PSQL $DB -P pager=off -c "SELECT id, mode, firing_system sys, pattern_id_at_entry pat,
  direction dir, state, to_char(entry_ts AT TIME ZONE 'America/New_York','MM-DD HH24:MI') entry_et,
  exit_reason, pnl_usd, pnl_sierra, outcome
  FROM v9_trades
  WHERE (entry_ts AT TIME ZONE 'America/New_York')::date = date '$DAY'
  ORDER BY entry_ts;"
```

**אפס שורות? לפני שמדווחים "המערכת לא ירתה" — להוכיח שהיא חיה** (§3.4):

```bash
curl -s -m 5 http://localhost:8000/api/v9/health        # {"status":"ok",...}
lsof -nP -iTCP:8000 -sTCP:LISTEN | head -3              # יש מאזין
ls -lt ~/SierraChart_Data/v9_export/ | head -5          # mtime של עכשיו
$PSQL $DB -P pager=off -c "SELECT count(*) rows, max(ts) max_ts, now()
  FROM v9_bars_5min_woodies WHERE ts > now() - interval '36 hours';"
```

**ב · היסטוגרמת חסימות** — הפיד **חסום ל-200 שורות** בלי קשר ל-`limit` (§3.2):

```bash
curl -s "http://localhost:8000/api/v9/gateway/decisions?limit=2000" > /tmp/dec.json
python3 - <<'PY'
import json,collections,datetime
rows=json.load(open('/tmp/dec.json'))['decisions']
today=[r for r in rows if r['ts'][:10]==datetime.date.today().isoformat()]
print("החזיר:",len(rows),"| מהיום:",len(today))
print("טווח:",today[-1]['ts'],"->",today[0]['ts'] if today else None)   # ← §3.2
def et(r): return datetime.datetime.fromisoformat(r['ts']).astimezone(
    datetime.timezone(datetime.timedelta(hours=-4)))
rth=[r for r in today if 9.5 <= et(r).hour+et(r).minute/60 < 16]
for label,src in (("כל היום",today),("RTH בלבד",rth)):
    print(f"\n-- blocked_by · {label} (n={len(src)}) --")
    for k,v in collections.Counter(r.get('blocked_by') or '(none)' for r in src).most_common():
        print(f"{v:5d}  {k}")
    print("  כיוונים:",collections.Counter(r['direction'] for r in src))
PY
```

**לפצל RTH מטרום-סשן.** ב-18.08 היו 147 `cold_start_guard` שנראו כמו הממצא
הגדול — כולם 04:02–04:51 ET, אחרי ריסטארט, לפני שהשוק נפתח. הממצא האמיתי היה
30 חסימות בתוך RTH. שער שחסם **≥3 בתוך RTH** = מדווחים, עם פילוח-כיוון.

**ג · מסלול-המחיר** — בלעדיו "השער חסם X" הוא ספירה בלי משמעות:

```bash
$PSQL $DB -P pager=off -c "SELECT count(*) n, (array_agg(close ORDER BY ts))[1] first_close,
  (array_agg(close ORDER BY ts DESC))[1] last_close, max(high) rth_high, min(low) rth_low
  FROM v9_bars_5min_woodies
  WHERE (ts AT TIME ZONE 'America/New_York')::date = date '$DAY'
    AND (ts AT TIME ZONE 'America/New_York')::time >= time '09:30'
    AND (ts AT TIME ZONE 'America/New_York')::time <  time '16:00';"
```

→ 18.08 החזיר: `n=78 · first_close 7726 · last_close 7715.25 · high 7735.25 · low 7710.25`.

**ד · לוגים — `backend.err.log`, לא `backend.log`** (§3.1):

**ד0 · קודם כל: האם הלוג בכלל רואה?** (§3.9 — המלכודת שהרגה את כל 19.08).
כל הפקודות שמתחת מניחות שורות עם **חותמת-זמן** ורמת-INFO. אם שכבת-ה-INFO לא
נטענה, כולן יחזירו 0 — וזה **עיוורון, לא ממצא**. השער הזה חייב לעבור ראשון:

```bash
PID=$(pgrep -f "uvicorn backend.main:app" | head -1)
grep "\[boot\] logging OK" /tmp/backend.err.log | tail -1     # חייב לכלול pid=$PID
# → 2026-08-20 15:01:18 [INFO] [mems26.boot] [boot] logging OK level=INFO pid=… commit=…
```

אין שורה כזו, או שה-pid בה **אינו** ה-pid שרץ ⇒ התהליך עלה בלי שכבת-INFO:
לעצור, לא לדווח "0 שורות" על שום דבר. (`python3 scripts/fire_drill.py` נכשל
NO-GO על בדיוק זה — `T-61 שכבת-INFO בלוג`.)

**ד1 · ספירות — תחומות ליום, אחרת סופרים את כל ההיסטוריה.** פורמט-השורה מאז
20.08 הוא `‏YYYY-MM-DD HH:MM:SS [LEVEL] [logger.name] הודעה`, כך ש-`grep "^$D"`
תוחם ליום ו-`[logger.name]` אומר מאיזה קובץ זה בא:

```bash
D="$DAY"        # ← לא date +%F: אחרי חצות IDT זה כבר המחר (§3.3)
for k in ExitVerify exit_not_executed exit_needs_manual exit_unverifiable \
         OPENING_DIR_FUSION TREND_STEP SCALE_IN PROTECTED_QTY drive_exhaustion; do
  printf "%-22s today=%-6s all=%s\n" "$k" \
    "$(grep "^$D" /tmp/backend.err.log | grep -c -- "$k")" \
    "$(grep -c -- "$k" /tmp/backend.err.log)"
done
grep "^$D" /tmp/backend.err.log | grep -E "LIVE trade TM id|SHADOW trade TM|LIVE fire BLOCKED|ORPHAN|COMMAND QUEUED"
```

**`today=0` אבל `all>0`?** או שהיום באמת שקט, או שהלוג נכתב בלי חותמות — לחזור
ל-ד0. שורות **בלי** חותמת בכלל הן של uvicorn עצמו (יש לו פורמט משלו) ושל
`[env_loader]` (‏`print` לפני שהלוגינג בכלל יכול לעלות) — אלו בלבד ותקינות.

**ה · הצלבת-ברוקר** — הספרים כבר טעו (14.08: −$135 בספרים מול +$120 אצל הברוקר):

```bash
cat ~/SierraChart_Data/v9_export/sierra_state.json | python3 -m json.tool | \
  grep -E "is_sim|position_qty|daily_pnl|acct_daily_pl|daily_total_qty_filled|trade_account"
ls -lt ~/SierraChart/TradeActivityLogs/*.data | head -3
```

**ו · שערי-שפיות** (שניהם חייבים לעבור לפני שכותבים לקבצים):

```bash
python3 scripts/flag_guard.py     | tail -3    # PASS — all N ruled flags match
python3 scripts/task_log_guard.py | tail -3    # ✅ current, structured, and the only one
```

---

## §3 · המלכודות — כל אחת הפכה דוח לשקר, או כמעט

**3.1 · `/tmp/backend.log` הוא לוג-גישה של uvicorn בלבד.** לוגי-האפליקציה הולכים
ל-**`/tmp/backend.err.log`** (stderr). ב-18.08 גרפ ב-`backend.log` החזיר **0**
לכל חמשת השינויים — מסקנה "שום דבר לא רץ" הייתה שקר גמור; ב-`backend.err.log`
היו 28 שורות `OPENING_DIR_FUSION` ו-25 `TREND_STEP`.
לאמת עם `lsof -p <pid> | grep '\.log'` לפני שמסיקים מאפס-תוצאות.

**3.2 · `/api/v9/gateway/decisions` מחזיר 200 שורות מקסימום** — `limit=2000`
מוחזר זהה ל-`limit=200`. תמיד להדפיס את ה-**ts הישן ביותר** בתשובה: אם הוא
מאוחר מפתיחת-הסשן, ההיסטוגרמה חתוכה ואסור לומר "כל ההחלטות של היום".

**3.3 · שתי מלכודות-תאריך, ושתיהן שקטות.**
**(א)** `WHERE entry_ts >= date '...'` משתמש ב-TZ של השרת; יום-מסחר הוא **ET** —
תמיד `(entry_ts AT TIME ZONE 'America/New_York')::date`. גם `created_at` נבדק
בנפרד: "0 שורות **נוצרו** היום" הוא ממצא אחר מ-"0 עסקאות עם **כניסה** היום".
**(ב) `CURRENT_DATE` ו-`date +%F` שקריים ב-EOD.** ה-EOD רץ ב-23:15 IDT ולעיתים
מסתיים אחרי חצות — ואז שניהם מצביעים על **מחר**, וכל שאילתה מחזירה 0 שורות בלי
שגיאה. זה בדיוק מה שקרה בבנייה של המסמך הזה: אותן שאילתות שהחזירו 78 ברי-RTH
ב-23:24 החזירו `n=0` ב-00:10. **תמיד לגזור `DAY` מהנתונים** (הבלוק בראש §2)
ולהדפיס אותו לפני שממשיכים.

**3.4 · אפס עסקאות ≠ מערכת מתה.** לפני שמדווחים תקלה — health + מאזין + טריות-פיד
+ mtime של הייצוא. ב-18.08 כל הארבעה היו תקינים; היום היה אפס-ירי **בגלל שער**,
לא בגלל נפילה. הדיווח ההפוך היה שולח את מייקל לתקן תשתית בריאה.

**3.5 · `daily_pnl` ב-`sierra_state` הוא של החשבון, לא של המערכת.** החשבון משותף
עם המסחר הידני של מייקל. לפני שמייחסים P&L למערכת — לספור פקודות:

```bash
grep "^$DAY" /tmp/backend.err.log | grep -c "COMMAND QUEUED"
```

אפס פקודות-כניסה ⇒ **שום fill באותו יום אינו של המערכת**, ולכן גם לא ה-P&L.
ככה נסגר T-44 ב-18.08: פקודה אחת בלבד כל היום (`op=FLATTEN_ACCOUNT`), ולכן
46 החוזים ו-−$443.75 היו של מייקל — לא "fill שאבד".

**3.6 · היעדר שורת-לוג ≠ פיצ'ר שבור.** `EXIT_VERIFY_V1` נתן 0 שורות ב-18.08 כי
היו 0 יציאות-מערכת. **"לא-נבחן" הוא ממצא שונה מ"נכשל"** — ואסור להסליק אותו
ל"עובד". כל דגל שרץ ביום עם 0 עסקאות נשאר לא-נבחן.

**3.7 · `high_during_pos` / `low_during_pos` ב-`sierra_state` מכילים זבל-סנטינל**
(±1.79e308) כשאין פוזיציה. לא לדווח אותם כמחירים.

**3.9 · לוג בלי חותמות = `logging.lastResort` = עיוורון-מלא, ולא "שקט".**
כל 19.08 (מריסטארט-16:09) נכתבו רק WARNING+ בלי חותמת/רמה. השורש: אף אחד לא
הגדיר את ה-root logger — `uvicorn` מגדיר רק את הלוגרים שלו, וה-`basicConfig`
היחיד באפליקציה יושב מאחורי **import עצל** ב-`status.py:172`, כלומר הקונפיג עלה
רק כשמישהו פתח את הדשבורד. עד אז Python נופל ל-`logging.lastResort` —
`_StderrHandler` נעול על WARNING **בלי פורמטר**. התוצאה: 22 עסקאות-צל בספרים מול
**0** שורות `SHADOW trade TM`, ו-`[ExitVerify]`/`OPENING_DIR_FUSION` (שניהם INFO)
בלתי-נראים. תוקן 20.08 (F3/T-61) ב-`backend/logging_setup.py`, שנקרא ב-import של
`backend/main.py` לפני כל `backend.v9`. **הזיהוי בשטח:** שורה בלוג שלא מתחילה
ב-`YYYY-MM-DD`. **השער:** ד0 למעלה + `fire_drill`.

**3.8 · `task_log_guard` דורש את מזהה-ה-T המילולי ב-STATUS_BOARD.** פריט ✅
שמכוסה ברשומה שכותרתה "T-36..T-40" **ייכשל** — הטווח לא מתרחב. לכתוב
`T-36 · T-37 · T-38 · T-39 · T-40`.

**3.9 · גודל-עסקה נקבע ב-`contract_size.ruled_contracts()`, לא ב-`.env`.**
הפונקציה בודקת `_6→_5→_4→_2→_3`; מסלול שקורא `getenv("FIXED_CONTRACTS_4")`
ישירות **סותר** אותה (T-51). המדידה מ-19.08, שלושתם באותו רגע:

```bash
set -a; source .env; set +a
python3 -c "
import os,sys; sys.path.insert(0,'.')
from backend.v9.services.contract_size import ruled_contracts
def on(n): return os.getenv(n,'0').lower() in ('1','true','yes')
print('ruled_contracts()   ->', ruled_contracts())
print('_ct_resolve()       ->', 4 if on('FIXED_CONTRACTS_4') else 2 if on('FIXED_CONTRACTS_2') else 3)
print('five_min:1516       ->', 3 if os.getenv('FIXED_CONTRACTS_3','0')=='1' else (4 if os.getenv('FIXED_CONTRACTS_4','0')=='1' else 1))"
```
→ החזיר **6 · 3 · 1**. שלוש תשובות, אותו רגע. **לעולם לא לענות על "בכמה חוזים
המערכת סוחרת" מקריאת `.env`** — להריץ את זה.

**3.10 · המצב זז בין סשנים — לקרוא `git log` לפני שמסתמכים על אתמול.**
בין ה-EOD של 18.08 לסשן שאחריו, מייקל **כיבה את `drive_exhaustion_veto`** ועבר
ל-6 חוזים (`c2d6a125`, `7ed455bb`). דוח שהיה חוזר על "השער חוסם 30 מועמדים"
היה מדבר על מערכת שכבר לא קיימת:

```bash
git log --oneline -5
git log --oneline -3 -- config/RULED_FLAGS.yaml .env
```

---

## §4 · מה מותר לשנות בבדיקה יומית

**קריאה-בלבד על המסחר.** לא דגלים · לא ריסטארט · לא כתיבה ל-DB · לא נגיעה
ב-`~/SierraChart_Data`. פוזיציה של מייקל — לא נוגעים (פסיקת 18.08: "היא שלי").

**מותר וחובה לכתוב:** `TASK_LOG.md` (הצעד-הבא · פריט חדש · סגירה מאומתת) ושורה
ב-`STATUS_BOARD.md` בתבנית **ממצא → תיקון/הצעה → ראיה (פקודה + פלט גולמי)**.
"בוצע" בלי ממצא ובלי אימות — לא קביל (כלל 5).

**`n<10` = לסמן ראיה-דקה במפורש.** ב-18.08: 4 מועמדי-פיוז'ן ו-2 מדרגות הם
סימן-כיוון, לא מסקנה. ספירת-מועמדים של שער היא **לא** P&L — הכימות דורש
`gate_profit_audit` (חסום מאחורי באג-TZ, T-11).

### מלכודת 11 · CVD מתמלא רק ב-RTH (פסיקת-מייקל 25.08)

מייקל: *"cvd פועל — תרשום לעצמך שהוא מקבל מידע בפתיחה."*

`v9_bars_cumulative_delta` נראה **"קפוא"** בכל שעה שאינה שעת-מסחר, כי השורה האחרונה
היא סוף-הסשן הקודם. **טריות-CVD נמדדת רק מ-09:30 ET ואילך.**

**הטעות בפועל (cowork, 25.08 16:12 IL = 09:12 ET, טרום-פתיחה):**
```
CVD אחרון: 2026-08-24 23:55 | לפני 16 שעות
```
דיווחתי "הזרם קפוא". הוא לא היה קפוא — השוק היה סגור.

אותה משפחה כמו *"אפס עסקאות ≠ מערכת מתה"*: **לבדוק את שעון-השוק לפני שקוראים לנתון
תקוע.** ‏`T-57` ב-`TASK_LOG` טוען "קפוא מ-18.08 20:55" — **לאמת מול חלון-RTH לפני
שמסתמכים עליו.**
