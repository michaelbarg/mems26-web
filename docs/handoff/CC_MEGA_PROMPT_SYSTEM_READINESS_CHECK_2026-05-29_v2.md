# MEGA-PROMPT v2 — MEMS26 System Readiness Check (S1 · S2 · S4)

> **תיקון 2026-05-29:** גרסה זו מתוקנת לסכמה **האמיתית** של `data/mems26_local.db`.
> הגרסה הקודמת הניחה עמודות שלא קיימות (`session_date`, `lock_state`, `ib_source`,
> `v9_session_meta.id`). השמות הנכונים, וכל הממצאים מ-Phase A של 29-05, מוטמעים כאן.
> **חובה להריץ על ה-Mac** (לא ב-sandbox) — רק שם נגישים `localhost:8000`, `/tmp`,
> ו-`~/SierraChart_Data`.

**לשימוש בשלוש נקודות זמן:**
- **PHASE A — לפני מסחר** (לפני 09:30 ET): לפחות 15 דקות לפני פתיחה
- **PHASE B — תוך כדי מסחר** (09:30–16:00 ET): כל שעה, במיוחד אחרי 10:30 (IB lock)
- **PHASE C — סוף מסחר** (אחרי 16:00 ET): ניתוח יום + אימות archive

**הורה ל-CC:** קרא הפרומפט הזה במלואו, בצע **כל** הפקודות לפי השלב הרלוונטי, הדפס
OUTPUT גולמי מכל פקודה, וסיים בטבלת `PASS / FAIL / WARN` מפורטת. אל תסמוך על
זיכרון — הרץ הכל מחדש ו**הדבק פלט גולמי** (כלל אימות CLAUDE.md §5).

---

## הבדלי סכמה קריטיים מול הגרסה הקודמת (קרא קודם!)

| נושא | הנחה שגויה (v1) | מציאות (v2) |
|------|-----------------|-------------|
| טבלת day-type | `v9_day_type_history.session_date` | העמודה היא **`date`** |
| מצב נעילה | `lock_state` | העמודה היא **`status`** (ערכים: `PENDING`, `LOCKED`, `LOCKED_LOW_CONF`) |
| סטטוס rollover | `status='ROLLED_OVER'` בשורת אתמול | **לא קיים** ערך כזה. rollover נרשם ב-`v9_session_meta` (key=`last_rollover_date`) |
| מקור IB | עמודה `ib_source` | **לא קיימת**. הסינתזה נמדדת ע"י `v9_bars_5min.is_synthetic` |
| ביטחון | `conf` | העמודה היא **`confidence`** |
| session_meta | טבלה עם `id` | טבלת **key/value** (`key`, `value`, `updated_at`) |
| state חי של S1 | — | קיימת `v9_day_type_state` (stage, lock_state, ts UTC) — מקור חי טוב |
| state של S2 | — | קיימת `v9_five_min_state` (session_date, mode, opening_type, choppiness_score, last_processed_ts) — **הייתה ריקה ב-Phase A** |
| trades open | `state IN ('FILLED','PARTIAL','OPEN')` | ערכים בפועל: **`CLOSED`, `PARTIAL`** בלבד |
| TS של 5min bars | נחשב age תקין | `v9_bars_5min.ts` **naive (ללא TZ)** → age יוצא שלילי מול UTC. הווודיז כן UTC נקי |

**שתי נורות מ-Phase A 29-05 לעקוב אחריהן:**
1. **12 עסקאות במצב `PARTIAL`** ב-`v9_trades` לפני פתיחה — לאמת שזה מכוון ולא state לא-מסונכרן.
2. **TZ ambiguity ב-`v9_bars_5min.ts`** — מפר את CLAUDE.md Rule 4. לפנות את המרת הגבול.

---

## 0. BOOTSTRAP — סביבה ומצב בסיסי

