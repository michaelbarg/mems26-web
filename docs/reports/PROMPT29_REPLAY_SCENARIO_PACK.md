# P29 — Replay Scenario Pack

**Date:** 2026-05-18  
**Status:** GREEN — 10/10 offline scenarios PASS after approved gateway contract fix  
**No SHADOW/DEMO/LIVE enabled. No trade_command writes.**

## Summary

P29 started as an offline reproducible scenario pack. The first harness uses
fixtures only and avoids live Sierra, bridge, backend services, frontend dev
servers, POST endpoints, mode flags, and `trade_command.json`.

The pack currently validates 10 required P29 scenarios against local pure
components where possible:

- Day Type V2 decision matrix.
- S6 Killzone D-061 observational/tag behavior.
- S5 TPO offline profile builder.
- Shared `pre_fire_validator`.
- TradingGateway with mocked trade manager and DEMO/LIVE disabled.

The harness initially found a real blocker: the active `TradingGateway`
implementation allowed firing systems `{1, 2, 4}` while Master Index V2 and
P29 require firing systems **S2/S3/S4** and observing systems **S1/S5/S6**.
After Michael approval and CC review, the smallest contract fix was applied:
`FIRING_SYSTEMS = frozenset({2, 3, 4})`, and gateway tests now prove S3 is
accepted while S1 is rejected.

## Scenario Matrix

| ID | Scenario | Fixture/source | Expected | Actual | Result |
|----|----------|----------------|----------|--------|--------|
| P29.1 | Trending day | `tests/v9/replay/fixtures/p29/scenarios.json` | S4 valid, shadow-only offline route | PASS | PASS |
| P29.2 | Balance / non-trend | same | No firing; D-061 lunch advisory only | PASS | PASS |
| P29.3 | Opening drive | same | S2 valid, shadow-only offline route | PASS | PASS |
| P29.4 | S2 Five-Min setup | same | S2 valid SHORT route | PASS | PASS |
| P29.5 | S3 Footprint setup | same | S3 valid, shadow-only offline route | PASS | PASS |
| P29.6 | S4 Woodies setup | same | S4 valid, requires `woodies_5min` | PASS | PASS |
| P29.7 | Killzone context change | same | `CLOSE_FINAL` is context/tag, not hard block | PASS | PASS |
| P29.8 | TPO context / location | same | POC/VAH/VAL computed offline | PASS | PASS |
| P29.9 | Missing / degraded data | same | Missing prior-day remains `UNKNOWN/DEGRADED` | PASS | PASS |
| P29.10 | Pre-fire / risk block | same | `pre_fire` rejects low R:R; no route | PASS | PASS |

## Per-Scenario Evidence

Targeted command:

```bash
python3 -m pytest tests/v9/replay/test_p29_scenario_pack.py -q
```

Initial blocker result:

```text
1 failed, 10 passed
FAILED tests/v9/replay/test_p29_scenario_pack.py::test_p29_scenario_pack_contracts[P29.5]
ValueError: Invalid system_id: 3. Must be one of [1, 2, 4]
```

Post-fix targeted result:

```text
python3 -m pytest tests/v9/services/test_trading_gateway.py tests/v9/replay/test_p29_scenario_pack.py -q
33 passed
```

Relevant code evidence:

- `backend/v9/services/trading_gateway/gateway.py` now defines
  `FIRING_SYSTEMS = frozenset({2, 3, 4})`.
- `backend/v9/systems/footprint/footprint_system.py` defines
  `system_id = 3` and routes S3 fires with `route_setup(..., 3)`.
- `backend/v9/systems/wrappers.py` states firing systems are
  5-Min `(2)`, Footprint `(3)`, Woodies `(4)`, and observers are
  DayType `(1)`, TPO `(5)`, Killzone `(6)`.
- Master Index V2 states S1 is observer/context, S2/S3/S4 are firing,
  S5 is observer, and S6 is observer + gate.

## Tests Run

| Command | Result |
|---------|--------|
| `python3 -m pytest tests/v9/replay/test_p29_scenario_pack.py -q` | Initial FAIL — 1 failed, 10 passed; found gateway contract mismatch |
| `python3 -m pytest tests/v9/services/test_trading_gateway.py tests/v9/replay/test_p29_scenario_pack.py -q` | PASS — 33 passed |
| `python3 -m pytest tests/v9/ -q` | PASS — 1255 passed, 1 skipped |

Full `tests/v9/` is green after the targeted fix.

## Safety Verification

- DEMO enabled: no.
- LIVE enabled: no.
- `trade_command.json` written: no.
- Bridge started/stopped: no.
- `scripts/start_all.sh`: not run.
- `npm run dev` / `next dev`: not run.
- P29 used offline fixtures and mocks only.

## Blockers / Residual Risks

### Resolved — TradingGateway firing-system contract mismatch

Master Index V2 / P29 require:

- Observing/context: S1, S5, S6.
- Firing: S2, S3, S4.

Previous service gateway allowed:

- `{1, 2, 4}`.

That made S1 route-capable and S3 route-blocked in the W13 gateway service,
which contradicted the current authority docs and the S3 Footprint fire path.

Approved correction:

- `backend/v9/services/trading_gateway/gateway.py`: `{1, 2, 4}` -> `{2, 3, 4}`.
- `tests/v9/services/test_trading_gateway.py`: updated to accept S3 and reject S1.

Residual risk: P29 is an offline contract pack, not a live Sierra/full-session
market replay. SHADOW/DEMO/LIVE activation remains gated by later phases.

## Phase Gate

P29 scenario pack is GREEN. Stop here. Michael must explicitly approve
Phase 2 -> Phase 3 before moving to the Data Collection Package.
