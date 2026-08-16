# MEMS26 · פרוטוקול פתיחת-יום-מסחר (גרסה 2026-08-16)

**מחליף** את `LIVE_MORNING_PROTOCOL.md` (07-09) ואת `MORNING_RUNBOOK_2026-07-21.md` כרשימת-הביצוע.
`PRE_TRADE_PROTOCOL.md` נשאר כמילון-תקלות; `FIRING_READINESS_PROTOCOL.md` נשאר לאבחון "למה לא ירה".
**כל שלב כאן נגזר מתקרית אמיתית** — הנספח בסוף נותן לכל שלב את התקרית שהוא קיים כדי למנוע.

> **למה הישנים לא מספיקים:** `LIVE_MORNING_PROTOCOL` נועל בטקסט `2 חוזים · עצירת יום −$400` —
> היום `FIXED_CONTRACTS_4=1` ו-`RISK_HALT_V1` על −$450/5d (ופסיקת-6-חוזים בתור). מספר קשיח
> בפרוטוקול הופך לשקר תוך שבוע. **הכלל כאן: אף מספר-מסחר לא נכתב בפרוטוקול — הוא נבדק מול
> `config/RULED_FLAGS.yaml` דרך `flag_guard`.** בנוסף: `MORNING_RUNBOOK_2026-07-21` §6 מורה
> "iMac = Sim מאושר לפני שה-MacBook חמוש" — פסיקת 08-13 מתירה **שתי מכונות LIVE במקביל**;
> הסעיף הזה מיושן ומטעה.

---

## §0 · על איזו מכונה, ואיך מוכיחים — BLOCKING, לפני כל דבר אחר

**כל שלב במסמך רץ על מכונת-המסחר עצמה, בטרמינל אמיתי (Desktop Commander / iTerm).**
**לעולם לא מסנדבוק-Cowork ולא מהמכונה השנייה.** זו מחלקת-כשל שחזרה 5 פעמים (נספח I-7).

```bash
cd /Users/michael/Downloads/mems26_web_git && bash scripts/mems26_fingerprint.sh
```
→ **PASS:** השורה הראשונה `══ MEMS26 fingerprint · <hostname> · <date> ══` — ה-hostname הוא
המכונה שאתה מתכוון לסחור עליה; `FP|git.head` = ה-HEAD שאתה מצפה לו; `FP|study.deployed` תואם.
→ **מדביקים את בלוק ה-`FP|` בראש כל דיווח.** דיווח בלי חותם-פרובננס = לא-דיווח.

**שלושה כללים נגזרים (כל אחד מתקרית):**
1. `UNKNOWN ≡ FAIL`. פקודה שלא רצה, החזירה ריק, או ConnectionRefused — היא **לא** "ירוק".
   *(S6_EOD 07-15 כתב "0 עסקאות · אין ממצאים" ביום-לייב-1 אמיתי, כי רץ בסנדבוק.)*
2. **מספר ממכונה אחרת אינו מדידה.** אין להעתיק יתרה/IB/מצב מהערוץ של המכונה השנייה לתוך
   דיווח של המכונה הזאת. *(preopen 08-13 ציטט יתרת-מק-2 מלפני שעתיים בתוך דוח מק-1.)*
3. **המשימות-המתוזמנות מכוונות למכונה** — לפני שסומכים על watch/EOD, מוודאים שהוא רץ על
   מכונת-המסחר הנוכחית. *(session-watch נשאר מכוון ל-iMac 10+ ימים אחרי המעבר ל-MacBook;
   `MOBILE_REMOTE_URL` הצביע על מכונת-הסים.)*

---

## §1 · ציר-הזמן (שעון IL · פתיחת RTH 16:30 IL = 09:30 ET)

| מתי | שלב | סוג |
|---|---|---|
| T-60 (15:30) | P0 זהות · P1 ספרים ופוזיציה · P2 דגלים | BLOCKING |
| T-45 (15:45) | P3 שירותים ומשטחים · P4 אמת-נתונים · P5 חיוּת-כתיבה | BLOCKING |
| T-30 (16:00) | P6 חימוש-מערכות · P7 שרשרת-החלטה · P8 שרשרת-ביצוע | BLOCKING |
| T-15 (16:15) | P9 ערוץ-התראות · P10 בריפינג + ביקורת-שערים | P9 BLOCKING · P10 ADVISORY |
| T-0 (16:30) | חימוש בסיירה — **מייקל בלבד** | — |
| T+60 (17:30) | P11 נעילת-IB ואימות-מספרים-נגזרים | BLOCKING לפני עסקה שנייה |