```bash
cd /Users/michael/Downloads/mems26_web_git

# 0.1 — backend פעיל
curl -s http://localhost:8000/health | python3 -m json.tool
# ציפייה: {"status":"ok",...}

# 0.2 — sot_health (בסיס לכל שלב)
python3 scripts/sot_health.py --strict 2>&1 | head -80

# 0.3 — שעה ET + IL + שלב
python3 -c "
from zoneinfo import ZoneInfo
from datetime import datetime
et=datetime.now(ZoneInfo('America/New_York')); il=datetime.now(ZoneInfo('Asia/Jerusalem'))
m=et.hour*60+et.minute
print(f'ET: {et:%Y-%m-%d %H:%M:%S %Z}'); print(f'IL: {il:%Y-%m-%d %H:%M:%S %Z}')
print(f'RTH: {\"YES\" if 9*60+30<=m<16*60 else \"NO\"}')
print('PHASE:', 'A' if m<9*60+30 else ('B' if m<16*60 else 'C'))
"
```

**שגיאות שאסור לראות:** `API push FAILED to https://` (bridge לענן → עצור!); `MISSING` ב-sot_health; backend לא עונה.

---

## 1. S1 — DAY TYPE

### 1.1 DB State — שורות פעילות

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
SELECT date, day_type, opening_type, ib_width_class, status, confidence,
       ib_high, ib_low, substr(last_updated_at,1,19) AS updated
FROM v9_day_type_history
WHERE status NOT IN ('ROLLED_OVER')   -- (אין כיום ROLLED_OVER; משאיר לתאימות עתידית)
ORDER BY date DESC
LIMIT 5;
SQL
```

**PHASE A:** ציפייה: שורת היום עם `status=PENDING`, `day_type=UNKNOWN`, `ib_high/ib_low=NULL`.
**אסור:** שורת היום כבר `LOCKED` לפני חלון ה-IB.

**PHASE B (אחרי 10:30):** ציפייה: שורת היום `status` מתחיל ב-`LOCKED` (`LOCKED`/`LOCKED_LOW_CONF`), `day_type != UNKNOWN`, `ib_high/ib_low` לא NULL.

**PHASE C:** שורת היום `LOCKED*`, ו-`last_rollover_date` (ראה 1.2) עדיין = היום.

### 1.2 Rollover — דרך session_meta (לא דרך status!)

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
SELECT key, value, substr(updated_at,1,19) AS updated
FROM v9_session_meta
WHERE key = 'last_rollover_date';
SQL
```

**PASS (כל השלבים):** `value` == תאריך היום ET. זהו אות ה-rollover הקנוני — **אין** להסתמך על `status='ROLLED_OVER'`.

### 1.3 Live state — v9_day_type_state

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
SELECT id, substr(ts,1,19) AS ts_utc, stage, day_type, classification,
       confidence, ib_width_class, opening_type, lock_state
FROM v9_day_type_state
ORDER BY id DESC
LIMIT 1;
SQL
```

**בדוק:** `ts` עדכני (UTC, פחות מ-2 דקות ב-RTH); `stage`/`lock_state` עקביים עם 1.1
(PHASE A: stage מוקדם כמו `A2`, lock_state=`PENDING`).

### 1.4 API Endpoint

```bash
curl -s http://localhost:8000/api/v9/day_type/v9/current | python3 -m json.tool
```

**בדוק:** `session_date`/`date` == היום ET; `day_type` תואם DB; אחרי 10:30 — `ib_high/ib_low` לא None.
אם ה-API מחזיר שדה `ib_source` — ציפייה `sierra_study` (לא `derived`/`missing`).

### 1.5 IB Consistency (3 מקורות)

```bash
python3 << 'PY'
import sqlite3, json, urllib.request
DB="/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
db=sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
row=db.execute("""SELECT ib_high, ib_low, ib_width, ib_width_class
  FROM v9_day_type_history WHERE status NOT IN ('ROLLED_OVER')
  ORDER BY date DESC LIMIT 1""").fetchone()
