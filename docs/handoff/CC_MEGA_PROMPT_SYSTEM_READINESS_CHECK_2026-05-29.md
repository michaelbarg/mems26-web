# MEGA-PROMPT — MEMS26 System Readiness Check (S1 · S2 · S4)

**לשימוש בשלוש נקודות זמן:**
- **PHASE A — לפני מסחר** (לפני 09:30 ET): הרצה מלפני RTH, לפחות 15 דקות לפני פתיחה
- **PHASE B — תוך כדי מסחר** (09:30–16:00 ET): כל שעה, במיוחד אחרי 10:30 (IB lock)
- **PHASE C — סוף מסחר** (אחרי 16:00 ET): ניתוח יום + אימות archive

**הורה ל-CC:** קרא הפרומפט הזה במלואו, בצע **כל** הפקודות לפי השלב הרלוונטי, הדפס OUTPUT גולמי מכל פקודה, וסיים בטבלת `PASS / FAIL / WARN` מפורטת לכל סעיף.

---

## 0. BOOTSTRAP — סביבה ומצב בסיסי

```bash
# 0.1 — בדוק שה-backend פעיל
curl -s http://localhost:8000/health | python3 -m json.tool
# ציפייה: {"status":"ok","version":"..."}

# 0.2 — הרץ sot_health.py (בסיס לכל שלב)
cd /Users/michael/Downloads/mems26_web_git
python3 scripts/sot_health.py --strict 2>&1 | head -80

# 0.3 — שעה נוכחית ET + IL
python3 -c "
from zoneinfo import ZoneInfo
from datetime import datetime
et = datetime.now(ZoneInfo('America/New_York'))
il = datetime.now(ZoneInfo('Asia/Jerusalem'))
print(f'ET: {et.strftime(\"%Y-%m-%d %H:%M:%S %Z\")}')
print(f'IL: {il.strftime(\"%Y-%m-%d %H:%M:%S %Z\")}')
print(f'RTH: {\"YES\" if 9*60+30 <= et.hour*60+et.minute < 16*60 else \"NO\"}')
"
```

**שגיאות שאסור לראות:**
- `API push FAILED to https://` → bridge שולח לענן במקום localhost — **עצור!**
- `MISSING` ב-sot_health → מערכת לא מקבלת נתונים
- Backend לא עונה → הפעל `screen -r mems26_backend`

---

## 1. S1 — DAY TYPE (מערכת סוג היום)

### 1.1 DB State

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
-- שורה פעילה של היום
SELECT
    session_date,
    day_type,
    opening_type,
    ib_width_class,
    lock_state,
    conf,
    substr(last_updated_at, 1, 19) as updated,
    ib_source
FROM v9_day_type_history
WHERE lock_state NOT IN ('ROLLED_OVER')
ORDER BY session_date DESC
LIMIT 3;
SQL
```

**PHASE A (pre-market):** ציפייה: `lock_state=PENDING`, `day_type=UNKNOWN`, שורה של היום. **אסור: lock_state=LOCKED של אתמול ללא ROLLED_OVER.**

**PHASE B (תוך מסחר, לאחר 10:30):** ציפייה: `lock_state=LOCKED`, `day_type != UNKNOWN/PENDING`, `ib_source='sierra_study'`. **אסור: `ib_source='derived'` או `ib_source='missing'` לאחר IB lock.**

**PHASE C (סוף):** ציפייה: שורת היום עם lock_state=LOCKED, אתמול = ROLLED_OVER.

### 1.2 API Endpoint

```bash
curl -s http://localhost:8000/api/v9/day_type/v9/current | python3 -m json.tool
```

**בדוק:**
- `session_date` == תאריך היום ET (לא אתמול!)
- `day_type` תואם את DB
- `ib_high`, `ib_low` — לא None לאחר 10:30 ET
- `ib_source == "sierra_study"` (לא "derived" / "missing")

### 1.3 IB Consistency Check

```bash
python3 << 'PY'
import sqlite3, json, urllib.request
from zoneinfo import ZoneInfo
from datetime import datetime

db = sqlite3.connect("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")

