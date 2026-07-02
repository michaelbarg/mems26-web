# CC — Finalize WIP + ONE clean restart + post-restart verify — 2026-07-02

**Owner:** Michael · **Prepared by:** Cowork · **Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` (Rule 5 raw output).
**Decision (Michael 2026-07-02):** commit/verify the outstanding WIP first, then a **single clean restart** brings every fix live together. Nothing is live yet — the running backend booted BEFORE all these commits, so it's still the old code.

## Context — the fix set that must go live
- **GAP-1 contracts (Cowork, committed `6ec3209`):** `FIXED_CONTRACTS_3` was dead-wired (only `compute_v2_sizing`). Now forced (flag-gated, reject/0 preserved) at the S2 sizing source `get_quality_tier_v2` **and** the command choke point `command_from_setup`. 3 regression tests pass (`test_fixed_contracts_3_command.py`). Live bug it fixes: MED/LOW fires sent **2** contracts.
- **CC committed:** resolver `168391c`+`e6add5d` (GAP-3), warm-start `faa1056` (GAP-5), slot `e72f7f7` (GAP-2), opposite-exit `0930229` (GAP-6, `OPPOSITE_EXIT_V1` default OFF), P5 e2e test `5d70763` (GAP-4). Verified flag-gated correctly.

## Step 1 · Finalize the UNCOMMITTED WIP (do NOT let a restart activate unreviewed code)
`git status` shows these modified-but-uncommitted:
- **`woodies_system.py` — Mechanism-C ZLR** (DLL zlr on a non-new-bar push → run detection). This is **trading-logic** → verify it can't double-detect/double-fire the same `bar_ts`; add/confirm a regression test; commit with rationale, or revert if not ready.
- **`five_min_system.py` — bar-key normalization** (setdefault o/h/l/c/v before buffering). Robustness (extends the `'c'` fix to overnight bars). Confirm + commit.
- **docs** (`STATUS_BOARD.md`, `ROADMAP_TO_LIVE.html`, `MEMS26_ISSUES_REGISTER.md`, `SOURCE_OF_TRUTH.md`, `PATTERN_PAGE.html`, `EOD_SCHEDULER_LOG.md`, `CC_STAGE1_*`) — commit the tracking updates. **Fold GAP-1 into STATUS_BOARD** (root=dead-wiring, fix=6ec3209, verified=3 tests) per the roadmap-auto-update rule.
- End state: `git status` clean.

## Step 2 · ONE clean restart (RTH must be CLOSED or pre-market)
`launchctl kickstart -k gui/$(id -u)/com.mems26.backend` (do NOT start a duplicate; check listeners on 127.0.0.1:8000 first).

## Step 3 · Post-restart verification — paste raw output (Rule 5)
1. **Flags at boot:** `[env_loader]` line shows `FIXED_CONTRACTS_3=1 · DAYTYPE_TARGETS_STRUCTURAL=1 · DAYTYPE_POSITION_GATE=0` and `OPPOSITE_EXIT_V1` unset (OFF).
2. **Warm-start (GAP-5):** within 1 bar of open — Woodies `buf=50`, `day_type≠UNKNOWN`, VA present; `hydrate_demo_slot` logged (free or hydrated).
3. **GAP-1 live proof:** the FIRST fire → `trade_command.json` has `"contracts":3`. Especially catch a **MEDIUM/LOW-tier** fire (those were 2). Paste the JSON.
4. **GAP-3 live proof:** a fire's targets are structural + capped — no −92pt T1, no +4.75 off a 0.25 stop.
5. **GAP-2 live proof:** when a demo trade closes **normally** (not EOD), `demo_slot` frees and the next fire can take demo (yesterday only 261/267 got demo; 267 held until EOD_MANUAL).

## NOT-DONE
- ❌ Don't restart with unreviewed WIP still uncommitted (Step 1 first).
- ❌ Don't restart mid-RTH.
- ❌ Don't revert `6ec3209` or the flags (`FIXED_CONTRACTS_3=1`, `DAYTYPE_POSITION_GATE=0`).
- ❌ Don't claim "3 contracts" or "targets fixed" from tests alone — prove from the live `trade_command.json` after a real fire (Rule 5).
