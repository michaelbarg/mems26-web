# Investigation Prompt — Why Day Type = "Nontrend" on 2026-05-19?

**For:** new chat, fresh agent (no prior context)
**Mode:** read-only diagnostic. Do **not** edit code, do **not** restart services, do **not** commit.
**Repo:** `~/Downloads/mems26_web_git`
**Date in question:** 2026-05-19 (US futures session, MES_M26 / ES_M26)
**Reporter:** Michael — "I'm certain today was NOT a Non-Trend day. Price action showed clear directional movement. The cockpit classified it as Nontrend. Find out why."

---

## 1. Context (MEMS26 Day Type Engine)

The engine produces one of seven labels per RTH session:

```python
class DayType(str, Enum):
    Trend_Normal = "Trend_Normal"
    Trend_DD     = "Trend_DD"        # Double Distribution Trend
    Variation    = "Variation"
    Normal       = "Normal"
    Neutral      = "Neutral"
    Nontrend     = "Nontrend"        # ← today's verdict; Michael disputes
    UNKNOWN      = "UNKNOWN"
```

It runs a 13-stage state machine (`A1→A2→A3→A4→B1…B6→C1→C2→C3`) and locks a
verdict around session_min ≥ 210 (13:00 ET) or when confidence ≥ 0.85.

**Key source files (read these first, in order):**

```
backend/v9/systems/day_type/schemas.py           # enums + state model
backend/v9/systems/day_type/state_machine.py     # 13-stage progression + voting
backend/v9/systems/day_type/decision_matrix.py   # vote weights per stage
backend/v9/systems/day_type/detector.py          # opening type + drive direction
backend/v9/systems/day_type/opening_detector.py
backend/v9/systems/day_type/targets_table.py     # tactical targets per day type
backend/v9/systems/day_type/hydration.py         # how DB rows feed back into state
backend/v9/api/v9/day_type_v9_routes.py          # /api/v9/day_type/* endpoints
backend/v9/db/migrations/versions/014_day_type_v9_columns.sql  # DB schema
```

---

## 2. What the agent must answer (1-page deliverable)

1. **Final classification** for 2026-05-19 — exact `day_type`, `confidence`, `lock_state`, the timestamp it locked at.
2. **Top three votes by weight** that pushed the decision toward `Nontrend` — include stage, reason, and weight.
3. **Inputs that drove those votes** — IB width, opening type, drive direction, gap size+direction, extensions_up/down, range vs ATR, profile shape if available.
4. **Comparison to ground truth** — did today's RTH session on the live MES_M26 chart actually look like a non-trend day, or did it have clear directional movement (range expansion, sustained one-side extensions)?
5. **Root cause hypothesis** — one of:
   - (a) Inputs are correct but Nontrend rule fires too aggressively (criteria too loose)
   - (b) Inputs are wrong (e.g. IB width / extension counts misfed)
   - (c) Voting weights skewed Nontrend over Trend_Normal
   - (d) Lock fired too early on stale evidence
   - (e) Hydration replayed stale state from DB after a restart
6. **Recommendation** — specific file + function + line number where the fix would go. Do **not** apply it; just point.

---

## 3. Step-by-step investigation procedure

### A) Live API snapshot (must run first, while session is fresh)

```bash
curl -s http://localhost:8000/api/v9/day_type/state | jq .
curl -s http://localhost:8000/api/v9/day_type/history?limit=50 | jq '.items[] | {ts, day_type, confidence, lock_state, opening_type, ib_width, behavior, range_category, failed_extension, session_min}'
```

Capture the raw JSON in your report. Note the exact `day_type` and the
`lock_state` (`PENDING` / `LOCKED` / `LOCKED_FORCED`).

### B) DB query for today's full classification trail

```bash
sqlite3 ~/Downloads/mems26_web_git/data/mems26_local.db <<'SQL'
.headers on
.mode column
SELECT ts, day_type, confidence, lock_state, opening_type, ib_width,
       behavior, range_category, failed_extension, session_min, stage
FROM v9_day_type_history
WHERE date(ts, 'unixepoch', 'localtime') = '2026-05-19'
ORDER BY ts ASC;
SQL
```

If the trail shows the verdict flipping (e.g. Trend_Normal early → Nontrend
late), capture the flip timestamp and which inputs changed around it.

### C) Cross-check the inputs against Sierra Chart

Look up today's true values from `~/SierraChart_Data/v9_export/`:

```bash
python3 - <<'PY'
import json
for p in ('tpo.json','woodies_5min.json','cumulative_delta.json'):
    d = json.load(open(f'/Users/michael/SierraChart_Data/v9_export/{p}'))
    print(p, '→ keys:', list(d.keys()))
PY
```