print(f"DB IB: high={row[0]} low={row[1]} width={row[2]} class={row[3]}")
def get(ep):
    try:
        return json.loads(urllib.request.urlopen("http://localhost:8000"+ep,timeout=3).read())
    except Exception as e: return {"_err":str(e)}
t=get("/api/v9/tpo/current");  k=get("/api/v9/key_levels")
print(f"API /tpo/current: high={t.get('ib_high')} low={t.get('ib_low')} found={t.get('ib_found')} src={t.get('ib_source')}")
print(f"API /key_levels:  high={k.get('ib_high')} low={k.get('ib_low')}")
PY
```

**PASS:** DB == /tpo == /key_levels (אחרי lock). **FAIL:** ערכים שונים → סתירה, עצור.
**PHASE A:** IB עדיין NULL/None לפני 10:30 — זה תקין, לא FAIL.

---

## 2. S2 — FIVE-MIN PATTERN SYSTEM

### 2.1 Bar Buffer Freshness + TZ guard

> ⚠️ `v9_bars_5min.ts` הוא **naive (ללא TZ)** — חישוב age מול `'now'` (UTC) עלול לצאת
> שלילי. לכן בודקים גם age גולמי וגם השוואה ל-`last_processed_ts` של S2.

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
SELECT ts,
       round((julianday('now') - julianday(ts)) * 86400) AS age_s_naive,
       symbol, close, is_synthetic
FROM v9_bars_5min
ORDER BY ts DESC
LIMIT 3;
SQL
```

**PHASE A:** bar אחרון קיים מהבוקר (Globex). **PHASE B:** ה-bar האחרון צריך להיות מה-5 דקות
האחרונות. אם `age_s_naive` יוצא שלילי או ענק → **WARN: TZ ambiguity (CLAUDE.md Rule 4)** —
ודא איזו TZ נכתבת ל-`ts` והאם יש המרת גבול. אל תסמוך על age גולמי כל עוד ה-TZ לא נעוץ.

### 2.2 Synthesis Guard (is_synthetic — מחליף את ib_source)

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
SELECT is_synthetic, COUNT(*) AS n
FROM v9_bars_5min
GROUP BY is_synthetic;
SQL
```

**PASS:** כל השורות `is_synthetic=0`. **FAIL:** שורות עם `is_synthetic=1` ב-RTH → סינתזה אסורה.

### 2.3 S2 State + Day Type Hydration

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
SELECT session_date, mode, opening_type, choppiness_score,
       substr(last_processed_ts,1,19) AS last_proc, substr(updated_at,1,19) AS upd
FROM v9_five_min_state
ORDER BY rowid DESC
LIMIT 1;
SQL

# חצי השני דרך ה-API (אם רץ):
curl -s http://localhost:8000/api/v9/status | python3 << 'PY'
import sys, json
d=json.load(sys.stdin)
s2=d.get("systems",{}).get("five_min", d.get("five_min",{}))
print("S2 mode:", s2.get("mode","?"))
print("S2 current_day_type:", s2.get("current_day_type","NOT_IN_STATUS"))
print("S2 bar_count:", s2.get("bar_count","?"))
print("S2 last_bar_ts:", s2.get("last_bar_ts","?"))
PY
```

> ℹ️ ב-Phase A של 29-05 הטבלה `v9_five_min_state` הייתה **ריקה** — סביר ש-S2 מתמלא רק
> בפתיחה. לכן ריקנות לפני 09:30 = WARN ולא FAIL; ריקנות אחרי הפתיחה = FAIL.

**PASS:** `mode` תקין ל-RTH + `current_day_type != None` אחרי פתיחה.
**WARN:** `current_day_type==None` → בדוק logs ל-`[FiveMin] current_day_type is None`.
**FAIL:** `bar_count==0` / טבלת state ריקה אחרי הפתיחה.

### 2.4 Pattern Eligibility

