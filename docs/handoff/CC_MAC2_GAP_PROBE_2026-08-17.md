# ערכת אבחון-עצמי ל-cc-mac2 — "למה מק-2 לא סוחר" (2026-08-17)

**מאת:** cowork-dev (מק-1, קריאה-בלבד). **אל:** `cc-mac2` (Claude Code על ה-iMac).
**מטרה:** לא האבחון שלי — **הכלים שלך**. כל שלב מחזיר *ראיה שלא ניתן לזייף בשורת-לוג ירוקה*
(ספירת-שורות, קובץ שקיים, חותמת-ACK). אם שלב לא מחזיר ראיה — כתוב **"לא ניתן לקבוע"**, לא "ירוק".

**עובדת-הרקע שמניעה את הכל:** מק-2 לא כתב שורת-trade מאז 2026-07-17.
השורש שאותר (commit `555838df`, כבר ב-`origin`): **Session משותף מורעל**.
`backend/main.py:1076` יוצר `SessionLocal()` אחד ומחלק אותו ל-`TradeManager` +
`BarLevelDetector` + `FillPoller`. כשאחד מהם נכשל בלי `rollback()` — Postgres זורק **כל**
פקודה מאוחרת יותר באותה טרנזקציה. הירי עובר את כל השערים, ואז מת ב-`add()` בשקט.
`pool_pre_ping` לא עוזר: הוא מזהה *חיבור מת*, לא *טרנזקציה מבוטלת על חיבור חי*.

---

## 0. מה נמדד מרחוק ממק-1 (17.08, 03:55–04:05 IDT) — ומה לא

**מק-2 לא נגיש כלל.** ZeroTier של מק-1 תקין (`10.1.118.147/24`, `status OK`), מק-2 לא עונה:

```
$ ping -c 3 -t 8 10.1.118.70
3 packets transmitted, 0 packets received, 100.0% packet loss

$ curl -sS -m 25 -w "\nHTTP=%{http_code}\n" http://10.1.118.70:8000/api/v9/health
curl: (28) Connection timed out after 25005 milliseconds
HTTP=000

$ psql "postgresql://michael@10.1.118.70:5432/mems26?connect_timeout=25" -Atc "select now();"
psql: error: connection to server at "10.1.118.70", port 5432 failed: timeout expired

$ zerotier-cli listnetworks
200 listnetworks 08752e18b1e32b2e Michael 2e:f1:b6:fc:4c:ed OK PRIVATE feth3995 10.1.118.147/24
```

⇒ **health / gateway / arming / max(ts) / v9_trades של מק-2 = "לא ניתן לקבוע" מרחוק.**
(מק-2 כבוי או ישן ב-04:00; מק-1 עצמו תקין — `psql postgresql://localhost/mems26` החזיר
`2026-08-17 03:59:16+03|597` שורות ב-`v9_trades`.)

**בסיס-השוואה ממק-1 (אמת, לא הנחה):**
`HEAD = 17d1815a` על `stabilize/mems26-local-truth-2026-05-16` (מסונכרן ל-origin) ·
תיקון ה-Session = `555838df`, נמצא ב-`origin/stabilize/mems26-local-truth-2026-05-16`
(כלומר **ניתן למשיכה במק-2**).

---

## 1. ערכת האבחון — הרץ **על מק-2**, לפי הסדר, עצור בשלב הראשון שנופל

הכן פעם אחת:

```bash
cd /Users/michael/Downloads/mems26_web_git
PSQL=$(ls /Applications/Postgres.app/Contents/Versions/latest/bin/psql 2>/dev/null || command -v psql)
DB=postgresql://localhost/mems26
SIG=/Users/michael/SierraChart_Data/v9_export
LOG=/tmp/backend.err.log
```

### שלב 0 — האם הקוד עצמו מכיל את התיקון (לפני כל דבר אחר)

```bash
git log --oneline -1
git log --oneline -1 -- backend/v9/db/session_guard.py
grep -n "ensure_clean" backend/v9/services/fill_poller.py \
     backend/v9/services/trade_manager/manager.py \
     backend/v9/gateway/trading_gateway.py
```

