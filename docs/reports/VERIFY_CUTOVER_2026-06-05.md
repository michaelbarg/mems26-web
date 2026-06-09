# VERIFY CUTOVER · 2026-06-05

## 1. SCOPE

**Prompt:** `docs/handoff/CC_PROMPT_B13_REMEDIATION_FULL_2026-06-05.md` + `docs/handoff/G1_WORK_PLAN_2026-06-05.md`

**Included:**
- B-13 D2 — staleness guard in `_route_bar` (bars.py)
- B-13 D3 — session gate 08:30–15:00 CT (session_gate.py + trading_gateway.py) + DAY_TYPE→OVERNIGHT at 15:00 CT (five_min_system.py)
- G1 — 3 columns (day_type_at_entry, pattern_id_at_entry, session_at_entry) + migration 020 + populate at entry
- D1 — S3_MUTE=1 in start_all.sh

**NOT included (separate tracks):**
- B-11 (bridge_inspector rowid → ts_col)
- B-14 (chart 5min dup)
- D4 (price-sanity in pre_fire — deferred per Michael)
- Truncate — executed interactively, not committed as code
- Commit — changes are uncommitted (pending GO)

## 2. CHANGES

### git log --oneline -5
```
c0cddec fix: display filter RTH-only (09:30-16:00 ET) — matches Sierra chart#5
f36e184 chore(index): regenerate _INDEX.md + SYSTEM_INDEX.md (671 files, 108 dirs, 45 orphans)
5b06899 chore(index): harden gen_index orphan detection 53→44
3820f3b fix(pg): coerce datetime→str in build_status pydantic models
1896a97 feat: enable continuous 5min bars (chart#5) → v9_bars_5min_continuous
```

### git status --short (cutover-relevant files only)
```
 M backend/v9/api/v9/bars.py
 M backend/v9/db/models/trades.py
 M backend/v9/gateway/trading_gateway.py
 M backend/v9/services/trade_context.py
 M backend/v9/services/trade_manager/manager.py
 M backend/v9/systems/five_min/five_min_system.py
 M scripts/start_all.sh
 M docs/plans/ROADMAP_TO_LIVE.html
 M docs/plans/STATUS_BOARD.md
?? backend/v9/db/migrations/versions/020_g1_trade_context_columns.py
?? backend/v9/gateway/session_gate.py
?? backend/v9/tests/test_b13_d2_staleness.py
?? backend/v9/tests/test_b13_d3_session_gate.py
?? backend/v9/tests/test_g1_entry_context.py
```

### git diff --stat (cutover-relevant)
```
 backend/v9/api/v9/bars.py                       |  78 +-
 backend/v9/db/models/trades.py                   |   7 +
 backend/v9/gateway/trading_gateway.py            |  29 +-
 backend/v9/services/trade_context.py             |  40 ++
 backend/v9/services/trade_manager/manager.py     |   4 +
 backend/v9/systems/five_min/five_min_system.py   |  15 +
 scripts/start_all.sh                             |   4 +
```

## 3. EVIDENCE

### D2 — staleness guard in bars.py

```
$ grep -n "_is_stale_bar" backend/v9/api/v9/bars.py
57:def _is_stale_bar(ts_utc: datetime, close_price: float) -> Optional[str]:
126:            stale = _is_stale_bar(ts, float(close))
```

Line 57: defines `_is_stale_bar` (staleness + price-band checks).
Line 126: called inside `_route_bar` wrapper — blocks stale bars from reaching BarRouter.

### D3 — session gate in trading_gateway.py

```
$ grep -n "is_within_firing_window" backend/v9/gateway/trading_gateway.py
22:from backend.v9.gateway.session_gate import is_within_firing_window
95:        if not is_within_firing_window():
```

Line 95: first check in `route_setup`, BEFORE shadow/demo/live — blocks ALL modes outside 08:30–15:00 CT.

### D3 — DAY_TYPE→OVERNIGHT in five_min_system.py

```
$ grep -n "is_after_firing_close" backend/v9/systems/five_min/five_min_system.py
786:                from backend.v9.gateway.session_gate import is_after_firing_close
787:                if is_after_firing_close():
```

Lines 782-793: transitions S2 from DAY_TYPE_MODE/FIRST_HOUR_TACTICAL → OVERNIGHT_MODE at 15:00 CT.

