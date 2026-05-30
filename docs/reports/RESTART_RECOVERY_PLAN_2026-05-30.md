# Restart Recovery Plan — 2026-05-30

## Problem 1: 5-min Bar Gaps After Restart

**Root cause:** `Bars5MinStream._push_api()` sends only `bars[-1]` (latest bar) on each poll. After a backend restart mid-RTH, bars between the last DB entry and the current Sierra export are lost.

**Proposed fix:**
1. On startup, query `SELECT MAX(ts) FROM v9_bars_5min` to get the last known bar timestamp.
2. On first `_push_api` call, send all bars from Sierra export where `bar.ts > last_known_ts` instead of just the latest.
3. After the initial backfill, resume sending only the latest bar.

**Implementation:** Add a `_first_push = True` flag to `Bars5MinStream`. On first push, filter `bars` to those after last DB ts. Set `_first_push = False` after.

## Problem 2: S1 Day Type Resets on Restart

**Root cause:** `state_machine.py:reset()` clears all state (IB, opening, confidence, lock). No `day_type_seed.py` found — hydration exists but only reads from DB history, which may itself be stale or missing opening data.

**Proposed fix:**
1. On backend restart during RTH, **replay the last N opening bars** from `v9_bars_5min` (N=6, covering 09:30-10:00 ET) through the state machine's A1→A2→A3 stages to reconstruct `opening_type`.
2. Load IB from `v9_tpo_sessions` or Sierra `tpo.json` export (already ingested).
3. Load confidence/lock_state from last `v9_day_type_state` row if today's date matches.
4. Skip replay if we're past forced-lock time (13:00 ET) — just load the locked state from DB.

**Risk:** Replay of bars after IB lock may trigger re-evaluation loop. Mitigate by checking `session_min >= 210` (post-lock) and skipping to C3 directly.

## Implementation Priority

Both fixes are pre-LIVE requirements. Implement after Michael reviews and approves the heuristics (replay window size, when to skip, etc.).