* **PASS:** `555838df` (או צאצא) מופיע, ו-`grep` מחזיר **5 מופעים**:
  `fill_poller.py:170` · `manager.py:368` · `trading_gateway.py:3266, 3423, 3605`.
* **הפער כאן:** ה-grep ריק / פחות מ-5 → הצ'קאאוט ישן. `git pull` (ואז **restart** —
  קוד לא נטען חם) ורק אז המשך. **הערה:** גם אם התיקון קיים בקוד, זה לא אומר שהוא *נטען
  לתהליך הרץ* — את זה מוכיח שלב 5א.

### שלב 1 — הפיד: טרי **לפי תוכן**, לא לפי mtime

```bash
$PSQL "$DB" -Atc "SELECT max(ts), now()-max(ts) AS lag, count(*) FROM v9_bars_5min_woodies WHERE ts::date = current_date;"
$PSQL "$DB" -Atc "SELECT count(*) FROM v9_bars_5min_woodies WHERE ts::date=current_date AND (cci_14 IS NULL OR lsma_value IS NULL OR trend_state IS NULL);"
```

* **PASS:** בשעות-מסחר `lag < 00:06:00`, `count` גדל בין שתי הרצות במרווח 5 דק', ושורת
  ה-NULL מחזירה **0**.
* **הפער כאן:** `max(ts)` לא זז בין שתי הרצות → הפיד קפוא (בדוק `/tmp/bridge.err.log`).
* ⚠️ **אל תסיק מ-`v9_bars_5min` (הישנה) ואל תסיק מ-`stream health`.** ב-14.08 הוכח שמונה
  ה-`5min` במק-2 היה קפוא (`push_count=52`) בזמן שהערוץ **חי ומייצר מועמדים** —
  `_record_push` בולע חריגות בשקט (`backend/v9/api/v9/bars.py:221-227`). מונה קפוא ≠ פיד מת.
  גם `build/pattern-status → readiness: BLOCKED` הוא **תצוגה בלבד** ולא חוסם ירי
  (`aggregator.py:246-249`).

### שלב 2 — האם המערכות בכלל מייצרות מועמדים

```bash
curl -s "http://localhost:8000/api/v9/gateway/decisions?limit=200" \
 | python3 -c "import sys,json,collections;d=json.load(sys.stdin);r=d['decisions'];print('total',len(r),'today',d.get('today'));print(collections.Counter((x['system'],x['outcome']) for x in r))"
```

* **PASS:** `total > 0` ויש רשומות מהיום (`ts` של היום). זו הראיה שמערכות S2/S4/TREND_STEP חיות.
* **הפער כאן:** `total = 0` בשעת-מסחר → אף מועמד לא נוצר. חזור לשלב 1, ואז
  `python3 scripts/mems26_arming_gate.py` (ראה שלב 2ב).

### שלב 2ב — דרוך או שבור? (ההבחנה שמייקל ביקש)

```bash
python3 scripts/mems26_arming_gate.py ; echo "EXIT=$?"
```

* **PASS:** `EXIT=0` (ARMED) — או חסימות שכולן **market** (`awaiting_*`).
* **הפער כאן:** חסימות **internal** (`five_min_bar_recency`, `cci_14_history`,
  `mode_context`, `fhb_eligible`, `day_type_known`, `buffer`) → המכונה שבורה, לא ממתינה.
  `EXIT=2` = לא ניתן להעריך — דווח כך, אל תדווח ירוק.

### שלב 3 — מה בדיוק חוסם

```bash
curl -s "http://localhost:8000/api/v9/gateway/decisions?limit=300" \
 | python3 -c "import sys,json,collections;r=json.load(sys.stdin)['decisions'];print(collections.Counter(x['blocked_by'] for x in r if x['outcome']=='blocked').most_common(15))"
```

* **PASS:** ה-`blocked_by` השכיח הוא סיבת-שוק לגיטימית.
* **הפער כאן:** `cold_start_guard` (= לא-הידרטד), `rr_hard_floor` **בכל** המועמדים
  (בדוק IB — ב-14.08 מק-2 ייצא `ib_low` שגוי שהפך ל-T1 והרס R:R), או `blocked_by=null`
  ללא `trade_id` = הירי "עבר" ולא נכתב → **קפוץ ישר לשלב 5**.

### שלב 4 — לאן זה מנותב, ומה `is_sim` באמת

