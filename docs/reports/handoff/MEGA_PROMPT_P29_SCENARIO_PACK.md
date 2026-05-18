# MEGA PROMPT — P29 Replay Scenario Pack

**Status:** PREPARED ONLY — do not execute until Michael explicitly approves Phase 1 -> Phase 2  
**Prepared:** 2026-05-18  
**Repo:** `/Users/michael/Downloads/mems26_web_git`  
**Branch:** `stabilize/mems26-local-truth-2026-05-16`

---

## Paste From Here

You are continuing MEMS26 in `/Users/michael/Downloads/mems26_web_git`.

We are in pre-LIVE discipline. Every change can affect real-money readiness.
Diagnose first, read code first, make the smallest correct change, add focused
tests, update reports immediately, and do not advance phase gates without
Michael's explicit approval.

### 0. First Actions

1. Run:
   ```bash
   git status --short --branch
   ```
2. Confirm the branch is:
   `stabilize/mems26-local-truth-2026-05-16`
3. Expect the branch to be ahead of remote. Do **not** push.
4. If there are uncommitted changes from P27.5b/P28/D-061 closeout, stop and
   ask Michael whether to commit them before starting P29. Do not silently mix
   P29 work into earlier uncommitted work.
5. Read these files before changing anything:
   - `.cursor/rules/mems26-pre-live-protocol.mdc`
   - `.cursor/rules/mems26-stability.mdc`
   - `CLAUDE.md`
   - `docs/reports/handoff/CHECKLIST_TO_LIVE.md`
   - `docs/reports/handoff/GANTT_TO_LIVE.md`
   - `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md`
   - `docs/reports/PROMPT28_REPLAY_SMOKE_RUN.md`
   - `docs/reports/PROMPT27_REPLAY_VALIDATION_PLAN.md`

### 1. Current State

- Phase 0 is GREEN.
- P27.5b is GREEN:
  - `scripts/uat_prompt_27_5b_live_price.sh` returned 10/10 PASS.
  - `age_ms=178-982ms`, latency `1-6ms`, valid JSON.
  - `/api/v9/live_price` reads Sierra's file directly; bridge is not in that endpoint path.
- Phase 1 / P28 is GREEN:
  - `status_check` PASS.
  - `prompt_26_replay_clock_smoke` PASS.
  - endpoint checks PASS.
  - `python3 -m pytest tests/v9/ -q` PASS: `1244 passed, 1 skipped`.
- Killzone is aligned to D-061:
  - Killzone zones are observational/tag/context only.
  - Zone labels such as `PRE_MARKET`, `LUNCH`, `CLOSE_FINAL`, `AFTER_HOURS`
    do **not** hard-block trades by themselves.
  - Hard blocks come from trading calendar, manager disable, news/risk/mode controls.
  - `sizing_modifier` is advisory/context, not a hard gate by itself.
- Day Type policy:
  - Prior-day candles/context are required for trading.
  - Missing prior-day context remains `A1 / UNKNOWN / DEGRADED`.
  - Do not pretend Day Type is tradable when previous-day context is missing.
- No SHADOW/DEMO/LIVE is enabled.
- Do not write `trade_command.json`.

### 2. Authoritative Spec Rule

If the task touches naming, taxonomy, system scope, governance, or proposes a
new `D-###`, and Master Index V2 / Constitution V3 / `MEMS26_FIRST.md` are not
in context, stop and ask Michael to paste the relevant sections. Do not invent
D-numbers.

Known authority already clarified by Michael:

- **D-061 wins** for Killzone:
  - The old Cockpit V5 §3.3 hard-block interpretation is overridden.
  - Killzone is tag-only / observational context unless calendar, manager,
    news, risk, or mode controls block.
- Day Type V2 is the current Day Type source:
  - Keep probability matrix behavior when present.
  - `top1` is acceptable for winner compatibility.
  - Prior-day data is mandatory for trade readiness.

### 3. Task

Prepare and execute **P29 — Replay Scenario Pack** only after Michael explicitly
approved the Phase 1 -> Phase 2 gate.

Goal: validate the full pipeline against 10 reproducible scenarios, each with:

- fixture or replay source,
- exact input data,
- expected S1/S5/S6 advisory context,
- expected S2/S3/S4 fire/block behavior,
- expected reason tree,
- expected route/block outcome,
- PASS/FAIL evidence,
- no DEMO/LIVE path engaged.

Required scenarios:

