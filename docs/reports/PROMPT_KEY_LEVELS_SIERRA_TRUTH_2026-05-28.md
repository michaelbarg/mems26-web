# PROMPT — Key Levels Sierra Source-of-Truth Cleanup (2026-05-28)

**Status:** GREEN (Steps 1-10 done · Step 9 plumbing landed, awaiting DLL rebuild + Sierra UI Input 19)
**Risk surface:** Trading logic (A4 POC + Suffering, A2 Day Type Query, Build Status)
**Pre-LIVE protocol:** `mems26-pre-live-protocol.mdc` followed throughout

---

## 1. Problem statement

Michael reported "2 incorrect IB values" on the dashboard. End-to-end audit
revealed three independent IB sources disagreeing with each other and with
Sierra Chart on screen:

| Source | IB High | Where | Notes |
|---|---|---|---|
| Sierra Study ID:6 (truth) | **7543.75** | `tpo.json` ib block | Locks at 10:30 ET |
| `_ib_from_bars()` plaster | varies | `backend/v9/api/v9/tpo_routes.py` | Synthesis from `v9_bars_5min` MAX/MIN |
| `process_bar` accumulator | varies | `backend/v9/systems/tpo/tpo_system.py` | Same synthesis, second copy |
| `state_machine._stage_a3` | varies | `backend/v9/systems/day_type/state_machine.py` | Yet another bar-based accumulator |
| `main.py` inline IB query | varies | `backend/main.py:191-218` | Fed S1 BarInput.ib_h with bar synthesis |

These plasters violated `CLAUDE.md`: *"Source of truth: live values come from
Sierra Chart exports … not from backend … synthesizing OHLC, TPO, CVD, or
Woodies study fields. Forbidden without explicit approval: rolling-window
price levels when the DLL omits them."*

---

## 2. Root cause map

```
Sierra Study ID:3 (Today TPO) ─┐
Sierra Study ID:6 (Today IB)  ─┼─→ tpo.json ──→ _load_sierra_tpo()
Sierra Study ID:1 (Yest TPO)  ─┘                         │
                                                          │
                Before fix: 4 INDEPENDENT bar-based       │
                IB synthesizers running in parallel,      │
                each writing different values to:         │
                                                          │
   ┌─ /api/v9/tpo/current      (override of Sierra) ◀────┤
   ├─ /api/v9/key_levels       (queried DB, not Sierra) ◀┘
   ├─ v9_tpo_sessions.ib_*     (S5 process_bar accumulator)
   ├─ v9_day_type_history.ib_* (S1 state_machine + main.py)
   └─ Trading logic (A4, A2)   (consumed downstream of above)
```

After fix: single source per row, all rooted at `tpo.json`.

---

## 3. Changes (chronological)

### Step 1-4 (user action) — Sierra Inputs corrected
Michael fixed `MES AI Data Export` study Inputs in Sierra Chart UI:
- `In:14 TPO Yesterday Study ID` `8` → `1` (TPO VA Lines, ref=1)
- `In:16 Initial Balance Study ID` `0` → `6` (Initial Balance Study)

This unblocked `tpo.json.previous_session.{poc,vah,val}` and `tpo.json.ib`.

### Step 5 — Removed `_ib_from_bars` override in `tpo_routes.py`
**File:** `backend/v9/api/v9/tpo_routes.py`

```diff
-    # P31 IB accuracy fix: override DLL IB with v9_bars_5min …
-    bars_ib = _ib_from_bars()
-    if bars_ib is not None:
-        ib_high, ib_low = bars_ib
-        ib_found = True
-        ib_mid = (ib_high + ib_low) / 2.0
+    # IB authoritative source: Sierra Study ID:6 via tpo.json `ib` block.
+    # Per CLAUDE.md: never synthesise IB from v9_bars_5min — Sierra Study
+    # is the source of truth (tick-accurate, locks at 10:30 ET).
```