```bash
curl -s http://localhost:8000/api/v9/gateway/status | python3 -m json.tool
grep -a "env_loader" $LOG | tail -1
grep -aiE "MEMS26_MODE|is_sim" $LOG | tail -5
```

* **PASS:** `demo_enabled_systems` / `live_enabled_systems` אינם ריקים; `demo_slot`/`live_slot`
  פנויים; שורת-ה-boot של `env_loader` קיימת ומראה את המצב שאתה חושב שיש.
* **הפער כאן:** רשימת-מערכות ריקה = אין לאן לנתב · סלוט תפוס בלי עסקה חיה = סלוט תקוע.
* ⚠️ **אמת דגלים דרך שורת-ה-`[env_loader]` בלוג — לא דרך `ps eww` ולא מהזיכרון.**

### שלב 5 — האם נכתבה שורת-trade, ואם לא — האם ה-Session מורעל

```bash
$PSQL "$DB" -Atc "SELECT id, mode, state, firing_system, entry_ts, created_at FROM v9_trades ORDER BY id DESC LIMIT 5;"
$PSQL "$DB" -Atc "SELECT max(id) AS max_id, (SELECT last_value FROM v9_trades_id_seq) AS seq_last;"
```

* **PASS:** יש שורה מהיום; `seq_last > max_id` פירושו ש-`add()` כן רץ (גם אם התגלגל אחורה).
* **🔴 החתימה של התקלה:** `decisions` מראה ירי/`duplicate_fire` (= רישום שאחרי כל השערים)
  **אבל** `max_id` לא זז **ו-**`seq_last == max_id` → **`Session.add()` מעולם לא הגיע.**
  זו בדיוק החתימה שהוכיחה את השורש ב-14.08. עבור ל-5א.

---

## 2. פרובה 5א — הוכחת ההרעלה (מבצעת, לא מסקנה)

**(א) האם ה-Session החי מורעל *ברגע זה*** — דרך הבקאנד עצמו, לא דרך חיבור חדש:

```bash
grep -a "session_guard" $LOG | tail -20
grep -ac "poisoned transaction detected" $LOG
```

* **PASS:** אפס שורות `poisoned` **ו**-שלב 5 עבר.
* **הפער כאן:** שורות `[session_guard] poisoned transaction detected in <where>` — ה-`where`
  אומר איפה: `accept_setup` · `FillPoller.run` · `gateway.commit` · `gateway.shadow_commit`.
  אם ה-grep ריק אבל טריידים לא נכתבים — **התהליך הרץ לא טעון את התיקון** (ראה שלב 0):
  restart נדרש.

**(ב) השגיאה **הראשונה** שהרעילה — זה השורש; כל השאר רעש:**

```bash
grep -an -m1 -iE "InFailedSqlTransaction|current transaction is aborted|PendingRollbackError" $LOG
# ואז 60 שורות לפניה — שם יושבת ההצהרה שנכשלה באמת:
FIRST=$(grep -an -m1 -iE "InFailedSqlTransaction|current transaction is aborted" $LOG | cut -d: -f1)
[ -n "$FIRST" ] && sed -n "$((FIRST>60?FIRST-60:1)),${FIRST}p" $LOG
grep -acE "InFailedSqlTransaction|current transaction is aborted" $LOG
```

* **הראיה:** מספר-השורה + 60 השורות שלפניה. **דווח את השגיאה הראשונה, לא את הספירה.**
  (ב-14.08 היו 37 מופעים — כולם צאצאים של אחת.)

**(ג) האם יש session תקוע ב-Postgres (המלכודת של 07-22, PID 28917):**

```bash
$PSQL "$DB" -Atc "SELECT pid, state, wait_event_type, now()-state_change AS idle_for, left(query,120) FROM pg_stat_activity WHERE datname='mems26' AND state <> 'idle' ORDER BY state_change LIMIT 20;"
$PSQL "$DB" -Atc "SELECT count(*) FROM pg_stat_activity WHERE datname='mems26' AND state='idle in transaction' AND now()-state_change > interval '2 minutes';"
$PSQL "$DB" -Atc "SELECT pid, left(query,80), now()-query_start FROM pg_stat_activity WHERE datname='mems26' AND wait_event_type='Lock';"
```

