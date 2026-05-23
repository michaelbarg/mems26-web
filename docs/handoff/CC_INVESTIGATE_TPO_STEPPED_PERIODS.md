# CC Investigation — TPO stepped periods source (Issue B follow-up)

**Issued:** 2026-05-22 08:50 IL (05:50 UTC) · **For:** Claude Code · **Mode:** read-only investigation, no code edits, no service restarts, no git ops.
**Predecessor:** Issue B clarification (Michael, 2026-05-22 AM) — pink today POC/VAH/VAL lines must look like Sierra Study ID:3 developing TPO: stepped, RTH-only, 30-min step granularity.
**Cursor agent already shipped (this morning):** frontend fix to `tpoLevels.ts` + `TpoContinuityOverlay.tsx` + 5 new tests under `tests/v9/frontend/test_tpo_stepped_lines.py` — handles `+00:00`/`Z` suffix on `periods[].opened_ts` and defers the flat horizontal fallback when periods exist for today. **Frontend is ready; the bottleneck is now the data source.**

---

## What Michael wants the chart to show

Sierra Chart `MESM26_FUT_CME` reference (Study ID:3 "TPO Value Area Lines · Today (developing)" — see `docs/handoff/SIERRA_STUDIES_CONFIG_2026-05-19.md`):

- **Pink/magenta stepped** developing POC, VAH, VAL — recalculated **every 30 min** as a new TPO letter is added (A = 09:30, B = 10:00, C = 10:30 … M = 15:30 ET). Renders as a `LineType.WithSteps` from RTH open to "now".
- **White locked** previous-session POC, VAH, VAL — a single horizontal line for the prior CASH session. Already working ✓.
- **Green/cyan IB** lines — from `ib.high/mid/low`. Already working ✓.

Reference Sierra screenshot values (2026-05-19, doc 06): white VAH 7428.50 / POC 7411.25 / VAL 7390.75; magenta stepped ~7373 / 7382 / 7356.

**Michael's hard constraint:** do **not** propose new DLL work unless you can prove the existing DLL output is structurally insufficient. He says "we already fixed the DLL — the data is live". The investigation must validate or refute this against ground truth.

---

## What the DLL currently emits

Live snapshot of `/Users/michael/SierraChart_Data/v9_export/tpo.json` (2026-05-22 05:39 UTC, age ~1 s):

```json
{
  "type": "tpo",
  "version": "v9.4.2-p30.11",
  "export_ts": 1779429584,
  "session": {
    "poc": 7483.25, "vah": 7489.25, "val": 7475.25,
    "va_ok": true, "session_date": "2026-05-22",
    "session_high": 7494.75, "session_low": 7484.25,
    "total_volume": 0.0
  },
  "ib": { "found": true, "high": 7501.75, "mid": 7495.88, "low": 7490.0 },
  "prior_day": { "found": true, "high": 7493.75, "low": 7407.75, "close": 7493.25 },
  "previous_session": { "found": true, "poc": 7430.25, "vah": 7444.25, "val": 7415.0 }
}
```

**Critical observation:** the DLL emits a **single live value** for today's `session.poc/vah/val` (the latest developing VAH/POC/VAL at the moment of export). It does **not** emit a per-letter history array. There is **no `periods` / `letters` / `developing_history` key** in `tpo.json` at all.

---

## What the API returns as `periods[]`

`/api/v9/tpo/current` exposes a `periods[]` array. This is **NOT** from the DLL — it is built in `backend/v9/api/v9/tpo_routes.py::_load_tpo_periods` from a SQLite SELECT:

```sql
SELECT opened_ts, closed_ts, poc_price, vah_price, val_price
FROM v9_tpo_sessions
ORDER BY id DESC LIMIT 12
```

Latest 4 rows from `v9_tpo_sessions` (2026-05-22 05:40 UTC):

```
id=276 GLOBEX 2026-05-22  opened_ts=2026-05-21T16:50:00-04:00  POC=7491.25
id=275 CASH   2026-05-22  opened_ts=2026-05-21 17:20:00+00:00  POC=7454.75
id=183 CASH   2026-05-21  opened_ts=2026-05-20 15:55:00+00:00  POC=7440.75
id=181 GLOBEX 2026-05-21  opened_ts=1779327300                 POC=7454.5
```