```bash
curl -s http://localhost:8000/api/v9/build/pattern-status | python3 << 'PY'
import sys, json
d=json.load(sys.stdin)
rtb=d.get("rtb_session",{})
print(f"RTH: in_session={rtb.get('in_session')} minutes_to_open={rtb.get('minutes_to_open')}")
s2=next((s for s in d.get("systems",[]) if "five" in s.get("id","").lower()), None)
if s2:
    print(f"S2 mode={s2.get('mode')} running={s2.get('running')} hydrated={s2.get('hydrated')}")
    print(f"  data_freshness: {s2.get('data_freshness',{})}")
    for p in s2.get("patterns",[])[:5]:
        print(f"  pattern {p.get('id')}: status={p.get('status')} blocked_by={p.get('blocked_by')}")
else:
    print("Systems:", [s.get("id") for s in d.get("systems",[])])
PY
```

**PHASE B:** לפחות pattern אחד `ELIGIBLE`/`FIRED`. אם הכל `BLOCKED` → בדוק day_type gate ו-RTH gate.

---

## 3. S4 — WOODIES CCI SYSTEM

### 3.1 Bar Freshness + Frozen-tail (TS הוא UTC נקי כאן)

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
SELECT ts,
       round((julianday('now') - julianday(ts)) * 86400) AS age_s,
       cci_14, cci_6_tcci, swi_value, trend_state
FROM v9_bars_5min_woodies
WHERE ts < '2099-01-01'        -- מסנן 5 שורות sentinel
ORDER BY ts DESC
LIMIT 5;
SQL
```

**PHASE A:** `age_s < 21600` (6 שעות; Globex). **PHASE B:** `age_s < 360`.
**FAIL frozen-tail:** כל 3+ השורות עם אותם `cci_14`/`swi_value` → DLL frozen. ודא DLL
חדש (v9.4.3-p31.1) ו-Input = 12.
**WARN:** `cci_14==swi_value==0` → ייתכן Chart 12 לא פתוח.

### 3.2 Current Bar Routing (API)

```bash
python3 << 'PY'
import json, urllib.request, sqlite3
try:
    d=json.loads(urllib.request.urlopen("http://localhost:8000/api/v9/woodies/chart",timeout=3).read())
    bars=d.get("bars", d.get("data",[]))
    if bars:
        b=bars[-1]
        print("Latest /woodies/chart bar:")
        print(f"  ts={b.get('ts')} cci_14={b.get('cci_14')} swi={b.get('swi_value')} trend={b.get('trend_state')}")
    else: print("No bars in /woodies/chart")
except Exception as e:
    print("API error:", e, "— DB fallback:")
    DB="/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    db=sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    print(db.execute("SELECT ts,cci_14,swi_value,trend_state FROM v9_bars_5min_woodies WHERE ts<'2099-01-01' ORDER BY ts DESC LIMIT 1").fetchone())
PY
```

**PHASE B:** `cci_14 != 0.0` ו-`swi_value != 0.0`.

### 3.3 Woodies signals recency + System state

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
SELECT substr(MAX(ts),1,19) AS latest_signal_utc FROM v9_woodies_signals;
SQL

curl -s http://localhost:8000/api/v9/status | python3 << 'PY'
import sys, json
d=json.load(sys.stdin)
s4=d.get("systems",{}).get("woodies", d.get("woodies",{}))
print("S4 state:", s4.get("state","?"))
print("S4 bar_count:", s4.get("bar_count","?"))
print("S4 time_stop_minutes:", s4.get("time_stop_minutes","?"))
print("S4 active_trades:", s4.get("active_trades","?"))
PY
```

**PASS:** state != ERROR, bar_count > 0 (PHASE B), signal latest עדכני.
**WARN:** `time_stop_minutes != null` → W-10 נדלק; Layer 4 צריך להיות הסמכות.

---

## 4. DATA CONSISTENCY MATRIX