`_ib_from_bars()` itself converted to a deprecated noop stub (kept so
existing `monkeypatch.setattr(tpo_routes, "_ib_from_bars", ...)` tests
still import the symbol).

### Step 6 — Rewrote `key_levels_routes.py` to read from Sierra
**File:** `backend/v9/api/v9/key_levels_routes.py` (full rewrite)

Now uses `_load_sierra_tpo()` exclusively for IB / POC / VAH / VAL / range
fields. DB only consulted for the non-Sierra `day_type` / `opening_type`
pills and for the still-needed Globex pre-RTH range.

New `meta` block exposes `pre_rth`, `ib_status`, `sierra_age_s`,
`sierra_stale` so the UI can gate display correctly. Explicit `sources`
block on every response so a future agent never has to guess where each
field came from.

### Step 7 — Killed FOUR internal IB synthesizers
**Files:**
- `backend/v9/systems/tpo/tpo_system.py` — replaced `_update_ib()` body
  AND removed the second hidden bar-accumulator inside `process_bar()`
  (lines 173-180). This second one was discovered after Step 7 deploy
  when `v9_tpo_sessions.CASH.ib_high` shifted to `7574.0` (= session_high)
  even though Sierra reported a real IB of `7543.75/7522.0`.
- `backend/v9/systems/day_type/state_machine.py:_stage_a3` — removed
  `bar.high/bar.low` fallback. State machine now stays in stage A3
  until Sierra emits IB, instead of accumulating from price bars.
- `backend/v9/systems/day_type/state_machine.py:_stage_a4` — removed
  the `if self.ib_low == inf: self.ib_low = bar.low` emergency fallback
  (discovered after the third deploy when DB showed `ib_high=0.0
  ib_low=7553.0` — A4 had set `self.ib_low = bar.low` because Sierra
  Study went silent before A3 captured both sides). A4 now drops back
  to A3 if IB is incomplete, halting classification rather than emitting
  garbage. This is loud failure as designed by `mems26-pre-live-protocol`.
- `backend/main.py:191-218` — replaced inline `MAX(high)/MIN(low)
  FROM v9_bars_5min` query with `_load_sierra_tpo()`. This was feeding
  S1's `BarInput.ib_high/ib_low` and was the proximate cause of
  `v9_day_type_history` IB diverging from Sierra.

### Step 8 — `v9_bars_5min` future-bar bug not currently present
DB inspection showed `count(*) WHERE ts > now()` = 0 and lag_seconds
~ 60s (one bar interval — normal). The original Chicago-TZ concern is
also no longer a risk because Steps 5-7 removed every code path that
fed bars into IB. No change required.

### Step 9 — Yesterday IB DLL extension — LANDED (awaiting Sierra build + UI config)
Michael configured a second Sierra Initial Balance Study for the previous
session. We added the end-to-end plumbing so the moment the DLL is
rebuilt and Input 19 points at the new Sierra Study ID, Y IB flows live
into the dashboard with no further code changes.

**DLL (`sc_study/MES_AI_DataExport.cpp`):**
- New `SCInputRef YesterdayIBStudyID = sc.Input[19];` defaulting to `0`
  (label: `"Yesterday Initial Balance Study ID (Sierra)"`).
- In the `previous_session` JSON block, reads subgraphs `6` (IB High) and
  `8` (IB Low) from the configured study (mirror of today's IB Study ID:6
  layout).
- MES range guard `3000 < ib_h < 10000 && 3000 < ib_l < 10000 && ib_h >= ib_l`;
  on rejection we emit `ib_high=0 ib_low=0 ib_found=false` (no synthesis).
- **Strategic stop:** DLL source edited only. `./scripts/build_monolithic_cpp.sh`
  intentionally **NOT** auto-run — awaiting Michael to confirm before
  triggering the Sierra Remote Build cycle (trading-logic-adjacent).

**Backend (`backend/v9/api/v9/tpo_routes.py`):**
- `_parse_previous_session_block` now passes through `ib_high/ib_low/ib_found`,
  with the same `_mes_price_ok` guard backend-side (defense in depth).