Manually answer:

- **IB high / IB low / IB width** (RTH 09:30–10:30 ET). Compare to
  `ib_narrow_max_pt=15` / `ib_medium_max_pt=25` thresholds in
  `DayTypeConfig`.
- **Opening type** — did 09:30–09:45 look like OPEN_DRIVE, OPEN_TEST_DRIVE,
  OPEN_REJECTION_REVERSE, or OPEN_AUCTION_IN/OUT?
- **Extensions** — how many IB-high and IB-low breakouts after 10:30 ET?
- **Range vs ATR** — `tpo.session.session_high - session_low` vs the bar's
  `atr` (if recorded).
- **Profile shape** — TPO `prior_day.found` and any shape hint (D, P, b,
  bell, double distribution) from the chart screenshot if Michael provides
  one.

### D) Map inputs → votes → final label

Read `decision_matrix.py` and trace which votes Nontrend wins. Typical
Nontrend triggers (per Auction Market Theory):

- IB NARROW (<15 pt) + COMPRESSED range
- Both-side extension + DELTA_BOOST_NEUTRAL (+0.2 to neutral prob)
- Opening type = OPEN_AUCTION_IN with NEUTRAL drive
- Low session range vs ATR (range_category=COMPRESSED)

If today's chart shows a clear trending move (e.g. extensions only one
side, range_category=EXPANDED or EXTREME), Nontrend should *not* win. That
mismatch IS the bug.

### E) Lock timing audit

If `lock_state=LOCKED` happened before `session_min=210` (i.e. before
13:00 ET) with `confidence>=0.85`, check whether that early lock was
warranted, or whether late-session trending behavior would have flipped
the verdict. The engine has a "min_session_min_for_lock" guard at 210;
verify it was honoured.

---

## 4. Mandatory guardrails

- **Read-only.** Do not edit any source file. Do not run migrations.
- **No service restarts.** Do not touch the bridge, LaunchAgent, screen
  sessions, or `npm run dev`.
- **No DB writes.** Use `sqlite3` only with SELECT statements (no
  INSERT/UPDATE/DELETE/REPLACE).
- **No git ops.** Do not stage, commit, push, or branch.
- **No cloud calls.** Operate locally only. `CLOUD_URL` must remain
  `http://localhost:8000`.
- **No `sc_study/` edits.** That's Claude Code territory.
- **No `.cursor/` edits.** That's Cursor app config.

If a step fails (e.g. DB locked, endpoint times out), report it — do
**not** improvise a workaround.

---

## 5. Deliverable format (exactly this layout)

Send Michael a single message in this shape:

```
DAY TYPE INVESTIGATION — 2026-05-19

VERDICT (from /api/v9/day_type/state):
  day_type = <Nontrend|...>
  confidence = <0.xx>
  lock_state = <PENDING|LOCKED|LOCKED_FORCED>
  locked_at_ts = <unix|null>
  locked_at_session_min = <int|null>

TOP 3 VOTES:
  1. <DayType> weight=<x.xx> stage=<A1..C3> reason=<short>
  2. ...
  3. ...

INPUTS THAT DROVE THE VERDICT:
  IB width = <pt> → IBWidth.<NARROW|MEDIUM|WIDE>
  opening_type = <enum>, drive_direction = <UP|DOWN|NEUTRAL>
  gap = <pt> <UP|DOWN|FLAT>
  extensions_up = <n>, extensions_down = <n>
  range_category = <COMPRESSED|NORMAL|EXPANDED|EXTREME>
  failed_extension = <NONE|STRONG_FAILED_UP|...>

GROUND TRUTH FROM SIERRA:
  Actual RTH range high/low = <h>/<l>
  Visible behavior = <"clear uptrend"|"compressed"|"two-way auction"|...>
  Sierra Chart screenshot timestamp = <if Michael provided>

ROOT CAUSE HYPOTHESIS:
  <a|b|c|d|e from §2.5> — one paragraph

RECOMMENDED FIX LOCATION (do NOT apply):
  file: backend/v9/systems/day_type/<file>.py
  function: <name>
  line: <n>
  proposed change: <one sentence>
```

Do not embellish. Do not add markdown decoration. Send exactly that block.

---

## 6. After the agent reports back

Michael will decide whether to:

- Adjust a threshold in `DayTypeConfig` (read-only change),
- File a P-ID for a code fix in `state_machine.py` / `decision_matrix.py`,
- Or accept the verdict if the inputs match the chart truthfully.

The Cursor agent (current chat) will then implement the chosen change
with a regression test, following the four UAT axes from
`.cursor/rules/mems26-pre-live-protocol.mdc` (quality / recency /
cardinality / latency where applicable).