```bash
python3 << 'PY'
"""Cross-source consistency — schema-correct (v2)."""
import json, sqlite3, urllib.request
from pathlib import Path
DB="/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
db=sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
def get(ep):
    try: return json.loads(urllib.request.urlopen("http://localhost:8000"+ep,timeout=3).read())
    except Exception as e: return {"_err":str(e)}

# IB 3 sources
r=db.execute("""SELECT ib_high,ib_low,ib_width_class FROM v9_day_type_history
  WHERE status NOT IN ('ROLLED_OVER') ORDER BY date DESC LIMIT 1""").fetchone()
tpo=get("/api/v9/tpo/current"); kl=get("/api/v9/key_levels"); dt=get("/api/v9/day_type/v9/current")
print("=== IB CROSS-SOURCE ===")
print(f"  DB:          high={r[0]} low={r[1]} class={r[2]}")
print(f"  /tpo/current: high={tpo.get('ib_high')} low={tpo.get('ib_low')} found={tpo.get('ib_found')} src={tpo.get('ib_source')}")
print(f"  /key_levels:  high={kl.get('ib_high')} low={kl.get('ib_low')}")

# Day type consistency
ddt=db.execute("""SELECT day_type,opening_type,status FROM v9_day_type_history
  WHERE status NOT IN ('ROLLED_OVER') ORDER BY date DESC LIMIT 1""").fetchone()
print("\n=== DAY TYPE CROSS-SOURCE ===")
print(f"  DB history: {ddt}")
print(f"  DB state:   {db.execute('SELECT day_type,lock_state,stage FROM v9_day_type_state ORDER BY id DESC LIMIT 1').fetchone()}")
print(f"  API /day_type/v9/current: day_type={dt.get('day_type')} lock={dt.get('lock_state') or dt.get('status')}")

# Rollover
rv=db.execute("SELECT value FROM v9_session_meta WHERE key='last_rollover_date'").fetchone()
print(f"\n=== ROLLOVER ===\n  last_rollover_date = {rv[0] if rv else None}")

# Bar freshness
print("\n=== BAR FRESHNESS ===")
print("  5min latest ts (naive):", db.execute("SELECT ts FROM v9_bars_5min ORDER BY ts DESC LIMIT 1").fetchone())
print("  woodies latest ts (UTC):", db.execute("SELECT ts FROM v9_bars_5min_woodies WHERE ts<'2099-01-01' ORDER BY ts DESC LIMIT 1").fetchone())

# Synthesis guard
syn=db.execute("SELECT COUNT(*) FROM v9_bars_5min WHERE is_synthetic=1").fetchone()[0]
print(f"\n=== SYNTHESIS GUARD ===\n  v9_bars_5min is_synthetic=1: {syn}  {'FAIL' if syn else 'PASS'}")

# Open trades (real states: CLOSED/PARTIAL)
opn=db.execute("SELECT COUNT(*) FROM v9_trades WHERE state IN ('PARTIAL','OPEN','FILLED')").fetchone()[0]
print(f"\n=== OPEN TRADES ===\n  PARTIAL/OPEN/FILLED: {opn}  {'WARN -- unreconciled?' if opn else 'PASS'}")
print("Done.")
PY
```

**PASS:** IB תואם בין המקורות (אחרי lock); `is_synthetic=1` ⇒ 0; `last_rollover_date`=היום.
**FAIL:** מספרי IB שונים בין DB/API.
**WARN:** עסקאות PARTIAL/OPEN פתוחות לפני פתיחה (היו 12 ב-29-05).

---

## 5. FRONTEND CHECK

```bash
curl -s -o /dev/null -w "frontend :3000 -> %{http_code}\n" http://localhost:3000

for ep in "/health" "/api/v9/status" "/api/v9/day_type/v9/current" \
          "/api/v9/tpo/current" "/api/v9/key_levels" \
          "/api/v9/build/pattern-status" "/api/v9/woodies/chart"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000$ep")
    echo "$code $ep"
done
```