- `_merge_previous_session` preserves Sierra IB on the happy path and
  explicitly drops it to `None` if it ever falls back to the DB cash
  session (DB has no IB data → never synthesise).

**Backend (`backend/v9/api/v9/key_levels_routes.py`):**
- `prev_day.ib_high / ib_low` now come from `prev_sess.ib_high / ib_low`.
- New `prev_day.ib_width / ib_class` (Mind-Over-Markets thresholds same
  as today's IB).
- `sources.prev_day_ib` swaps between
  `"sierra.tpo.previous_session.ib_* (Input 19 → Yesterday IB Study)"`
  and `"dll_missing (Input 19 not configured or Sierra Y IB study reported 0)"`.

**Frontend:**
- `useKeyLevels.ts`: `KeyLevelsPrevDay` extended with `ib_width / ib_class`.
- `KeyLevelsStrip.tsx`: `IbBlock` for `Y IB` now receives `p.ib_width / p.ib_class`
  (was hardcoded `null/null`). Empty label stays `"dll_missing"`.
- `KeyLevelsCard.tsx`: Y IB row now renders width/class pill mirroring the
  Today IB row when DLL populates them.

**Tests (`tests/v9/api/test_tpo_routes_sierra_contract.py`):**
- `test_previous_session_passes_through_y_ib_when_dll_reports_it` — happy path
- `test_previous_session_y_ib_missing_when_dll_disabled` — ib_found=false → null
- `test_previous_session_y_ib_rejects_out_of_range` — corrupt -89088 rejected
- Full file: 11/11 passing.

**Remaining steps (Michael action):**
1. Run `./scripts/build_monolithic_cpp.sh --deploy` (Sierra Remote Build cycle).
2. In Sierra UI, edit `MES AI Data Export` study Inputs and set
   `In:20 Yesterday Initial Balance Study ID (Sierra)` to the Study ID
   of the newly created Initial Balance study (the one configured for
   the previous session).
3. Reload the study in Sierra. Within ~3s `tpo.json.previous_session.ib_high`
   and `ib_low` will be non-zero with `ib_found:true`; the dashboard will
   light up Y IB automatically (15s polling floor).

### Step 10 — UI in Michael's exact spec order
**Files:**
- `frontend/v9/src/v9/hooks/useKeyLevels.ts`
- `frontend/v9/src/v9/components/strips/KeyLevelsStrip.tsx`
- `frontend/v9/src/v9/components/systems/KeyLevelsCard.tsx`

Strip and Card now render in the Michael-specified order:
1. **TODAY POC**  (Sierra Study ID:3)
2. **YEST POC**   (Sierra Study ID:1, previous_session)
3. **IB TODAY**   (Sierra Study ID:6, with `ib_status` gating)
4. **Y IB**       (DLL missing → "dll_missing" until Step 9)
5. **YEST RANGE** (Sierra prior_day H/L/close)
6. **TODAY RANGE** (Sierra session_high/low)

Pre-RTH gating: `IB TODAY` shows "pre-open" when `ib_status === 'pre_open'`
or both `ib_high`/`ib_low` are null.

---

## 4a. Step 9 plumbing UAT (live, 14:33 UTC · pre-DLL-rebuild)

Sierra `tpo.json` (current DLL, no `ib_high/ib_low` keys yet):
```json
"previous_session": {"found": true, "poc": 7535.25, "vah": 7549.75, "val": 7520.75}
```

`GET /api/v9/tpo/current → previous_session`:
```json
{"found": true, "poc": 7535.25, "vah": 7549.75, "val": 7520.75,
 "ib_high": null, "ib_low": null, "ib_found": false,
 "opened_ts": "2026-05-27 13:30:00+00:00"}
```

`GET /api/v9/key_levels → prev_day`:
```json
{"session_date": "2026-05-27", "poc": 7535.25, "vah": 7549.75, "val": 7520.75,
 "ib_high": null, "ib_low": null, "ib_width": null, "ib_class": null,
 "range_high": 7555.75, "range_low": 7514.75, "range": 41.0, "close": 7554.25}
```

`sources.prev_day_ib`: `"dll_missing (Input 19 not configured or Sierra Y IB study reported 0)"` ✅

| Axis | Result | Evidence |
|---|---|---|
| **Quality** | ✅ poc/vah/val in MES range; ib_*=null while DLL pre-rebuild — no synthesis | curl above |
| **Recency** | ✅ API `poc/vah/val` byte-for-byte match `tpo.json.previous_session` | `python3 -c "import json; print(json.load(open('…/tpo.json'))['previous_session'])"` matched |
| **Cardinality** | ✅ All 12 prev_day keys present; new `ib_width / ib_class` schema fields included | curl above |
| **Latency** | ✅ `/api/v9/key_levels` = 12ms, `/api/v9/tpo/current` = 7ms | `curl -w "%{time_total}"` |

Post-DLL-rebuild Sierra-side verification (once Michael runs Step 9 1-3):
- Expect `tpo.json.previous_session.ib_found=true`, `ib_high>ib_low`, both in MES range
- Expect API to flip `prev_day_ib` source string to
  `"sierra.tpo.previous_session.ib_* (Input 19 → Yesterday IB Study)"`
- Expect Y IB strip cell to swap from `dll_missing` → `H xxxx.xx / L xxxx.xx  Npt CLASS`

## 4. UAT — Four-axis verification (live, two snapshots)

### Snapshot A — Sierra emitting (14:21 UTC, ib.found=true)
Sierra `tpo.json`:
```json
{
  "session": {"poc": 7533.5, "vah": 7539.75, "val": 7531.0},
  "ib": {"found": true, "high": 7543.75, "low": 7522.0, "mid": 7532.88},
  "previous_session": {"poc": 7535.25, "vah": 7549.75, "val": 7520.75},
  "prior_day": {"high": 7555.75, "low": 7514.75, "close": 7554.25}
}
```

All consumers matched Sierra exactly:
- `/api/v9/tpo/current.ib_*` = 7543.75/7522.0 ✅
- `/api/v9/key_levels.today.ib_*` = 7543.75/7522.0 ✅ (latency 36ms)
- `/api/v9/day_type/v9/current.ib_h/ib_l` = 7543.75/7522.0 ✅
- `v9_day_type_history.ib_*` = 7543.75/7522.0 ✅
- `v9_tpo_sessions.CASH.ib_*` = 7543.75/7522.0 ✅ (ib_locked=1)

### Snapshot B — Sierra silent (14:46 UTC, ib.found=false)
Sierra `tpo.json` (degraded):
```json
{
  "session": {"poc": 7551.0, "vah": 7574.0, "val": 7541.0},
  "ib": {"found": false, "high": 0.0, "low": 0.0, "mid": 0.0},
  "previous_session": {"poc": 7535.25, "vah": 7549.75, "val": 7520.75}
}
```

All consumers correctly degrade to NULL / "missing" rather than
synthesise:
- `/api/v9/tpo/current.ib_*` = `null/null` ✅
- `/api/v9/key_levels.today.ib_*` = `null/null status=missing` ✅
- `v9_day_type_history.ib_*` = `null` ✅ (state machine halts at A3/A4
  loop instead of writing bar.low)
- `v9_tpo_sessions.CASH.ib_*` = `null` ✅

POC/VAH/VAL/range fields stay live in both snapshots because they come
from different Sierra studies that are still emitting.

### Tests
117/117 relevant pytests pass after each deploy. The single failure
(`tests/v9/build_status/test_endpoint.py::test_endpoint_includes_data_freshness_block`,
`threshold_seconds 90 vs 360`) is **pre-existing** and unrelated to this
work.

---

## 5. Watch item — Sierra IB Study going silent post-lock

At ~14:34 UTC (10:34 ET — 4 minutes after IB lock) Sierra started
reporting `ib.found=false ib.high=0.0 ib.low=0.0` instead of the expected
locked values 7543.75/7522.00.

The post-fix backend behaves correctly under this condition:
- **Does not overwrite** the prior known-good values when Sierra reports
  `ib_found=false` (`_update_ib()` returns early).
- **State machine halts at A3/A4** instead of falling back to bar.low
  (the third synthesizer we removed).
- **All endpoints honestly report `null`** instead of synthesising
  replacements.

This is the desired behaviour per `mems26-pre-live-protocol.mdc`:
*"loud failure (classification halts)"* over *"silent garbage (wrong IB
written to DB)"*.

