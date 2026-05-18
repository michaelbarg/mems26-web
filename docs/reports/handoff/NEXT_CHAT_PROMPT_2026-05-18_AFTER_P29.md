# NEXT CHAT PROMPT — After P29 Scenario Pack

**Status:** paste into next chat before any Phase 3 work  
**Prepared:** 2026-05-18  
**Repo:** `/Users/michael/Downloads/mems26_web_git`  
**Branch:** `stabilize/mems26-local-truth-2026-05-16`

---

## Paste From Here

You are continuing MEMS26 in `/Users/michael/Downloads/mems26_web_git`.

We are in pre-LIVE discipline. Every change can affect real-money readiness.
Read current code before changing it. Diagnose first, fix second. Smallest
correct change only. No silent failures. Update reports immediately.

### 0. First Commands

Run:

```bash
cd /Users/michael/Downloads/mems26_web_git
git status --short --branch
```

Expected high-level state at handoff time:

- Branch: `stabilize/mems26-local-truth-2026-05-16`
- Branch is ahead of remote.
- P29 work may still be uncommitted unless Michael committed it after this
  prompt was prepared.
- Do **not** push.
- Do **not** commit unless Michael explicitly asks.

If the working tree is dirty, summarize the dirty files first and ask Michael
whether to commit the P29 closeout before starting Phase 3. Do **not** mix
Phase 3 Data Collection work into uncommitted P29 work without approval.

At the time this prompt was prepared, dirty P29 files were:

- `backend/v9/services/trading_gateway/gateway.py`
- `tests/v9/services/test_trading_gateway.py`
- `tests/v9/replay/fixtures/p29/scenarios.json`
- `tests/v9/replay/test_p29_scenario_pack.py`
- `docs/reports/PROMPT29_REPLAY_SCENARIO_PACK.md`
- `docs/reports/handoff/CHECKLIST_TO_LIVE.md`
- `docs/reports/handoff/GANTT_TO_LIVE.md`
- `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md`

### 1. Must-Read Repo Context

Read these before acting:

1. `.cursor/rules/mems26-pre-live-protocol.mdc`
2. `.cursor/rules/mems26-stability.mdc`
3. `CLAUDE.md`
4. `docs/spec_authority/README.md`
5. `docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown`
6. `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt`
7. `docs/spec_authority/MEMS26_FIRST.md`
8. `docs/reports/PROMPT28_REPLAY_SMOKE_RUN.md`
9. `docs/reports/PROMPT29_REPLAY_SCENARIO_PACK.md`
10. `docs/reports/handoff/CHECKLIST_TO_LIVE.md`
11. `docs/reports/handoff/GANTT_TO_LIVE.md`
12. `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md`

Also inspect the P29 code/test changes if still uncommitted:

- `backend/v9/services/trading_gateway/gateway.py`
- `tests/v9/services/test_trading_gateway.py`
- `tests/v9/replay/test_p29_scenario_pack.py`
- `tests/v9/replay/fixtures/p29/scenarios.json`

### 2. Current Verified State

- Phase 0 is GREEN.
- Phase 1 / P28 is GREEN:
  - `status_check` PASS.
  - `prompt_26_replay_clock_smoke` PASS.
  - post-P27.5 endpoint checks PASS.
  - `python3 -m pytest tests/v9/ -q` previously PASS: `1244 passed, 1 skipped`.
- Master Review before P29 completed:
  - Master Index V2 and Constitution V3 were saved locally under
    `docs/spec_authority/`.
  - P29 was approved as **offline scenario pack only**.
  - D-061: Killzone zones are observational/tag/context only.
  - D-074: S4 Woodies runtime must use `woodies_5min`.
- Phase 2 / P29 is GREEN at the offline scenario-pack level:
  - 10/10 scenarios represented in `tests/v9/replay/fixtures/p29/scenarios.json`.
  - P29 + gateway targeted tests: `33 passed`.
  - Full `tests/v9/`: `1255 passed, 1 skipped`.
  - Report: `docs/reports/PROMPT29_REPLAY_SCENARIO_PACK.md`.

### 3. P29 Important Finding

P29 found and fixed a gateway governance mismatch:

- Master Index V2 requires firing systems **S2/S3/S4** and observing systems
  **S1/S5/S6**.
- `TradingGateway` previously allowed `{1,2,4}`.
- With Michael approval and CC review, the smallest correction was applied:
  `FIRING_SYSTEMS = frozenset({2, 3, 4})`.
- Tests were updated so S3 is accepted and S1 is rejected.

Do not revert this.

### 4. Current Gate

We are stopped at the **Phase 2 -> Phase 3** gate.

Do **not** begin Phase 3 / P29.5 Data Collection unless Michael explicitly
writes approval such as:

```text
I approve Phase 2 -> Phase 3. Start P29.5 Data Collection Package.
```

If Michael only asks for review/planning, do review/planning only.

### 5. If Michael Approves Phase 3

Use `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md` Phase 3 as the starting
scope.

Phase 3 / P29.5 goal: define and wire the storage/log contract for SHADOW:

1. bars + stream health
2. S1-S6 state snapshots
3. pre-fire decisions
4. gateway dry-run decisions
5. reason trees
6. lifecycle events

Preferred approach:

- Start with schema design and offline validation.
- Do not activate SHADOW.
- Do not start bridge unless Michael explicitly asks.
- Do not write `trade_command.json`.
- Do not enable DEMO/LIVE.
- Preserve reason-tree auditability from P29.

### 6. Hard Safety Rules

Do not:

- run `scripts/start_all.sh`,
- run `npm run dev` or `next dev`,
- start bridge unless Michael explicitly asks,
- change LaunchAgent settings,
- change SHADOW/DEMO/LIVE flags,
- write `trade_command.json`,
- enable DEMO/LIVE,
- push to remote,
- proceed past a phase gate without Michael approval.

For any endpoint/data path you touch, preserve the four UAT axes where relevant:
Quality / Recency / Cardinality / Latency.

### 7. Stop Conditions

Stop and ask Michael if:

- P29 changes are still uncommitted and Phase 3 work is requested;
- any path might write a real/demo/live command;
- a DEMO/LIVE flag or gateway slot becomes non-empty;
- full `tests/v9/` regresses;
- schema decisions require new governance or a new D-###;
- bridge/Sierra/live replay becomes necessary.

## Paste To Here

---

## Operator Note

This handoff does **not** approve Phase 2 -> Phase 3 by itself. Michael must
explicitly approve before Phase 3 / Data Collection work starts.

