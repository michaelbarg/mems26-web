# META-PROMPT · G4 UAT + SHADOW Gate Execution
**מיועד ל:** Claude Desktop
**תפקיד Desktop:** לכתוב את ה-mega-prompts שCC יריץ + checklists שמיכאל יבצע ב-RTH
**תפקיד Cursor:** לבדוק את הפלט של Desktop ולאשר G3 לפני שמיכאל מבצע

---

## הקשר

Phase A של Pipeline 1 (S2 · D-091) **בנוי ומאושר G3** (14/14 packages).
כדי לפתוח SHADOW (מסחר shadow אוטומטי חי) צריך לעבור 4 שלבים:
1. **G4 UAT** — כל package עובר 4 axes (Quality / Recency / Cardinality / Latency)
2. **L4 RTH UAT** — בדיקות Memorial Day שנדחו (L4-2/3/4)
3. **Systems-snapshot UAT** — endpoint `/cockpit/systems-snapshot` 4 axes
4. **60min soak** — מערכת ירוקה 60 דקות ברציפות

---

## מה Desktop צריך לייצר

### פריט 1 · CC Mega-Prompt: G4 Test Scaffolding

**קובץ:** `docs/handoff/CC_MEGA_PROMPT_G4_UAT_SCAFFOLDING_2026-05-26.md`

CC צריך לכתוב בדיקות שחסרות ולהריץ אותן **לפני** ש-RTH נפתח.
Desktop צריך לכתוב mega-prompt מלא (כולל 7 שדות · SCOPE / FORBIDDEN / Golden tests / Stop signals).

**מה CC צריך לבצע בפועל:**

#### א. Pkg 5a/5b — 4 integration tests חסרים
קובץ: `tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py`
הוסף 4 async tests:
- `test_chart_pattern_inverse_hns_fires_t1setup`
- `test_chart_pattern_hns_top_fires_t1setup`
- `test_chart_pattern_double_bottom_ee_fires_t1setup`
- `test_chart_pattern_double_top_aa_fires_t1setup`

כל test: pre-seed buffer → trigger `process_bar(breakout_bar)` → assert T1Setup payload נכון.
**מקורות:** `docs/handoff/G4_UAT_PKG5A_5B_PREP.md` §3.1–§3.4 · §6.1

#### ב. Latency probe script
קובץ חדש: `scripts/g4_pkg5_latency_probe.py`
100 calls על `process_bar` עם plain bar · מדווח p50/p95/p99 · exits 1 אם p95≥50ms
**מקור:** `docs/handoff/G4_UAT_PKG5A_5B_PREP.md` §6.2

#### ג. Pkg 8 / Pkg 6 — API quality probe script
קובץ חדש: `scripts/g4_pkg8_pkg6_api_probe.py`
כולל:
- קריאה ל-`/api/v9/patterns/auth-table?pattern=REACTIVE_LONG&day_type=Trend_Normal`
- קריאה ל-`/api/v9/trade/active`
- קריאה ל-`/cockpit/systems-snapshot`
מדווח כל axis (Quality / Recency / Cardinality / Latency) per endpoint.

**Spec authority:**
- `docs/spec_authority/S2_AUTH_TABLE_V1.md` — 70 cells · pattern × day_type
- `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` — Pkg 6 hooks

#### ד. L4-2/3/4 RTH probe script
קובץ חדש: `scripts/l4_rth_probe.py`
שלושה axes:

**L4-2 (Stream B · לא קשור לתיקוני Memorial Day · TPO stream)**
```python
# Recency axis: endpoint.latest_ts == DB.MAX(ts)
resp = requests.get("http://localhost:8000/api/v9/tpo/latest")
db_max = db.execute("SELECT MAX(ts) FROM v9_tpo_bars").scalar()
delta = abs(resp.json()["ts"] - db_max)
assert delta == 0, f"Recency FAIL: delta={delta}"
```

**L4-3 (Cardinality · Five-Min bars)**
```python
resp = requests.get("http://localhost:8000/api/v9/bars/5min?limit=20")
assert len(resp.json()["bars"]) == 20, "Cardinality FAIL"
```