* **PASS:** `idle in transaction > 2min` מחזיר **0**, ואין ממתיני-`Lock`.
* **הפער כאן:** `idle in transaction` ותיק = ה-Session המורעל, והוא גם חוסם `ALTER`/`VACUUM`.
  **אל תריץ `pg_terminate_backend` בעצמך אם יש פוזיציה פתוחה** — דווח את ה-PID ובקש פסיקה.

### שלב 6 — האם הפקודה הגיעה לסיירה (ACK, לא לוג)

```bash
ls -l $SIG/command_queue/ 2>/dev/null | tail -20
ls -l $SIG/trade_command.json $SIG/trade_result.json $SIG/sierra_state.json
python3 -c "import json;print(json.load(open('$SIG/trade_result.json')))"
stat -f "%N mtime=%Sm" -t "%H:%M:%S" $SIG/trade_command.json $SIG/trade_result.json
```

* **PASS:** `command_queue/` **ריק** (הנקז רוקן אותו), ו-`trade_result.json` נושא `r >= 0`
  עם mtime **מאוחר** מ-`trade_command.json` — זו חותמת-ה-ACK.
* **הפער כאן:** קבצי `cmd_*.json` שנערמים ב-`command_queue/` = הנקז לא רץ
  (`FillPoller._drain_command_queue_safe`, `fill_poller.py:192`) → הלולאה מתה או לא הותנעה ·
  `r = -1` ב-`trade_result.json` = ה-DLL דחה · `trade_command.json` שלא מתרוקן = מרוץ-Wine.

### שלב 7 — האם סיירה באמת מחזיקה את הפוזיציה

```bash
python3 -c "import json;d=json.load(open('$SIG/sierra_state.json'));print({k:d.get(k) for k in ('position_qty','account','is_sim','ts')});print('orders',len(d.get('orders',[])))"
tail -5 $SIG/trade_activity_events.jsonl
```

* **PASS:** `position_qty` תואם למה שה-DB חושב, ו-`is_sim` תואם למצב-המסחר בשלב 4.
* **הפער כאן:** DB אומר "עסקה פתוחה" ו-`position_qty=0` → העסקה מדומה. הפוך — פוזיציה
  יתומה. **המפתח הוא `position_qty`, לא `position_quantity`** (לקח 07-23).
  ⚠️ `orders[]` סופר רק `GetOrderByIndex` — bracket-מוחזק לא מופיע שם, אל תכריז "naked"
  בלי הצלבה מול יומן-הפילים.

---

## 3. אסור לך (cc-mac2)

1. **אין restart כשיש פוזיציה פתוחה.** בדוק `sierra_state.json → position_qty == 0` תחילה.
   restart עם פוזיציה חיה = יצירת יתום (מחלקת 07-10/14/17/20/23).
2. **אין שינוי דגלים בלי פסיקה כתובה של מייקל.** `config/RULED_FLAGS.yaml` +
   `python3 scripts/flag_guard.py` הם הזיכרון האוכף. `flag_guard` ירוק ≠ אישור להדליק.
   פסיקה קיימת = לא לבקש שוב; פסיקה חסרה = לא להדליק.
3. **אין הכרזת "אומת" בלי פלט-גולמי מודבק** (כלל 5). "should work" / "confirmed" נפסלים.
4. **אין הסקת ירוק ממה שלא נמדד** (כלל 1) — "לא ניתן לקבוע" היא תשובה לגיטימית ונדרשת.
5. **אין `pg_terminate_backend`, `TRUNCATE`, `ALTER`, או כתיבה ל-DB** כחלק מהאבחון. הכל קריאה.

---

## 4. מה לדווח בחזרה (שורה אחת לכל שלב, ב-LIVE_CHANNEL)

`שלב N — PASS/GAP/לא-ניתן-לקבוע — <הפלט הגולמי, לא פרפראזה>`

השלב הראשון שנופל = הפער. **אל תמשיך לתקן שלבים שאחריו** — הם מציגים תסמינים, לא סיבות
(בדיוק כמו `readiness: BLOCKED` וה-`push_count` הקפוא שהסתירו את השורש ב-14.08).

— cowork-dev, מק-1, 2026-08-17