**חוק-ריסטארט:** כל ריסטארט חייב להסתיים **לפני 16:30**. ריסטארט אחרי הפתיחה = ראה §4.

---

## §2 · השלבים

### P1 · ספרים, פוזיציה, והזמנות-יתומות — BLOCKING
*(מונע: I-1 משפחת-האורפן-העירום 07-10/14/17/20/23 · I-2 ברקט-דמו שדלף ללייב)*

```bash
python3 - <<'PY'
import json,os,time
p=os.path.expanduser('~/SierraChart_Data/v9_export/sierra_state.json')
d=json.load(open(p))
print('age_s',round(time.time()-os.path.getmtime(p),1),
      '| position_qty',d['position_qty'],'| working_orders',d['working_orders'],
      '| is_sim',d.get('is_sim'),'| armed',d.get('order_placement_armed'),
      '| acct',d.get('trade_account'))
PY
```
→ **PASS:** `age_s < 10` **וגם** `position_qty 0` **וגם** `working_orders 0`.
> ⚠️ קוראים במפתח `d['position_qty']` עם סוגריים — **לא** `.get()`. ב-07-23 כל בדיקות-הערב
> קראו `position_quantity` (מפתח לא-קיים) → `None` → "שטוח" כוזב בזמן ששורט −8 רץ בחשבון.
> `.get()` על שם שהשתנה מחזיר `None` בשקט; `[]` זורק. זו אינה קוסמטיקה.

```bash
curl -s http://localhost:8000/api/v9/agent/sierra_live_check | python3 -m json.tool | head -30
```
→ **PASS:** `"all_ok": true` ו-`"verdict": "🟢 GREEN..."` (כולל `records_eq_reality: TM net=0 vs Sierra qty=0 → MATCH`).

```bash
for f in sierra_state.json trade_state.json trade_activity_events.jsonl trade_fills_journal.jsonl; do
  printf '%s ' "$f"; python3 -c "import os,sys,time;p=os.path.expanduser('~/SierraChart_Data/v9_export/'+sys.argv[1]);print('MISSING' if not os.path.exists(p) else round(time.time()-os.path.getmtime(p))) " "$f"
done
```
→ **PASS:** אף אחד לא `MISSING`, ואף אחד לא ישן מהסשן הקודם.
> ב-07-17 `trade_state.json` **נעלם** מתיקיית-הייצוא → הרקונסיילר עיוור לתוך סוף-שבוע עם −5 עירום.
> ב-07-20 הרקונסיילר נפל ל-`src=events` מקובץ **קפוא מ-07-17** והסיק −3 מדומה.

**הזמנות-יתומות:** כל `working_order` שאין לו הורה ב-`v9_trades` = ברקט שדלף. `working_orders=0` בשטוח סוגר את זה.

### P2 · דגלים — BLOCKING
*(מונע: I-8 החלקת-דגלים · I-9 דגל שלא הוגדר בכלל)*

```bash
python3 scripts/flag_guard.py ; echo "exit=$?"
python3 scripts/gen_flag_index.py --check ; echo "exit=$?"
```
→ **PASS:** `FLAG-GUARD: PASS — all <N> ruled flags match.` + `exit=0`, וגם
`flag index: no undocumented drift.` + `exit=0`.
> **ה-`<N>` הוא המספר של היום** (178 כלל-דגלים ב-`RULED_FLAGS.yaml` נכון ל-08-16) — לא לנעול
> מספר בפרוטוקול. `flag_guard` הוא גם **הוכחת-סנכרון בין המכונות**: אותו N בשתיהן.
> `PHONE_ALERTS_V1` ב-08-12 לא היה "כבוי" — הוא **לא היה מוגדר**; דגל חסר נראה בדיוק כמו
> מערכת עובדת. רק השוואה מול `RULED_FLAGS.yaml` תופסת את זה.

### P3 · שירותים ומשטחים — BLOCKING
*(מונע: I-3 קפיאת-פיד-הברים 06-25)*