# IB מה-DB
row = db.execute("""
    SELECT ib_high, ib_low, ib_width_points, ib_source
    FROM v9_day_type_history
    WHERE lock_state NOT IN ('ROLLED_OVER')
    ORDER BY session_date DESC LIMIT 1
""").fetchone()
print(f"DB IB: high={row[0]} low={row[1]} width={row[2]} source={row[3]}")

# IB מה-API
try:
    r = urllib.request.urlopen("http://localhost:8000/api/v9/tpo/current", timeout=3)
    d = json.loads(r.read())
    print(f"API IB: high={d.get('ib_high')} low={d.get('ib_low')} source={d.get('ib_source')}")
    print(f"API ib_found={d.get('ib_found')}, ib_locked={d.get('ib_locked')}")
except Exception as e:
    print(f"API error: {e}")

# IB מה-key_levels
try:
    r2 = urllib.request.urlopen("http://localhost:8000/api/v9/key_levels", timeout=3)
    d2 = json.loads(r2.read())
    print(f"KeyLevels IB: high={d2.get('ib_high')} low={d2.get('ib_low')}")
except Exception as e:
    print(f"KeyLevels error: {e}")
PY
```

**PASS:** DB IB == API IB == KeyLevels IB, source=sierra_study (לאחר lock).
**FAIL:** ערכים שונים בין 3 מקורות / source=derived → **סתירה — עצור!**

---

## 2. S2 — FIVE-MIN PATTERN SYSTEM

### 2.1 Bar Buffer Freshness

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
-- מתי הגיע ה-5min bar האחרון?
SELECT
    ts,
    round((julianday('now') - julianday(ts)) * 86400) as age_seconds,
    symbol
FROM v9_bars_5min
ORDER BY ts DESC LIMIT 3;
SQL
```

**PHASE A:** ציפייה: age_seconds < 21600 (6 שעות — bar אחרון מ-Globex/pre-market).
**PHASE B:** ציפייה: age_seconds < 360 (לא יותר מ-6 דקות — bar נסגר לכל היותר bar קודם).
**FAIL PHASE B:** age_seconds > 600 → הbridge לא שולח bars, S2 blind.

### 2.2 Day Type Hydration

```bash
curl -s http://localhost:8000/api/v9/status | python3 << 'PY'
import sys, json
d = json.load(sys.stdin)
s2 = d.get("systems", {}).get("five_min", d.get("five_min", {}))
print(f"S2 mode: {s2.get('mode', '?')}")
print(f"S2 current_day_type: {s2.get('current_day_type', 'NOT_IN_STATUS')}")
print(f"S2 bar_count: {s2.get('bar_count', '?')}")
print(f"S2 last_bar_ts: {s2.get('last_bar_ts', '?')}")
PY
```

**PASS:** `current_day_type != None` לאחר פתיחה + `mode == DAY_TYPE_MODE` בשעות RTH.
**WARN:** `current_day_type == None` → בדוק logs לאזהרה `[FiveMin] current_day_type is None`.
**FAIL:** `bar_count == 0` לאחר פתיחה → S2 לא מקבל bars.

### 2.3 Pattern Eligibility (build_status)

```bash
curl -s http://localhost:8000/api/v9/build/pattern-status | python3 << 'PY'
import sys, json
d = json.load(sys.stdin)
# RTH session state
rtb = d.get("rtb_session", {})
print(f"RTH session: in_session={rtb.get('in_session')} minutes_to_open={rtb.get('minutes_to_open')}")
# S2 five_min system
s2 = next((s for s in d.get("systems", []) if "five" in s.get("id","").lower()), None)
if s2:
    print(f"\nS2 mode={s2.get('mode')} running={s2.get('running')} hydrated={s2.get('hydrated')}")
    print(f"  data_freshness: {s2.get('data_freshness', {})}")
    # patterns in S2
    for pat in s2.get("patterns", [])[:5]:
        print(f"  pattern {pat.get('id')}: status={pat.get('status')} blocked_by={pat.get('blocked_by')}")
else:
    print("Systems:", [s.get("id") for s in d.get("systems", [])])
PY
```

**PHASE B (תוך מסחר):** צפוי לראות לפחות pattern אחד `status=ELIGIBLE` או `FIRED`. אם הכל `BLOCKED`:
- בדוק: האם `day_type` תואם לday_type gate של הpatterns?
- בדוק: האם זמן המסחר תקין (RTH gate)?

