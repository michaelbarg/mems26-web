# DATA_CHAIN_FIX — 2026-07-17 (D-0717-A/B/C)

Author: cowork-dev subagent (data-chain + day-type wiring). Scope: the three live bugs
confirmed today. All code edits are minimal, fail-open, never-raise into trading paths.
**Nothing is committed; backend restart required for A+B to take effect live.**

Files changed (code): `backend/v9/systems/five_min/five_min_system.py` ·
`backend/v9/systems/build_status/aggregator.py` · `backend/v9/api/v9/bars.py`
Files added: `scripts/check_bars_ts_types.py` ·
`tests/v9/regression/test_auth_daytype_override.py` ·
`tests/v9/regression/test_bars_5min_ts_binding.py` · this doc.
**Not touched:** woodies write path, `trade_context.py`, DLL source (see item C), any flag.

---

## A. Auth-table day-type ignored DAY_TYPE_MANUAL_OVERRIDE (found 18:06)

### Root
`trade_context.get_live_day_type()` is the ONE override-aware source (it returns the
`DAY_TYPE_MANUAL_OVERRIDE=YYYY-MM-DD:Label` value FIRST, before the
`DAYTYPE_GATE_LIVE_V1` gate — `trade_context.py:536-546`). Two S2 auth-cell consumers
never consulted it:

1. **The trading seam** — `five_min_system.py` fire path called
   `compute_v2_sizing(day_type=self.current_day_type or "Normal", ...)` (old line 1333).
   `self.current_day_type` is fed by `_on_day_type_update` events (OLD engine) +
   hydration from `v9_day_type_state`. Inside `compute_v2_sizing` →
   `_auth_cell(auth_matrix, pattern, direction, day_type)` — so the auth VERDICT
   resolved `INITIATIVE_LONG × Normal` = **SKIP row** while the override said
   `Variation` = **FULL row** (`auth_table_v1.py:51-53`). The emit path
   (`_emit_day_type = _get_live_dt() or ...`) was already override-aware — the bug was
   the sizing/auth call that runs BEFORE it.
2. **The display seam** — `build_status/aggregator.py:get_status()` resolved
   `day_type_str` from `v9_day_type_history` (DB, old engine) and handed it to
   `s2_inspector`, which renders `"Auth Table SKIP for {pattern} × {day_type}"`
   (`s2_inspector.py:471-474`) — the exact string Michael saw.

### Fix (fail-open, never-raise)
- `five_min_system.py` (fire path, before the sizing block): resolve
  `_live_day_type = get_live_day_type()` ONCE inside `try/except → None`;
  sizing now passes `day_type=_live_day_type or self.current_day_type or "Normal"`,
  and `_emit_day_type = _live_day_type or self.current_day_type` reuses the SAME
  resolved label — sizing/auth, targets and emit can no longer diverge within one
  fire. Override unset/error → byte-identical prior behavior.
- `aggregator.py`: `day_type_str` = `get_live_day_type()` first (try/except),
  falling back to the legacy `_get_current_day_type()` DB read when None/error.

### Verify (raw, sandbox)
`tests/v9/regression/test_auth_daytype_override.py` — anti-tautological: drives the
REAL `process_bar()` fire (same reactive-long fixture as
`test_process_bar_emission.py`) with stale `current_day_type="Normal"` + env override
`<today-ET>:Variation`, and pins all three seams (emit kwarg, `compute_v2_sizing`
kwarg via spy with `STOP_ANCHORS_V2=1` + real YAML, aggregator→s2_inspector arg).

```
tests/v9/regression/test_auth_daytype_override.py::test_emit_path_sees_override_label PASSED
tests/v9/regression/test_auth_daytype_override.py::test_auth_sizing_path_sees_override_label PASSED
tests/v9/regression/test_auth_daytype_override.py::test_build_status_s2_display_sees_override_label PASSED
tests/v9/regression/test_day_type_manual_override.py (3 existing env-level pins) PASSED
```

RED-proof (fix temporarily reverted to `self.current_day_type or "Normal"`, then restored):
```
FAILED tests/v9/regression/test_auth_daytype_override.py::test_auth_sizing_path_sees_override_label
```

---

## B. `v9_bars_5min` stores ts 3h early (13:40 for the 16:40-IL bar)

### Root
Both write paths send the SAME tz-aware UTC value; the difference is the live COLUMN
TYPE. Both models declare `ts = Column(DateTime(timezone=True))`
(`bars_5min.py:19`, `bars_woodies.py:17`), but `create_all` never ALTERs an existing
table — the live `v9_bars_5min` predates the `timezone=True` model and drifted to
plain `timestamp without time zone`, while the newer `v9_bars_5min_woodies` (D-074)
got real `timestamptz`. Postgres **silently drops the `+00:00` suffix of an ISO
STRING** bound to a naive column → the UTC wall-clock (13:40) is stored bare, and
every session-TZ cast / local reader attributes it as IL → 13:40+03:00, 3h early.
The woodies path honored the same string's offset (timestamptz) → 16:40+03:00 correct.
Side casualty of the same root: `post_cumulative_delta`'s enrichment window
(`V9Bar5Min.ts >= aware-param`) compares a naive column against aware params — also
off by the session-TZ delta until the stored convention is consistent.