**PASS:** frontend=200 וכל ה-endpoints=200 (לא 5xx/404).

### אימות ויזואלי (Michael)

| רכיב | מה לבדוק | PASS |
|------|----------|------|
| DayType Strip | `date=היום`, `day_type != "---"` אחרי פתיחה | ☐ |
| IB / KeyLevels | IB High+Low מוצגים אחרי 10:30 | ☐ |
| Woodies CCI Panel | CCI/TCCI זז (לא frozen) | ☐ |
| Build Status | S1/S2/S4 מוצגים, אין ERROR ללא סיבה | ☐ |
| FiveMin Lens | `current_day_type` לא None + pattern statuses | ☐ |
| TPO Lens | POC/VAH/VAL/IB עם ערכים | ☐ |
| Trade History | רשומות / "no trades" | ☐ |
| TopBar | Heartbeat לא DEAD, last_push < 30s | ☐ |

---

## 6. PHASE-SPECIFIC CHECKS

### PHASE A — לפני פתיחה

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
-- שורת היום (ET = UTC-4 ב-EDT)
SELECT date, status, day_type, ib_high, ib_low, substr(last_updated_at,1,19) AS upd
FROM v9_day_type_history
WHERE date = date('now','-4 hours')
ORDER BY last_updated_at DESC LIMIT 3;

-- rollover רץ היום
SELECT key, value FROM v9_session_meta WHERE key='last_rollover_date';
SQL
```

**PASS Phase A:** שורת היום `status=PENDING`/`day_type=UNKNOWN`; `last_rollover_date`=היום.

### PHASE B — תוך מסחר

```bash
python3 << 'PY'
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
DB="/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
db=sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
now=datetime.now(ZoneInfo("America/New_York")); m=now.hour*60+now.minute
print(f"ET {now:%H:%M:%S} | RTH={9*60+30<=m<16*60}")
if m>=10*60+30:
    r=db.execute("""SELECT status,ib_high,ib_low FROM v9_day_type_history
      WHERE status NOT IN ('ROLLED_OVER') ORDER BY date DESC LIMIT 1""").fetchone()
    print("\nIB lock check (post 10:30):")
    print(f"  status={r[0]} {'PASS' if str(r[0]).startswith('LOCKED') else 'FAIL'}")
    print(f"  ib_high={r[1]} ib_low={r[2]} {'PASS' if r[1] is not None and r[2] is not None else 'FAIL -- None'}")
w=db.execute("""SELECT ts,cci_14,swi_value FROM v9_bars_5min_woodies
  WHERE ts<'2099-01-01' ORDER BY ts DESC LIMIT 5""").fetchall()
print("\nWoodies last 5:")
for x in w: print(f"  {x[0]}: CCI={x[1]} SWI={x[2]}")
cc=[x[1] for x in w if x[1] is not None]
print("  WARN frozen-tail!" if len(cc)>=2 and len(set(cc))==1 else "  CCI variance OK")
PY
```

### PHASE C — סוף מסחר

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
.mode column
.headers on
-- אין עסקאות פתוחות (ערכים בפועל: PARTIAL/CLOSED)
SELECT COUNT(*) AS open_trades FROM v9_trades WHERE state IN ('PARTIAL','OPEN','FILLED');

-- archive של היום
SELECT COUNT(*) AS archived_today FROM v9_day_type_archive
WHERE date = date('now','-4 hours');

-- day type סופי
SELECT date, day_type, opening_type, ib_width_class, status, confidence
FROM v9_day_type_history
WHERE status NOT IN ('ROLLED_OVER')
ORDER BY date DESC LIMIT 1;
SQL
```

**PASS Phase C:** `open_trades=0`, `archived_today>=1`, status `LOCKED*`.
**שים לב:** אם `open_trades>0` בסוף יום — חקור את אותן עסקאות PARTIAL (הנורה מ-29-05).