---

## 3. S4 — WOODIES CCI SYSTEM

### 3.1 Bar Stream Freshness (מ-Chart 12)

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
-- last 3 Woodies bars — CCI/SWI ריים (לא frozen 2099)
SELECT
    ts,
    round((julianday('now') - julianday(ts)) * 86400) as age_s,
    cci_14,
    cci_6_tcci,
    swi_value,
    trend_state
FROM v9_bars_5min_woodies
WHERE ts < '2099-01-01'  -- filter sentinel rows
ORDER BY ts DESC LIMIT 3;
SQL
```

**PHASE B (RTH):** ציפייה: age_s < 360, cci_14 != 0, swi_value != 0.
**WARN:** cci_14 == swi_value == 0 → ייתכן שChart 12 לא שלח נתונים (Chart 12 לא פתוח?).
**FAIL:** כל ה-3 rows עם אותם CCI/SWI values → **DLL frozen-tail** — בדוק שה-DLL החדש (v9.4.3-p31.1) פעיל ו-Input 18 = 12.

### 3.2 Current Bar Routing (live vs frozen)

```bash
python3 << 'PY'
import json, urllib.request, sqlite3
# API: latest Woodies bar via /woodies/chart
try:
    r = urllib.request.urlopen("http://localhost:8000/api/v9/woodies/chart", timeout=3)
    d = json.loads(r.read())
    bars = d.get("bars", d.get("data", []))
    if bars:
        last = bars[-1]
        print(f"Latest bar from /api/v9/woodies/chart:")
        print(f"  ts: {last.get('ts')}")
        print(f"  cci_14: {last.get('cci_14')}")
        print(f"  swi_value: {last.get('swi_value')}")
        print(f"  trend_state: {last.get('trend_state')}")
    else:
        print("No bars in /woodies/chart response")
except Exception as e:
    print(f"API error: {e}")
    # fallback: DB direct
    db = sqlite3.connect("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")
    row = db.execute("SELECT ts, cci_14, swi_value, trend_state FROM v9_bars_5min_woodies WHERE ts < '2099-01-01' ORDER BY ts DESC LIMIT 1").fetchone()
    print(f"DB fallback: {row}")
PY
```

**PHASE B:** ציפייה: `cci_14 != 0.0`, `swi_value != 0.0`. אם 0 — הbridge לא שולח current_bar עם ערכי SWI/CCI.

### 3.3 Woodies System State

```bash
curl -s http://localhost:8000/api/v9/status | python3 << 'PY'
import sys, json
d = json.load(sys.stdin)
s4 = d.get("systems", {}).get("woodies", d.get("woodies", {}))
print(f"S4 state: {s4.get('state', '?')}")
print(f"S4 bar_count: {s4.get('bar_count', '?')}")
print(f"S4 time_stop_minutes: {s4.get('time_stop_minutes', '?')}")
print(f"S4 active_trades: {s4.get('active_trades', '?')}")
PY
```

**PASS:** state != ERROR, bar_count > 0 (PHASE B).
**WARN:** `time_stop_minutes != null` → W-10 נדלק בטעות, Layer 4 צריך להיות הסמכות.

---

## 4. DATA CONSISTENCY MATRIX — ניתוח סתירות

```bash
python3 << 'PY'
"""Cross-source consistency: DB vs API vs Sierra files."""
import json, sqlite3, os, time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Users/michael/Downloads/mems26_web_git")
DB = REPO / "data" / "mems26_local.db"
SIERRA = Path("/Users/michael/SierraChart_Data/v9_export")
API = "http://localhost:8000"

import urllib.request
def get(endpoint):
    try:
        r = urllib.request.urlopen(f"{API}{endpoint}", timeout=3)
        return json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)}

db = sqlite3.connect(DB)

# ---- IB from 3 sources ----
db_row = db.execute(
    "SELECT ib_high, ib_low, ib_source FROM v9_day_type_history "
    "WHERE lock_state NOT IN ('ROLLED_OVER') ORDER BY session_date DESC LIMIT 1"
).fetchone()

tpo_api = get("/api/v9/tpo/current")
kl_api = get("/api/v9/key_levels")
dt_api = get("/api/v9/day_type/v9/current")

