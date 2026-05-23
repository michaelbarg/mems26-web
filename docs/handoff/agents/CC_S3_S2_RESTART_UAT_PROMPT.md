# CC Prompt — Restart backend + UAT post P31-STRAT-S3 fixes

**מטרה:** להפעיל את שני התיקונים שcommitted (`dcae75d` + `2bc6796`) ולוודא ש-COT/AMT עובדים נכון, ואם RTH פתוח — שS2 מתחיל לירות.

**הקשר:** Cursor + CC עברו על Bugs #2+#3 ב-`backend/v9/systems/footprint/footprint_system.py`. הקוד committed לbranch הנוכחי, אבל backend (PID 77057) רץ מקוד ישן (10:08:48).

---

## פעולה 1 — Restart backend (5 דק')

```bash
# Verify current backend
lsof -nP -iTCP:8000 -sTCP:LISTEN
# Expect: PID 77057 (or similar, started before 10:30 IL)

# Graceful kill
pkill -f "uvicorn backend.main" 2>/dev/null
sleep 2
# If still alive, force:
lsof -nP -iTCP:8000 -sTCP:LISTEN  # check
# pkill -9 -f "uvicorn backend.main"  # only if graceful failed

cd /Users/michael/Downloads/mems26_web_git
export DATABASE_URL=sqlite:///./data/mems26_local.db
nohup python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 \
    >> /tmp/backend.log 2>&1 &
sleep 5

# Verify
curl -s -o /dev/null -w "health=%{http_code}\n" http://127.0.0.1:8000/api/v9/health
lsof -nP -iTCP:8000 -sTCP:LISTEN  # new PID
```

**Expected:** `health=200` + new PID with start time after 10:40 IL.

---

## פעולה 2 — UAT 4-axis ל-Footprint state (5 דק')

```bash
# Sleep ~30s to let bridge push a few bars after restart
sleep 30

curl -s "http://127.0.0.1:8000/api/v9/footprint/current" | python3 -m json.tool
```

### Acceptance criteria — 4 צירים

| ציר | יעד | איך לקרוא |
|---|---|---|
| **Quality** | COT לא −144K. אם hydrate הופעל ב-session אחרי 18:00 ET אתמול, COT צריך להיות **קטן מ-50K** (יומי). | `cot` בoutput |
| **Recency** | AMT לא 0.0 (אם יש לפחות בר אחד עם volume + trade_count). אם פחות מ-18 ברים בוצעו מאז restart, AMT הוא ממוצע על מה שיש. | `amt` בoutput |
| **Cardinality** | bars_processed_today **גדל** ב-30 שניות (לפחות 2-3 ברים נוספים). | `bars_processed_today` |
| **Latency** | API מחזיר בפחות מ-1 שניה. | `time curl` |

### תוצאות צפויות

```json
{
  "cot": 0,              // אם session החל אחרי תחילת הbackend
  "amt": 50-300,         // אם יש activity (RTH/Asia/EU)
  // OR
  "amt": 0,              // אם השוק שקט (overnight 04:00-09:00 ET)
  "bars_processed_today": <growing>,
  "hydrated": true,
  "running": true
}
```

**אם AMT עדיין 0.0 אחרי 30 שניות + יש activity (volume>0 בברים)** → הקוד החדש לא נטען. בדוק:
```bash
grep "P31: Session-aware COT" /tmp/backend.log
# Expect this line to appear at backend startup.
```

אם לא — אולי השרצוצ הישן עדיין רץ. חזור ל-פעולה 1.

---

## פעולה 3 — אם RTH פתוח (09:30-16:00 ET = 16:30-23:00 IL)

```bash
# Wait 5-10 min for S2 to potentially fire
sleep 600

# Check S2 state
curl -s "http://127.0.0.1:8000/api/v9/five_min/current" | python3 -m json.tool

# Check if S2 fired anything new
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db \
  "SELECT id, firing_system, direction, state, entry_ts FROM v9_trades \
   WHERE firing_system = 2 ORDER BY id DESC LIMIT 5;"

# Grep for FIRE logs
grep -E "FiveMin.*FIRE|FiveMin.*Auto-routed" /tmp/backend.log | tail -20
```

### Expected — pre-LIVE:
- **S2 firing הוא bonus**, לא דרישה. הקוד החדש מאפשר ל-S2 לבדוק תנאי cot/amt, אבל עדיין דורש 4-bar pattern.
- אם S2 ירה: `firing_system=2` ב-trades, mode="OVERNIGHT_MODE" or "DAY_TYPE_MODE", FIRE log.
- **אם לא ירה תוך 30 דק' ב-RTH:** הסיבה כנראה היא שתנאי 4-bar pattern לא מתקיים. זה לא רגרסיה — זה ניתוח של ה-spec.

### אם RTH סגור (מסחר Asia/EU/overnight) — דחה את חלק זה
SHADOW data של overnight לא רלוונטי ל-decision של S2.

---

## פעולה 4 — דוח קצר (5 דק')

צור `docs/reports/PROMPT_P31_STRAT_S3_UAT.md` עם:

```markdown
# P31-STRAT-S3 UAT Report — 2026-05-22

## Backend restart
- Old PID 77057 (start: <time>) killed
- New PID <X> (start: <time>) up

## Footprint state — before vs after restart

| Field | Pre-fix (10:08 PID) | Post-fix (new PID) | Status |
|---|---|---|---|
| cot   | 19849.0 | <X>       | quality |
| amt   | 0.0     | <X>       | quality |
| bars_processed_today | 1024 (growing) | <Y> (growing) | recency |

## 4 UAT axes
- Quality:     [pass/fail with evidence]
- Recency:     [pass/fail with evidence]
- Cardinality: [pass/fail with evidence]
- Latency:     [pass/fail with evidence]

## S2 fire (RTH only)
- Trades from S2 since restart: <N>
- FIRE log entries: <N>
- If 0: 4-bar pattern conditions analysis (verbose only if RTH > 30min open with 0 fires)

## Issues found
- <none, or list>

## Next step recommendation
- <e.g., "S2 ירה X trades — proceed to baseline data collection">
- <e.g., "AMT עובד אבל S2 לא ירה — נדרשת UAT נוספת ב-RTH מלא">
```

---

## אזהרות

- **אל תיגע בקוד** — רק בדיקה.
- **אל תשנה את ה-bridge / LaunchAgent / CLOUD_URL** (per `mems26-stability.mdc`).
- **אל תפתח Sierra** אם לא פתוחה כבר — UAT עובד גם בלי, רק שתוצאות S2-firing דורשות data חי.
- אם backend לא עולה, בדוק `tail -50 /tmp/backend.log` והחזר את ה-log + השגיאה. אל תנסה fixes יצירתיים.
