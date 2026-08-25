# T-103B Candidate Ledger — Ready for Live · 2026-08-25

## Status per Section

| § | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Migration 024 NOT run | ✅ DONE | Not executed — ledger is JSONL-only today |
| 2 | is_synthetic NOT added to S2 | ✅ DONE | Skipped per cowork review — column doesn't exist |
| 3a | Rotation fix (mtime → first-line ts) | ✅ DONE | `trading_gateway.py:488-501` — reads first row's ts |
| 3b | Radar window filter | ✅ DONE | `context_radar.py:109,136` — `_is_gate_line` filters DETECTED/EMIT |
| 3c | gateway_routes hardening | ✅ DONE | `gateway_routes.py:105` — filter before truncation |
| 4 | _code_commit at boot | ✅ DONE | `candidate_ledger.py:35-44` — import-time subprocess |
| 5 | RULED_FLAGS registration | ✅ DONE | `CANDIDATE_LEDGER_V1 expected=1` — flag_guard 200 PASS |
| 6 | Contract §2 fixed | ✅ DONE | GATE_DECISION/ROUTED mutually exclusive, not sequential |
| 7 | Blocker tests | ✅ DONE | 2 new tests: rotation + radar (13/13 passed) |
| 8 | Gate check | ✅ DONE | See below |

## Gate Check (§8) — command + raw output

### 8.1 — Blocker fixes + tests

```
$ BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression/test_candidate_ledger.py -v
13 passed, 2 warnings in 0.23s
```

Including:
- `test_rotation_not_broken_by_ledger_write` PASSED
- `test_radar_window_not_swallowed_by_detected` PASSED

### 8.2 — flag_guard = 200 PASS

```
$ python3 scripts/flag_guard.py | tail -1
FLAG-GUARD: PASS — all 200 ruled flags match.
```

### 8.3 — Zero ledger events in live JSONL

```
$ grep -c "DETECTED\|EMIT_DECISION" ~/SierraChart_Data/v9_export/gateway_decisions.jsonl
0
```

### 8.4 — fire_drill (not run — flag still OFF in running backend; will pass after restart)

NOT-VERIFIED — requires restart with CANDIDATE_LEDGER_V1=1 to test live integration.

### 8.5 — Rotation verified on test file

```
test_rotation_not_broken_by_ledger_write: PASSED
  — yesterday ts in first line + today mtime → rotation fires correctly
```

### 8.6 — Contracts

```
$ python3 -c "from backend.v9.services.contract_size import ruled_contracts, ladder_for; ..."
ruled_contracts()=4  ladder_for(4)=(1,1,1,1)
```

## NOT-VERIFIED

- **Live integration** — flag OFF in running backend; requires restart by cowork+Michael
- **Volume threshold** — "if file exceeds 2,000 lines in first hour, disable" — will be
  monitored post-enable
- **S4 two-detected/route-one** — tested via existing `test_same_bar_repush_does_not_duplicate`
  but not with the full S4 detection chain
- **DB columns (024)** — deliberately NOT run today per §1

## Files Changed

```
backend/v9/services/candidate_ledger.py          — §4 boot-time commit
backend/v9/gateway/trading_gateway.py            — §3a rotation fix
backend/v9/api/v9/context_radar.py               — §3b radar filter
backend/v9/api/v9/gateway_routes.py              — §3c filter-before-truncate
config/RULED_FLAGS.yaml                          — §5 flag registration (200)
docs/spec_authority/CANDIDATE_LEDGER_CONTRACT.md — §6 GATE/ROUTED exclusive
tests/v9/regression/test_candidate_ledger.py     — §7 two blocker tests
.env                                             — CANDIDATE_LEDGER_V1=1 (gitignored)
```

## Commit

`562f51d2` — pushed to origin.

*Report by cc-macbook · 2026-08-25. The flag is set in .env but the backend has NOT been
restarted — **enable and restart are a cowork+Michael gate**.*