1. `P29.1` — Trending day
2. `P29.2` — Balance / non-trend
3. `P29.3` — Opening drive
4. `P29.4` — S2 Five-Min setup
5. `P29.5` — S3 Footprint setup
6. `P29.6` — S4 Woodies setup
7. `P29.7` — Killzone context change
8. `P29.8` — TPO context / location
9. `P29.9` — Missing / degraded data
10. `P29.10` — Pre-fire / risk block

### 4. Strong Preference: Offline Reproducible Fixtures

Start with offline reproducible fixtures/tests, not live Sierra randomness.

Preferred structure:

- fixtures under `tests/v9/replay/fixtures/p29/` or the nearest existing replay
  fixture location;
- tests under `tests/v9/replay/` or the nearest existing replay test package;
- a report at:
  `docs/reports/PROMPT29_REPLAY_SCENARIO_PACK.md`

Before creating new directories, inspect existing `tests/v9/` structure and use
local conventions. Do not invent a framework if a replay/test helper already
exists.

If there is no existing harness capable of executing the full scenario pack,
build the smallest harness needed to run the 10 scenario checks offline. If a
scenario cannot be executed without a new infrastructure decision, mark that
scenario `BLOCKED` with exact missing input rather than faking a PASS.

### 5. Safety Rules

Do **not**:

- start bridge unless Michael explicitly asks,
- run `scripts/start_all.sh`,
- run `npm run dev` or `next dev`,
- change LaunchAgent settings,
- change SHADOW/DEMO/LIVE flags,
- write `trade_command.json`,
- call POST endpoints that can route real/demo/live orders,
- enable DEMO/LIVE,
- push to remote.

For fire-path validation:

- Prefer pure functions, offline scenario harnesses, or read-only state endpoints.
- If a POST fire endpoint is needed, first read the route and prove it is dry-run
  / non-writing under current mode. If unsure, stop and ask Michael.

### 6. Acceptance Criteria

P29 goes GREEN only when all are true:

- 10/10 scenarios PASS.
- Every scenario has a reproducible fixture/source.
- Every scenario documents expected vs actual.
- Reason trees are auditable, not just boolean PASS.
- No DEMO/LIVE path is engaged.
- `trade_command.json` is not written.
- Relevant targeted tests pass.
- `python3 -m pytest tests/v9/ -q` remains green.
- `docs/reports/PROMPT29_REPLAY_SCENARIO_PACK.md` is updated with evidence.
- `docs/reports/handoff/CHECKLIST_TO_LIVE.md`, `GANTT_TO_LIVE.md`, and
  `PROMPT_LIST_TO_LIVE.md` are updated.
- Stop at the Phase 2 -> Phase 3 gate and ask Michael before moving to data
  collection (`P29.5` phase).

### 7. Report Template

Create/update `docs/reports/PROMPT29_REPLAY_SCENARIO_PACK.md` with:

```markdown
# P29 — Replay Scenario Pack

**Date:** YYYY-MM-DD
**Status:** GREEN / BLOCKED / PARTIAL
**No SHADOW/DEMO/LIVE enabled. No trade_command writes.**

## Summary

## Scenario Matrix

| ID | Scenario | Fixture/source | Expected | Actual | Result |
|----|----------|----------------|----------|--------|--------|
| P29.1 | Trending day | | | | |
| P29.2 | Balance / non-trend | | | | |
| P29.3 | Opening drive | | | | |
| P29.4 | S2 Five-Min setup | | | | |
| P29.5 | S3 Footprint setup | | | | |
| P29.6 | S4 Woodies setup | | | | |
| P29.7 | Killzone context change | | | | |
| P29.8 | TPO context / location | | | | |
| P29.9 | Missing / degraded data | | | | |
| P29.10 | Pre-fire / risk block | | | | |

## Per-Scenario Evidence

## Tests Run

## Safety Verification

- DEMO enabled: no
- LIVE enabled: no
- `trade_command.json` written: no
- Bridge started/stopped: no, unless explicitly approved and recorded

## Blockers / Residual Risks

## Phase Gate

Stop here. Michael must explicitly approve Phase 2 -> Phase 3.
```

### 8. Stop Conditions

Stop immediately and ask Michael if:

- a scenario requires a new D-### or taxonomy decision;
- Day Type V2 / Killzone D-061 interpretation conflicts with tests;
- a route might write to gateway/trade command paths;
- a scenario requires live Sierra/bridge rather than offline fixture;
- full `tests/v9/` regresses;
- any DEMO/LIVE flag or slot becomes non-empty.

## Paste To Here

---

## Operator Note

This prompt is a preparation artifact. It does not approve Phase 1 -> Phase 2
by itself. Michael must explicitly approve starting P29 before this is executed.