```bash
bash scripts/mems26_verify.sh
ls ~/SierraChart_Data/v9_export/*.json.tmp 2>/dev/null | wc -l
pgrep -f v9_export_promoter >/dev/null && echo promoter=UP || echo promoter=DOWN
```
→ **PASS:** `════ verdict: OK · <N> warn ════` + `0` קבצי-tmp תקועים + `promoter=UP`.
> 🔴 **`mems26_verify.sh` לא מפיל את ה-exit על אזהרות.** אי-התאמת-DLL, סחיפת-אינדקס ופיד-מיושן
> כולם `⚠️` בלבד. **חובה לקרוא כל שורת `⚠️` בעין ולהכריע** — "verdict: OK · 3 warn" אינו ירוק.
> `*.json.tmp` תקוע = ה-promoter לא רץ ⇒ `rename()` של Wine לא מחליף קובץ קיים ⇒ ה-`.json` קופא
> בעוד פיד-הטיקים חי ומסווה את זה (06-25: 88% מהסשן ללא נתונים).

### P4 · אמת-נתונים: טריות לפי תוכן, לא לפי mtime — BLOCKING
*(מונע: I-4 מק-1 קפוא-מ-11:10 עם DTC חי · I-6 סטיית-ts 07-20 · I-5 נעילת-PG 07-22)*

