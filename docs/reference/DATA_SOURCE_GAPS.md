# Data Source Gaps — Why categories 1–4 are not all "DB direct"

Date: 2026-05-28

## What you asked

Why some dashboard fields show **NULL** even though the **DB table already has data**, and why categories **1–4** were not designed as a single "read always from table X" layer.

---

## Root cause summary

| # | Category | Designed as | Gap |
|---|----------|-------------|-----|
| 1 | Bars / price | DB direct ✅ | Footprint has no UNIQUE key → no gap-fill; live price skips DB by design (WS) |
| 2 | TPO / POC / IB | **Split: file + DB** | `/tpo/current` reads **file**; KeyLevels read **DB**; IB had **wrong table priority** |
| 3 | Day Type | DB direct ✅ | IB only fills after RTH hour; pre-RTH `v9_day_type_history.ib_*` = NULL by spec |
| 4 | Woodies | DB partial | 13 JSON fields were **never migrated to columns** until migration 018 |

---

## Gap A — IB today NULL in Strip (fixed 2026-05-28)

**Symptom:** KeyLevels showed `IB: NULL` while DB had values.

**Evidence:**
```
v9_day_type_history.ib_high = NULL     ← KeyLevels read ONLY this
v9_tpo_sessions CASH.ib_high = 7534.25 ← data existed, unused
```

**Why it happened:** KeyLevels was wired to S1 table only. S1 IB locks from RTH bars at 10:30 ET. Before that, row is DEVELOPING/NULL. S5 TPO system already writes IB to `v9_tpo_sessions` from Sierra/bars.

**Fix:** `key_levels_routes.py` fallback chain:
1. `v9_day_type_history` (authoritative after S1 lock)
2. `v9_tpo_sessions.CASH`
3. `v9_tpo_sessions.GLOBEX`

API now returns `"sources": {"ib": "v9_tpo_sessions.CASH", ...}`.

---

## Gap B — `/tpo/current` bypasses DB (intentional, not fixed)

**Why:** P30 decision — chart POC lines need **sub-30s freshness**. Reading `tpo.json` avoids SQLite contention with bridge POSTs on single-worker uvicorn.

**Trade-off:**
- Chart / TPO lens → **file** (`tpo.json`)
- Key Levels / history → **DB** (`v9_tpo_sessions`)

**When they disagree:** Sierra file updates every ~3s; `v9_tpo_sessions` updates on S5 `process_bar` / snapshotter cadence. This is expected drift, not a missing table row.

---

## Gap C — Woodies JSON fields not in DB (fixed 2026-05-28)

**Symptom:** `woodies_5min.json` had `proj_hi`, `proj_lo`, `hfe_*`, `lsma_above_price` but engine/DB did not persist them.

**Why:** Original D-074 migration only added core CCI columns. DLL added proj/HFE fields in P30 without a matching SQL migration. `bars.py` INSERT silently dropped unknown columns (`except: pass`).

**Fix:**
- Migration `018_woodies_5min_extra_fields.sql`
- Extended `POST /api/v9/bars/woodies_5min` INSERT

**Still JSON-only (low priority):** `ccidiff_*`, `predictor_cci_high/low`, `prev_ohlc`, `low_prev_angle` — display/HUD fields, not used in pattern engine.

---

## Gap D — Woodies touch-points empty (known, separate fix)

**Symptom:** A4 shows `day_type:missing, tpo:missing, ...`

**Why:** `decision_tree._load_touchpoints()` refuses HTTP self-calls inside asyncio event loop (P30 woodies slow-handler fix). Touchpoints must be **pre-fetched** in `asyncio.to_thread` before `process_bar`. Not a missing DB table — missing wiring.

---

## Gap E — Sierra `tpo.json ib.found=false`

**Symptom:** DLL exports `ib.found: false` while Sierra UI shows IB.

**Why:** Study Input 15 (IB Study ID) wrong chart, wrong subgraph, or IB study not configured for "whole day" mode the user expects. DLL reads subgraph **6=high, 8=low** on Study ID 6.

**DB path still works:** S5 can compute IB from `v9_bars_5min` 09:30–10:30 window and write `v9_tpo_sessions`.

---

## Design principle going forward

1. **One writer per field** — Sierra → Bridge → DB; systems read DB.
2. **UI reads DB** — except `/tpo/current` (file) for chart latency.
3. **Every API field exposes `sources`** — which table supplied the value.
4. **New Sierra JSON fields → migration + INSERT in same PR** — no JSON-only drift.

---

## Verification after fixes

```bash
curl -s localhost:8000/api/v9/key_levels | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('IB', d['today']['ib_high'], d['today']['ib_low'], 'source', d['sources']['ib'])
"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_bars_5min_woodies)" | grep proj_hi
```

Backend restart required after code deploy.