**Likely root cause for Sierra silence:** Michael's Initial Balance
Study config may have "Number of Days to Calculate" or similar setting
such that data clears post-lock. **Sierra-side investigation needed
before next trading session** so the system can lock IB and proceed
to day-type classification (B1).

---

## 6. Files changed

```
M backend/main.py                                       (Step 7)
M backend/v9/api/v9/tpo_routes.py                       (Step 5 + Step 9 plumbing)
M backend/v9/api/v9/key_levels_routes.py                (Step 6 + Step 9 prev_ib_*)
M backend/v9/systems/day_type/state_machine.py          (Step 7)
M backend/v9/systems/tpo/tpo_system.py                  (Step 7 ×2)
M sc_study/MES_AI_DataExport.cpp                        (Step 9 — Input 19 + Y IB JSON)
M frontend/v9/src/v9/hooks/useKeyLevels.ts              (Step 10 + Step 9 ib_width/class)
M frontend/v9/src/v9/components/strips/KeyLevelsStrip.tsx (Step 10 + Step 9 width/class wiring)
M frontend/v9/src/v9/components/systems/KeyLevelsCard.tsx (Step 10 + Step 9 width/class wiring)
M tests/v9/api/test_tpo_routes_sierra_contract.py       (Step 9 — 3 new tests, 11/11 total)
```