Two structural problems with this source:

1. **It's per-SESSION not per-LETTER.** Each row covers an entire CASH or GLOBEX session — at most ~2 rows per day. Stepping these gives 2 segments, not 13.
2. **`opened_ts` format is inconsistent across rows** — ISO with `-04:00`, naive with `+00:00`, and bare unix-epoch-as-string all appear. The frontend fix this morning handles ISO/UTC suffix variations, but **does not** handle raw `1779327300` epoch strings. Worth confirming the actual writer (it's `backend/v9/systems/tpo/tpo_system.py`) and pinning a single format.

---

## The data gap, stated precisely

| Need | What we have | Gap |
|------|--------------|-----|
| 13 stepped POC/VAH/VAL points across today's RTH (09:30 → 16:00 ET) | 1 live point in `session.poc` + 2 daily rows in `v9_tpo_sessions` | **12 missing per-letter history points per day** |
| Consistent `opened_ts` format | 3+ formats in `v9_tpo_sessions` | Normalize to one (recommended: naive ET wall-clock, matches bar `ts` convention post-§9) |

---

## Cursor's three candidate paths (please grade)

### B1 — Backend snapshot job (no DLL change)

Run a 30-min boundary scheduler inside the backend (or in the bridge) that, during RTH (09:30 → 16:00 ET):

1. Reads `tpo.json::session.poc/vah/val` from disk.
2. Persists a row to `v9_tpo_history` (table already exists, schema matches: `ts, poc, vah, val, ib_high, ib_low, profile_shape, poc_migration_direction`). Table is **currently empty** — no writer exists.
3. Updates `_load_tpo_periods` to read from `v9_tpo_history` (per-letter) instead of `v9_tpo_sessions` (per-session) when serving the developing-today view.

**Pros:** zero DLL touch. Uses an already-defined empty table. Bounded scope (1 cron + 1 SELECT change).
**Cons:** snapshots can drift from Sierra's internal calc if the DLL exports lag a 30-min boundary by even a few seconds; the visual will match Sierra closely but not pixel-perfect.

### B2 — Extend `TPOSystem` consumer to write per-letter rows

Hook into the existing TPO consumer (`backend/v9/systems/tpo/tpo_system.py`) so that whenever a new bar crosses a 30-min boundary during RTH, it stamps the then-current `session` POC/VAH/VAL into `v9_tpo_history`. Same SELECT change as B1 to expose them.

**Pros:** event-driven (no timer drift), tied to bar arrival.
**Cons:** more invasive (touches the consumer hot path); risk of double-write under high bar churn; harder to backfill historical days.

### B3 — DLL exposes per-letter history (Michael rejected unless proven necessary)

`MES_AI_DataExport.cpp::v9_tpo_to_json` reads Sierra Study ID:3 subgraphs (POC dev, VAH dev, VAL dev) **at multiple chart indices** — one read per 30-min boundary during RTH — and emits a `periods[]` array. Backend reads this directly.

**Pros:** canonical, pixel-perfect with Sierra by construction. No backend storage / no clock drift.
**Cons:** Michael does not want DLL work unless investigation shows B1/B2 cannot match Sierra closely enough.

---

## What CC should investigate (please return a recommendation, no code changes)

### 1. Verify the data inventory

```bash
# Confirm tpo.json has no periods / history array
python3 -c "import json; d=json.load(open('/Users/michael/SierraChart_Data/v9_export/tpo.json')); print(list(d.keys()))"

# Confirm v9_tpo_history is empty
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db \
  "SELECT COUNT(*) FROM v9_tpo_history;"

# Inspect tpo_system writer to v9_tpo_sessions — is there *any* per-letter
# emission already wired up that I missed?
grep -nE "INSERT INTO v9_tpo|tpo_history|letter" \
  backend/v9/systems/tpo/tpo_system.py \
  | head -40
```

### 2. Confirm the inconsistent `opened_ts` format originates in the writer (not a normalization bug)

```bash
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db \
  "SELECT id, session_type, trading_date, opened_ts FROM v9_tpo_sessions \
   ORDER BY id DESC LIMIT 30;"
```

If raw unix epochs like `1779327300` come from one code path and ISO `-04:00` from another, name the code paths and propose normalization.

### 3. Read these files to ground your recommendation

| File | Why |
|------|-----|
| `backend/v9/api/v9/tpo_routes.py` (especially `_load_tpo_periods`, lines 75–106) | Where the per-letter SELECT would land |
| `backend/v9/systems/tpo/tpo_system.py` | Existing writer to `v9_tpo_sessions` — could host B2 hook |
| `backend/v9/db/models/tpo_history.py` | Empty table schema waiting for a writer |
| `docs/handoff/SIERRA_STUDIES_CONFIG_2026-05-19.md` (Study ID:3 section) | DLL-side option B3 — confirm Subgraph indices |
| `docs/reports/PROMPT30_10b_TPO_LEVELS_FIX.md` §"Still needed" | Original P30 framing of "Native `periods[]` in `tpo.json`" |
| `frontend/v9/src/v9/components/chart/v5b/TpoContinuityOverlay.tsx` (post-fix from this morning) | What the frontend now expects on the wire |

### 4. Estimate effort + risk for each path

For each of B1, B2, B3 give:

- **Files touched**
- **Lines of change (LOC) estimate**
- **Risk to existing hot paths** (consumer loop, bar churn, DB I/O)
- **Pixel-fidelity vs Sierra** (close enough? identical? off by a few cents?)
- **Effort in hours**

### 5. Pick one

State your **single recommended path** with one paragraph of reasoning. Note any edge cases the recommendation must handle (e.g., session-day rollover at 18:00 ET, DST transitions, restart mid-RTH after snapshots have been missed).

---

## Deliverable format

A single Markdown block, no embellishment:

```
TPO STEPPED-PERIODS INVESTIGATION — 2026-05-22 <HH:MM> ET

DATA INVENTORY:
  tpo.json keys:       <list>
  v9_tpo_history rows: <count>
  v9_tpo_sessions writer: <file:line>
  opened_ts format origin (raw unix vs ISO): <file:line>

GAP CONFIRMED:
  per-letter snapshots missing: YES / NO
  if NO, where they are: <answer>

PATH GRADES:
  B1 backend snapshot job:    LOC=__, risk=__, fidelity=__, effort=__h
  B2 TPOSystem letter hook:   LOC=__, risk=__, fidelity=__, effort=__h
  B3 DLL per-letter periods[]: LOC=__, risk=__, fidelity=__, effort=__h

RECOMMENDED PATH: <B1 | B2 | B3>
REASONING (1 paragraph):
<text>

EDGE CASES TO HANDLE:
- <bullet>
- <bullet>

NO CODE CHANGE APPLIED IN THIS INVESTIGATION.
```

---

## Guardrails (workspace rules)

- Read-only file system + DB.
- **No service restarts, no `kill`, no `launchctl`, no `screen`.**
- **No edits to `sc_study/`, `bridge/`, LaunchAgent, `.cursor/`.**
- **No git commits or pushes.**
- If a hypothesis cannot be confirmed by data within ~10 minutes, **stop and tell Michael** — do not guess to fill the table.
- Bridge must continue pushing only to `http://localhost:8000` — do not touch any `CLOUD_URL` config.
- Reports go under `docs/reports/` if Michael asks; otherwise return the deliverable inline.

---

## What happens after CC returns

1. Michael picks the recommended path.
2. Cursor implements minimal change with regression test (one of: backend snapshot job, TPOSystem hook, or — only if Michael flips on — a DLL handoff prompt for CC).
3. Live UAT after RTH open (17:30 IL) — chart pink lines step every 30 min in the same shape as Sierra's developing TPO study.
4. Update `docs/handoff/P31_TASK_BOARD.md` §0 and `docs/reports/PROMPT_P31_*.md`.
