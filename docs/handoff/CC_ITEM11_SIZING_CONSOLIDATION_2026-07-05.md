# CC prompt — item-11: consolidate the two live sizing systems (LIVE-blocker)

**Owner:** Claude Code. **Priority:** the ONE missing-code piece Michael ruled
in (2026-07-05) — a real LIVE-blocker. Everything else (12/13/16/17/7/8) is
deferred until a profitable validated baseline. **Do NOT build those.**

## The problem (verify before touching — Rule 2)

Two sizing systems run in parallel in the routing path:
- **`calculate_size` (legacy)** — still referenced in ~5 files
  (`gen_index`/grep `calculate_size`): `woodies_system.py`, `decision_tree.py`,
  `five_min_system.py`, `stop_anchors/sizing.py`, `footprint_system.py`.
- **`compute_v2_sizing` / `get_quality_tier_v2` (V2)** — the intended path.

Live symptom on record (STATUS_BOARD 2026-07-02 ~18:50): **A5 emitted a
"reject" while V2 said 3 contracts** — the legacy path can still veto/resize a
fire the V2 path approved. Under `FIXED_CONTRACTS_3=1` the *number* is masked
(forced to 3), but the legacy **reject branch can still block a fire entirely**.
Before LIVE this ambiguity must be gone: one sizing authority, one answer.

Also fold in the related fill-fallback risk noted the same day: the
FillPoller "most recent active" fallback can close an UNRELATED trade when no
per-contract mapping exists (I-58 narrowed it to demo-only; confirm no legacy
sizing path re-introduces an unmapped close).

## Deliverable

1. **Audit first, paste raw output** (Rule 5): grep every `calculate_size`
   call site; for each, classify KEEP / ADAPT / REPLACE / DEAD. Show which are
   actually reached at runtime vs dead imports. Do not refactor blind.
2. **Single sizing authority:** route every live sizing decision through the V2
   path (`get_quality_tier_v2` / `compute_v2_sizing`). The legacy
   `calculate_size` either (a) becomes a thin shim delegating to V2, or (b) is
   removed at the dead sites. Under `FIXED_CONTRACTS_3=1` the contract count
   must be identical before/after — prove it.
3. **Kill the legacy reject path** as an independent fire-veto: a sizing module
   must not silently block a fire the gateway approved. If a zero-size condition
   is legitimate, it must surface as an explicit, logged gateway `blocked_by`,
   not a swallowed reject. (No silent failures.)
4. **Flag-gate if behavior changes at all:** if consolidation changes any live
   number/verdict, put it behind `SIZING_CONSOLIDATION_V1` default-OFF +
   strategic-stop for Michael. If it's provably a pure no-op refactor under
   `FIXED_CONTRACTS_3=1`, it may land un-flagged — but only with the
   before/after proof in the report.

## Tests (anti-tautological, fail-on-old)

- A fire that the legacy path would `reject` but V2 approves → **routes** after
  the fix (fails on current code).
- Under `FIXED_CONTRACTS_3=1`: contract count == 3 at every sizing source,
  before == after (no drift).
- No unmapped/unrelated close path survives (guard the I-58 fallback).

## Constraints

- Local Postgres only; restart via `launchctl kickstart -k
  gui/$UID/com.mems26.backend`, 0 open trades first.
- Snapshot before any `.env` touch. Regenerate `gen_index.py` +
  `gen_flag_index.py` if structure/flags change.
- Update `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` + `MICHAEL_ISSUES_LEDGER.md`
  (item-11 row) with finding + fix + raw verification per the reporting rule.
- **NOT-DONE section mandatory** at the end: anything you didn't finish, and why.

## Context pointers

`docs/plans/GAP_ANALYSIS_2026-07-05.md` (item-11 = the one owed missing-code
piece) · `docs/plans/SYSTEM_CLEANUP_AUDIT_2026-07-02.md` §א (two-sizing-systems
row) · `docs/handoff/NEW_CHAT_ONBOARDING_2026-07-05.md` §3.