### Diagnose (run ON THE MAC — sandbox has no DB access)
```
python3 scripts/check_bars_ts_types.py
```
Prints session `TimeZone`, `information_schema.columns.data_type` of `ts` for BOTH
tables, and 2 newest sample rows each (raw + python type/tzinfo). Read-only.
Expected: `v9_bars_5min.ts = 'timestamp without time zone'`,
`v9_bars_5min_woodies.ts = 'timestamp with time zone'` (or text). If both show
`with time zone`, stop and re-diagnose before trusting the theory (Rule 2).

### Fix (5min write path ONLY — woodies untouched)
`bars.py:post_bars_5min` now binds the tz-aware **datetime OBJECT** instead of
`ts.isoformat()`. Why this round-trips correctly REGARDLESS of column type:
- `timestamptz` column → driver sends an explicit timestamptz value → exact instant
  (the model's intent; identical to woodies behavior);
- naive `timestamp` column → PG assignment-casts the timestamptz value through the
  SAME session TimeZone it later uses to read/cast the column back — symmetric
  conversion, instant preserved (the string bind was asymmetric: offset dropped on
  write, session TZ applied on read);
- TEXT column (SQLite test fixtures) → value rendered WITH its offset.
Dedup unchanged (`ON CONFLICT (ts, symbol)`); in-memory `_route_bar` payload unchanged.

### Verify (raw, sandbox)
```
tests/v9/regression/test_bars_5min_ts_binding.py::test_post_5min_binds_aware_datetime_not_string PASSED
backend/v9/tests/test_bars_safe_writer.py (10 tests, real handler → SQLite fixture) PASSED
```
RED-proof (bind temporarily reverted to `ts.isoformat()`, then restored):
```
FAILED tests/v9/regression/test_bars_5min_ts_binding.py::test_post_5min_binds_aware_datetime_not_string
```
Post-restart live UAT (orchestrator, per the four axes): run the diagnostic script,
then after the next bridge push confirm the newest `v9_bars_5min` row reads the same
instant as the matching `v9_bars_5min_woodies` row (`SELECT max(ts) FROM ...` both,
same psql session). **Today's already-poisoned rows (UTC-wall stored as naive) are
NOT rewritten by this fix** — they need a one-off data correction (see NOT-DONE).

---

## C. `cumulative_delta.json` per-bar array empty while the CVD study exists (chart5)

**No DLL code change** — no one-line mapping bug exists in the current source; the
empty array is a chartbook/Input mapping condition (below). Redeploy needs Michael's
Remote Build anyway.

### What the code actually does (source of the paradox)
- The DLL **never reads the "Cumulative Delta Bars - Volume" study** — there is no
  study-ID Input for CVD at all. All CVD exports compute from the chart's base
  bid/ask volume arrays (`sc.AskVolume/BidVolume`, `v9_exports.h:670-686`;
  chart5: `c5_data[SC_ASKVOL/SC_BIDVOL]`, `MES_AI_DataExport.cpp:1691,1732`).
  Adding/removing that study cannot affect the export — its presence proves nothing
  about the export (resolves "study exists yet bars empty").
- The caption `CVD: 33545` is the v9 study's own Subgraph[0] on its HOST chart
  (`MES_AI_DataExport.cpp:190`) → host bid/ask arrays are alive.
- **Main `cumulative_delta.json`** (Export 7, `v9_exports.h:631`): session-anchored
  loop `session_start..sc.Index` over HOST arrays, key **`points[]`** (not `bars`).
  This loop ALWAYS emits ≥1 point when it runs — a fresh main file **cannot** have an
  empty array from the current source (`v9.4.5-wc-fix`). If the file on disk shows an
  empty/`"bars"`-keyed array with a FRESH `export_ts`, the deployed DLL is not this
  source → Remote Build redeploy.
- **`cumulative_delta_continuous.json` / `5min_continuous.json`** (Export 10,
  `MES_AI_DataExport.cpp:1650-1750`): read a chart **by NUMBER** from Input
  “Continuous 24h Chart Number (0=disabled)” (code `sc.Input[20]`, Sierra UI shows it
  1-based as **In:21** — identify by NAME per the 07-13 lesson, runbook §חימוש). Chart
  numbers are **chartbook-local**: in the NEW RTH chartbook loaded today, “#5” is not
  necessarily the 24h Globex chart. Failure modes:
  - referenced chart absent / 0 bars → `c5_size==0` → block skipped → files go
    **STALE** (old `export_ts`, old points);
  - referenced chart present but every `v9_sc_datetime_to_unix(ts) <= 0` → loop
    `continue`s everything → file **FRESH with EMPTY array** (`points:[]`/`bars:[]`);
  - referenced chart present but without bid/ask volume → points PRESENT with `d=0`
    everywhere (distinguishable from empty).

### Operator steps (Sierra, exact)
1. Open `~/SierraChart_Data/v9_export/cumulative_delta.json` and
   `cumulative_delta_continuous.json`; note for each: `export_ts` fresh? array key
   (`points` vs `bars`)? array empty? `version` == `v9.4.5-wc-fix`?
2. Decision:
   - `version` ≠ `v9.4.5-wc-fix` or main file has `bars` key → **stale DLL deployed**
     → Michael: `./scripts/build_monolithic_cpp.sh --deploy` + Remote Build + reload
     study (snapshot first per Change-Safety).
   - continuous file stale/empty → **chart-number mapping**, step 3.
3. In the NEW chartbook find the 24h MESM26 5-min Globex chart; read its real number
   from the title bar (`#N`). On the chart hosting the study named
   **“MES AI Data Export …”**: `Analysis → Studies → MES AI Data Export → Settings →
   Inputs` → set **“Continuous 24h Chart Number (0=disabled)”** to `N` (identify the
   Input by NAME — UI numbering is 1-based vs code). If the chartbook has no such
   chart, open the 24h Globex chart into this chartbook first.
4. If points exist but `d=0` on every row: the referenced chart lacks bid/ask volume →
   `Chart Settings → Data/Trade Service Settings` on THAT chart: Intraday Data Storage
   Time Unit = 1 tick (tick-by-tick w/ bid&ask volume), then reload.
5. Re-check the JSONs (fresh `export_ts`, non-empty array, non-zero `d`/`cum`), then
   backend side: `v9_bars_cumulative_delta` newest ts advancing.
6. If the FILE is healthy but the DB stays empty → backend-side drop, not Sierra: the
   RTH gate in `post_cumulative_delta` drops points whose `t` is shifted by the new
   chartbook's −1h epoch bug — `_hour_shift_fix` is wired ONLY into `bars_5min` +
   `woodies_5min`, NOT the CVD endpoint (follow-up below), and the bridge's legacy
   Chicago-TS rewrite of `points[].t` (`cumulative_delta_stream.py`) can compound it.

---

## Verification summary (sandbox, raw)
```
$ python3 -m py_compile backend/v9/systems/five_min/five_min_system.py \
    backend/v9/systems/build_status/aggregator.py backend/v9/api/v9/bars.py \
    scripts/check_bars_ts_types.py tests/v9/regression/test_auth_daytype_override.py \
    tests/v9/regression/test_bars_5min_ts_binding.py
PY_COMPILE OK (6 files)

$ BRIDGE_TOKEN=x python3 -m pytest tests/v9/regression/test_auth_daytype_override.py \
    tests/v9/regression/test_bars_5min_ts_binding.py \
    tests/v9/regression/test_day_type_manual_override.py \
    backend/v9/systems/five_min/tests/test_process_bar_emission.py \
    backend/v9/tests/test_bars_safe_writer.py --no-header -q
23 passed, 7 warnings in 0.82s
```
Baseline no-regression proof: `tests/v9/build_status/ + backend/v9/systems/five_min/tests/`
fail-set is IDENTICAL with and without the fixes (37 pre-existing failures, diff empty —
none caused by this change; 4 additional files error at collection importing
long-deleted modules, e.g. `five_min.confluence`).

## NOT-DONE / follow-ups (explicit, per CC handoff contract)
1. **Backend restart** required to make A+B live (orchestrator/Michael;
   `launchctl kickstart -k gui/$UID/com.mems26.backend`), then run
   `scripts/check_bars_ts_types.py` + the B live UAT above and paste raw output.
2. **Today's poisoned `v9_bars_5min` rows** (naive UTC-wall, e.g. stored 13:40 for the
   16:40-IL bar) are not auto-corrected; one-off `UPDATE`/backfill decision for cc-imac
   after the column type is confirmed by the script.
3. **`test_daytype_gate_live.py`**: 2 pre-existing failures during ET session hours —
   the 07-16 `_g1_replay_fallback_ok` root-fix gates the classify_replay fallback to
   outside-session, and these tests still assume the old fallback; they need the
   session-hours gate stubbed (not touched here — outside scope).
4. **CVD ingest hour-shift**: extending `_hour_shift_fix` to `post_cumulative_delta`
   (and/or retiring the bridge Chicago rewrite) is a separate change — only do it if
   C-step-6 shows healthy files with an empty DB.
5. `post_cvd_continuous` remains a stub (records push, writes nothing) — pre-existing,
   documented here so chart5 CVD "missing from DB" isn't mis-diagnosed as C.