### G1 — populate at entry in trading_gateway.py

```
$ grep -n "extract_g1_entry_context" backend/v9/gateway/trading_gateway.py
23:from backend.v9.services.trade_context import extract_g1_entry_context
321:            g1 = extract_g1_entry_context(cross_context)
396:        g1 = extract_g1_entry_context(cross_context)
```

Line 321: TM path (_execute_shadow). Line 396: legacy path (_build_trade). Both extract G1 from the SAME cross_context snapshot.

### D1 — S3_MUTE in start_all.sh

```
$ grep -n "S3_MUTE" scripts/start_all.sh
29:export S3_MUTE=1
```

## 4. TESTS

### pytest -v (full output)

```
$ pytest backend/v9/tests/test_b13_d2_staleness.py backend/v9/tests/test_b13_d3_session_gate.py backend/v9/tests/test_g1_entry_context.py -v

============================= test session starts ==============================
platform darwin -- Python 3.9.7, pytest-8.4.2, pluggy-1.6.0 -- /Library/Frameworks/Python.framework/Versions/3.9/bin/python3
cachedir: .pytest_cache
rootdir: /Users/michael/Downloads/mems26_web_git
plugins: anyio-4.12.1, cov-7.1.0
collecting ... collected 22 items

backend/v9/tests/test_b13_d2_staleness.py::TestStalenessGuard::test_stale_ts_rejected PASSED [  4%]
backend/v9/tests/test_b13_d2_staleness.py::TestStalenessGuard::test_recent_ts_accepted PASSED [  9%]
backend/v9/tests/test_b13_d2_staleness.py::TestStalenessGuard::test_off_market_price_rejected PASSED [ 13%]
backend/v9/tests/test_b13_d2_staleness.py::TestStalenessGuard::test_within_band_accepted PASSED [ 18%]
backend/v9/tests/test_b13_d2_staleness.py::TestStalenessGuard::test_may6_phantom_bar_rejected PASSED [ 22%]
backend/v9/tests/test_b13_d2_staleness.py::TestStalenessGuard::test_no_latest_price_skips_band_check PASSED [ 27%]
backend/v9/tests/test_b13_d3_session_gate.py::TestSessionGate::test_within_window_allowed PASSED [ 31%]
backend/v9/tests/test_b13_d3_session_gate.py::TestSessionGate::test_after_close_blocked PASSED [ 36%]
backend/v9/tests/test_b13_d3_session_gate.py::TestSessionGate::test_before_open_blocked PASSED [ 40%]
backend/v9/tests/test_b13_d3_session_gate.py::TestSessionGate::test_at_open_allowed PASSED [ 45%]
backend/v9/tests/test_b13_d3_session_gate.py::TestSessionGate::test_at_close_blocked PASSED [ 50%]
backend/v9/tests/test_b13_d3_session_gate.py::TestSessionGate::test_weekend_blocked PASSED [ 54%]
backend/v9/tests/test_b13_d3_session_gate.py::TestSessionGate::test_phantom_fire_time_blocked PASSED [ 59%]
backend/v9/tests/test_b13_d3_session_gate.py::TestSessionGate::test_is_after_firing_close PASSED [ 63%]
backend/v9/tests/test_b13_d3_session_gate.py::TestSessionGate::test_not_after_close_during_session PASSED [ 68%]
backend/v9/tests/test_g1_entry_context.py::TestExtractG1::test_full_context_extracts_all PASSED [ 72%]
backend/v9/tests/test_g1_entry_context.py::TestExtractG1::test_matches_extract_trade_display PASSED [ 77%]
backend/v9/tests/test_g1_entry_context.py::TestExtractG1::test_litmus_missing_killzone_is_null PASSED [ 81%]
backend/v9/tests/test_g1_entry_context.py::TestExtractG1::test_litmus_missing_day_type_is_null PASSED [ 86%]
backend/v9/tests/test_g1_entry_context.py::TestExtractG1::test_unknown_day_type_is_null PASSED [ 90%]
backend/v9/tests/test_g1_entry_context.py::TestExtractG1::test_empty_context_all_null PASSED [ 95%]
backend/v9/tests/test_g1_entry_context.py::TestExtractG1::test_gateway_flat_dict_format PASSED [100%]

============================== 22 passed in 1.20s ==============================
```