```bash
PSQL="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/psql | head -1)"
"$PSQL" postgresql://localhost/mems26 -t -c \
 "SELECT max(ts), now()-max(ts) FROM v9_bars_5min_woodies;"
curl -s localhost:8000/api/v9/health/streams | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['summary']);print([(s['name'],s['status']) for s in d['streams'] if s['name'] in ('5min','woodies_5min','live_price')])"
```
→ **PASS:** ה-`max(ts)` של ה-DB **שווה** לחותמת-התוכן שה-endpoint מדווח (שוויון, לא "שניהם נראים
טריים"), הפער מ-`now()` סביר לשעה, ושלושת ה-streams `healthy`.
> **`summary` עם `green:0` וכל הרשימות ריקות = השירות מעולם לא הוזרק באתחול** — זו ריקנות
> שקטה ש-`arming_gate` קורא כ"אין streams מתים". ריק ≡ FAIL.
> ב-08-13 ה-DLL כתב את הקובץ **כל שנייה** (=כל בדיקת-mtime עברה) בעוד `current_bar` ריק
> ו-`history[-1]` תקוע מ-11:10, וה-backend צעק `TS-OFFSET-GATE non-advancing batch 59400s` ברצף.

```bash
"$PSQL" postgresql://localhost/mems26 -t -c \
 "SELECT ts,count(*) FROM v9_bars_5min_woodies WHERE ts::date=CURRENT_DATE GROUP BY ts HAVING count(*)>1;"
"$PSQL" postgresql://localhost/mems26 -t -c \
 "SELECT pid, now()-xact_start AS age, left(query,60) FROM pg_stat_activity
   WHERE state='idle in transaction' AND now()-xact_start > interval '1 minute';"
"$PSQL" postgresql://localhost/mems26 -t -c \
 "SELECT pid, pg_blocking_pids(pid) FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid))>0;"
curl -sf -m 4 localhost:8000/health >/dev/null && echo health=OK || echo health=TIMEOUT
```
→ **PASS:** אפס שורות בשלוש השאילתות + `health=OK`.
> 07-22: `idle-in-transaction` בן 52 דק' חסם `ALTER TABLE v9_trades`, ובקשת-הנעילה-הבלעדית-בתור
> חסמה **את כל קוראי v9_trades** → ה-backend נתקע 95 דק'. **הכשל הוא תקיעה, לא שגיאה** — לכן
> ה-`-m 4` הוא הסימן, ו-`curl` בלי timeout היה מדווח "בסדר".

### P5 · חיוּת-כתיבה ל-DB — BLOCKING
*(מונע: I-10 מק-2 כתב 0 עסקאות במשך 28 יום מול פרה-אופן ירוק כל בוקר)*

```bash
"$PSQL" postgresql://localhost/mems26 -t -c \
 "SELECT max(entry_ts::date), count(*) FILTER (WHERE entry_ts::date=CURRENT_DATE) FROM v9_trades;"
grep -ac "InFailedSqlTransaction" /tmp/backend.err.log
```
→ **PASS:** התאריך האחרון הוא יום-המסחר הקודם (על מכונה שאמורה לסחור), **וגם** ספירת
`InFailedSqlTransaction` = `0`.
> ספירה > 0 = הסשן המשותף מורעל. Postgres זורק כל פקודה בטרנזקציה שנכשלה, ולכן **כל כתיבה
> מאוחרת מתה בשקט**. `pool_pre_ping` כבר דלוק ולא תופס את זה — הוא מזהה חיבור מת, לא טרנזקציה
> מבוטלת. זה הכשל שגרם למק-2 לעבור flag_guard/verify/fire_drill/arming_gate **ולא לרשום שורה
> אחת ב-28 יום**: אף אחת מהבדיקות לא כותבת בייט.

### P6 · חימוש-מערכות — BLOCKING
*(מונע: I-11 S2 מת-על-מכונה-נקייה · I-12 זריעת-day_type שנבלעה 3 שבועות)*

```bash
python3 scripts/mems26_arming_gate.py --preopen ; echo "exit=$?"
curl -s localhost:8000/api/v9/day_type/state | python3 -c "import sys,json;print(json.load(sys.stdin)['state'])"
```
→ **PASS:** `══ ✅ ALL SYSTEMS ARMED ══` + `exit=0` (S1/S2/S3/S4 עם `broken=0`), ו-`state` קיים
עם שדות מלאים. `day_type: UNKNOWN` **לפני** הפתיחה תקין; `UNKNOWN` **אחרי** נעילת-IB אינו.
> `flag_guard`=דגלים · `verify`=שירותים · `fire_drill`=מסלול — **אף אחד מהם לא בדק אם התבניות
> חמושות.** `arming_gate` נבנה בדיוק בלילה שבו מק-2 ישב יום-לייב בחוץ עם 14/14 תבניות מתות
> על `five_min_bar_recency` (הקוד קרא את הטבלה **הישנה** `v9_bars_5min`, שהייתה ריקה במכונה
> נקייה ומלאת-שאריות במכונה הוותיקה — "עובד על המלוכלכת, מת על הנקייה").

### P7 · שרשרת-החלטה — BLOCKING
*(מונע: I-13 `le=3` בלע כל ירי-S2 ביום-לייב-1)*

```bash
python3 scripts/fire_drill.py ; echo "exit=$?"
```
→ **PASS:** `🟢 GO — כל שרשרת ההחלטה כשרה לירי.` + `exit=0`, ובגוף הפלט
`effective_contracts` **שווה למספר שנפסק ב-`RULED_FLAGS.yaml`** (לא למספר במסמך הזה).
> 07-15: סכמת `T1Setup` הגבילה `sizing_contracts` ל-`le=3` בעוד `FIXED_CONTRACTS_4=1` →
> `ValidationError` נבלע ב-`except` → `route_setup` לא נקרא → **0 עסקאות-S2 חיות כל היום**,
> כולל שלוש תבניות ב-`conf=1.00`. אי-התאמה בין הסייז הפסוק לסייז שה-drill מודד = NO-GO.
> ⚠️ אל תסתמך על `mems26_preflight.sh` כתחליף: הוא בודק `fire_drill | tail -1 | grep GO`,
> ובכשל השורה האחרונה היא כדור-כשל שעלול להכיל "GO"; והוא קורא `day_type` מהשורש במקום
> מ-`["state"]` ולכן מדפיס `?` ומדווח ✅ — שני ירוקים-שקריים ידועים.

### P8 · שרשרת-ביצוע — BLOCKING אחרי כל deploy/ריסטארט, אחרת ADVISORY
*(מונע: I-14 שלושת מסלולי-ה-FLATTEN שזרקו TypeError · I-15 הצפת MODIFY_STOP)*

בסיירה ב-**Sim** בלבד, מחוץ ל-RTH: `PLACE` → ACK עם `parent_id/target_id/stop_id` →
`FLATTEN_ACCOUNT` → `position_qty=0`.
→ **PASS:** `{"status":"ORDER_SUBMITTED",...}` **וגם** `qty=0` אחרי FLATTEN, **וגם** אפס
`ORDER_FAILED` ואפס קבצי-תור שפגו.
> עד 08-16 שלושת מסלולי-היציאה — `MAE_SCRATCH`, `TARGET_APPROACH_REALIZE`, **וכפתור-החירום
> בטלפון** — העבירו `trade_id` בתוך `context` בעוד `write_trade_command` מכריז עליו
> keyword-only-חובה ⇒ `TypeError` **לפני שנכתב בייט**. #682 נרשם CLOSED/$0 בעוד סיירה החזיקה
> −4 במשך 58 דקות. **התיקון הקודם (08-15) נכשל כי הטסטים היו `inspect.getsource` — טקסט,
> לא ביצוע.** מכאן הכלל: **בדיקה שלא הריצה את נתיב-הייצור וראתה מוטציה (קובץ שנכתב, שורה
> שנוספה, ACK שחזר) אינה ראיה.**

### P9 · ערוץ-התראות — BLOCKING
*(מונע: I-16 האורפן של 08-12 — −$229 כי אף התראה לא יצאה)*

לשלוח פוש-בדיקה דרך **נתיב-הייצור** (`phone_alert.push`, לא `ntfy_notify` ישירות).
→ **PASS:** קבלה `{"status":1,"request":"<uuid>"}` **מודבקת בדיווח**, והכותרת נושאת את
`MACHINE_TAG` הנכון.
> 08-12: המערכת זיהתה נכון פוזיציה זרה, הציבה סטופ-וירטואלי נכון, צעקה נכון פעמיים
> `Decide manually` — ולא הצליחה לספר לאף אחד. הפוזיציה נסגרה ב-−$228.75 ומחקה את היום.
> **ערוץ לא-מאומת = "Decide manually" ללא נמען = אי-החלטה.**

### P10 · בריפינג + ביקורת-שערים — ADVISORY
```bash
python3 scripts/gate_profit_audit.py          # איזה שער חסם מנצחים לאחרונה
python3 scripts/replay_day.py --date <יום-המסחר-הקודם>
```
→ מחפשים: **שער עם 0 מעברים אי-פעם** = מתג-כיבוי מוסווה כמסנן, לא פילטר.
> `OPENING_DIR_FUSION` עבר **0 פעמים בכל חייו** כי `opening_vol` קרא מפתח שלא קיים (2,212 מול
> 89,246 אמיתי). `OPENING_CONF_ENGINE_FUSE_V1` מגודר על `conf>=0.5` — בדיוק המספר שהוא בא
> להחליף (catch-22). `OPENING_FIRST_TRADE_STRICT` עלה $227.50 ביום אחד. **שער ב-0 מעברים
> הוא ממצא, לא רעש.**
> ⚠️ `replay_day.py` דיווח "0 patterns" במשך יומיים כי שאל **SQLite מושחת** במקום Postgres,
> ועל בסיס זה נכתב "S2 לא ייצר את הלונג" — האבחון של יום שלם היה הפוך. תמיד לוודא שהוא
> על `DATABASE_URL=postgresql://localhost/mems26`.

### P11 · נעילת-IB ומספרים-נגזרים (T+60) — BLOCKING לפני העסקה השנייה
*(מונע: I-17 IB שגוי במק-2 → R:R קטלני → 0 עסקאות)*

→ **PASS:** `ib_high/ib_low/ib_width` מה-API **שווים** ל-IB שעל צ'ארט-Sierra (±טיק), **וגם**
שווים לנגזר מ-12 ברי-ה-RTH הראשונים. ב-two-machine: זהים בשתי המכונות.
> 08-14: הצ'ארטבוק של מק-2 ייצא IB באיחור של שעה — `ib_width 7.0` מול 17.0 במק-1. מנגנון:
> ה-snapper מצמיד את T1 ל-`ib_low`, ולכן IB צר קורס את `T1_dist` ל-0.50 בעוד `stop_dist`
> נשאר 5.25 → `rr_hard_floor` על **בדיוק העסקה שמק-1 לקחה**. הפרה-אופן היה ירוק:
> 173/173 דגלים, ALL SYSTEMS ARMED, fire_drill GO — **כי הוא השווה דגלים ושירותים,
> ואף פעם לא את המספרים שהשערים באמת צורכים.**

---

## §3 · כלל-הביטול: מה הופך את היום ל-NO-TRADE (מוכרעים לפני 16:30, לא מתווכחים אחרי)

יום הוא **NO-TRADE** אם אחד מאלה נכון ב-T-15:

1. **פוזיציה פתוחה או הזמנה עובדת** שאינה מוסברת (P1). לעולם לא מתחילים יום עם פוזיציה.
2. **פיד-ברים לא מוכיח התקדמות-תוכן** (P4) — גם אם הקובץ נכתב וגם אם המחיר חי.
3. **`InFailedSqlTransaction > 0` או `idle-in-transaction` פעיל** (P4/P5).
4. **`flag_guard` לא PASS**, או ה-N שונה בין המכונות (P2).
5. **`arming_gate` לא `ALL SYSTEMS ARMED`** או `broken>0` באחת המערכות (P6).
6. **`fire_drill` NO-GO**, או `effective_contracts` ≠ הסייז הפסוק (P7).
7. **ערוץ-ההתראות לא החזיר קבלה** (P9).
8. **בדיקה כלשהי לא רצה / החזירה ריק / רצה מהמכונה הלא-נכונה** — `UNKNOWN ≡ FAIL` (§0).

**NO-TRADE = לא מחמשים.** לא "נסחר קטן", לא "נראה איך זה הולך". התיקון קורה אחרי הסגירה.
אם התגלה כשל אחרי החימוש — `FLATTEN_ACCOUNT` (לעולם לא `op=EXIT` חלקי), ואז אבחון.

---

## §4 · בתוך הסשן — מותר ואסור

**אסור (כל אחד מגובה בתקרית):**
- **ריסטארט-backend אחרי הפתיחה.** `COLD_START_GUARD_V1` דורש `bars_processed_today >= 3`
  (`trading_gateway.py:826-833`, מונה פר-תהליך שמתאפס), ולכן כל ריסטארט = **~15 דקות
  חלון-עיוור fail-closed**. ב-08-13 ריסטארט של 18:40 חסם 12 מועמדים עד סוף הסשן. בנוסף,
  ריסטארט באמצע השעה הראשונה מוחק את ה-FHB ומעוור את S2 (מק-2, 17:00→17:57).
  אם ריסטארט בלתי-נמנע: להריץ `bash scripts/post_restart_verify.sh` → `🟢 GREEN`, **ולהצהיר
  במפורש על חלון-העיוורון** עד ש-`bars_processed_today >= 3`.
- **reload של ה-DLL בשעות-מסחר.** ה-reload של 17:41 ב-06-25 הוא מה שהפעיל את קיפאון-הייצוא;
  ב-07-15 reload החזיר את `Trade-Sim` ל-OFF בשקט (`is_sim 1→0`) בעוד החימוש נשאר.
- **הדלקה/כיבוי של דגל תוך-כדי מסחר** ללא פסיקת-מייקל כתובה. שינוי משטח-סיכון = snapshot +
  ריסטארט-בשטוח + `flag_guard` — כלומר לא באמצע סשן.
- **שינוי-קוד תוך-כדי מסחר.** נקודה.
- **`op=EXIT` חלקי** — שבור מהיסוד (`r=-1`), לפי `CLAUDE.md`. יציאה ידנית = `FLATTEN_ACCOUNT`.

**מותר:**
- קריאה, מדידה, `decision_replay`, צילום-ראיות.
- `FLATTEN_ACCOUNT` (מלא) בכל רגע.
- `kill_switch` / PAUSE.
- **חימוש בסיירה — מייקל בלבד.** אף סוכן לא מחמש.

---

# נספח · טבלת-התקריות (הראיה שכל שלב נשען עליה)

| # | תאריך | מה מייקל ראה | שורש (מנגנון) | מה היה תופס לפני הפתיחה | קיים היום? |
|---|---|---|---|---|---|
| I-1 | 07-10/14/17/20/23 | "המערכת אומרת שטוח" בעוד סיירה מחזיקה −3…−9 בלי סטופ | הרקונסיילר **מדווח ולא מיישר** (`sierra_position_reconciler.py:246-256`); `phantom-heal` מכסה רק את ההיפוך והמונה ננעל 0/3 על כל `sierra_qty!=0`; `ORPHAN_AUTO_STOP_V1=0` חסום על `is_sim=0` | P1 — `sierra_state['position_qty']`/`working_orders` + `sierra_live_check` | ✅ P1 |
| I-1b | 07-23 | כל בדיקות-הערב + דריל-P8 החזירו GO | הבדיקות קראו `position_quantity` — מפתח **לא-קיים** → `None` → "שטוח" כוזב | P1 — קריאה ב-`[]` ולא `.get()`; יש טסט-רגרסיה + grep על `position_quantity` | ✅ P1 |
| I-2 | 07-14 | החשבון מחזור `0→+3→0→−3` עם 0 שורות ב-`v9_trades` | ברקט של עסקת-"דמו" (order 8945) **דלף לחשבון-הלייב**; הרשומה נוקתה כ-phantom אבל ההזמנה נשארה חיה בסיירה | P1 — `working_orders=0` בשטוח; כל working-order בלי הורה ב-DB = דליפה | ✅ P1 |
| I-3 | 06-25 | הפיד מת ב-09:40 CT, 88% מהסשן ללא נתונים; פיד-הטיקים נראה חי | `std::rename()` תחת Wine **יוצר אך לא מחליף** קובץ קיים → כל promotion של `.tmp→.json` נכשל אחרי הכתיבה הראשונה; `live_price` נכתב ישירות ולכן הסווה | P3 — `promoter=UP` + `*.json.tmp` = 0 | ✅ P3 |
| I-4 | 08-13 | מק-1: מחיר חי, קובץ נכתב כל שנייה — ואפס ברים חדשים מ-11:10 | הצ'ארט הפסיק לעדכן ברים; `current_bar` ריק ו-`history[-1]` תקוע בעוד ה-mtime מתקתק. `TS-OFFSET-GATE non-advancing 59400s` ברצף | P4 — טריות לפי **תוכן** מול `MAX(ts)` ב-DB, לא לפי mtime | ✅ P4 (נתפס — מק-1 קיבל NO-GO) |
| I-5 | 07-22 | `/health` מחזיר כלום; ה-backend חי ותקוע 95 דק' | `idle-in-transaction` בן 52 דק' חסם `ALTER TABLE v9_trades`; בקשת ACCESS-EXCLUSIVE בתור חסמה ראש-תור את כל הקוראים. שורש-עומק: `read.py` השתמש במנוע-הראשי ⇒ BEGIN מרומז על כל SELECT | P4 — `pg_stat_activity` + `pg_blocking_pids` + `curl -m 4` (הכשל הוא **תקיעה**, לא שגיאה) | ✅ P4 |
| I-6 | 07-20 | תווית `Neutral_Extreme` בעוד הצ'ארט מראה Variation→Trend-down | ה-backend כתב את כל ברי-ה-RTH **שעה מוקדם**, מתחת לחלון-התיקון ⇒ לא-הוזז ולא-נדחה ⇒ "12 הברים הראשונים" היו השעה השנייה ⇒ `S1_IB_SANITY_V1` פסל את ה-IB הנכון | P4 — כפילויות-ts + רציפות; `TS_OFFSET_INGEST_GATE_V1=1` (דחייה כנה, בלי ניחוש-הזזה) | ✅ P4 + דגל |
| I-7 | 07-15/16/17/18/19 · 08-13/14 | דוחות "0 עסקאות · אין ממצאים" ביום-לייב אמיתי; watch מכוון למכונה הלא-נכונה; טלפון מצביע על מכונת-הסים | סקריפט רץ **מסנדבוק/מכונה אחרת**; `localhost:8000` הוא ה-localhost של הסנדבוק. `MOBILE_REMOTE_URL` נשאר על ה-iMac אחרי המעבר | §0 — `mems26_fingerprint.sh` כחותם-פרובננס; `UNKNOWN ≡ FAIL`; אימות יעד-המשימות-המתוזמנות | ✅ §0 (משמעת, לא נאכף בקוד) |
| I-8 | שוטף | דגל "אמור להיות דלוק" ואינו | סחיפה בין `.env` לפסיקה | P2 — `flag_guard` + `gen_flag_index --check` | ✅ P2 |
| I-9 | 08-12 | אזעקת-אורפן צעקה פעמיים, אף פוש לא יצא | `PHONE_ALERTS_V1` **לא היה מוגדר כלל**; `phone_alert` קרא שמות-env לא-קיימים; SSL של urllib שבור | P2 (דגל חסר ≠ דגל כבוי) + P9 (קבלה) | ✅ P2+P9 |
| I-10 | 07-17→08-14 | מק-2 ירוק כל בוקר, 17 מועמדים ב-08-14 — ו-0 שורות ב-`v9_trades` **28 יום** | סשן משותף אחד ל-TradeManager+BarLevelDetector+FillPoller (`main.py:1076`); ברגע שנכשל בלי rollback, PG זורק כל פקודה בטרנזקציה ⇒ כל כתיבה מתה בשקט. `pool_pre_ping` מזהה חיבור מת, לא טרנזקציה מבוטלת | P5 — `max(entry_ts::date)` + ספירת `InFailedSqlTransaction` | ✅ P5 (בדיקה חדשה) |
| I-11 | 08-13 | מק-2: 14/14 תבניות S2 חסומות `five_min_bar_recency` בזמן שהפיד חי | בדיקת-הטריות **וטעינת-הבאפר** קראו את הטבלה הישנה `v9_bars_5min` (הוחלפה ב-`_woodies`) — ריקה במכונה נקייה, מלאת-שאריות בוותיקה | P6 — `arming_gate` (`broken=0`), שמפריד חסימה-פנימית מהמתנה-לשוק | ✅ P6 |
| I-12 | 07-22→08-13 | `day_type=UNKNOWN` אחרי כל ריסטארט, 3 שבועות | `classify_session` יובא ממודול שגוי ⇒ `ImportError` בכל בוט, נבלע כ-"non-fatal" ⇒ חצי מהשערים עיוורים | P6 — `day_type/state` מלא + `arming_gate` | ✅ P6 |
| I-13 | 07-15 | "אין עסקאות לא בדמו ולא בלייב" ביום-לייב-1 | סכמת `T1Setup` `le=3` מול `FIXED_CONTRACTS_4` ⇒ `ValidationError` נבלע ⇒ `route_setup` לא נקרא | P7 — `fire_drill` שמודד `effective_contracts` דרך הסכמה, מול הסייז הפסוק | ✅ P7 |
| I-14 | 08-14 | "המערכת דיווחה על מימוש ובפועל לא בוצע בסיירה"; #682 CLOSED/$0 מול −4 חי 58 דק' | `write_trade_command` מכריז `trade_id` keyword-only-חובה; שלושת המסלולים (כולל **כפתור-החירום**) העבירו אותו ב-`context` ⇒ `TypeError` לפני כתיבה. תיקון 08-15 נכשל כי הטסטים היו `inspect.getsource` | P8 — דריל שמריץ את הכותב מול תיקיית-signals אמיתית ובודק שנוצר קובץ | ✅ P8 + `EXIT_VERIFY_V1=1` |
| I-15 | 08-14/16 | הצפת-פקודות; FLATTEN שמאחוריו פג בתור | `stop_not_at_be` פלט `MODIFY_STOP` בלי לכתוב חזרה את `trade.stop` ⇒ ההפרה נשארת ⇒ 393 פקודות זהות, 110 קבצי-תור פגו | P8 — ספירת פקודות-תור פגות = 0 | ✅ (תוקן 08-16, dedup 60s) |
| I-16 | 08-12 | היום האוטונומי הראשון (+$73.75) הסתיים ב-−$155 בחשבון | פוזיציה ידנית 6c לא-מנוהלת + שרשרת-ההתראות מתה (I-9) ⇒ `Decide manually` בלי נמען ⇒ −$228.75 | P1 + P9 | ✅ |
| I-17 | 08-14 | מק-2 לא לקח את העסקה שמק-1 לקחה | הצ'ארטבוק ייצא IB באיחור שעה: `ib_width 7.0` מול 17.0; ה-snapper מצמיד T1 ל-`ib_low` ⇒ `T1_dist 0.50` מול `stop_dist 5.25` ⇒ `rr_hard_floor` | P11 — השוואת IB מול הצ'ארט **ומול 12 הברים הראשונים**, ובין המכונות | ✅ P11 + `IB_BARS_VALIDATE_V1` |
| I-18 | 08-13 | ריסטארט 18:40 → 12 מועמדים נחסמו עד סוף הסשן | `COLD_START_GUARD_V1` fail-closed על `bars_processed_today < 3`; המונה פר-תהליך ומתאפס בריסטארט | §4 — איסור ריסטארט אחרי הפתיחה; אם נכפה — הצהרת חלון-עיוורון | ✅ §4 (משמעת) |
| I-19 | 08-13/14 | מנצחים בפתיחה נחסמו: ZLR LONG 16:34 (+12נק'), DRIVE SHORT 16:50 ($207.50) | `EARLY_BIAS` חושב מבר-הפתיחה **המתהווה** ולא-רוענן בסגירה; `opening_type_gate` נשאר ער כל היום כי `ib_locked` לא הגיע מה-TPO; `OPENING_CONF_ENGINE_FUSE_V1` מגודר על המספר שהוא בא להחליף | P10 — census של שערים: **0 מעברים אי-פעם = מתג-כיבוי** | 🟡 חלקי (P10 ADVISORY; H14/H23 פתוחים) |
| I-20 | 08-13/14 | `replay_day` דיווח "0 patterns" → אבחון הפוך של יום שלם | הסקריפט שאל **SQLite מושחת** במקום Postgres (חוסר `DATABASE_URL`) | P10 — לוודא מקור-נתונים לפני שסומכים על replay | ✅ (תוקן `a0272896`) |
| I-21 | 08-16 | P&L שגוי, `RISK_HALT` נדלק מאוחר | `contract_exits` נבנה תמיד כ-3 רגליים ואז `[:n]` — חיתוך 3 ב-`[:4]` מחזיר 3 ⇒ **25% מה-P&L נעלם ב-102 עסקאות**; ב-6 חוזים היה מסתיר 50% | ADVISORY: השוואת P&L של הספרים מול **יומן-הברוקר** ב-EOD | ✅ (תוקן `1f2f2167`) |

---

**תחזוקה:** כל תקלת-בוקר חדשה מתווספת כשורה בנספח **ובשלב שהיה אמור לתפוס אותה**.
פרוטוקול בלי תקרית מאחורי הצעד = צעד שיימחק בהזדמנות הראשונה.