print("=== IB CROSS-SOURCE ===")
print(f"  DB:          high={db_row[0] if db_row else '?'} low={db_row[1] if db_row else '?'} src={db_row[2] if db_row else '?'}")
print(f"  /tpo/current: high={tpo_api.get('ib_high')} low={tpo_api.get('ib_low')} found={tpo_api.get('ib_found')} src={tpo_api.get('ib_source')}")
print(f"  /key_levels:  high={kl_api.get('ib_high')} low={kl_api.get('ib_low')}")
print(f"  /day_type:    ib_width_class={dt_api.get('ib_width_class')}")

# ---- Day Type consistency ----
print("\n=== DAY TYPE CROSS-SOURCE ===")
db_dt = db.execute(
    "SELECT day_type, opening_type, lock_state FROM v9_day_type_history "
    "WHERE lock_state NOT IN ('ROLLED_OVER') ORDER BY session_date DESC LIMIT 1"
).fetchone()
print(f"  DB: {db_dt}")
print(f"  API /day_type/v9/current: day_type={dt_api.get('day_type')} lock={dt_api.get('lock_state')}")
print(f"  API /key_levels: day_type={kl_api.get('day_type')}")
print(f"  API /status: day_type={get('/api/v9/status').get('day_type', {})}")

# ---- Woodies bar age ----
print("\n=== WOODIES BAR FRESHNESS ===")
w_row = db.execute(
    "SELECT ts, cci_14, swi_value FROM v9_bars_5min_woodies "
    "WHERE ts < '2099-01-01' ORDER BY ts DESC LIMIT 1"
).fetchone()
if w_row:
    ts_str = str(w_row[0])
    print(f"  Last woodies bar: {ts_str}")
    print(f"  CCI14={w_row[1]}, SWI={w_row[2]}")
else:
    print("  NO WOODIES BARS IN DB")

# ---- 5min bar age ----
bar5_row = db.execute(
    "SELECT ts FROM v9_bars_5min ORDER BY ts DESC LIMIT 1"
).fetchone()
print(f"\n  Last 5min bar: {bar5_row[0] if bar5_row else 'NONE'}")

# ---- Flag any synthesis ----
print("\n=== SYNTHESIS GUARD ===")
synth = db.execute(
    "SELECT COUNT(*) FROM v9_day_type_history WHERE ib_source='derived'"
).fetchone()[0]
print(f"  Rows with ib_source='derived': {synth}  {'FAIL -- synthesis present!' if synth else 'PASS'}")

print("\nDone.")
PY
```

**PASS:** כל ה-IB values תואמים בין שלושת המקורות. `ib_source` == `sierra_study` (לאחר IB lock). 0 rows עם `ib_source='derived'`.
**FAIL:** מספרים שונים בין DB / API / key_levels — יש סתירה קריטית לפני LIVE.

---

## 5. FRONTEND CHECK — כל הרכיבים מוצגים

### 5.1 בדוק שה-frontend רץ

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# ציפייה: 200
```

### 5.2 רשימת רכיבים לאימות ויזואלי (Michael מבצע)

פתח `http://localhost:3000` ובדוק:

| רכיב | מה לבדוק | PASS |
|------|----------|------|
| **DayType Strip** | מציג `session_date = היום`, `day_type != "---"` לאחר פתיחה | ☐ |
| **IB Strip / KeyLevels** | IB High + Low מוצגים (לא `null`/`N/A` לאחר 10:30 ET) | ☐ |
| **Woodies CCI Panel** | CCI/TCCI bar chart זז — לא frozen על אותו ערך | ☐ |
| **Build Status** | לפחות S1/S2/S4 מוצגים. אין `ERROR` אדום ללא סיבה | ☐ |
| **FiveMin Lens** | מציג `current_day_type` (לא `None`) + pattern statuses | ☐ |
| **TPO Lens** | POC/VAH/VAL/IB מוצגים עם ערכים (לא 0/null) | ☐ |
| **Trade History** | מציג רשומות (או "no trades today" לאחר reset) | ☐ |
| **TopBar** | Heartbeat לא "DEAD", last_push_ts < 30s ago | ☐ |

### 5.3 בדיקת API responses לfrontend components