> ⚠️ ודא ש-`v9_day_type_archive` מכיל עמודת `date` (בדוק `PRAGMA table_info(v9_day_type_archive)`
> אם השאילתה נכשלת — ייתכן שם עמודה שונה, כמו ב-`v9_day_type_history`).

---

## 7. VERDICT — מבנה הדיווח

```
=== MEMS26 READINESS VERDICT (v2) ===
Phase: [A/B/C] | ET: XX:XX | IL: XX:XX

SECTION                                STATUS   NOTE
──────────────────────────────────────────────────────────
0. Backend alive                       [ PASS ] /health OK
0. sot_health --strict                 [ PASS ] / [FAIL: X STALE, Y MISSING]

1. S1 today's row exists               [ PASS ] / [FAIL]
1. S1 status correct for phase         [ PASS ] / [WARN/FAIL]
1. S1 last_rollover_date = today       [ PASS ] / [FAIL]   (לא status=ROLLED_OVER!)
1. S1 live state (day_type_state) fresh [ PASS ] / [WARN]
1. S1 IB cross-source agreement        [ PASS ] / [FAIL]   (N/A לפני 10:30)

2. S2 5min bars present                [ PASS ] / [FAIL]
2. S2 is_synthetic = 0                 [ PASS ] / [FAIL]
2. S2 5min ts TZ sane (Rule 4)         [ PASS ] / [WARN: naive/neg age]
2. S2 state hydrated (post-open)       [ PASS ] / [WARN pre-open / FAIL post-open]
2. S2 patterns not all BLOCKED         [ PASS ] / [WARN]

3. S4 Woodies bars fresh               [ PASS ] / [FAIL]
3. S4 CCI not frozen                   [ PASS ] / [WARN]
3. S4 time_stop = null (Layer 4)       [ PASS ] / [FAIL: W-10]

4. IB 3-way match                      [ PASS ] / [FAIL]
4. is_synthetic = 0                    [ PASS ] / [FAIL]
4. Open PARTIAL/OPEN trades            [ PASS=0 ] / [WARN: N unreconciled]

5. Frontend :3000 + 7 endpoints 200    [ PASS ] / [FAIL]

──────────────────────────────────────────────────────────
OVERALL: [ GO / WARN / STOP ]
  GO   = all PASS
  WARN = 1+ WARN, no FAIL (סחר בזהירות)
  STOP = any FAIL
```

**חובה:** הדבק OUTPUT גולמי מכל command לפני ה-VERDICT, וסיים ב-`git log --oneline -5`.

---

## 8. שגיאות ידועות + תיקונים

| שגיאה | סיבה | תיקון |
|-------|------|--------|
| `no such column: session_date/lock_state/ib_source` | הרצת SQL מ-v1 | השתמש בגרסה הזו (v2) — `date`/`status`, ואין `ib_source` |
| Backend לא עונה | תהליך מת | `screen -r mems26_backend` או `source .env && uvicorn backend.main:app --port 8000` |
| `day_type=None` ב-API | seed לא רץ | logs `[SessionBoundary] seed_today_if_missing`; אחרת restart |
| CCI frozen | DLL לא rebuilt / Input != 12 | Sierra Input=12; DLL timestamp עדכני |
| 5min age שלילי | `ts` naive ללא TZ | Rule 4 — נעוץ TZ בהמרת הגבול; אל תסמוך על age גולמי |
| עסקאות PARTIAL תקועות | reconciliation gap? | חקור `v9_trades WHERE state='PARTIAL'` לפני LIVE |

---

## 9. LOG CHECKS

```bash
screen -r mems26_backend 2>/dev/null | tail -50 || \
  cat /tmp/mems26_backend.log 2>/dev/null | grep -E "ERROR|WARNING|FAIL" | tail -20

cat /tmp/bridge.err.log 2>/dev/null | grep -E "FAILED|ERROR" | tail -10
# "FAILED to https://" → bridge לענן — עצור!
```

**סיום:** VERDICT table + `git log --oneline -5`.
