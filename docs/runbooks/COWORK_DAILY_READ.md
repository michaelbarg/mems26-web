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

**ו-`set -a; source .env; set +a` הוא חלק מהפקודה, לא קישוט** (נמדד 16.09 14:37,
cowork). `ruled_contracts()` קורא `os.environ` ואינו טוען את `.env` בעצמו; גם
ייבוא שרשרת-הבקאנד אינו טוען אותו. לכן הנוסח החד-שורתי **בלי** ה-`source`:

```
ruled_contracts()                      -> None      ← נקרא כ"אין פסיקה פעילה"
effective_contracts({"size":"full"})   -> 3         ← ברירת-המחדל, לא הפסיקה
   (ובתוך fire_drill: `_want = ruled_contracts() or 1`)
עם .env טעון:  ruled_contracts() = 1        ← פסיקת-מייקל 18.09 12:05 "חוזה 1"
```

**המספר הזה זז, והדוגמה כאן כבר הכשילה פעם אחת.** עד 23.09 נכתב כאן `= 2`
(פסיקת 15.09), אחרי שפסיקת 18.09 כבר הורידה ל-1 — סוכן שמאמת מול הדוגמה רואה
`1`, מסיק "אי-התאמה", ועוצר שער תקין. **הדוגמה אינה מקור-אמת לגודל.** המקור הוא
`config/RULED_FLAGS.yaml` + `ruled_contracts()` עם `.env` טעון, ולאישוש —
`contracts_cfg` מהתהליך החי (נמדד 23.09 19:14, cowork-daily: שלושתם `1`).

`None` אינו אפס ואינו "אין פסיקה" — הוא "לא נמדד". `fire_drill.py:38-41` טוען
`.env` בעצמו כשהוא רץ כסקריפט, ולכן **השער תקין**; הנפילה היא באגף המדידה.
הדרך הקצרה והבטוחה ביותר לענות על השאלה היא מהתהליך **החי**:
`GET /api/v9/mobile/data?key=…` → `contracts_cfg` — מה שהבקאנד באמת מחזיק.

**3.10 · המצב זז בין סשנים — לקרוא `git log` לפני שמסתמכים על אתמול.**
בין ה-EOD של 18.08 לסשן שאחריו, מייקל **כיבה את `drive_exhaustion_veto`** ועבר
ל-6 חוזים (`c2d6a125`, `7ed455bb`). דוח שהיה חוזר על "השער חוסם 30 מועמדים"
היה מדבר על מערכת שכבר לא קיימת:

```bash
git log --oneline -5
git log --oneline -3 -- config/RULED_FLAGS.yaml .env
```

**3.11 · `v9_trades.mode` הוא באותיות קטנות — `mode='LIVE'` מחזיר אפס שורות, בשקט.**
נמדד 02.10 10:36 (cowork-dev ריצה 150). הערכים הקנוניים הם `live` · `shadow` ·
`demo`, וכך גם בקוד (`backend/v9/tests/test_postmortem_v1.py:74` ואילך):

```
SELECT mode, count(*) FROM v9_trades GROUP BY mode;   ->  shadow|2440 · live|213 · demo|29
WHERE mode='LIVE'  -> 0 שורות        WHERE mode='live' -> #2843 (האחרונה, 10-01 14:10 ET)
```

זו מחלקת-הכשל של §3.4 בדיוק: אפס-שורות שנראה כמו "המערכת לא ירתה / מתה" כשהיא
חיה לגמרי. **לפני שמדווחים אפס-עסקאות מתוך שאילתה עם פילטר-`mode` — לאמת את
האיות ב-`GROUP BY mode`.** שאילתת §2א לא מסננת לפי `mode` כלל (היא בוחרת אותו
כעמודה) ולכן אינה חשופה — החשיפה היא בכל פילטר שמוסיפים לה.

**וגם, מאותה מדידה:** `state<>'CLOSED'` על `mode='live'` החזיר 36 — **כולן
`CANCELLED`, האחרונה 27.07**. היסטוריה, לא פוזיציות תקועות. הספירה לבדה אינה
ממצא; הפילוח הוא: `SELECT state, count(*) … GROUP BY state` ⇒ `CLOSED|177 · CANCELLED|36`.

**3.12 · הרלה נקראת `mobile_relay.py` — `pgrep -f phone_relay` מחזיר ריק על רלה חיה.**
נמדד 02.10 11:37 (cowork-dev ריצה 152). אין שום סקריפט בשם `phone_relay`; מי שעונה
לטלפון הוא `scripts/mobile_relay.py` תחת `com.mems26.mobile_relay`. `pgrep` שותק
בהצלחה (rc=1, אפס פלט) ולכן זה נקרא כ-"הרלה מתה" — ואם ההודעה ההפוכה נשלחת, מייקל
נשלח לתקן תשתית בריאה. **הפוסק הנכון, והוא מכסה את כל התשעה בבת-אחת:**

```bash
launchctl list | grep -i mems26 | sort
# 611 0 com.mems26.backend · 621 frontend · 637 bridge
# 1619 export_promoter · 1624 activity_feed · 1629 mobile_relay      ← שישה עם PID
# -   0 eod_handoff · startup_check · update_check                   ← מתוזמנים-בלבד
```

`-` בעמודת-ה-PID על שלושת המתוזמנים הוא **מצבם התקין בין הרצות**, לא כשל — אל
תדווח 6/9. ולהפך, PID על אחד מהם בשעה שאינה שעת-ההרצה שלו הוא כן ממצא.

זו אותה מחלקה כמו §3.4 ו-§3.11: **אפס-תוצאות מכלי-חיפוש אינו ממצא עד שהתבנית
אומתה.** לפני שמדווחים "תהליך X מת" — `ps aux | grep -i <שם-הקובץ האמיתי>` או
`launchctl list`, ולא תבנית מהזיכרון.

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

### מלכודת 12 · "אפס ממתינות בטלפון" אינה ראיה עד שמוכח שהרלה חי (06.09)

`docs/handoff/PHONE_THREAD.jsonl` הוא הקובץ שקוראים — אבל **הכותב היחיד** של
הודעות-מייקל לתוכו הוא `com.mems26.mobile_relay`. כשהרלה מת, הקובץ נשאר ריק
**בלי קשר** למה שמייקל שלח. ⇒ "אין ממתינות ⇒ שקט" היא **שלילה-כוזבת**.

**הטעות בפועל (cowork, 06.09):** שתי ריצות רצופות (`17:12`, `17:37`) הסיקו "שקט"
מקובץ שהדוור-המת לא מילא. הרלה נפל בריסטארט של `17:03` ולא עלה 3.5 שעות.

**הבדיקה הנכונה — שתי שורות, לפני שמסיקים שקט:**
```bash
launchctl print gui/$UID/com.mems26.mobile_relay | grep -E "state|pid"   # "Could not find service" = לא-מאותחל
curl -s "$RENDER_MOBILE_URL/instruction/pending?key=$MOBILE_ACCESS_KEY"  # התיבה במקור — peek, לא pop
```
`GET /instruction/pending` ו-`GET /cmd/pending` הם **peek** (המחיקה רק ב-`POST
/instruction/status` / `/cmd/ack`) ⇒ קריאה בטוחה ונטולת-תופעות-לוואי, גם כשהרלה מת.
**הודעה שנשלחה בזמן שהרלה מת אינה אובדת** — היא ממתינה ב-Render עד ה-ack.

**וההכללה, שהיא העיקר:** `mems26_verify.sh` ו-`fire_drill` בודקים **שירותים**
(backend/bridge/frontend) ולא **סוכנים**. ב-06.09 הם החזירו ירוק מלא — `health=200`,
שלושה שירותים, `0 ERROR` — בזמן ששישה LaunchAgents לא עלו כלל **וסיירה לא רצה בכלל**.
⇒ **ירוק שנמדד על הסט הלא-נכון.** לפני שמדווחים "המערכת תקינה", לספור:
```bash
for a in backend bridge frontend mobile_relay export_promoter activity_feed eod_handoff startup_check update_check; do
  printf "%-16s " "$a"; launchctl print gui/$UID/com.mems26.$a 2>/dev/null | grep -cE "^\s*state = " ; done
ps aux | grep -i sierra | grep -v grep    # לסיירה אין LaunchAgent — היא לא תעלה לבד אחרי ריסטארט
```

**התיקון כשמוצאים סוכן שלא עלה:** `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.mems26.<name>.plist`
— אומת 06.09 `20:38` שהוא מחזיק **גם** לסוכנים המסומנים `disallowed` ב-Background
Task Management. ⚠️ **לפני העלאת `mobile_relay` בלבד:** לוודא `GET /cmd/pending ⇒ null`,
כי הוא מושך פקודות-חירום ממתינות ומבצע אותן מקומית ⇒ עלייה עיוורת עלולה לירות
`FLATTEN` ישן. לשאר הסוכנים אין נתיב-ביצוע ⇒ אין סיכון כזה.

### מלכודת 13 · `pgrep sierra ⇒ 0` **אינו** מוכיח שסיירה למטה (07.09)

סיירה רצה תחת **CrossOver/wine**, ולכן שם-התהליך אינו "sierra" אלא
`wine64-preloader` / `Menu Helper`. ‏`pgrep -i sierra` החזיר `0` **גם ב-13:37,
עשרים דקות אחרי שמייקל פתח אותה ב-13:17** והפיד כבר זרם.

ב-07.09 דווח שבע פעמים "סיירה למטה" על סמך `pgrep` בלבד. הדיווחים היו **נכונים
בפועל**, אבל הכלי אינו קביל כראיה-שלילית — הוא היה מחזיר בדיוק אותו `0` גם אילו
הייתה רצה. זהו `grep ⇒ 0` שמוכיח רק שהמחרוזת **שניחשתי** לא נמצאה.

**המדידה הקבילה — שלוש, ולא אחת:**

```bash
ps aux | grep -i "sierra\|SierraChart" | grep -v grep     # תופס את wine
cat ~/SierraChart_Data/v9_export/live_price.json          # ts טרי + bid/ask ⇒ הפיד חי
psql … -c "select max(ts), now()-max(ts) from v9_bars_5min_woodies;"   # הקנוני נקלט?
```

**⚠️ והכיוון ההפוך מסוכן לא פחות:** `ps` שמראה תהליך **אינו** מוכיח שהפיד זורם —
ב-07.09 סיירה רצה, `live_price` היה טרי, **ובכל-זאת** ייצוא-ה-RTH (`5min.json`)
היה תקוע על שישי ושער-הקליטה דחה כל אצווה ([[T-265]]). **חיוּת-תהליך · טריוּת-ייצוא ·
קליטה-ל-DB הן שלוש שאלות נפרדות** — לענות על שלושתן לפני שמצהירים "הפיד תקין".

### מלכודת 14 · `exit_ts IS NULL` **אינו** "עסקה פתוחה" — השדה הקובע הוא `state` (16.09)

בבוקר 16.09 סגר `close_stale_shadow.py --apply` ‏26 עסקאות-צל תקועות (הן החזיקו את
ה-TradeManager ב-55-80% CPU ו-1,000 שורות-לוג בדקה). שעתיים אחר-כך, אימות-צד עם
`count(*) … where exit_ts is null` החזיר **57 שורות** — מספר שנראה בדיוק כמו חזרת-התקלה.

**זה היה שקר-מדידה.** הפילוח הראה שכל 57 כבר סגורות:

```bash
psql … -c "select date(entry_ts), mode, state, exit_reason, count(*)
           from v9_trades where exit_ts is null group by 1,2,3,4 order by 1 desc;"
# 51 × shadow CLOSED STALE_UNRESOLVED   ·   6 × live CANCELLED (ORDER_FAILED / PHANTOM_*)
python3 scripts/close_stale_shadow.py   # no stale shadow trades — nothing to do
```

**השורש הוא תכנוני, לא באג:** ‏`close_stale_shadow.py` סוגר **בלי תוצאה** בכוונה —
`state=CLOSED · exit_reason=STALE_UNRESOLVED · exit_price=NULL · pnl=NULL`, וגם
`exit_ts` נשאר ריק — כדי לא לייצר מנצח או מפסיד שלא היה (פסיקת-מייקל 28.07:
"אתה לא לוקח נתונים או מציב נכונים"). שורות `CANCELLED` מעולם לא נכנסו לשוק ולכן
גם להן אין `exit_ts`. שתי הקבוצות סגורות לחלוטין.

**המדידה הקבילה — לפי `state`, כמו שהסקריפט עצמו עושה:**

```bash
psql … -c "select mode, state, count(*) from v9_trades
           where state not in ('CLOSED','CANCELLED') group by 1,2;"   # ריק = אין פתוחות
python3 scripts/close_stale_shadow.py    # dry-run; הוא הפוסק, לא שאילתת-exit_ts
```

**↻ חידוד 23.09 (‏cowork-dev, ‏10:34 — הריצה נפלה במלכודת הזו בעצמה, בפעם השלישית):**
**המספר גדל לנצח, ולכן המלכודת מחמירה עם הזמן:** ‏16.09 ⇒ `57` · **23.09 ⇒ `100`**
(‏`94 shadow CLOSED` מ-11/14/15/17.09 ‏+ `6 live CANCELLED`). השורות האלה מצטברות
לפי התכנון ואינן נמחקות, כך שכל ריצה עתידית תראה מספר **גדול ומפחיד יותר על אותה
מציאות תקינה בדיוק** — ‏150, ‏200, וכן הלאה. אל תקרא לגידול "החמרה".