```bash
# כל ה-endpoints שה-frontend קורא
for ep in \
  "/health" \
  "/api/v9/status" \
  "/api/v9/day_type/v9/current" \
  "/api/v9/tpo/current" \
  "/api/v9/key_levels" \
  "/api/v9/build/pattern-status" \
  "/api/v9/woodies/chart"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000$ep")
    echo "$code $ep"
done
```

**PASS:** כל ה-endpoints מחזירים 200. לא 500 / 404.

---

## 6. PHASE-SPECIFIC CHECKS

### PHASE A — לפני מסחר (לפני 09:30 ET)

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
-- 1. אין שורות של היום עם lock_state=LOCKED לפני פתיחה
SELECT session_date, lock_state, day_type, last_updated_at
FROM v9_day_type_history
WHERE session_date = date('now', '-5 hours')  -- ET today
ORDER BY last_updated_at DESC LIMIT 3;

-- 2. session_meta מכיל את תאריך היום
SELECT * FROM v9_session_meta ORDER BY id DESC LIMIT 1;

-- 3. אתמול מסומן ROLLED_OVER
SELECT session_date, lock_state FROM v9_day_type_history
WHERE session_date < date('now', '-5 hours')
ORDER BY session_date DESC LIMIT 2;
SQL
```

**PASS Phase A:**
- שורת היום: `lock_state=PENDING`
- `v9_session_meta.last_rollover_date` == תאריך היום
- שורת אתמול: `lock_state=ROLLED_OVER`

### PHASE B — תוך כדי מסחר (09:30–16:00 ET)

```bash
python3 << 'PY'
"""Phase B live check — runs during RTH."""
import sqlite3, time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DB = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
db = sqlite3.connect(DB)

now_et = datetime.now(ZoneInfo("America/New_York"))
minutes_et = now_et.hour * 60 + now_et.minute

print(f"ET time: {now_et.strftime('%H:%M:%S')}")
print(f"RTH: {9*60+30 <= minutes_et < 16*60}")

# IB lock should happen by 10:30
if minutes_et >= 10*60+30:
    row = db.execute(
        "SELECT lock_state, ib_source, ib_high, ib_low "
        "FROM v9_day_type_history ORDER BY session_date DESC LIMIT 1"
    ).fetchone()
    locked = row[0] == "LOCKED"
    src_ok = row[1] == "sierra_study"
    ib_ok = row[2] is not None and row[3] is not None
    print(f"\nIB Lock check (post 10:30):")
    print(f"  lock_state={row[0]} {'PASS' if locked else 'FAIL'}")
    print(f"  ib_source={row[1]} {'PASS' if src_ok else 'FAIL -- synthesis?'}")
    print(f"  ib_high={row[2]} ib_low={row[3]} {'PASS' if ib_ok else 'FAIL -- None'}")

# Woodies bars not frozen
w_rows = db.execute(
    "SELECT ts, cci_14, swi_value FROM v9_bars_5min_woodies "
    "WHERE ts < '2099-01-01' ORDER BY ts DESC LIMIT 5"
).fetchall()
print(f"\nWoodies last 5 bars:")
for r in w_rows:
    print(f"  {r[0]}: CCI={r[1]} SWI={r[2]}")

ccis = [r[1] for r in w_rows if r[1] is not None]
if len(ccis) >= 2 and len(set(ccis)) == 1:
    print("  ⚠️  WARN: all CCI values identical — possible frozen tail!")
else:
    print("  CCI variance OK")
PY
```

### PHASE C — סוף מסחר (אחרי 16:00 ET)

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db << 'SQL'
-- 1. trades אכן נסגרו — אין open trades
SELECT COUNT(*) as open_trades FROM v9_trades WHERE state IN ('FILLED','PARTIAL','OPEN');

-- 2. archive triggered (rows moved to archive tables)
SELECT COUNT(*) as archived_today FROM v9_day_type_archive
WHERE session_date = date('now', '-5 hours');

-- 3. Final day type
SELECT session_date, day_type, opening_type, ib_width_class, lock_state, conf
FROM v9_day_type_history
WHERE lock_state NOT IN ('ROLLED_OVER')
ORDER BY session_date DESC LIMIT 1;
SQL
```

**PASS Phase C:** `open_trades = 0`, `archived_today >= 1`, lock_state=LOCKED.

---