**L4-4 (Latency · all endpoints)**
```python
for url in ["/api/v9/tpo/latest", "/api/v9/bars/5min?limit=20", "/cockpit/systems-snapshot"]:
    start = time.perf_counter()
    requests.get(f"http://localhost:8000{url}")
    ms = (time.perf_counter() - start) * 1000
    assert ms < 500, f"Latency FAIL: {url} = {ms:.0f}ms"
```

**מקור:** `docs/spec_authority/S2_EXIT_DEFINITION_V6.md` · `.cursor/rules/mems26-pre-live-protocol.mdc`

---

### פריט 2 · Checklist מיכאל G4 RTH (16:30 IL)

**קובץ:** `docs/handoff/G4_RTH_CHECKLIST_2026-05-26.md`

Desktop ייצר checklist מפורט למיכאל לביצוע ב-RTH.
הchecklist חייב לכסות כל package ו-4 axes.

**מבנה מחייב:**

```
## Pre-RTH (לפני 16:30 IL)
[ ] CC scaffold tests עברו (pytest tests/v9/ ≥1694 pass)
[ ] Services עולים: curl http://localhost:8000/health
[ ] Bridge: tail /tmp/bridge.log — streams=12/12 · pushes rising
[ ] L4-1 live-trigger: VA reset בשעה 16:00 · בדוק session_va_ok=false לפני RTH

## RTH Axis checks (בוצע ב-16:30–17:30 IL)

### L4-2 Recency (TPO)
[ ] python3 scripts/l4_rth_probe.py --axis recency
[ ] delta == 0 ✓

### L4-3 Cardinality (Five-Min bars)  
[ ] python3 scripts/l4_rth_probe.py --axis cardinality
[ ] len(bars) == 20 ✓

### L4-4 Latency
[ ] python3 scripts/l4_rth_probe.py --axis latency
[ ] all endpoints < 500ms ✓

### G4 Smoke Trades (1 per package group)
עבור כל package הבא · Cursor יאשר לפני ואחרי:

#### Pkg 1 · Adaptive Stop
[ ] python3 scripts/g4_pkg5_latency_probe.py (כי אותה שרשרת)

#### Pkg 2a · OFA Entry
[ ] בשוק חי: כשמתקיים REACTIVE_LONG (b1-b4 על 5 דקות), בדוק:
    - log: `[FiveMin] FIRE: REACTIVE LONG (conf=...)`
    - DB: `SELECT * FROM v9_five_min_setups ORDER BY id DESC LIMIT 1`
    - expected: `setup_kind='REACTIVE'` · `direction='LONG'` · `stop_price` < entry

#### Pkg 2bc · OFA Config
[ ] בדוק שעם day_type=Nontrend → no_trade=True (log: "NO_TRADE (D-091.Q2)")

#### Pkg 3a · EXIT_V6 / Day-type targets
[ ] GET /api/v9/state/day-type → current_day_type ב-4 axes:
    - Recency: ts == now ± 60s
    - Quality: value in [Trend_Normal, Variation, NeutralExtreme, NeutralCenter, Nontrend, Normal]

#### Pkg 3b-3 · TrailEngine
[ ] כשיש עסקה פתוחה: בדוק /api/v9/trade/active → trail_active field
[ ] log: `[TrailEngine] armed=True` · stop moving with bars

#### Pkg 5a · Inv H&S / H&S Top
[ ] pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -k "hns" -v
[ ] python3 scripts/g4_pkg5_latency_probe.py

#### Pkg 5b · Double Bottom/Top
[ ] pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -k "double" -v

#### Pkg 5c · Bull/Bear Flag
[ ] pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -k "flag" -v

#### Pkg 8 · Auth Table
[ ] python3 scripts/g4_pkg8_pkg6_api_probe.py --pkg 8
[ ] expected: 70/70 cells return valid tier (not null)

#### Pkg 6 · TradeManager
[ ] python3 scripts/g4_pkg8_pkg6_api_probe.py --pkg 6
[ ] GET /api/v9/trade/active → structure matches S2_TRADEMGR_HOOKS_V1.md schema

## Systems-snapshot UAT
[ ] GET /cockpit/systems-snapshot
[ ] Quality: 6 systems present · no null values for active fields
[ ] Recency: snapshot.ts == now ± 30s
[ ] Cardinality: len(systems) == 6
[ ] Latency: response_time < 200ms

## 60-minute soak (17:30–18:30 IL)
[ ] tail /tmp/bridge.log — zero ERROR lines
[ ] tail /tmp/v9.err.log — zero WARNING/ERROR lines (new ones)
[ ] GET /api/v9/status every 5min × 12 — bridge.available=true all 12
[ ] Build Status tab: no RED patterns that weren't already RED at start

## מיכאל sign-off
[ ] כל הboxes מסומנים ✓
[ ] שלח screenshot/output של כל section לCursor לאישור G3 סופי
```

