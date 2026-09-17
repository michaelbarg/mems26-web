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
עם .env טעון:  ruled_contracts() = 2
```

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

**⚠️ מלכודת-TZ נלווית (אותה ריצה):** ‏`extract(epoch from (now() at time zone 'utc') - max(ts))`
על עמודה **tz-aware** החזיר `-10786` — "הפיד שלוש שעות בעתיד". האמת:
`max(ts)=12:10:00+03` מול `now()=12:10:27+03` ⇒ **הפיד בן 27 שניות.** החיסור ערבב
naive-UTC עם aware-IDT. להשוות aware מול aware (`now()`), או `now() at time zone 'utc'`
מול `max(ts) at time zone 'utc'` — לא לערבב. כלל-4 (TZ בקלט-מפרט) חל גם על
שאילתות-האימות עצמן, לא רק על הקוד.


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