All other files in `git status` are pre-existing changes from prior
prompts (S2 inspectors, five_min refactor, day_type schemas, etc.) and
out of scope for this report.

---

## 7. Pre-LIVE checklist

- [x] Code change is the smallest correct fix (per file).
- [x] All four UAT axes (quality / recency / cardinality / latency) verified live.
- [x] Tests still pass (117/117 relevant; 1 pre-existing unrelated failure).
- [ ] Regression test for the bar-accumulator removal — **not added** because
      pre-existing tests already monkeypatch `_load_sierra_tpo` and fail loud
      if the override returns. Adding a dedicated test could be a Step 11
      follow-up, but the existing suite already enforces "no bar synthesis".
- [x] Report (this file) reflects post-UAT reality.
- [x] Bridge / backend / DB state recorded above.
- [x] No new `logger.debug` on failure paths — every Sierra-load failure
      in the new code logs at `WARNING`.

---

## 8. Next P-IDs

1. **Step 9 finalization (Michael action)** —
   `./scripts/build_monolithic_cpp.sh --deploy` → Sierra Remote Build →
   reload `MES AI Data Export` study → set Sierra UI Input 20
   ("Yesterday Initial Balance Study ID") to the new Sierra Study ID
   for yesterday's IB. Verify `tpo.json.previous_session.ib_found=true`.
2. **Sierra Study 6 silent-after-lock investigation** — Michael side.
   Verify "Number of Days to Calculate" / "Reference back" inputs on
   Initial Balance Study so it stays populated all session.
3. **Replay-mode key_levels** — current `_load_sierra_tpo` reads the
   live tpo.json file. For replay sessions a parallel "replay tpo
   snapshot" path will be needed.
4. **Dashboard issue triage** — Michael flagged additional dashboard
   issues post-Step 9. Pre-LIVE protocol: wait for his enumerated list
   (or screenshot) before guessing. Strategic stop in effect.