---

### פריט 3 · Template תיעוד G4 PASS

**קובץ:** `docs/reports/G4_UAT_SHADOW_GATE_PASS_2026-05-26.md` (skeleton)

Desktop יכתוב skeleton שCursor ימלא לאחר ה-RTH.

מבנה:
- §1 · Pre-RTH checks
- §2 · L4-2/3/4 axes results (עם actual values)
- §3 · G4 smoke results per package (עם actual DB values)
- §4 · Systems-snapshot UAT axes
- §5 · 60min soak summary
- §6 · Final verdict: SHADOW gate GREEN / RED
- §7 · Michael sign-off timestamp

---

## מסמכי spec authority שDesktop צריך לקרוא

Desktop חייב לקרוא את כל המסמכים הבאים לפני שכותב את ה-prompts:

| מסמך | נתיב | מה רלוונטי |
|---|---|---|
| D-091 | `docs/decisions/D-091_S2_LIVE_SCOPE.md` | כל הpackage specs |
| D-094 | `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md` | Trail engine G4 |
| S2 Auth Table | `docs/spec_authority/S2_AUTH_TABLE_V1.md` | Pkg 8 · 70 cells |
| S2 TradeMgr Hooks | `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` | Pkg 6 · hook schema |
| S2 Exit V6 | `docs/spec_authority/S2_EXIT_DEFINITION_V6.md` | Exit rules · UAT axis def |
| Pre-LIVE Protocol | `.cursor/rules/mems26-pre-live-protocol.mdc` | 4 UAT axes mandatory |
| G4 UAT Prep 5a/5b | `docs/handoff/G4_UAT_PKG5A_5B_PREP.md` | Integration tests §6.1 + latency §6.2 |
| STATUS_BOARD | `docs/plans/STATUS_BOARD.md` | Current G4 status per package |

---

## Cursor תבדוק (G3)

כאשר Desktop מחזיר את 3 הפריטים, Cursor יבצע:

1. **CC scaffolding prompt** — G3 adversarial scan: כל 7 שדות קיימים · FORBIDDEN zones מוגדרים · Golden tests מכסים שני axes לפחות · Stop signals כוללים "field not found"
2. **Michael checklist** — G3 spot check: לפחות 12 checkbox items · כל Pkg מצוין · 4 axes per section · DB query לכל smoke · sign-off רשמי
3. **Report skeleton** — G3 verify: §1–§7 קיימים · actual values placeholders (לא hardcoded) · verdict section ברורה

---

## Stop signals לDesktop

`STOP — <סיבה> · צריך החלטת מיכאל על <שאלה>` אם:
- חסר spec authority document בנתיב המצוין
- G4 smoke trade דורש פעולה בשוק שDesktop לא יכול לבצע (כמובן) — במקרה זה ציין בchecklist "Michael executes manually"
- נמצא package שG3 שלו לא PASS בSTATUS_BOARD — עצור ודווח

---

*End of META-PROMPT · G4 UAT + SHADOW Gate · Desktop → CC + Michael*