**ולמה הקוד עצמו מטעה:** ‏`close_stale_shadow.py:44` ⇒ `OPEN_STATES = ("CLOSED","CANCELLED")`
הוא **שם הפוך למשמעות** — זו רשימת **NOT-IN** (ההערה בקוד: *"anything NOT in here is
open"*), לא רשימת המצבים-הפתוחים. סוכן שקורא את השם כפשוטו מסיק שהסקריפט מחפש
`CLOSED` ולכן "פספס" 100 שורות, ומגיע בדיוק למסקנה ההפוכה מהאמת.

⚠️ **ובפעם השלישית — הסוכן ניסח את זה כ„מלכודת חדשה #19" והתחיל להוסיף אותה לקובץ הזה.**
מה שעצר: חיפוש-כפילות לפני הכתיבה (`grep "מלכודת"` על הקובץ). **לפני שמוסיפים מלכודת —
לבדוק שהיא לא כאן כבר.** מלכודת כפולה גרועה מהיעדרה: שני מרשמים ⇒ אף אחד אינו המקור.

**⚠️ מלכודת-TZ נלווית (אותה ריצה):** ‏`extract(epoch from (now() at time zone 'utc') - max(ts))`
על עמודה **tz-aware** החזיר `-10786` — "הפיד שלוש שעות בעתיד". האמת:
`max(ts)=12:10:00+03` מול `now()=12:10:27+03` ⇒ **הפיד בן 27 שניות.** החיסור ערבב
naive-UTC עם aware-IDT. להשוות aware מול aware (`now()`), או `now() at time zone 'utc'`
מול `max(ts) at time zone 'utc'` — לא לערבב. כלל-4 (TZ בקלט-מפרט) חל גם על
שאילתות-האימות עצמן, לא רק על הקוד.

**↻ חידוד 18.09 (‏cowork-dev, ‏11:10 — הריצה נפלה במלכודת הזו בעצמה, על `exit_price`):**
המלכודת רחבה משנרשם ב-16.09 בשתי דרכים, ושתיהן מחמירות אותה עם הזמן:

1. **לא רק `exit_ts` — גם `exit_price IS NULL` הוא אותו שקר-מדידה בדיוק.**
2. **האוכלוסייה אינה מוגבלת ל"נסגר בלי תוצאה" — היא כוללת מנצחות אמיתיות.** הפילוח
   המלא (נמדד 11:10; `entry_ts < היום`, ‏`exit_price IS NULL`) ⇒ `303` שורות, מהן
   **`301` ‏`state=CLOSED`**: `121 × T2_HIT` · `95 × STALE_UNRESOLVED` · `25 × T3_HIT` ·
   `21 × phantom_reconcile` · `12 × MAE_SCRATCH` · `8 × T1_HIT` · ועוד. שתי היתר —
   `CANCELLED` מיולי (`REJECTED`, `PHANTOM_FILLED_FLAT`), גם הן מצב-סופי ⇒ **אפס פתוחות.**
   ⇒ `T2_HIT`/`T3_HIT` הן עסקאות שפגעו ביעד ונסגרו ברווח, ובכל-זאת `exit_price` שלהן ריק;
   מי שיקרא את המספר כ"תקועות" יספור מנצחות כתקלה.
3. **המספר גדל מונוטונית לנצח:** `57` ב-16.09 ⇒ **`303`** ב-18.09. כל יום-מסחר מוסיף
   שורות שלעולם לא ייצאו מהספירה ⇒ ככל שעובר הזמן ה"ממצא" השקרי נראה מפחיד יותר.

```bash
# ❌ אסור כאמת-מדידה — שלוש גרסאות של אותה טעות:
#    exit_ts IS NULL  ·  exit_price IS NULL  ·  pnl_usd IS NULL
# ✅ הפוסק היחיד (dry-run, קריאה-בלבד) — והוא מסתכל על state, לא על עמודות-יציאה:
python3 scripts/close_stale_shadow.py     # ⇒ "no stale shadow trades — nothing to do"
# close_stale_shadow.py:61 — WHERE state NOT IN %s AND mode='shadow' AND created_at < %s
```

**הכלל המוכלל:** בטבלת `v9_trades` **אף עמודת-יציאה אינה מדד-מצב.** המצב הוא `state`,
והפוסק הוא הסקריפט. עמודה ריקה מעידה על מה שלא נרשם — לא על מה שפתוח.


### מלכודת 15 · `shadow_active_count` בפיד-הגייטוויי **אינו** מונה עסקאות-צל פתוחות (16.09)

בניטור-RTH של 22:06 החזיר `GET /api/v9/gateway/status` את `"shadow_active_count": 13`
בזמן שה-DB הראה **2** עסקאות-צל לא-סגורות. הפער נראה בדיוק כמו בק-לוג-הצל שהרים
את הבקאנד ל-80% CPU באותו בוקר — ‏"11 תקועות" הוא בדיוק סוג-הממצא שנשלח לטלפון.

**זה היה שקר-מדידה. השדה מודד דבר אחר לגמרי:**

```bash
grep -rn "shadow_active_count" backend/ --include=*.py
# trading_gateway.py:5282   "shadow_active_count": len(self.shadow_trades),
grep -n "shadow_trades" backend/v9/gateway/trading_gateway.py
# 433   self.shadow_trades: List[Dict] = []
# 886   # Do NOT append to shadow_trades (§3.4 — no feedback)   ← נתיב שמדלג בכוונה
# 4756  self.shadow_trades.append(shadow_trade)
# 4757  if len(self.shadow_trades) > 500:
# 4758  self.shadow_trades = self.shadow_trades[-300:]          ← גיזום
```

‏`shadow_trades` הוא **חוצץ-טבעת בזיכרון, append-only, נגזם ב-500→300, ולפחות נתיב
אחד מדלג עליו בכוונה.** הוא סופר תת-קבוצה של צל-שנרשמו-מאז-הריסטארט — לא פתוחות,
ולא "מאז תחילת-היום" (ריסטארט מאפס אותו). הפער מול ה-DB הוא **תקין ולא דריפט**.

**המדידה הקבילה — `state`, כמו במלכודת-14:**

```bash
psql … -c "select mode, state, count(*) from v9_trades
           where state not in ('CLOSED','CANCELLED') group by 1,2;"
python3 scripts/close_stale_shadow.py    # dry-run — הוא הפוסק
```

**הכלל הרחב:** מונה שנקרא `*_active_*` בפיד-תצוגה אינו ראיה עד שנקרא הקוד שמאחוריו.
‏`gateway/status` הוא שכבת-תצוגה; ה-DB הוא מקור-האמת (‏`docs/SOURCE_OF_TRUTH.md`).
**הצעה (לא בוצעה — RTH):** לשנות שם ל-`shadow_buffer_len` כדי שהשם יגיד מה הוא מודד.

---

### מלכודת 16 · פוזיציה ≠ TM היא **פסיקה**, לא אזעקה — ו-`TASK_LOG` הוא שמכריע (17.09)

`position_qty` בסיירה שאינו תואם את ה-TM נראה כמו הממצא הגדול של הריצה: הבקאנד
צועק `T-43 contract mismatch DETECTED — BLOCKING new entries`, ה-Reconciler מוסיף
`SYS-3 DIVERGENCE … Records ≠ reality!`, והמרג'ין נבלע. **הכל נכון — והמסקנה
"חריגה שדורשת החלטה" עדיין שגויה.**

**פסיקת-מייקל [[T-402]] (17.09 17:35), עומדת:** *כל פוזיציה שנפתחה לא על-ידי המערכת
היא של מייקל.* הצעד-הבא שם: **אין FLATTEN, אין דיווח-חריגה על פוזיציה זרה** —
ומייקל **כבר יודע** שפוזיציה ידנית פתוחה חוסמת את כניסות-המערכת דרך T-43 ותופסת
את המרג'ין. ⇒ דיווח כזה אינו מקרה (ג): הוא מבקש ממייקל להחליט דבר שכבר החליט.

**הטעות בפועל (cowork-dev, 17.09 17:41):** ריצת-ניטור מדדה נכון (SHORT 2 @7701.75,
סטופ 11284, T-43 נעול מ-17:27:42, `avail` 87.98), הוכיחה בעלות נכון לפי `order_id`
— ואז שלחה מקרה (ג) לטלפון שנחתם בשאלה *"היא שלך?"*. הפסיקה נכנסה לעץ ב-`6983723d`
בשעה **17:32**; ה-`git pull` של אותה ריצה היה **17:36:52**. ⇒ הפסיקה הייתה על הדיסק
ארבע דקות לפני תחילת העבודה. מה שלא נעשה: **`docs/plans/TASK_LOG.md` לא נקרא.**

**הכלל, ולכן הסדר:** `LIVE_CHANNEL` מספר מה *קרה*; `TASK_LOG` מספר מה כבר *נפסק*.
ריצה שקוראת רק את הראשון תמציא מחדש שאלות שנענו. ⇒ **`TASK_LOG` נקרא לפני כל
מסקנה מבצעית, לא רק בתחילת הסשן** (זו כבר חובה ב-`CLAUDE.md`).

```bash
# לפני שמכריזים "חריגה" על כל פער פוזיציה⇄TM:
grep -nE "T-402|פוזיציה שנפתחה לא על-ידי המערכת" docs/plans/TASK_LOG.md
git -C . log -1 --format="%h %ad" --date=format:"%m-%d %H:%M" -- docs/plans/TASK_LOG.md
# ואז, רק אם אין פסיקה מכסה — לבדוק בעלות לפי order_id, לא לפי הפרש-כמות:
grep -c "COMMAND QUEUED" /tmp/backend.err.log          # כמה פקודות המערכת הוציאה היום
strings -a ~/SierraChart/TradeActivityLogs/TradeActivityLog_$(date +%F)_UTC.*.data \
  | grep -c "Auto-trade"                                # חתימת-הסטאדי; ידני ⇒ אפס
```

**והכלל הרחב, שהוא העיקר:** פסיקה עומדת גוברת על מדידה טרייה. מדידה נכונה שמובילה
לשאלה שכבר נפסקה אינה "זהירות" — היא הפרה, באותה מחלקה כמו הדלקת דגל שכובה בכוונה
(‏`CLAUDE.md` § *Rulings are one-time and standing*: *"'האם עדיין רוצה X?' היא
הפרת-פרוטוקול"*). **ל-Render אין endpoint מחיקה, והודעת-תיקון היא בעצמה הפרה של
כלל-הטלפון** ⇒ למחיר אין החזר: התיקון נכתב ל-`LIVE_CHANNEL`, והטלפון נשאר שקט.


---

### מלכודת 17 · `ORDER BY entry_ts DESC LIMIT 1` מחזיר ב-Postgres שורה **בלי זמן** (20.09)

השאלה "מה העסקה האחרונה?" נשאלת בכל סיכום-יומי (חובה-2) ובכל ניטור-RTH (חובה-3).
הניסוח האינטואיטיבי **עונה תשובה שגויה, בשקט, ובדיוק על השדה שאמור להכריע**:

```sql
-- ❌ הורץ 20.09 22:39 (Rule 5, פלט גולמי):
select id, mode, entry_ts, state from v9_trades order by entry_ts desc limit 3;
  398 | live |          | CANCELLED      ← entry_ts NULL
-- ✅ אותה שאילתה, NULLS LAST:
select id, mode, entry_ts, state from v9_trades order by entry_ts desc nulls last limit 3;
 2005 | shadow | 2026-09-18 22:55:10.356846+03 | CLOSED
 2004 | shadow | 2026-09-18 22:45:04.222773+03 | CLOSED
-- כמה שורות חשופות:
select count(*) null_entry_ts, count(*) filter (where state='CANCELLED') cancelled
  from v9_trades where entry_ts is null;   ⇒  42 | 34
```

**השורש:** Postgres ממיין `NULL` כ**גדול מכל ערך**, כלומר ב-`DESC` הוא **ראשון**.
SQLite ו-MySQL עושות את ההפך (NULL = הקטן ⇒ אחרון ב-`DESC`). הריפו **היגר מ-SQLite
ל-Postgres** (`CLAUDE.md` § *DB — local Postgres*) ⇒ כל שאילתת-"אחרון" שנכתבה או
הועתקה מתקופת-SQLite **התהפכה במשמעותה בלי שורת-שגיאה אחת**.

**מה הדוח היה אומר:** *"העסקה האחרונה — לייב, CANCELLED"* — נשמע כמו כישלון-פקודה
טרי שדורש בדיקה. בפועל `#398` היא שורת-ארכיון מ-07-27 בלי זמן-כניסה כלל, והעסקה
האחרונה באמת היא `#2005` shadow מ-18.09 שנסגרה כרגיל. ⇒ **חקירה מומצאת על סמך
מיון, ואזעקה אפשרית על "לייב שבוטל" שלא קרה.**

**הכלל:** כל מיון לפי עמודת-זמן ב-`v9_trades` נושא `NULLS LAST` **או** מסנן
`WHERE entry_ts IS NOT NULL`. אין יוצא-מן-הכלל — `entry_ts NULL` הוא מצב תקף
(פקודה שלא מולאה), לא זבל, ולכן הוא לא ייעלם.

**משפחה אחת עם מלכודת 14:** שתיהן קוראות ל-`NULL` בעמודת-זמן מידע שאין בו —
14 קראה לו "עסקה פתוחה", 17 קוראת לו "העסקה האחרונה". **בשתיהן הפוסק הוא `state`.**

### מלכודת 18 · `ruled_contracts()` בלי `.env` מחזיר `None` — ו-`None` נקרא כ"אין פסיקה" (23.09)

הפקודה שמצוטטת בכל מקום כמקור-האמת לגודל-העסקה **אינה עומדת בפני עצמה**:

```bash
$ python3 -c 'from backend.v9.services.contract_size import ruled_contracts; print(ruled_contracts())'
None                       # ← לא הפסיקה. ולא שגיאה.
$ set -a && . ./.env && set +a && python3 -c '…אותה פקודה בדיוק…'
1                          # ← הפסיקה
```

**השורש:** `ruled_contracts()` נשענת על `_on(name)` שקוראת `os.environ` בלבד
(`backend/v9/services/contract_size.py`). הבאקנד טוען `.env` בעלייה, אבל
`python3 -c` יבש **לא** — ולכן כל דגלי-`FIXED_CONTRACTS_*` נראים כבויים.

**ולמה זו מלכודת ולא אי-נוחות:** הדוקסטרינג של הפונקציה אומר מפורשות
*"None means 'no fixed-size ruling is active' — the caller keeps whatever the
risk ladder produced. It does NOT mean zero."* ⇒ `None` הוא **ערך תקף בעל
משמעות מסחרית** (סולם-סיכון חופשי), לא סימן-שגיאה. סוכן שמריץ את הפקודה
היבשה ומדווח "אין פסיקת-גודל" מדווח **היפוכה של האמת**, בלי שורת-שגיאה אחת
שתעצור אותו. זו אותה משפחה כמו מלכודות 14 ו-17: קריאת משמעות ל-`NULL`/`None`
שאין בו.

**המדידה הקבילה — שלוש, לא אחת:**

```bash
grep -E '^FIXED_CONTRACTS_' .env                       # מי דלוק בפועל
grep -n 'FIXED_CONTRACTS_' config/RULED_FLAGS.yaml     # הפסיקה + התאריך + הציטוט
set -a && . ./.env && set +a && python3 -c 'from backend.v9.services.contract_size import ruled_contracts; print(ruled_contracts())'
```

**⚠️ והחצי השני, שהוא החשוב:** את הגודל קוראים מהשלושה האלה — **לעולם לא ממספר
שכתוב בטקסט-משימה, בסקילל, או בזיכרון.** ב-23.09 טקסט-המשימה של cowork אמר
`"מ-16.09: 2, FIXED_CONTRACTS_2=1"`, בעוד המדידה נתנה `FIXED_CONTRACTS_1=1`,
‏`FIXED_CONTRACTS_2=0`, ו-`RULED_FLAGS.yaml:45` ⇒ פסיקת-מייקל **18.09 12:05**
*"היום לעבוד על חוזה 1"* (המאוחרת גוברת; `FIXED_CONTRACTS_2 expected:"0"`
בשורה 49). המספר בטקסט היה **פסיקה שנדרסה**, וההוראה עצמה מזהירה "אל תניח 5
ואל תניח 3" — אותה מחלקה בדיוק. ⇒ גם טקסט-ההוראה הוא מקור-מיושן-אפשרי, ולכן
`ruled_contracts()` **הוא** הפוסק, ובלבד ש-`.env` נטען.

---

### מלכודת 19 · `psql` בסשן-ירושלים מנפח גיל ב-`+180` דק' על עמודת-`timestamp` נאיבית (23.09)

**הגילוי:** פריט-שווא אחד ([[T-452]]) ושתי חזרות **באותו יום**. הכי קצר שאפשר:

```bash
$ psql $DB -At -c "SELECT round(extract(epoch from (now()-max(ts)))/60.0,2) FROM v9_day_type_state;"
189.10                      # ← "הטבלה מתה 3 שעות". ולא שגיאה.
$ PGTZ=UTC psql $DB -At -c "…אותה שאילתה בדיוק…"
9.10                        # ← האמת. הכותב חי.
```

**השורש, מהסכימה:** `v9_day_type_state.ts` הוא `timestamp **WITHOUT** time zone`
**שמאחסן UTC** — בעוד `v9_bars_5min_woodies.ts` הוא `timestamp **WITH** time zone`.
`now()` הוא `timestamptz`; בחיסור `now() - <naive>` פוסטגרס ממיר את ה-`timestamptz`
לפי ה-`TimeZone` של הסשן. `SHOW TimeZone ⇒ Asia/Jerusalem` (ברירת-המחדל של השרת
המקומי) ⇒ **`+180` דק' נוספות יש-מאין**, בלי אזהרה ובלי שורת-שגיאה.

**ולמה זו מלכודת ולא אי-נוחות:** `+180` דק' חוצה **כל** סף-טריות שיש במערכת
(‏`10` דק' של `daytype_watchdog`, `10` דק' של ניטור-הבר), ולכן היא לא מייצרת
"מספר מוזר" אלא **תקלה משכנעת לגמרי**: טבלה חיה שנכתבה לפני 9 דקות נקראת
כ"עצרה לפני 3 שעות", והסיפור שנבנה סביבה (שומר-שהשתתק · `degraded:false` שקרי ·
"הריסטארט שבר את הכותב") מתיישב מצוין עם הראיה-הפנטום. **הייצור מעולם לא טעה** —
`daytype_watchdog.py:199-202` עושה `last_ts.replace(tzinfo=timezone.utc)` לפני
החישוב; מי שנופל הוא **אגף-המדידה בלבד**, כלומר הסוכן עם ה-`psql` הידני.

**ההגנה — שורה אחת, לפני כל `psql` שמחשב גיל:**

```bash
PGTZ=UTC psql $DB …                        # הדרך הקצרה
SELECT now() - (ts AT TIME ZONE 'UTC') …   # או המרה מפורשת בשאילתה
```

**⚠️ בדיקת-שפיות בת-שנייה:** גיל שהוא **בדיוק** `~180` דק' יותר ממה שסביר —
או כל גיל `>180` על זרם שאמור להיות דקות — הוא **חשוד-TZ עד שהוכח אחרת**.
להריץ את אותה שאילתה שוב עם `PGTZ=UTC` **לפני** שנפתח פריט. ב-23.09 זה תפס
`187.4` ← `2.53` בריצת-`17:34`, ושוב `189.10` ← `9.10` בריצת-`18:37` — אותה
טבלה, אותה מלכודת, שתי ריצות, חמש שעות הפרש. ⇒ **הסף הוא לא "האם המספר גדול",
אלא "האם מדדתי אותו ב-UTC".**

**קרובי-משפחה בקובץ:** 3.3 (‏`CURRENT_DATE`/‏`date +%F` שקריים אחרי חצות) —
אותה משפחה בדיוק: **זמן שנקרא בלי TZ מפורש, ששותק במקום לשגות.**


### מלכודת 20 · בדיקת-נוכחות על נתיב שלא אומת מול פלט-הכלי היא **זיכרון, לא מדידה** (25.09)

**הגילוי ([[T-473]]):** פריט שלם ([[T-471]]) נפתח, הועבר לבעלים פעמיים בלילה ונשא
שלוש שורות `MISSING` — על תוצרים ש**נכתבו בהצלחה**. הכי קצר שאפשר:

```bash
$ ls data/review.json data/tree_board*
ls: data/review.json: No such file or directory          # ← "העמודים לא רצו"
$ ls -la render_mobile_relay/static/docs/data/review.json
-rw-r--r--  1 michael  staff  160783 Sep 25 10:05 review.json   # ← רצו. לפני דקותיים.
```

**השורש:** אף כלי מעולם לא כתב ל-`data/`. ארבעת הכלים מצביעים על אותה תיקייה אחת:

```bash
$ grep -nE "OUT *=|--out" scripts/{day_review,gen_tree_board,progress_study,review_report}.py
day_review.py:42      --out default=…/render_mobile_relay/static/docs/data
gen_tree_board.py:25  OUT = …/render_mobile_relay/static/docs/data
progress_study.py:32  --out default=…/render_mobile_relay/static/docs/data/progress.json
review_report.py:17   OUT = …/render_mobile_relay/static/docs
```

**ולמה זו מלכודת ולא שגיאת-הקלדה:** `ls` על נתיב לא-קיים **אינו שוגה** — הוא מחזיר
בדיוק את אותה תשובה שהיה מחזיר אילו הכלי באמת לא רץ. הבדיקה **אינה מבחינה בין
"לא רץ" ל"רץ וכתב במקום אחר"**, ולכן היא מייצרת לא "מספר מוזר" אלא **פריט משכנע
לגמרי**: הסיפור שנבנה סביבה ("ההרנס תפס את המכונה" · "התנגשות-כתיבה" · "הבעלים לא
סיים") מתיישב מצוין עם הראיה-הפנטום, והתוצר האמיתי יושב על הדיסק כל אותו זמן.
**הייצור מעולם לא טעה** — `gen_phone_pages.py` קורא דרך אותו `OUT` ומצא את הקבצים;
מי שנפל הוא **אגף-הדיווח בלבד**, כלומר הסוכן עם ה-`ls` הידני.

**ההגנה — לקרוא את הנתיב מהכלי, לא מהזיכרון:**

```bash
# ❌ אסור כראיה — נתיב שנכתב מהזיכרון, ושותק במקום לשגות:
ls data/review.json

# ✅ הפוסק: שורת-הפלט של הכלי מדפיסה את הנתיב שהוא באמת כתב (תוקן 25.09)
python3 scripts/gen_tree_board.py | tail -1
#   → … → render_mobile_relay/static/docs/data/tree_board.html (1300x1956)
# ✅ או: לשאול את הקוד, לא את הזיכרון
grep -nE "OUT *=|--out" scripts/<tool>.py
```

**⚠️ בדיקת-שפיות בת-שנייה:** `MISSING` על תוצר שדווח כ"רץ" בשורת-לוג קודמת הוא
**חשוד-נתיב עד שהוכח אחרת** — לפני שנפתח פריט, להריץ `find . -name "<basename>"
-newermt today` פעם אחת. ב-25.09 זה היה הופך פריט בן יומיים לשורה אחת.

**קרובי-משפחה בקובץ:** מלכודת 19 ו-3.3 (זמן שנקרא בלי TZ מפורש) — אותה משפחה
בדיוק, **Rule 2**: *ערך שנלקח מהזיכרון במקום מהמקור, ששותק במקום לשגות.* ההבדל
היחיד הוא הציר — שם זמן, כאן נתיב.

---

### מלכודת 21 · לפיד-הליגר **שתי צורות-שורה**, ומי שסופר לפי `ts` מוחק את חצי-המודעות (27.09)

`~/SierraChart_Data/v9_export/gateway_decisions.jsonl` אינו טבלה אחידה.
`GATE_DECISION` ו-`ROUTED` נושאים `ts`; **`DETECTED` ו-`EMIT_DECISION` נושאים
`ts: null`** ומתארכים ב-`observed_at` / `signal_bar_ts` (‏`candidate_ledger.py`
מוסיף אותם כ-events נפרדים, ו-`UI_EVENT_TYPES` בכוונה לא מכניס אותם לפאנל-הירי).

**הטעות בפועל (cowork-dev, 27.09 ריצה 31):** ספירה לפי `ts` בלבד החזירה
`total_lines=225 · rows per ET day {2026-09-25: 106}` — כלומר **119 מ-225 שורות
(53%) נשרו בשקט**, ובדיוק החצי שהוא **המונה של המודעות**:

```raw
$ python3 … when(r) = ts בלבד   ⇒ 106  (GATE_DECISION 97 · ROUTED 9)
$ python3 … rows_without_iso_ts ⇒ 119  {DETECTED: 60, EMIT_DECISION: 59} · ts types {NoneType: 119}
$ python3 … when(r) = ts → observed_at → signal_bar_ts
   ⇒ ts-field used {ts: 106, observed_at: 119} · 2026-09-25 כל 225 השורות
   ⇒ הליגר האמיתי: DETECTED 60 → EMIT_DECISION 59 → GATE_DECISION 97 → ROUTED 9  (ROUTED/DETECTED 15.0%)
```

**הכלל:** לגזור זמן משלושת השדות בסדר `ts → observed_at → signal_bar_ts`, ולהדפיס
**איזה שדה שימש לכל שורה** (‏`ts-field used`) לפני שמדווחים ליגר. ‏`DETECTED=0`
שנמדד לפי `ts` הוא **עיוורון-סכימה, לא יום שקט** — אותה משפחה של 3.2 (פיד חתוך
ל-200) ושל מלכודת 17: מספר ששותק במקום לשגות.

⚠️ **ולא לבלבל עם [[T-495]]** — שם ה-`ts` היה epoch ונדחה ב-`fromisoformat`
(‏`DatetimeFieldOverflow`), כאן השדה **חסר לגמרי מעצם התכנון**. תיקון T-495 אינו
הופך את הספירה-לפי-`ts` לנכונה.

---

### מלכודת 22 · `mtime` אינו מבחן-חיוּת **באף כיוון** — לא טרי⇒חי, ולא ישן⇒מת (27.09)

[[T-430]] קבע צד אחד: **קובץ-יצוא טרי ≠ פיד חי** (ה-DLL כותב גם כשחיבור-הנתונים
של סיירה מת). ב-27.09 נמדד **הצד המראה**, והוא הפריך נוסח שריצה 29 שלי עצמה כתבה
(*"ה-DLL כותב כל 3 שנ' גם בשוק סגור"*):

```raw
$ ls -lt ~/SierraChart_Data/v9_export/   (now 15:06)  ⇒ שישה קבצים קפואים על 14:14 — 52 דק'
$ 5min_continuous.json  גודל על פני 6 שנ' ⇒ 57561 → 57561   (יציב, לא נכתב)
$ cat live_price.json ⇒ bid 0.00 · ask 0.00 · ts=14:14      $ pgrep -fl -i sierra ⇒ 1355/1358/1365 חיים
$ [15:39] [INFO] [tpo_routes] Sierra tpo.json stale age=5077.6s > 30.0s — serving anyway
```

⇒ **באותו חלון הסטאדי לא נקרא כלל.** זה לא "הסטאדי נשבר": בלי טיק נכנס
אי-אפשר להפריד *idle* מ-*stopped*, והטיק הראשון הוא Globex 01:00 IL.

**⚠️ תיקון-נוסח (cowork-dev, ריצה 34, 27.09 17:20) — אי-הקריאה אינה תכונת-השוק-הסגור.**
עד כאן נכתב "בשוק סגור לחלוטין הסטאדי אינו נקרא **כלל**", והכללה הזו **הופרכה באותו יום**:
ב-`17:08`, כשהשוק סגור בדיוק באותה מידה (הטיק הראשון עוד לפני Globex 01:00), **שבעת
קבצי-הייצוא נשאו `mtime 17:08`** ונכתבו כל 3 שנ'. צד-הדחיפה **עצר מעצמו ב-`14:14:44`
וחזר מעצמו ב-`16:39:51`** — **בלי ריסטארט**, בשוק סגור בשני הקצוות:

```raw
$ פער-הענק בזרם-ה-ERROR של היום ⇒ 2:25:07 · 14:14:44 -> 16:39:51   (n=1,482)
$ דליים של 10 דק' ⇒ 14:10→66 · [14:20-16:20 ריק] · 16:30→7 · 16:40→399 · 17:00→401
$ ls -lt v9_export (17:08) ⇒ שבעה קבצים על 17:08     $ live_price ⇒ bid 0.0 · ask 0.0 · last null
$ 5min_continuous ⇒ 57,561B יציב · הבר החדש 09-25 18:45     $ ברים שנקלטו ל-27.09 ⇒ 0
```

⇒ **הכותרת של המלכודת מתחזקת** (אותו שוק-סגור נתן גם "קפוא" וגם "טרי" באותו יום), אבל
`14:14-16:39` הוא **חלון**, לא מצב-השוק. ⇒ אל תסיק "הסטאדי לא אמור להיכתב עכשיו" מהשעה.

**והמדד הטוב יותר, שנמצא אגב-אורחא:** קצב-ה-`TS-OFFSET-GATE` ב-`backend.err.log` הוא
**עד-היסטורי מתוארך** לשאלה "האם הסטאדי דוחף", בעוד `mtime` עונה רק על "עכשיו". שני
הכלים הסכימו כאן על אותן שתי חותמות בדיוק — ולכן כשצריך לדעת **מתי** התחיל או נפסק
הדחיפה, הלוג הוא המקור, לא `ls`.

**לכן שתי מסקנות שהן שקר, ושתיהן נראות סבירות:** "קבצים טריים ⇒ הפיד חי"
(מייצר GO מדומה) · "קבצים קפואים ⇒ ה-DLL נפל" (מייצר NO-GO מדומה ושולח את מייקל
לתקן תשתית בריאה — משפחת 3.4).

**המבחן היחיד הקביל, וזה שלב D של `fire_drill` מ-20.09:** מול ה-DB, לא מול ה-mtime.

```bash
$PSQL $DB -At -c "select max(ts), now()-max(ts) from v9_bars_5min_woodies;"
# יום-מסחר: בר בן <10 דק' ⇒ חי · שוק סגור: max(ts)=סגירת-שישי + rows_36h=0 ⇒ הסינגטורה הנכונה
```

‏27.09 15:37 החזיר `2026-09-25 23:30+03 · age 1 day 16:07 · rows_36h 0` ⇒ **סגור,
כמצופה**. קרוב-משפחה: מלכודת 13 (‏`ps` שמראה תהליך אינו מוכיח שהפיד זורם).

**↻ חידוד 04.10 (cowork-dev, ריצה 179) — `rows_36h` **בין** 0 לערך-מסחר הוא שעון-עצר,
לא מד-בריאות.** השורה למעלה מכסה את שני הקצוות (`<10` דק' ⇒ חי · `0` ⇒ סגור-כמצופה),
אבל **הערך האמצעי נקרא כדריפט** — ושתי ריצות באותו בוקר, על אותו שוק סגור ועל אותם
נתונים בדיוק, מחזירות מספרים יורדים:

```raw
$ ריצה 178, 11:06 IDT  ⇒ rows_36h = 10
$ ריצה 179, 11:37 IDT  ⇒ rows_36h = 4          ← "הפיד נשחק ב-60% בחצי שעה"? לא.
$ PGTZ=UTC psql ⇒ now_utc 08:37:37 · window_start 2026-10-02 20:37:37
                  oldest_in_window 20:40 · newest 20:55            ← רק הקצה השמאלי זז
$ אותו קטע-שישי בלי חלון ⇒ 13 שורות · min 19:55 · max 20:55       ← הנתונים דוממים
$ max(ts)+36h ⇒ 2026-10-04 11:55:00 IDT                            ← השעה שבה יגיע ל-0
```

**השורש אריתמטי, כמו במלכודת 27:** `ts > now() - interval '36 hours'` הוא חלון נע על
**אוכלוסייה קפואה**. בשוק סגור אף שורה לא נוספת, ולכן הספירה יכולה רק **לדעוך** — בקצב
של בר-5-דקות כל 5 דקות — עד שהיא נוגעת ב-0 בדיוק ב-`max(ts)+36h`. ⇒ **ההפרש בין שתי
ריצות אינו מודד כלום** מלבד את הזמן שעבר ביניהן.

**ולמה זה יקר:** זה הכיוון המסוכן (כמו מלכודות 24 · 27) — **אזעקה על מערכת בריאה.**
ריצה שמשווה `10 → 4` מדווחת "פיד מתדרדר", ומי שמגיע בחלון `11:50-11:55` רואה `1` ואז
`0` ועלול לקרוא ל-`0` "הפיד מת עכשיו" — כשזו בדיוק **הסינגטורה הנכונה** של השורה
שמעל. **הפוסק אינו הספירה אלא `max(ts)`:** חותמת-סגירת-שישי שאינה זזה היא שוק-סגור
תקין, בכל ערך-`rows_36h` שבדרך.

```bash
# ❌ אסור כמדד-בריאות, ואסור להשוות בין ריצות:
#    rows_36h לבדו  ·  "rows_36h ירד מאז הריצה הקודמת"
# ✅ הפוסק — max(ts) מול שעון-השוק, ו-rows_36h רק כהקשר:
PGTZ=UTC $PSQL $DB -At -c "select max(ts), now()-max(ts) from v9_bars_5min_woodies;"
# שוק סגור ⇒ max(ts) = סגירת-שישי ואינו זז  ·  יום-מסחר ⇒ בר בן <10 דק'
```

---

### מלכודת 23 · אין בידך מד-CPU חי — `ps` וגם `machine_health` עונים על שאלה אחרת (27.09)

**הגילוי, והוא מביך:** ריצה 34 כתבה סעיף שכותרתו **"תיקון-עצמי, כלל 5"**, ובתוכו
החליפה מכשיר שגוי במכשיר שגוי אחר — ונתנה למסקנה את הביטחון של ממצא-מאומת, **כי היא
הייתה מסומנת כתיקון**. הכי קצר שאפשר:

```raw
$ ps -o %cpu -p 11167   ⇒ 62.8%     ← נדחה כ"ממוצע-לכל-החיים". ❌ הוא לא.
$ machine_health.py     ⇒ 5.0%      ← אומץ כ"האמת החיה".      ❌ הוא ממוצע-לכל-החיים.
$ Δ(cputime)/Δ(wall) על 30 שנ':  9345.97 -> 9353.64 = 7.67s/30.0s
   LIVE CPU     = 25.6%     ← האמת
   LIFETIME avg = 5.56%     ← בדיוק מה ש-machine_health הדפיס
```

**השורש, ושני המכשירים הפוכים ממה שנדמה:**
- **‏`ps -o %cpu` ב-macOS הוא ממוצע-דועך קצר-טווח**, לא ממוצע-לכל-החיים. הראיה שאין
  עליה עוררין: הוא נע `12.3 → 100.5` **בתוך אותן 30 שניות** (ו-`51.2` · `14.9` בדגימות
  אחרות). ממוצע-לכל-החיים על תהליך בן יומיים **אינו יכול** לזוז כך — הוא רועש, לא שקרי.
- **‏`machine_health.py` מדפיס `cputime/elapsed`** — ממוצע אמיתי על כל חיי-התהליך. על
  תהליך שרץ יומיים, **כל** פרץ נבלע: ‏26% חי נראה שם `5%`. מצוין למגמה, **חסר-ערך
  ל"מה קורה עכשיו"**, וזה בדיוק השימוש שנעשה בו.

**המדידה הקבילה — אחת, והיא לא תלויה בשום החלקה:**

```bash
# ✅ הפוסק: הפרש זמן-מעבד חלקי זמן-קיר. אין כאן ממוצע ואין דעיכה.
python3 - <<'PY'
import subprocess,time
g=lambda: float(subprocess.run(['ps','-o','time=','-p','11167'],capture_output=True,text=True)
                .stdout.strip().replace('-',':').split(':')[-2])*60 + \
          float(subprocess.run(['ps','-o','time=','-p','11167'],capture_output=True,text=True)
                .stdout.strip().split(':')[-1])
c1=g(); t1=time.time(); time.sleep(30); c2=g()
print(f"LIVE CPU = {(c2-c1)/(time.time()-t1)*100:.1f}%")
PY
# ✅ או, אם צריך רק סדר-גודל: top -l 7 -s 5 ונקרא את הפיזור, לא דגימה בודדת
```

**⚠️ והחצי החשוב — כלל 5 חל על תיקונים בדיוק כמו על טענות.** שורה שנפתחת ב-"תיקון-עצמי"
או "כלל 5" **אינה קונה חסינות**: ריצה 34 עברה מ-`62.8%` ל-`5.0%` בלי למדוד את אף אחד
מהם במכשיר שעונה על השאלה, ופרסמה "אפס סיכון-משאבים" על בקאנד ששרף `~26%` ביום-ראשון
עם שוק סגור ואפס מסחר. **הכיוון של הטעות אינו משנה** — דיווח-חסר (`5%` על `26%`) הוא
אותה מחלקה כמו דיווח-יתר (`62.8%` שהיה שולח מקרה (ג) מיותר, משפחת 3.4).

**קרובי-משפחה בקובץ:** מלכודות 19 (‏TZ), 20 (נתיב מהזיכרון) ו-17 (‏`NULLS LAST`) — כולן
**Rule 2**: *ערך שנלקח ממכשיר שעונה על שאלה אחרת, ששותק במקום לשגות.* ההבדל היחיד הוא
הציר — שם זמן, שם נתיב, כאן חלון-הדגימה.

### מלכודת 24 · `"API push FAILED"` בלי המסנן `https` — 39 תוצאות שאינן דריפט (29.09)

**הכלל ב-CLAUDE.md מורה לעצור את הברידג' ולשאול את מייקל** על השורה
`[<stream>] API push FAILED to https://...` — כי היא סימן לדריפט-תצורה (פוש לענן).
**אבל grep על המחרוזת בלי `https` מחזיר 39 תוצאות בלוג הנוכחי**, וכולן תקינות:

```raw
$ grep -c 'API push FAILED' /tmp/bridge.log                    ⇒ 39      ← נראה כמו דריפט
$ grep -o 'API push FAILED to [^ ]*' /tmp/bridge.log | grep -v localhost:8000 | wc -l
                                                               ⇒ 0       ← אף יעד מרוחק, אי-פעם
$ grep 'API push FAILED' /tmp/bridge.log | awk '{print $1,substr($2,1,5)}' | sort | uniq -c
     24  2026-09-28 15:40        ← הברידג' עלה 15:40:21, הבקאנד נקשר 15:40:25
     15  2026-09-28 15:58        ← ריסטארט-בקאנד שני, המאזין 16241 נקשר 15:58:34
$ ... אחרי 16:00 ב-28.09, ובכל 29.09                           ⇒ 0
$ ps eww <bridge-pid> | tr ' ' '\n' | grep '^CLOUD_URL='       ⇒ http://localhost:8000
```

**השורש:** השגיאה היא `<urlopen error [Errno 61] Connection refused>` אל `localhost:8000` —
**סדר-עלייה**, לא יעד שגוי. הברידג' עולה לפני שהבקאנד נקשר לפורט, דוחף כמה מחזורים
לדלת סגורה, ומפסיק ברגע שהמאזין קם. שני האשכולות הם בדיוק שני רגעי-הקשירה.

**המדידה הקבילה — המסנן `https` הוא חלק מהמבחן, לא קישוט:**

```bash
# ✅ הפוסק לכלל Bridge Local-Only:
grep -c 'API push FAILED to https' /tmp/bridge.log   # ⇒ 0 = נקי
grep -o 'API push FAILED to [^ ]*' /tmp/bridge.log | grep -v localhost:8000 | wc -l   # ⇒ 0
# ❌ grep -c 'API push FAILED'  — סופר גם Connection refused מקומי ⇒ אזעקת-שווא
```

**למה זה מסוכן בכיוון ההפוך משאר המלכודות:** רובן גורמות לדווח "תקין" על שבור. **זו
גורמת לעצור מערכת בריאה** — הכלל מורה *לעצור את הברידג'* על הממצא, כלומר ריצת-ניטור
שתספור 39 תקטע את הפיד באמצע יום-מסחר ותשלח מקרה (ג) מיותר. **קרוב-משפחה:** מלכודת 23
(דיווח-יתר ודיווח-חסר הם אותה מחלקה) ו-Rule 2 (מכשיר שעונה על שאלה אחרת).


---

### מלכודת 25 · `grep "[EntryGuard]"` על הלוג הוא **שלילי-שקרי** — התג הזה לא קיים (30.09)

**מה קרה.** ריצה 104 (30.09) בדקה אם EntryGuard חסם ירי, והריצה את הבדיקה הטבעית:

```raw
grep -c "2026-09-30.*\[EntryGuard\]" /tmp/backend.err.log  ⇒  0
```

ונרשם `EntryGuard ⇒ 0`. **באותו יום עצמו הגארד ירה שלוש פעמים** — ריצה 107 מצאה אותן
ב-`16:50:01`, `16:55:03`, `17:00:01`, כל אחת מהן `[CRITICAL]`:

```raw
grep -c "pre_send_entry_guard\|UNMANAGED POSITION" /tmp/backend.err.log  ⇒  3

התג שקיים בפועל:
[CRITICAL] [backend.v9.gateway.trading_gateway] [Gateway] LIVE fire BLOCKED pre-send:
  UNMANAGED POSITION +1 on the account (live slot was free → not TM-managed).
  No manual trading (ruling 2026-08-21) → … Blocked pre-send
  — LONG DALTON_EDGE_LONG sys=2 — no trade row, no slot, no Sierra command
```

**המדידה הקבילה — הפיד, לא ה-grep.** הרשומה הקנונית של חסימת-שליחה היא שדה, לא מחרוזת:

```bash
curl -s "http://localhost:8000/api/v9/gateway/decisions?limit=2000" | python3 -c "
import sys,json
rows=json.load(sys.stdin)
for r in rows:
    if r.get('live_blocked_by'):
        print(r['t_il'], r['pattern'], r['direction'], r['live_blocked_by'], r['live_block_reason'])"
```

**ולמה זו מלכודת ולא שגיאת-הקלדה:** `grep` על תג שאינו קיים **אינו שוגה** — הוא מחזיר
`0`, שנקרא בדיוק כמו "נבדק, ולא היה". שם-הרכיב בקוד (`entry_guard`) ושם-התג בלוג
(`[Gateway]`) **אינם אותו דבר**, ולכן חיפוש לפי שם-הרכיב נראה סביר ומחזיר שקר שקט.
זו אותה משפחה כמו מלכודות 14 · 17 · 18: **קריאת משמעות ל-`0`/`NULL`/`None`** שמשמעותו
"לא נמצא בשיטה הזו", לא "לא קרה".

**ולמה זה יקר במיוחד כאן:** `live_blocked_by` הוא ההבדל בין *"העץ לא אישר"* לבין
*"העץ אישר והשליחה נחסמה"* — שתי מסקנות הפוכות על אותו יום. ב-30.09 הפער הזה בדיוק
הוא שהחליף את האבחנה: החוסם לא היה **המרג'ין** (כפי שנשלח לטלפון ב-12:45) אלא
**הפוזיציה הידנית** דרך פסיקת `2026-08-21`, והגארד עוצר `pre-send` — **לפני** בדיקת
מרג'ין ולפני כל פקודה לסיירה (`no trade row, no slot, no Sierra command`).

**הכלל:** EntryGuard/חסימת-שליחה נבדקים **רק** דרך `decisions.live_blocked_by`.
grep על הלוג — רק עם `pre_send_entry_guard` או `LIVE fire BLOCKED pre-send`,
**לעולם לא עם `[EntryGuard]`**.

---

### מלכודת 26 · "ליגר-כותב" נבדק בתיקיית-הנדאוף שנוצרת ב-23:05 — ולכן נכשל בוודאות בכל ריצת-יום (02.10)

**מה שנראה כמו ליגר מת בשער-15:30 של 02.10:**

```raw
$ python3 -c "awareness_score.find_ledger(date(2026,10,2))"  ⇒  (None, None)
$ stat ~/SierraChart_Data/v9_export/gateway_decisions.jsonl
  mtime Oct  1 22:55:11 2026 · size 196113 · today lines 0
```

שני הקצוות אומרים "אפס היום". הקריאה המתבקשת — *הליגר הפסיק לכתוב* — **שגויה**,
ושתי מדידות מפרקות אותה:

**(1) תיקיית-ההנדאוף היא ייצוא-לילה, לא מסלול-כתיבה חי.** ‏`find_ledger()` מחזיר
`data_handoff/מק-1/<תאריך>/gateway_decisions.jsonl`, וה-`mtime` של **כל** התיקיות
שם הוא `23:05`:

```raw
$ ls -la "data_handoff/מק-1/"
  2026-09-24 ... Sep 24 23:05 · 2026-09-25 ... Sep 25 23:05 · 2026-09-28 ... Sep 28 23:05
  2026-09-29 ... Sep 29 23:05 · 2026-09-30 ... Sep 30 23:05 · 2026-10-01 ... Oct  1 23:05
```

⇒ `find_ledger(today)` מחזיר `None` **בכל ריצה שלפני 23:05**, בלי קשר לבריאות
הליגר. ‏`None` כאן אינו ממצא — הוא תכונת-לוח-זמנים.

**(2) הליגר כותב רק ב-RTH, וההוכחה היא השורה הראשונה של אתמול:**

```raw
$ first/last של 2026-10-01 (226 שורות)
  first 2026-10-01T13:30:07+00:00   ⇐ 16:30 IL = 09:30 ET = פתיחת-RTH בדיוק
  last  2026-10-01T19:55:11+00:00
  GATE_DECISION 83 · EMIT_DECISION 64 · DETECTED 63 · ROUTED 16
```

⇒ ריצת-שער ב-`15:30-16:10 IL` יושבת **לפני** פתיחת-ה-RTH ⇒ `0` שורות היום הוא
המצב **הנכון**, ולא כשל.

**ולמה זו מלכודת ולא אי-נוחות:** זו אותה משפחה של מלכודת 22 (`mtime` אינו מבחן-
חיוּת באף כיוון) ושל מלכודת 20 (בדיקת-נוכחות על נתיב שלא אומת) — שלושתן מחזירות
**שקט במקום שגיאה**. סוכן שמריץ `find_ledger(today)` בשער ומקבל `None` ירשום
"ליגר לא כותב ⇒ NO-GO" או ישלח מקרה (ג) מיותר, ושני הקצוות שלו עקביים עם
ההשערה השגויה. ‏[[T-430]] הוא בדיוק אותו כשל-הבחנה על הפיד: *שתי השערות שמנבאות
את אותה מדידה*, והמדידה שמבחינה היא **צורת** הקיפאון ולא עצם הקיפאון.

**הכלל — "ליגר-כותב" יש לו שתי בדיקות שונות לשתי שעות שונות:**

| מתי | מה נבדק | מה עובר |
|-----|---------|---------|
| שער `15:30-16:10` (לפני RTH) | **אין בדיקה תקפה.** לרשום את ספירת-אתמול + את השעה שבה השורה הראשונה מגיעה | `0` שורות היום = צפוי ⇒ **לא** NO-GO, **לא** מקרה (ג) |
| ריצת-RTH הראשונה אחרי `16:30` | ‏`stat ~/SierraChart_Data/v9_export/gateway_decisions.jsonl` ⇒ ‏`mtime` **מהיום** | mtime מהיום ⇒ כותב · עדיין `Oct N-1` ב-`16:40` ⇒ **חריגה אמיתית** ⇒ מקרה (ג) |

**ולעולם לא** `find_ledger(today)` כמבחן-חיוּת לפני `23:05` — זה הנתיב שנוצר
בייצוא-הלילה, והוא `None` גם כשהליגר כתב 226 שורות באותו יום.

---

### מלכודת 27 · `tail -N | grep -c ERROR` הוא **חלון-שורות, לא חלון-זמן** — ובסוף-שבוע הוא שולף אשכול-שבת כאילו הוא טרי (04.10)

**מה שנראה כמו 121 שגיאות טריות בריצה 178 (ראשון 11:08, שוק סגור):**

```raw
$ tail -3000 /tmp/backend.err.log | grep -cE "ERROR|Traceback"      ⇒ 121
$ grep -cE "^2026-10-04.*\[ERROR\]|^2026-10-04.*Traceback" …        ⇒ 0      ← אפס היום
$ tail -3000 … | grep -E "ERROR|Traceback" | grep -oE "^2026-..-.." | sort | uniq -c
   121 2026-10-03                                                   ← כולן משבת
$ tail -3000 … | grep -E "ERROR|Traceback" | grep -cvE "^2026-"      ⇒ 0      (ולא חוסר-חותמות — §3.9 תקין)
```

**השורש, והוא אריתמטי:** ‏`tail -N` חותך לפי **שורות**, וקצב-הלוג אינו קבוע — הוא
נגזר מהמסחר. ‏02.10 (יום-מסחר) כתב `7,345` שורות `TS-OFFSET-GATE` לבד; ראשון 04.10
כתב **‏1,166 שורות בסך-הכל עד 11:08** (~12-14 שורות/דקה). ⇒ חלון של 3,000 שורות
בסוף-שבוע **מגלגל אחורה אל אתמול ואל שלשום**: האשכול יושב בשורות `67,216–67,252`
מתוך `68,430`, כלומר `~1,180` שורות מהסוף — **בתוך** החלון, ויישאר בו שעות.

**והנתון עצמו אינו תקלה בכלל:** כל 121 הן `[bars/5min] TS-OFFSET-GATE REJECTED batch`
מ-`23:00:24–23:00:52` בשבת — שער-הקליטה **דוחה כראוי** אצווה של ברי-שישי בני 83,000
שנ'. אותה חתימה הופיעה `7,345` פעמים ב-02.10, יום-מסחר רגיל ⇒ **ירי-השער הוא שגרה
מתוארכת, לא אירוע**, והוא בדיוק המכשיר ש§מלכודת 22 ממליצה עליו כעד-היסטורי ל"האם
הסטאדי דוחף" (‏`7,345` ב-02.10 · `121` ב-03.10 · `0` היום = שוק סגור, ה-DLL בטל).

**המדידה הקבילה — לתחום בתאריך, כמו שכל §2ד1 כבר עושה לספירות:**

```bash
# ❌ אסור כשער-בריאות — חלון-שורות, ושותק במקום לשגות:
tail -3000 /tmp/backend.err.log | grep -cE "ERROR|Traceback"

# ✅ הפוסק — תחום ליום, ומפריד חותמת מרמה:
D=$(date +%F)       # ⚠️ אחרי חצות IDT גוזרים את D מהנתונים — §3.3(ב)
grep -cE "^$D.*\[ERROR\]|^$D.*Traceback" /tmp/backend.err.log
grep -E "^$D.*\[ERROR\]" /tmp/backend.err.log | sed -E 's/^[0-9: -]+//' | cut -c1-120 | sort | uniq -c | sort -rn | head
```

**⚠️ והחצי החשוב — הכיוון של הטעות הוא המסוכן.** רוב המלכודות בקובץ גורמות לדווח
"תקין" על שבור; **זו מייצרת אזעקה על מערכת בריאה** — "121 שגיאות" בשער-15:40 הוא
NO-GO מדומה, ובניטור-RTH הוא מקרה (ג) מיותר שמעיר את מייקל על אשכול-שבת שנדחה
כמתוכנן. אותה מחלקה כמו מלכודת 24 (`API push FAILED` בלי `https` ⇒ עצירת ברידג'
בריא) ומלכודת 23 (דיווח-יתר ודיווח-חסר הם אותה מחלקה).

**⚠️ ראיה שהמלכודת אכן מכשילה בפועל:** ריצה 177, **אותה פקודה על אותו קובץ 30 דק'
קודם** (10:35-11:10), פרסמה `⇒ 0` ב-`LIVE_CHANNEL` — בזמן שהאשכול היה `~1,150`
שורות מהסוף, כלומר בתוך החלון. ⇒ שני מספרים סותרים (`0` ו-`121`) מאותו שער על אותה
מציאות, בהפרש חצי שעה, **ושניהם חסרי-משמעות** — כי השער לא שאל "האם היו שגיאות
**היום**". הנכון לשתי הריצות הוא `0`, ומגיעים אליו רק בשאילתה התחומה.

**קרובי-משפחה בקובץ:** §3.3 (זמן שנקרא בלי תחימה מפורשת, ששותק במקום לשגות), §3.2
(פיד חתוך ל-200 שורות), ומלכודות 20 · 23 — כולן **Rule 2**: *ערך שנלקח ממכשיר
שעונה על שאלה אחרת.* ההבדל היחיד הוא הציר — שם נתיב, שם חלון-דגימה, כאן חלון-שורות.

### מלכודת 28 · `origin/main` **אינו** ה-upstream של הריפו — השוואה אליו היא "דריפט 4,241 קומיטים" על ריפו מסונכרן לחלוטין (04.10)

ענף-העבודה כאן הוא `stabilize/mems26-local-truth-2026-05-16`, **לא** `main`.
‏`origin/main` הוא ענף נטוש מ-**02.05.2026** — חמישה חודשים אחורה. מי שמאמת
`pull`/`push` מול `origin/main` (ההרגל מכל ריפו אחר) מקבל פער-ענק מובטח.

**המדידה בפועל (ריצה 180, ראשון 12:06, שוק סגור):**

```raw
$ git pull --ff-only                      ⇒ Already up to date.
$ git rev-parse --short HEAD              ⇒ e3ae983f
$ git rev-parse --short origin/main       ⇒ 9bdcd340          ← נראה כמו דריפט
$ git log -1 --date=format:'%Y-%m-%d' origin/main
    9bdcd340  2026-05-02  michaelbarg  feat(tools): pre-flight checklist script for Phase 3.2
$ git rev-list --left-right --count origin/main...HEAD   ⇒ 572   4241
$ git rev-parse --abbrev-ref HEAD         ⇒ stabilize/mems26-local-truth-2026-05-16
$ git rev-parse --abbrev-ref @{u}         ⇒ origin/stabilize/mems26-local-truth-2026-05-16
$ git rev-parse --short @{u}              ⇒ e3ae983f
$ git rev-list --left-right --count HEAD...@{u}          ⇒ 0   0   ← מסונכרן לחלוטין
$ git branch -r | wc -l                   ⇒ 10   (origin/main אחד מהם, ואינו ה-upstream)
```

**שתי הקריאות על אותה מציאות:** `4241/572` ו-`0/0`. השנייה היא האמת;
הראשונה מודדת מול גווייה.

**⚠️ והכיוון כאן גרוע ממלכודת 27.** שם האזעקה-הכוזבת מייצרת NO-GO מדומה או מקרה-(ג)
מיותר. כאן **התיקון המתבקש לאזעקה הוא ההרסני**: `merge`/`reset`/`push --force` לעבר
עץ מ-02.05 — לפני מיגרציית-Postgres, לפני עץ-ההחלטות `3.2.0`, לפני 274 הדגלים
הפסוקים. כלומר "סגירת דריפט" שמוחקת חמישה חודשי פסיקות-מסחר. ⇒ **אף פעם לא לפעול
על פער-ענק מול `origin/main`; קודם לאמת מול מה בכלל מודדים.**

**והכיוון ההפוך, באותה מידה:** מי שמאמת **הצלחת-push** מול `origin/main` יראה כל
דחיפה כנכשלת, ועלול לדחוף שוב ושוב או לדווח "הקומיט לא עלה" כשהוא עלה.

**המדידה הקבילה — `@{u}`, ולעולם לא שם-ענף קשיח:**

```bash
# ❌ אסור — שם-ענף קשיח שאינו ה-upstream:
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || echo "DRIFT"

# ✅ הפוסק — ה-upstream שהענף מצהיר עליו, ושתי המספרים בשורה אחת:
git -C /Users/michael/Downloads/mems26_web_git status -sb | head -1      # ## <branch>...<upstream> [ahead/behind]
git -C /Users/michael/Downloads/mems26_web_git rev-list --left-right --count HEAD...@{u}   # "0  0" = מסונכרן
```

**קרובי-משפחה בקובץ:** מלכודת 27 (חלון-שורות במקום חלון-זמן) · מלכודת 22 (`mtime`
כמד-חיוּת) · מלכודת 14 ומלכודת 17 (עמודה שעונה על שאלה אחרת, וסדר-NULL ב-Postgres)
— כולן **Rule 2**: *ערך שנלקח ממכשיר שעונה על שאלה אחרת.* הציר כאן הוא **שם-הרפרנס**.

---

### מלכודת 29 · פיד-תקוע: `bridge.err.log` הוא **מאתר-הקומה**, ובלעדיו "התיקון" הוא ריסטארט שאינו נוגע בתקלה (04.10)

**הממצא (ריצה 181, 12:35-12:50 IDT, ראשון — שוק סגור, פוזיציה 0):** `max(ts)` ב-DB
תקוע על **שישי 02.10 23:55 IDT**, כלומר 36.7 שעות. השאלה שקובעת מה עושים אינה "האם
הפיד תקוע" — היא **באיזו מהשלוש הקומות הוא נשבר:** ‏`Sierra/DLL → bridge → backend/DB`.
שלוש הקומות נותנות אותו סימפטום ב-DB ו**שלוש פעולות-תיקון שונות לגמרי**.

**הפוסק — שורת-הדופק של הברידג', ובה הכול:**

```bash
tail -5 /tmp/bridge.err.log
# 2026-10-04 12:38:24 [INFO] [bars_5min] heartbeat — pushes=16842 errors=1 last_push_age=49051s mode=polling
# 2026-10-04 12:38:36 [INFO] [tpo]       heartbeat — pushes=16848 errors=1 last_push_age=49064s mode=polling
```

`last_push_age` הוא `now - last_push_ts` — **שניות מאז הדחיפה המוצלחת האחרונה**
(`bridge/v9_streams/base_stream.py:468`), ולא גיל-הנתון שנדחף. לכן השורה הזאת פוסקת
בבת-אחת: **הברידג' חי** (חותמת מהשנייה הזאת), **מצליח** (`errors=1` מתוך 16,842
דחיפות), **סורק** (`mode=polling`) — ו**לא מצא דבר חדש 13.6 שעות**. ‏49,051s ≡ אותו
פער בכל חמשת הזרמים ⇒ אין כאן זרם-בודד-שנפל; המקור משותף ⇒ **השבר מעל הברידג'**.

**האישוש, שלוש מדידות שכולן מצביעות למעלה:**

```bash
pgrep -lf -i sierrachart | head -2        # ⇒ pid 761/762 חיים — סיירה רצה!
ls -lt ~/SierraChart_Data/v9_export/      # ⇒ sierra_state/live_price/5min_continuous כולם Oct 3 23:00
grep -cE '^2026-10-04.*TS-OFFSET-GATE' /tmp/backend.err.log   # ⇒ 0
```

הקומה שנשברה היא ה-**DLL**: סיירה חיה אבל **הפסיקה לכתוב יצוא** ב-`23:00:51`. לראיה,
`TS-OFFSET-GATE` החזיר **0 היום** מול **121 ERROR אתמול** — אתמול הגיעו דחיפות
(סטטיות, והשער דחה אותן בצדק: `newest bar ts 83152s behind now`, וה-`1790974500`
שבהודעה הוא **בדיוק** `max(ts)` של שישי); היום לא מגיע **כלום**. אפס-דחיות אינו
"השתפרנו" — הוא **שקט מוחלט במעלה הזרם**.

**⚠️ והכיוון כאן גרוע כמו במלכודת 28 — הפעולה המתבקשת היא הלא-נכונה.** בלי שורת-הדופק,
"הפיד מת 13 שעות" מוביל לריסטארט-ברידג' או ריסטארט-בקאנד. שניהם **לא נוגעים בתקלה**
(הברידג' עובד מושלם), שניהם שורפים את חלון-טרום-הפתיחה, וריסטארט הוא שינוי
בסיכון-מסחר (⇒ עצירה-אסטרטגית + פסיקת-מייקל). התיקון היחיד שנוגע בקומה הנכונה הוא
**בסיירה**: `File → Disconnect → Connect to Data Feed`, ואם היצוא עדיין שותק —
טעינה-מחדש של ה-study. זה בדיוק הניסוח ש-[[T-430]] מצווה לשלוח כמקרה (ג).

**היחס ל-[[T-430]] — שני צדדים של אותו מטבע, ושניהם נדרשים:**

| | T-430 (19.09) | מלכודת 29 (04.10) |
|---|---|---|
| הטענה | קובץ-יצוא **טרי** ≠ פיד חי | קובץ-יצוא **תקוע** ≠ ברידג' מת |
| הכשל | מדווחים GO על פיד מת | מרסטרטים את הקומה הבריאה |
| הפוסק | `max(ts)` ב-`v9_bars_5min_woodies` | `last_push_age` ב-`bridge.err.log` |

`max(ts)` עונה **האם** נשבר; `last_push_age` עונה **איפה**. ‏`fire_drill` שלב D בודק
את הראשון — את השני עדיין צריך להסתכל בעיניים לפני שנוגעים במשהו.

**קרובי-משפחה בקובץ:** מלכודת 22 (`mtime` כמד-חיוּת) · מלכודת 12
(`pgrep` ששותק בהצלחה ⇒ "הרלה מתה") · §3.4 (**אפס ≠ מת**) — כאן בגרסתו החדה
ביותר: *אפס-שגיאות הוא לפעמים התסמין, לא הבריאות.*

---

### מלכודת 30 · `lsof -ti :8000 | head -1` מחזיר **לקוח** ולא מאזין — ו-`ps -o lstart` עליו משקר על שעת-עליית-הבקאנד (05.10)

**הממצא (ריצה 190, 17:36 IDT, ניטור-RTH):** בדיקת "מתי המאזין על :8000 עלה" —
הבדיקה שכלל-בעלות-הריסטארט של חובה-2 בנוי עליה — הורצה כך:

```bash
ps -o pid=,lstart=,etime= -p $(lsof -ti :8000 | head -1)
#  4867  Mon Oct  5 15:58:15 2026   01:37:54      ← "עלה היום ב-15:58"
```

**זה לקוח, לא שרת.** ‏`lsof -ti :8000` מחזיר כל תהליך עם **socket** על הפורט —
כולל חיבורים יוצאים — ו-`head -1` בחר את הראשון בלי אבחנה. כאן זה היה
`Cursor Helper` (‏4867), והשני בתור היה `Google Chrome` (‏27362, מ-02.10). הפוסק:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
# COMMAND   PID    USER   FD   TYPE  ... NAME
# Python  71969 michael   18u  IPv4  ... TCP *:8000 (LISTEN)
ps -o pid=,lstart=,etime= -p 71969
# 71969  Sat Oct  3 16:22:52 2026   02-01:16:37      ← אמת: למעלה מיומיים, אפס ריסטארט היום
```

**⚠️ למה זה מסוכן דווקא בשער-15:30, ולא בניטור:** נוסח-החובה אומר *"אם המאזין על
:8000 עלה היום אחרי 12:00 לפי `ps -o lstart` — cowork-האינטראקטיבי הוא הבעלים:
אל תרים ריסטארט ואל תשלח GO/NO-GO"* ([[T-369]]). עם `head -1`, **כל** דפדפן או IDE
שנפתח אחרי 12:00 ויש לו טאב על `localhost:8000` מייצר "עלה היום" מזויף ⇒ ריצת-השער
מסיקה שהבעלות אינה שלה, **מדלגת על ריסטארט-קדם-פתיחה שכן נדרש**, ושותקת במקום
לשלוח שער. כלומר הכשל הוא **החמצה שקטה**, לא אזעקת-שווא — המחיר הוא יום-מסחר על
קוד-הבוקר שלא נטען.

**הכלל:** כל שאלה על **המאזין** — גיל, PID, commit, ריסטארט — נענית מ-
`lsof -nP -iTCP:<port> -sTCP:LISTEN` (או `pgrep -f "uvicorn backend.main:app"`),
לעולם לא מ-`lsof -ti`. ‏`-sTCP:LISTEN` הוא כל ההבדל.

**בקרה-צולבת זולה שתפסה את זה:** רשומת-הפיקוח של 17:36 אמרה `מאזין 71969`, וריצה
189 אמרה `pid 71969 lstart Sat Oct 3 16:22:52`. **שני מקורות בלתי-תלויים נגד
המספר שלי** ⇒ הנחתי שאני טועה ובדקתי מחדש, ולא הפוך. זו בדיוק מלכודת 28 בלבוש
אחר: פקודה שמחזירה פלט סביר על **האובייקט הלא-נכון**.

**קרובי-משפחה בקובץ:** מלכודת 12 (`pgrep` ששותק בהצלחה) · מלכודת 22 (`mtime`
כמד-חיוּת) · מלכודת 28 (`origin/main` שאינו ה-upstream) · מלכודת 27 (חלון-שורות
במקום חלון-זמן) — כולן אותה מחלקה: **הפקודה עבדה, היא פשוט נשאלה על משהו אחר.**

### מלכודת 31 · ל-"כמה נחסמו ולמה" יש **שלושה משטחים** — והלוג מנפח ×3 (tree) ו-×2 (שרשרת-השער) (05.10)

**מה שקרה:** ריצה 192 (18:40) דיווחה היסטוגרמת-חסימות `tree:location 26 ·
entry_location_quality 4 · None 2 · tree:kind 2 · news_blackout 2 ·
tree:stand_down 2 · rr_entry_gate 1 · entry_not_confirmed 1` ⇒ **40 שורות**.
ריצה 193 (19:13) מדדה על אותו יום `tree:location 27 · None 16 · tree:bias 2 ·
tree:kind 2 · tree:stand_down 2` ⇒ **49 שורות**, בלי `entry_location_quality`,
בלי `news_blackout`, בלי `rr_entry_gate`, בלי `entry_not_confirmed`. **שני
הדוחות נכונים.** הם פשוט נשאלו על שלושה משטחים שונים:

```bash
# (1) הלוג — מנפח, כי כל אירוע נכתב יותר מפעם אחת
grep -E "^$(date +%F)" /tmp/backend.err.log | grep -oE "blocked_by=[a-z_:]+" | sort | uniq -c
#   tree:location 81 · ELQ 8 · tree:stand_down 6 · tree:kind 6 · tree:bias 6
#   news_blackout 4 · rr_entry_gate 2 · entry_not_confirmed 2

# (2) v9_decision_vectors — שורה-לאירוע, אבל tree:* בלבד
psql … -c "select coalesce(blocked_by,'None'), count(*) from v9_decision_vectors
           where ts>=current_date and kind='DECISION' group by 1 order by 2 desc;"
#   tree:location 27 · None 16 · tree:bias 2 · tree:kind 2 · tree:stand_down 2   (=49)

# (3) ליגר-המועמדים (candidate_ledger.py) — שרשרת-השער המלאה: ELQ / news / rr / confirm
```

**המקדמים, ושניהם יצאו שלמים — ולכן אינם רעש:**

| חסימה | לוג | DB | יחס |
|---|---|---|---|
| `tree:location` | 81 | 27 | **3.0** |
| `tree:bias` · `tree:kind` · `tree:stand_down` | 6 · 6 · 6 | 2 · 2 · 2 | **3.0** |
| `ELQ` · `news_blackout` · `rr_entry_gate` · `entry_not_confirmed` | 8 · 4 · 2 · 2 | **0** | — (÷2 ⇒ 4·2·1·1 = מספרי-192) |

כלומר אותו אירוע בודד מודפס מספר פעמים שונה לפי **סוג** החוסם, וזה מאומת שורה-שורה:
```raw
# tree:* ⇒ שלוש שורות: BLOCKED מפורט → התאום-בצל → BLOCKED קצר
19:05:04 [Gateway] BLOCKED … FAILED_RE_IB … blocked_by=tree:bias ot=OPEN_AUCTION_IN hint=LONG bias=LONG kinds=[…] il=19:05
19:05:04 [Gateway] T-219 shadow_blocked: SHORT FAILED_RE_IB blocked_by=tree:bias → twin #3035 (41/150 today)
19:05:04 [Gateway] BLOCKED system=2 pattern=FAILED_RE_IB dir=SHORT entry=7811.0 blocked_by=tree:bias

# שרשרת-השער ⇒ שתי שורות בלבד: התאום-בצל → BLOCKED   (אין שורת-BLOCKED מפורטת)
17:10:10 [Gateway] T-219 shadow_blocked: LONG GHOST blocked_by=entry_location_quality → twin #3002 (13/150 today)
17:10:10 [Gateway] BLOCKED system=4 pattern=GHOST dir=LONG entry=7799.75 blocked_by=entry_location_quality
```
ואירוע של שרשרת-השער אינו מגיע **כלל** ל-`v9_decision_vectors.blocked_by` —
העמודה הזו מתעדת רק את פסיקת-העץ.

**ההצלבה שסוגרת את שלושת המשטחים לאירוע אחד:**
```bash
grep -oE "TREE_V3 .* → (TAKE|SKIP)" /tmp/backend.err.log | grep -coE "→ TAKE"   # 16
psql … -c "select count(*) from v9_decision_vectors where ts>=current_date and kind='DECISION';"  # 49
# 16 TAKE + 33 SKIP = 49  ≡  49 שורות DECISION  ⇒ אותו אירוע, שתי ספירות נכונות
```

**⚠️ והמלכודת-בתוך-המלכודת — `blocked_by IS NULL` אינו "עבר לשער":**
אותו יום נתן `None = 16` ב-DB מול `grep -c "shadow_only setup" = 7` בלוג
ו-`LIVE trade TM = 1`. כלומר 16 הן **כל ה-TAKE של העץ**; מהן 7 נעצרו
ב-`shadow_only` (פסיקה — ראה `RULED_FLAGS.yaml` ל-`CEILING_FLIP_TOUCH2_V1`),
**אחת** יצאה לייב, והיתר נפלו בשרשרת-השער שה-DB אינו מתעד. מי שקורא `None`
כ-"נותב" מדווח פי-16 מהלייב האמיתי.
**והראיה היא שמית, לא אריתמטית:** ארבע מ-16 שורות-ה-`None` הן בדיוק ארבעת
החסומים-ב-ELQ של אותו יום — זיווג אחד-לאחד לפי דפוס · כיוון · מחיר:
```raw
DB  (blocked_by = NULL)                         LOG (blocked_by=entry_location_quality)
17:10:10  GHOST                LONG 7799.75  ↔  17:10:10  GHOST                LONG 7799.75
17:20:07  INITIATIVE_LONG      LONG 7805.5   ↔  17:20:08  INITIATIVE_LONG      LONG 7805.5
17:25:04  INITIATIVE_LONG      LONG 7808.5   ↔  17:25:04  INITIATIVE_LONG      LONG 7808.5
17:30:06  DOUBLE_BOTTOM_EE_LONG LONG 7808.0  ↔  17:30:06  DOUBLE_BOTTOM_EE_LONG LONG 7808.0
```
**אותו דפוס, אותו מחיר, אותה שנייה (±1) — ושתי תשובות הפוכות לשאלה "נחסמה?".**

**הכלל:** לפני ציטוט מספר-חסימות — **לנקוב במשטח**. לספירת-אירועים: ליגר-המועמדים
(שרשרת מלאה) או `v9_decision_vectors` (עץ בלבד). הלוג הוא לראיית **רצף** של אירוע
בודד (Rule 5), לא לספירה. ו-"נותב לייב" נמדד רק מ-`COMMAND QUEUED` / `LIVE trade TM`,
שהיו **1** באותו יום.

**קרובי-משפחה בקובץ:** מלכודת 21 (לפיד-הליגר שתי צורות-שורה — שם: שדה-הזמן, כאן:
המשטח) · מלכודת 26 (`find_ledger` שמחזיר `None` לפי לוח-זמנים) · מלכודת 27
(חלון-שורות במקום חלון-זמן) · מלכודת 30 (הפקודה עבדה, נשאלה על אובייקט אחר).

### מלכודת 32 · `GET /chat` הוא **חלון-תצוגה בעל שעות-פתיחה** — מחוץ ל-`10:00-23:30` הוא מחזיר `[]` על חוט שלם ([[T-546]], 06.10)

ההזמנה מחייבת **אימות-מסירה דרך `GET /chat` ולא מה-`ok`** — והפוסק הזה **שקרי בדיוק
בשעות שבהן סוכן-לילה עובד.** `render_mobile_relay/app.py` מרכיב את `/chat` מ-`_PUSHED_THREAD`
+ `_INBOX` + `_REPLIES` + `_UPLOADS`, **כולם מבני-זיכרון**, ו-`_PUSHED_THREAD` מתמלא רק
מ-`POST /chat_push` שהמק דוחף. הדוחף הוא `scripts/mobile_relay.py` (לא `phone_relay` —
מלכודת §3.12), והוא **מכבה את עצמו בכוונה** מחוץ ל-`RELAY_WINDOW_IL=10:00-23:30` שב-`.env`
(`[relay] outside active window — idling (free-tier hours budget)`), ובמקביל Render נרדם.

**שתי המדידות, ואותו מופע בדיוק — 4 דקות הפרש משני צדי הגבול:**

```raw
cowork-dev ריצה 202 · 06.10 ~06:00-11:06 IL (מחוץ לחלון / בקצהו, קריאה קרה):
  GET /chat?key=…                 ⇒ http=200 · {"items":[]}            ← ולא 30 כמו בריצה 201
cowork-dev ריצה 203 · 06.10 11:16:30 IL (בתוך החלון, הרלה state=running pid=1629):
  GET /chat?key=…                 ⇒ http=200 · 13KB · items=30
  sender-counts                   ⇒ cowork-dev 23 · מייקל 2 · cc 2 · supervisor 2 · cowork 1
  אחרונת-מייקל                     ⇒ 2026-10-02T12:02:01Z (נענתה פעמיים) ⇒ אין ממתינה
```

⇒ **`{"items":[]}` אינו "אין ממתינות" — הוא "התיבה בזיכרון עוד לא התעוררה".** ושים לב
לכיוון-הכשל: הוא **שלילי-שקרי** (מסתיר הודעה שקיימת), כלומר הנזק הוא **שתיקה כלפי מייקל**,
לא רעש — אותה מחלקה כמו מלכודת 12.

**הפוסקים, בסדר:**

| שאלה | הפוסק | למה |
|---|---|---|
| יש ממתינה ממייקל? | **`docs/handoff/PHONE_THREAD.jsonl`** — קובץ, על הדיסק | חי גם כשהרלה ישן. ועדיין: §מלכודת 12 — לאמת שהרלה לא מת, אחרת הקובץ ריק משקר |
| ההודעה שלי נמסרה? | `GET /chat`, **רק בתוך `10:00-23:30`** | מחוץ לחלון אין snapshot להשוות אליו |
| יש הוראה/פקודה ממתינה? | `GET /instruction/pending` · `GET /cmd/pending` (שניהם **peek**) | מצב-ה-Render עצמו, לא תצוגה |

⚠️ **והשלכה לאחור:** רשומת [[T-442]] שקראה `{"items":[]}` ב-`10:05`/`10:09` כ-"אפס אובדן"
**אינה מכריעה** — בקצה-החלון אי-אפשר להבחין בין "אין ממתינות" ל-"הרלה התעוררה קרה".
ה-docstring של הרלה מבטיח את ההפוך (*"the page still opens (cold start ~50s) showing the
last snapshot"*) — אין snapshot, הוא בזיכרון שמת.

**קרובי-משפחה:** מלכודת 12 (אפס-ממתינות אינה ראיה עד שהרלה מוכח חי) · מלכודת 22
(`mtime` אינו מבחן-חיוּת באף כיוון) · §3.12 (שם-הרלה) · מלכודת 20 (בדיקה על נתיב
שלא אומת היא זיכרון, לא מדידה).

---

### מלכודת 33 · "אפס ERROR/CRITICAL" הוא **ציר-בריאות מוצף** בחלון-טרום-הפתיחה — 100% מהשגיאות הן `TS-OFFSET-GATE` ([[T-532]], 06.10)

**מקור הפסיקה:** ריצה 207 (06.10 13:05) כבר קבעה ש-*"NO-GO על ספירת-ERROR הוא מלכודות
24/27/28"* ושהפוסק הוא **woodies** ולא מספר-השגיאות. המלכודת הזאת **מקבעת את אותה פסיקה
בסדר-הקריאה** ומוסיפה לה את המדידה שלא נעשתה: **מה ההרכב של מחלקת-ה-ERROR**. ריצות
206/207 מדדו **קצב** (19/דק') ו**נפח** (21MB) — לא **נתח**, וזה מה שהופך את `0` לבלתי-קריא.

ריצות הניטור והשער בודקות *"כמה ERROR/CRITICAL מאז שעה X"* ומדווחות `0` כראיית-בריאות.
**בחלון-טרום-הפתיחה המדידה הזאת חדלה להיות ראיה:** `backend.err.log` מקבל
`TS-OFFSET-GATE REJECTED batch` בקצב **19.5 בדקה**, ו**כל** שגיאות היום הן הוא.

```raw
(06.10 14:38-14:41, נמדד)
grep "^2026-10-06" /tmp/backend.err.log | grep -E "\[(ERROR|CRITICAL)\]" | wc -l   ⇒ 4,382
                                                        … | grep -c TS-OFFSET-GATE ⇒ 4,382   ← 100%
                                                        … | grep -vc TS-OFFSET-GATE ⇒     0
חלון 40 שנ':  TS-OFFSET-GATE +13 (19.5/דק')  ·  כל-השורות +27 (40.5/דק')  ⇒ 48% מצמיחת-הלוג
גודל: 22.3MB  ·  0.52 MB/שעה  ⇒  12.5 MB/יום
הראשונה בכלל: 2026-10-02 10:16:47   ·   סך-הכל 15,896 שורות-שער (14,658 ERROR + 1,238 WARNING)
   מהן REJECTED: 14,492 על [bars/5min] (הזרם ה**מוזנח**) + 252 על [woodies_5min]
```

**הכיוון הפוך ממלכודות 12/32:** זה **רעש**, לא שתיקה. הנזק אינו שגיאה מומצאת אלא
**שגיאה אמיתית שתיקבר** בין 4,382 זהות — ומי שרואה `4,382` וקורא לזה תקלה, מדווח
תקלה שאינה קיימת. **שתי הטעויות מאותו מקור.**

**הפוסק — תמיד לסנן את השער לפני שסופרים:**

```bash
grep -E "\[(ERROR|CRITICAL)\]" /tmp/backend.err.log | grep -v TS-OFFSET-GATE   # ← זה המונה
```

**והפקודה אומתה על עצמה (Rule 5), לא רק נרשמה:**

```raw
$ grep -E "\[(ERROR|CRITICAL)\]" /tmp/backend.err.log | wc -l                       ⇒ 14,853   ← מה שריצת-שער רואה
$ grep -E "\[(ERROR|CRITICAL)\]" /tmp/backend.err.log | grep -v TS-OFFSET-GATE | wc -l ⇒     71   ← המונה האמיתי
$ … | grep -v TS-OFFSET-GATE | tail -3
    2026-10-05 19:25:06 [CRITICAL] [fill_poller] ORPHAN FILL — no trade for order_id=11408 kind=ENTRY
    2026-10-05 19:40:04 [CRITICAL] [trading_gateway] LIVE fire BLOCKED pre-send: 2 working order(s) …
    2026-10-05 20:44:17 [CRITICAL] [fill_poller] ORPHAN FILL — no trade for order_id=11409 kind=T1
$ grep "^2026-10-06" … | grep -vc TS-OFFSET-GATE                                     ⇒      0
```

⇒ `14,853 → 71`, וכל 71 הן שורות-[[T-545]] המוכרות מ-05.10; **היום `0`.** כלומר הסינון
לא רק מצמצם — הוא מחזיר את המונה למצב שבו `0` שוב **אומר** משהו.

**ולמה זה אינו אירוע — נמדד, לא הונח:**

```raw
v9_bars_5min_woodies  ⇒ 165 ברים 01:00→14:40, גיל 1.0 דק', 12 בשעה האחרונה
                         820 דק' / 5 = 164 מרווחים ⇒ 165 ברים = **אפס פערים** (T-430 תקין)
v9_decision_vectors   ⇒ 48 היום, אחרונה 14:35 ⇒ הגייטוויי כותב
/api/v9/health ⇒ 200 t=0.0017s · פוזיציה 0 · ruled_contracts() = 1
```

⇒ **הזרם הנדחה הוא `v9_bars_5min` הקפוא של [[T-532]], לא אמת-הלייב.** והשער עצמו **נכון**:
הוא דוחה batch שהבר-החדש-בו באמת `53,157s` (14.8 ש') מאחור — כשל-כשר לפי Rule 1 במקום
לנחש הסחה — והדגל `TS_OFFSET_INGEST_GATE_V1=1` **פסוק** (`RULED_FLAGS.yaml:185`, מייקל
2026-07-21) ⇒ **אין לגעת בו.**

🟢 **והוא נרפא מעצמו בפתיחת-ה-RTH — שלושה ימים נמדדו:**

```raw
10-02 (יום ראשון של התופעה): שעות 10→15 חמות (835·1181·1186·1189·1186·1180) ⇒ שעה 16: 588 ⇒ נעצר
10-05:                        שעות 00-13 שקטות (8-40/שעה) ⇒ 14: 734 · 15: 1187 ⇒ 16: 591 ⇒ נעצר
10-06:                        00-10 שקטות (8-43) ⇒ 11: 1005 · 12: 1168 · 13: 1193 · 14: 745 (חלקית)
```

ברגע שמגיעים ברים טריים (`_off < 900`) השער עובר, הסמן מתעדכן, והלוּפּ נגמר ⇒ **תופעת
טרום-פתיחה בלבד**, לא כשל מתגבר. **וזו בדיוק השעה שבה רצה ריצת-השער של `15:30`.**

⚠️ **מה שבמפורש אינו נטען:** לא בעיית-CPU — `top` אינסטנטני `18.3-21.8%`, ו-`ps -o %cpu`
נתן `46.7` ב-14:35 ו-`8.0` ב-14:42 על אותו pid ⇒ **`ps %cpu` אינו בר-סמך כאן ואין טענת-CPU**
(מלכודת 22 באותה מחלקה: המדד לא נבחן, לכן אינו ראיה). ולא נטען שמשהו **כן** נקבר היום —
נמדד `0` שגיאות אחרות ⇒ **סיכון-מיסוך, לא אובדן-שהתממש** (§3.6).

**קרובי-משפחה:** **מלכודות 24/27/28** (NO-GO על ספירת-ERROR — פסיקת ריצה 207; זו ההרחבה
שלהן עם הנתח) · §לוג-האפליקציה הוא `backend.err.log` ולא `backend.log` (בלי זה סופרים
בקובץ הלא-נכון מלכתחילה) · מלכודת 31 (לאותה שאלה שלושה משטחים, והלוג מנפח) · מלכודת 22
(`ps`/`mtime` אינם מבחן-חיוּת) · מלכודת 12 (אפס אינו ראיה עד שהמקור מוכח חי) ·
מלכודת 29 (`bridge.err.log` הוא מאתר-הקומה כשהפיד **כן** תקוע).

---

### מלכודת 34 · המונה של מלכודת 33 **ירד דרגה** — אפס-ERROR היום הוא `0` **לפי הגדרה**, והמבול עבר ל-WARNING ([[T-557]], 07.10)

**מלכודת 33 נשארת נכונה בניסוח שלה ושגויה בשימוש בה.** היא מחייבת את המונה
`grep -E "\[(ERROR|CRITICAL)\]" /tmp/backend.err.log | grep -v TS-OFFSET-GATE`, ומסבירה
שהמבול הוא `TS-OFFSET-GATE` ב-ERROR. **שתי העובדות האלה כבר אינן נכונות:** אין שורת-ERROR
אחת בכל הקובץ מאז `2026-10-06 17:30`, ו-`TS-OFFSET-GATE` מודפס היום כ-WARNING. לכן המונה
מחזיר `0` **בלי קשר למצב-הבריאות** — ומי שקורא `0` כראיית-בריאות מדווח בריאות שלא נמדדה.
זה אותו כיוון-נזק של מלכודת 33 (רעש שקובר אמת), אבל **דרגה אחת למטה**, שם אין מונה כלל.

```raw
(07.10 11:39-11:48, נמדד, קריאה-בלבד)
grep -c "^2026-10-07" /tmp/backend.err.log                           ⇒ 64,604   ← הקובץ כן נכתב
היסטוגרמת-רמות של היום                                               ⇒ 17,288 [INFO] · 47,316 [WARNING]
                                                                        0 [ERROR] · 0 [CRITICAL]
grep -nE "\[(ERROR|CRITICAL)\]" /tmp/backend.err.log | tail -1        ⇒ 2026-10-06 17:30:05 [CRITICAL]
                                                                        [trading_gateway] LIVE fire BLOCKED pre-send
grep -c "^2026-10-07.*TS-OFFSET-GATE" /tmp/backend.err.log           ⇒ 14,724   ← כולן WARNING
הנתח הגדול בכלל: "[S2-CVD] insufficient coverage"                    ⇒ 13,960   ← 30% מה-WARNING
grep "^2026-10-07.*\[WARNING\]" … | grep -vc TS-OFFSET-GATE          ⇒ 32,600
```

🔴 **והנתח החדש אינו `TS-OFFSET-GATE` כלל.** מלכודת 33 מתעדת "00-10 שקטות (8-43/שעה)" ל-06.10.
היום אין שעה שקטה — `[S2-CVD]` רץ ב-20/דקה **בלי הפסקה**, מאז הדקה שבה התחיל:

```raw
פר-יום בלוג      ⇒ 10-02: 1,462 · 10-03: 664 · 10-05: 977 · 10-06: 1,479 · 10-07: 13,960   (×9.4)
פר-שעה היום      ⇒ 00:1200 01:1192 02:1195 03:1197 04:1198 05:1193 06:1193
                    07:1196 08:1199 09:1195 10:1191 11:794 (חלקית)
תחילת-המבול      ⇒ 191698:2026-10-06 23:00:55 [WARNING] [mems26.systems.five_min]
                    [S2-CVD] insufficient coverage: 3/20 rows (min=18) — returning None (Rule 1)
                    ומשם 23:01 ⇒ 19/דק' ויציב
```

🟢 **והשורה עצמה אינה תקלה — היא Rule 1 עובד.** `five_min_system.py:845-872` קורא
`SELECT cumulative FROM v9_bars_cumulative_delta WHERE ts >= :t0 AND ts <= :t1`, והטבלה היא
**טבלת-RTH בלבד**:

```raw
PGTZ=UTC psql ⇒ count=8,964 · max(ts)=2026-10-06 20:55:00+00 · age 705.7 דק'
                rows in last 100 minutes ⇒ 0
rows/ET-day   ⇒ 10-06: 90 · 10-05: 90 · 10-02: 90 · 10-01: 126 · 09-30: 126 · 09-29: 126
```

מחוץ ל-RTH `len(cums)=1 < _window_min=18` ⇒ `return None` — **כשל-כשר** בדיוק כפי שכלל-1
מחייב, ולא ערך מסונתז. כלומר: **לא לפתוח אירוע על השורה**, ולא לנסות "לתקן" אותה.

**הפוסק — שני מונים, כי המבול נייד:**

```bash
grep -E "\[(ERROR|CRITICAL)\]" /tmp/backend.err.log | grep -v TS-OFFSET-GATE     # מלכודת 33
grep "^$(date +%F).*\[WARNING\]" /tmp/backend.err.log \
  | grep -vE "TS-OFFSET-GATE|S2-CVD insufficient|BarRouter: (dispatch|SLOW)"      # מלכודת 34
```

⚠️ **מה שבמפורש אינו נטען:** (א) שירי-S2 נחסם או שעסקה אבדה — דורש מדידת-RTH שלא נעשתה,
ו-06.10 נתן `290` בלבד בשעה 16 ⇒ הכיסוי **כן** מתאושש בפתיחה (זה הצעד-הבא של [[T-557]]);
(ב) שהצניחה `126→90 שורות/יום-ET` בין 01.10 ל-02.10 היא תקלה — נמדדה, לא אובחנה;
(ג) שמשהו **כן** נקבר היום — אפס ERROR ⇒ **סיכון-מיסוך, לא אובדן-שהתממש** (§3.6).

**קרובי-משפחה:** **מלכודת 33** (זו ההרחבה שלה — אותה מחלקה, דרגה אחת למטה) · מלכודת 31
(לאותה שאלה כמה משטחים) · מלכודת 27 (חלון-שורות במקום חלון-זמן) · מלכודת 12 (אפס אינו
ראיה עד שהמקור מוכח חי — כאן הוכח ב-`grep -c "^$(date +%F)"` ⇒ 64,604) · § Rule 1
(`None` כשהמקור שותק הוא הנכון; אין להמציא ערך).

---

### §מ-34ב · שתי המרות-אזור-זמן רצופות על `timestamptz` מנפחות את יום-ET (נמדד, ריצה 232)

לא מלכודת חדשה — **הפרה של הצורה הקנונית שכבר רשומה בקובץ** (`§177`: *תמיד*
`(entry_ts AT TIME ZONE 'America/New_York')::date`). נרשם כאן כי הוא ייצר מספר שגוי בריצה
חיה, וה-`::date` נראה תמים בשתי הצורות:

```raw
(07.10 11:38, נמדד על v9_bars_5min_woodies)
שגוי:  where (ts at time zone 'UTC' at time zone 'America/New_York')::date = …   ⇒ 140 ברים
נכון:  where (ts at time zone 'America/New_York')::date = …                       ⇒  56 ברים
אימות: min(ts)=2026-10-07 04:00:00+00 · max(ts)=2026-10-07 08:35:00+00 · now()@ET=04:37
       ⇒ 00:00→04:35 ET = 56 ברים של 5 דק' רצופים · dup(ts) ⇒ 0
```

העמודה היא `timestamp with time zone`. ההמרה הראשונה הופכת ל-naive-UTC, והשנייה **מפרשת
את ה-naive כ-ניו-יורק** — כלומר מזיזה פעמיים ומגלגלת ברים של אתמול לתוך יום-היום. הבדיקה
הזולה: יום-ET חלקי בשעה `HH:MM` ET אינו יכול להכיל יותר מ-`(HH*60+MM)/5` ברים.

**§מ-34ג · אותו שורש, צרכן אחר: חשבון-גיל. המרה אחת מספיקה כדי לזייף את ציר-הטריות
(נמדד, ריצה 239 · 07.10 15:06).** הצורה השגויה אינה כפולה כאן אלא **בודדת** — מספיק
`now() at time zone 'utc'` מול עמודת-`timestamptz` כדי להזיז את ההפרש בהיסט-המקומי:

```raw
(07.10 15:06, נמדד על שלושת זרמי-הברים)
שגוי:  extract(epoch from (now() at time zone 'utc' - max(ts)))   ⇒ woodies age = -179.17 min
נכון:  now() - max(ts)                                            ⇒ woodies age =    1.40 min
אימות: max(ts)=2026-10-07 15:05:00+03 · now()=15:06:09+03 · now()-ts = 00:01:09
       information_schema ⇒ v9_bars_5min{,_woodies,...}/cumulative_delta .ts :: timestamp with time zone
       -179.17 = -(3h) + 1.40min  בדיוק
```

`now()` הוא `timestamptz`; `at time zone 'utc'` הופך אותו ל-naive, ואז החיסור מול
`timestamptz` מפרש את ה-naive כ-מקומי ⇒ הזזה של `+3h` (IDT) בשתיקה. **למה זה מסוכן דווקא
בשער ולא רק מכוער:** גיל שלילי צועק ונתפס מיד, אבל **אותה הזזה בכיוון ההפוך מוסיפה 3 שעות
לגיל אמיתי** — ועל זרם תחום-RTH ([[T-558]]) זה הופך פער-לילה שגרתי `15.19h` ל-`18.19h`,
מעל הטווח השגרתי `13.58h`-`16.58h`, ומייצר **NO-GO שקרי**. הצורה היחידה המאושרת לציר-הטריות
היא `now() - ts` על `timestamptz`, או השיטה המודעת-אזור של `fire_drill` שלב D
(`fire_drill.py:276` ⇒ `datetime.now(timezone.utc) - max_ts`). הבדיקה הזולה: **גיל לא יכול
להיות שלילי**, ו-`|גיל שגוי − גיל נכון|` יוצא עגול בדיוק כהיסט-המקומי.

---

### מלכודת 35 · אזהרת-`EXIT_TRACK_ACTIVITY_V1` — **ערך-האמת שלה והתוצאה שלה נקבעים בנפרד**, ו-`mtime` טרי מפריך את הנימוק בלי להפריך את העיוורון (07.10)

השורה בלוג היא מהחמורות בקובץ — *"exit tracking is **BLIND**; Sierra-truth exits will not be
priced (check com.mems26.activity_feed)"* — ויש לה **שני רכיבים שחייבים להימדד בנפרד**:
ה**נימוק** (`mtime` מעל 900 שנ') וה**תוצאה** (יציאות לא יתומחרו). בניטור-RTH של 07.10 נמדד
ש**הנימוק שקרי והתוצאה נכונה** — ולכן *שתי* הקריאות החד-צדדיות שגויות.

**צד א׳ — הנימוק אכן שקרי בזמן-אמת:** 75 השורות של היום כולן בחלון-הלילה, והפיד טרי שניות.

```raw
(07.10 22:11, נמדד, קריאה-בלבד)
grep -c "^2026-10-07.*EXIT_TRACK_ACTIVITY_V1" /tmp/backend.err.log   ⇒ 75
  פר-שעה: 00→10 · 01→12 · 02→12 · 03→12 · 04→12 · 05→12 · 06→5  ⇒ ואז נעצר
  אחרי 07:00 היום ⇒ **0**   ·   האחרונה ⇒ 2026-10-07 06:24:52
trade_activity_events.jsonl staleness = **30 s**        (הסף שבאזהרה = 900 s)
  stat ⇒ 2026-10-07 22:09:47 · 564,536 bytes
  launchctl print …activity_feed ⇒ state = running · pid = 1624 · last exit code = (never exited)
פר-יום בכל הקובץ ⇒ 10-02:2 · 10-03:75 · 10-04:173 · 10-05:17 · 10-06:18 · 10-07:75
  ⇒ אשכול-לילה חוזר; השורש: בשוק סגור אין פעילות-חשבון ⇒ אין כתיבה ⇒ ה-mtime מתיישן,
     והאזהרה נעצרת בכתיבה הראשונה של הפיד.
```

🔴 **צד ב׳ — ובכל-זאת העיוורון אמיתי היום, מסיבה שהאזהרה אינה נוקבת בה כלל:** הקציר של
היום כולו הוא **שני events, שניהם `ORDER_REJECT`**. אפס `POSITION_CHANGE`, אפס `SIM_FILL`,
אפס `CLOSED_TRADE_PNL`:

```raw
(07.10 22:14, נמדד — אותו קובץ, פילוח לפי חשבון)
events בקובץ ⇒ 3,796   ·   today events ⇒ **2**  {ORDER_REJECT: 2}
account ⇒ {'37138283': 1596, 'Sim1': 33}     is_sim ⇒ {False: 1596, True: 33}
CLOSED_TRADE_PNL ⇒ 1,256 בסך-הכל  ·  **ל-2026-10-07: 0**
  האחרונה: {'type':'CLOSED_TRADE_PNL','pnl':'-17.5','symbol':'MESZ26_FUT_CME.',
            'scan_ts':'2026-10-06T15:14:06Z','account':'37138283','is_sim':'False'}
```

⇒ הסורק קוצר את החשבון ה**לא-סימולטיבי** `37138283`, בעוד המילויים של היום הולכים ל-`Sim1`
(‏`sierra_state ⇒ trade_account Sim1 · is_sim 1`). זהו בדיוק הממצא ש-[[T-562]] רשם
(‏`STATUS_BOARD`, ריצה 251) — וכאן הוא מאושש משטח-עצמאי: **`activity_feed` שרץ מושלם אינו
מספק אמת-ברוקר לעסקאות-Sim1.** הרצת-הסוכן אינה פותרת זאת, כי התקלה היא **תחום-חשבון**,
לא חיוּת-תהליך.

⚠️ **ולכן שתי הטעויות, והשנייה היא זו שכמעט פורסמה:**

| הקריאה | מה היא מסיקה | למה היא שגויה |
|---|---|---|
| **הלוג כפשוטו** (75 שורות) | "exit tracking שבור ⇒ מקרה (ג)" | הנימוק (staleness) חלף לפני 16 שעות |
| **`mtime` לבדו** (30 שנ' טרי) | "הפיד חי ⇒ אמת-הברוקר תקינה" | אפס events ל-Sim1 היום ⇒ **ירוק-כזב** |

🔴 **הכיוון המסוכן הוא השני**, ודווקא בערב: עמוד (1) של **חובה-4** הוא
`broker_truth.py --write`, וההוראה מחייבת לוודא `n/N = כל העסקאות` ולכתוב
**"אין רישום-ברוקר ל-#id"** כשלא. ריצה שתפריך את האזהרה לפי `mtime` ותכריז "אמת-הברוקר
תקינה" **תדלג על הרישום הזה בדיוק** — ותפרסם P&L-ברוקר כמאומת כשאינו.

**הפוסק — שלוש שאלות נפרדות, ואין אחת שמכסה את חברתה:**
```bash
# 1 · האם הסוכן חי?            (ולא: האם יש נתונים)
launchctl print gui/$UID/com.mems26.activity_feed | grep -E "state|pid"
# 2 · האם הנימוק של האזהרה עוד מתקיים?   (ולא: האם יש נתונים)
python3 -c "import os,time;p=os.path.expanduser('~/SierraChart_Data/v9_export/trade_activity_events.jsonl');print('%.0fs'%(time.time()-os.path.getmtime(p)))"
# 3 · ✅ הפוסק האמיתי לאמת-ברוקר — האם יש events לחשבון שבו העסקאות באמת נסגרו:
python3 - <<'PY'
import json,os,collections
p=os.path.expanduser('~/SierraChart_Data/v9_export/trade_activity_events.jsonl')
rows=[json.loads(l) for l in open(p) if l.strip()]
t=[r for r in rows if str(r.get('scan_ts') or '')[:10]==os.popen('date +%F').read().strip()]
print('today:',len(t),collections.Counter(r.get('type') for r in t))
print('accounts:',collections.Counter(str(r.get('account')) for r in rows))
PY
```

**קרובי-משפחה:** מלכודת 22 (`mtime` אינו מבחן-חיוּת **באף כיוון** — כאן *שני* הכיוונים
נכשלים על אותה שורה) · מלכודות 33/34 (מבול-לילה שנרפא בפתיחה) · מלכודת 29 (`last_push_age`
אומר **איפה** נשבר, לא **האם**) · §3.6 (**"לא-נבחן" ≠ "עובד"**) · מלכודת 23 (כלל 5 חל על
תיקון בדיוק כמו על טענה — הניסוח הראשון של מלכודת זו **הפריך את האזהרה לפי `mtime` בלבד**
והיה מפרסם ירוק-כזב; מה שעצר אותו היה קריאת הרשומה העליונה ב-`STATUS_BOARD`).

---


**↻ חידוד-דיוק מאותה ריצה (כלל 5, אימות-סגירה):** היסטוגרמת-החשבון שלמעלה מכסה **רק את
השורות הנושאות שדה-`account`**. הספירה המלאה היא `{'None': 2167, '37138283': 1596, 'Sim1': 33}`
— כלומר `2,167` מ-`3,796` השורות (57%) **אינן נושאות שדה-חשבון כלל**, ולכן `1596`/`33` הוא
הפילוח של `1,629` השורות המתוארכות-לחשבון בלבד, לא של הקובץ. ⇒ אל תקרא את `1596` כ-"רוב
הקובץ". **הראיה המכריעה אינה ההיסטוגרמה** אלא שלושת אלה יחד: `today events = 2
{ORDER_REJECT: 2}` · `CLOSED_TRADE_PNL ל-10-07 = 0` · והאחרונה שכן קיימת נושאת
`account 37138283 · is_sim False`. אותה מחלקה כמו מלכודת 31 (לספירה יש משטח, ויש לנקוב בו).

---

### מלכודת 36 · ציר-המרג'ין של [[T-34]] אינו קריא מ-`sierra_state.json` מאז 06.10 — שלושת שדות-החשבון הם סנטינל-DBL_MAX, והמקור הוא לוג-הברוקר (07.10)

‏§3.7 תיעד את הסנטינל (`±1.79e308`) על `high_during_pos`/`low_during_pos` **כשאין פוזיציה**.
זו ההרחבה שלו אל **שדות-החשבון**, שבהם הוא מופיע גם כשהחשבון פעיל לגמרי:

```raw
(07.10 22:08-22:11, נמדד)
sierra_state.json ⇒ acct_available_funds 1.7976931348623157e+308
                    acct_cash_balance    1.7976931348623157e+308
                    acct_margin_req      1.7976931348623157e+308
                    acct_under_margin    0
האזהרה המקבילה, 106 פעמים היום (ו-52 ב-06.10; אפס לפני):
  [MarginSizing] acct_available_funds is a sentinel (1.8e+308) — account data unusable,
  **size left unchanged**
חסימה מתוארכת: הלוג מתחיל 2026-10-02 10:15:02 · אפס סנטינל ב-02/03/05.10 ·
  הראשונה בכלל: שורה 158396 · **2026-10-06 18:39:18**   ⇒ מצב חדש מ-06.10, לא מאז-ומתמיד
```

**מה זה כן אומר, ומה במפורש לא:** `size left unchanged` הוא ניסוח הקוד עצמו ⇒ הסנטינל
**אינו חוסם** ואינו מקטין גודל, והגודל הפסוק נשאר `1` ⇒ **אין מקרה (ג) ואין NO-GO.**
מה שנשבר הוא **המדידה**: בדיקת-`avail < $1,595` של חובה-2 אינה יכולה לרוץ מול
`sierra_state`, ו**חייבת** לרוץ מול לוג-הברוקר — כפי שריצה 250 עשתה
(`avail 278.79` מול `margin needed 288.53`). סוכן שיקרא `1.8e+308` כמספר יקבל
"מרג'ין אין-סופי ⇒ הכול תקין" — **הקריאה ההפוכה מהאמת**, ובכיוון המסוכן.

**וזה אותו שורש של מלכודת 35, מצד שני:** המסחר יושב ב-`Sim1` בעוד שדות-החשבון והסורק
מכוונים לחשבון האחר ⇒ **שני הצרכנים מקבלים "אין נתון" בצורות שונות** (סנטינל כאן, אפס-events
שם). ⇒ כשמופיע אחד מהם, לבדוק את חברו באותה נשימה.

**ההקשר שמסביר את הסנטינל, וגם הוא כבר רשום ⇒ לא לשאול שוב (מלכודת 16):**
```raw
ORDER_REJECT בפיד-הפעילות ⇒ 41 בסך-הכל (07-13 → 10-07) · 2 היום:
  2026-10-07T12:15:43Z  margin needed 288.53   ⇐ 15:15 IL
  2026-10-07T14:52:21Z  margin needed 288.53   ⇐ 17:52 IL   = האחרונה
  "Trade Order Error - Insufficient Account Value (NLV) for margin for order"
כבר ב-LIVE_CHANNEL: ORDER_REJECT ×10 · "288.53" ×8 · "278.79" ×2   ⇒ T-34 דיווח-בלבד
```

⚠️ **ומה שאינו בר-הוכחה, ולכן נרשם כלא-מוכרע (כלל 1):** החשבון המתבקש
*"4 `COMMAND QUEUED` − 2 דחיות = 2 עסקאות-דמו"* **אינו נגזר מהנתון** — כל 41 שורות-ה-
`ORDER_REJECT` נושאות `ts: None` ורק `scan_ts` של הסורק, ושתי דחיות-היום מקדימות שתיים
מארבע פקודות-ה-PLACE (`#404 16:50:09 · #405 18:00:04 · #406 18:15:05 · #407 19:40:06`).
⇒ התאמה אריתמטית מסודרת **אינה** ראיה כשציר-הזמן חסר מעצם התכנון (מלכודת 21).

**קרובי-משפחה:** §3.7 (אותו סנטינל, שדות אחרים) · §3.5 (`daily_pnl` של החשבון אינו של
המערכת) · מלכודת 35 (אותו פיצול-חשבון, הצרכן השני) · מלכודת 18 (ערך-תקף שנקרא כמשמעות
שאין בו) · מלכודת 16 (פסיקה עומדת גוברת על מדידה טרייה).