## 7. EXPECTED OUTPUTS — מה CC צריך לדווח

CC: בסוף ה-run, הפק טבלת **VERDICT** במבנה הזה:

```
=== MEMS26 READINESS VERDICT ===
Phase: [A/B/C] | ET time: XX:XX | IL time: XX:XX

SECTION                           STATUS   NOTE
─────────────────────────────────────────────────────
0. Backend alive                  [ PASS ] http://localhost:8000/health OK
0. sot_health --strict            [ PASS ] / [FAIL: X STALE, Y MISSING]

1. S1 DB row exists today         [ PASS ] / [FAIL: date mismatch]
1. S1 lock_state correct          [ PASS ] / [WARN: LOCKED before IB window]
1. S1 IB source = sierra_study    [ PASS ] / [FAIL: derived/missing]
1. S1 cross-source IB agreement   [ PASS ] / [FAIL: DB != API != KeyLevels]

2. S2 bar_count > 0               [ PASS ] / [FAIL]
2. S2 current_day_type != None    [ PASS ] / [WARN: None — check logs]
2. S2 patterns not all BLOCKED    [ PASS ] / [WARN: all blocked, check gate]

3. S4 Woodies bars fresh          [ PASS ] / [FAIL: age > 6min in RTH]
3. S4 CCI not frozen              [ PASS ] / [WARN: all bars same CCI]
3. S4 time_stop = null (Layer 4)  [ PASS ] / [FAIL: W-10 re-enabled]

4. IB cross-source 3-way match    [ PASS ] / [FAIL: CONTRADICTION]
4. No synthesis rows (derived=0)  [ PASS ] / [FAIL: N rows with derived]

5. Frontend http://localhost:3000  [ PASS ] / [FAIL: not 200]
5. /health /status /day_type/current /tpo/current /key_levels /build/pattern-status /woodies/chart — all 200  [ PASS ] / [FAIL: X = 5xx/404]

Phase-specific checks             [see above]

─────────────────────────────────────────────────────
OVERALL: [ GO / WARN / STOP ]
  GO   = all PASS, no FAIL
  WARN = 1+ WARN, no FAIL (can trade, watch closely)
  STOP = any FAIL (do not trade until resolved)
```

**חובה:** הדפס OUTPUT גולמי מכל command לפני ה-VERDICT. אל תסמוך על זיכרון — הרץ הכל מחדש.

---

## 8. שגיאות ידועות + תיקונים מהירים

| שגיאה | סיבה | תיקון |
|-------|------|--------|
| Backend לא עונה | תהליך מת | `screen -r mems26_backend` אם קיים, אחרת `cd /Users/michael/Downloads/mems26_web_git && source .env && uvicorn backend.main:app --port 8000` ב-screen חדש |
| `day_type=None` ב-API | SessionBoundaryManager לא הריץ seed | בדוק logs: `[SessionBoundary] seed_today_if_missing`, אם לא קיים — restart backend |
| CCI frozen (כל הbars אותו ערך) | DLL לא rebuilt / Input 18 != 12 | בדוק ב-Sierra: Analysis → Edit Studies → Input 19 = 12. אם OK — בדוק DLL timestamp > May 29 15:47 |
| `ib_source='derived'` | synthesis fallback קיים | `grep -r "_ib_from_bars\|ib_source.*derived" backend/` — חייב להיות ריק |
| Frontend 404/500 | Next.js לא רץ | `cd frontend/v9 && npm run dev` בport 3000 |
| `stop_hit_ts < entry_ts` | הbug E תוקן ב-commit e3b986c | בדוק שה-backend רץ מה-commit הנכון: `git log --oneline -3` |

---

## 9. LOG CHECKS (אחרי כל phase)

```bash
# Backend errors בשעה האחרונה
screen -r mems26_backend 2>/dev/null | tail -50 || \
  cat /tmp/mems26_backend.log 2>/dev/null | grep -E "ERROR|WARNING|FAIL" | tail -20

# Bridge errors
cat /tmp/bridge.err.log 2>/dev/null | grep -E "FAILED|ERROR" | tail -10
# אם יש "FAILED to https://" → bridge שולח לענן — עצור!
```

---

**סיום:** CC מסיים ב-VERDICT table + `git log --oneline -5` לוידוא commit נכון פעיל.
