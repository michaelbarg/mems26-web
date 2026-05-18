# NEXT CHAT PROMPT — P29 Master Review Before Scenario Pack

**Status:** paste into next chat before P29 work  
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

Expected high-level state:

- Branch: `stabilize/mems26-local-truth-2026-05-16`
- Branch is ahead of remote.
- There may be uncommitted local work from P27.5b/P28/D-061 closeout and P29
  prompt preparation.
- Do **not** push.
- Do **not** commit unless Michael explicitly asks.

If the working tree is dirty, first summarize the dirty files and ask Michael
whether to commit before starting P29. Do not mix new P29 implementation into
uncommitted closeout work without approval.

### 1. Must-Read Repo Context

Read these before acting:

1. `.cursor/rules/mems26-pre-live-protocol.mdc`
2. `.cursor/rules/mems26-stability.mdc`
3. `CLAUDE.md`
4. `docs/reports/handoff/CHECKLIST_TO_LIVE.md`
5. `docs/reports/handoff/GANTT_TO_LIVE.md`
6. `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md`
7. `docs/reports/PROMPT28_REPLAY_SMOKE_RUN.md`
8. `docs/reports/handoff/MEGA_PROMPT_P29_SCENARIO_PACK.md`

### 2. Master Review Is Required Before P29

Before starting P29, review the authoritative spec docs Michael provides:

- Master Index V2
- Constitution V3
- `MEMS26_FIRST.md`

If they are not pasted into the chat or otherwise available in context, stop
and ask Michael to paste the relevant sections. Do not infer missing governance
or taxonomy from local derived docs alone.

Pay special attention to:

- P29 scenario taxonomy and scope.
- Day Type V2 expectations.
- D-061 Killzone policy.
- Governance rules for SHADOW -> DEMO -> LIVE.
- Any D-### decisions that affect replay/scenario behavior.

Do not invent any D-###. If a new decision seems needed, write
`(DRAFT — needs governance review)` and stop.

### 3. Current Verified State

- Phase 0 is GREEN.
- P27.5b is GREEN:
  - `scripts/uat_prompt_27_5b_live_price.sh` returned 10/10 PASS.
  - `age_ms=178-982ms`, latency `1-6ms`, valid JSON.
  - `/api/v9/live_price` reads Sierra file directly; bridge is not in that endpoint path.
- Phase 1 / P28 is GREEN:
  - `status_check` PASS.
  - `prompt_26_replay_clock_smoke` PASS.
  - post-P27.5 endpoint checks PASS.
  - `python3 -m pytest tests/v9/ -q` PASS: `1244 passed, 1 skipped`.
- Killzone is aligned to D-061:
  - Killzone zones are observational/tag/context only.
  - `PRE_MARKET`, `LUNCH`, `CLOSE_FINAL`, and `AFTER_HOURS` do not hard-block
    by zone label alone.
  - Hard blocks come from trading calendar, manager disable, news/risk/mode controls.
  - `sizing_modifier` is advisory/context, not a hard block by itself.
- Day Type policy:
  - Prior-day candles/context are required for trading.
  - Missing prior-day context remains `A1 / UNKNOWN / DEGRADED`.
  - Do not mark Day Type tradable when previous-day context is missing.
- No SHADOW/DEMO/LIVE is enabled.
- No `trade_command.json` writes.
- No push.

### 4. Current Gate

We are stopped at the **Phase 1 -> Phase 2** gate.

Do not begin P29 unless Michael explicitly writes approval such as:

```text
I approve Phase 1 -> Phase 2. Start P29 Scenario Pack.
```

If Michael only asks for review/planning, do review/planning only.

### 5. If Michael Approves P29

Use:

`docs/reports/handoff/MEGA_PROMPT_P29_SCENARIO_PACK.md`

P29 goal: build/execute a reproducible 10-scenario replay scenario pack:

1. Trending day
2. Balance / non-trend
3. Opening drive
4. S2 Five-Min setup
5. S3 Footprint setup
6. S4 Woodies setup
7. Killzone context change
8. TPO context / location
9. Missing / degraded data
10. Pre-fire / risk block

Strong preference: offline reproducible fixtures/tests. Do not use live Sierra
randomness unless Michael explicitly decides that is required.

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

### 7. Claude Code Coordination

Michael may be sending work to Claude Code in parallel.

Claude Code may be useful for:

- report drafting,
- summarizing raw test output,
- non-destructive read-only exploration,
- preparing a P29 scenario matrix from existing fixtures.

Do not accept Claude Code summaries at face value. Verify raw evidence before
marking GREEN. If Claude Code changes files, inspect the diff and run tests.

### 8. Stop Conditions

Stop and ask Michael if:

- Master Index V2 / Constitution V3 / `MEMS26_FIRST.md` are needed but absent;
- P29 scenario scope conflicts with authoritative docs;
- any path might write a real/demo/live command;
- `tests/v9/` regresses;
- a DEMO/LIVE flag or gateway slot becomes non-empty;
- bridge/Sierra/live replay becomes necessary.

## Paste To Here

---

## Operator Note

This is a handoff prompt. It does not approve Phase 1 -> Phase 2 by itself.
Michael must explicitly approve before P29 execution.