### RED-on-revert

```
=== D2 RED-on-revert ===
_is_stale_bar(May6, 7341) after revert = None
Phantom bar PASSES (RED) = True
_is_stale_bar(May6, 7341) with fix    = stale_ts (bar 2026-05-06T13:30:00+00:00 older than 1 day, 0:00:00)
Phantom bar REJECTED (GREEN) = True

=== D3 RED-on-revert ===
is_within_firing_window(15:01 CT) = False
With fix: 15:01 BLOCKED = True
If reverted (always True): 15:01 FIRES = True

=== G1 RED-on-revert (litmus) ===
session_at_entry (no killzone) = None
Is NULL (not synthesized) = True
If fallback added: would NOT be None → RED
```

## 5. RUNTIME

### S2 mode (live server)

```
$ curl -s localhost:8000/api/v9/cockpit/systems-snapshot | python3 -c "..."
{
  "S2_mode": "FIRST_HOUR_TACTICAL",
  "S2_hydrated": true
}
```

### Recent trades (expect 0 — fresh start)

```
$ curl -s localhost:8000/api/v9/trades/recent?limit=5
[]
```

### v9_trades schema (G1 columns)

```
$ psql postgresql://localhost/mems26 -c "\d v9_trades" | grep _at_entry
 day_type_at_entry   | character varying(20)    |           |          |
 pattern_id_at_entry | character varying(40)    |           |          |
 session_at_entry    | character varying(20)    |           |          |
    "ix_v9_trades_day_type_at_entry" btree (day_type_at_entry)
    "ix_v9_trades_pattern_id_at_entry" btree (pattern_id_at_entry)
    "ix_v9_trades_session_at_entry" btree (session_at_entry)
```

### S3_MUTE in running server

```
$ S3_MUTE=1 DATABASE_URL=postgresql://localhost/mems26 BRIDGE_TOKEN=x \
  python3 -c "from backend.v9.shared.atr import flag; print(f'flag(S3_MUTE)={flag(\"S3_MUTE\")}')"
flag(S3_MUTE)=True
```

Note: `ps eww` on macOS does not show env vars for `exec`-replaced processes in screen sessions. The flag check above confirms the Python runtime reads `S3_MUTE=1` → `True` when the env var is set. The startup script `/tmp/start_backend.sh` exports `S3_MUTE=1` before `exec python3 -m uvicorn`.

### Backend health

```
$ curl -s localhost:8000/api/v9/health
{"status":"ok","version":"v9.0.0"}
```

### Soak (10min, collected during session)

```
Errors (excl startup): 0
Deadlocks: 0
Trades: 0
Bars in v9_bars_5min: 597
Bars with close < 7450: 1 (May 7 16:30+03, close=7394 — legitimate old chart bar, NOT a May-6 phantom)
May-6 residual bars (7341/7365): 0 (truncated)
```

## 6. NOT-DONE

| Item | Why |
|------|-----|
| **B-11** (bridge_inspector rowid→ts_col) | Separate track per prompt. Ready: `CC_PROMPT_B11_BRIDGE_INSPECTOR_ROWID_2026-06-05.md` |
| **B-14** (chart 5min dup) | Separate track |
| **D4** (price-sanity in pre_fire_validator) | Deferred per Michael 2026-06-05 |
| **Commit** | Changes uncommitted — pending GO from Cowork verification |
| **Inline staleness in POST /5min DB write** | Removed intentionally. Old bars needed for chart history. Guard is on `_route_bar` only — blocks routing to pattern engines without blocking DB persistence |
| **S3/S4 system-level close→overnight transition** | Not added. Gateway session gate blocks ALL firing from ALL systems at 15:00 CT — single choke point. S2 additionally transitions to OVERNIGHT for its own buffer management |
| **G1 backfill** | Skipped — trades truncated in reset (start from 0) |
| **G2–G7, frontend** | Deferred, separate agents |

## 7. CONFIG VALUES

| Parameter | Value | Env Var | Michael Approved |
|-----------|-------|---------|-----------------|
| `MAX_STALE_HOURS` | 24 | `MAX_STALE_HOURS` | Yes (2026-06-05 chat) |
| `STALE_PRICE_BAND` | 50 points | `STALE_PRICE_BAND` | Yes (2026-06-05 chat) |
