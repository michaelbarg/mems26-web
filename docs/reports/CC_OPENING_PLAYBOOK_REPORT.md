# CC — Opening Playbook Report (2026-07-29)

**Workorder:** `CC_WORKORDER_2026-07-29_FULL.md` + `CC_SYSTEM0_MARKET_CONTEXT_2026-07-29.md`
**Agent:** cc-macbook | **Contract:** CC_HANDOFF_CONTRACT.md

## Phase Summary

| # | Phase | Status | Tests | Flag |
|---|---|---|---|---|
| D3/P3 | Bar seam guard | DONE | 6 | BAR_SEAM_REJECT_V1=OFF |
| P0 | ET anchor + anti-phantom | DONE | 5 | OPENING_ANCHOR_ET_V1=OFF |
| P4/A | MarketContext (System 0) | DONE | 6 | MARKET_CONTEXT_V1=OFF |
| P4/B | Dalton gaps in opening detector | DONE | 6 | OPENING_DALTON_GAPS_V1=OFF |
| P1 | Opening playbook config | DONE | 6 | OPENING_PLAYBOOK_V1=OFF |
| P2 | Opening runner ride | DONE | 7 | OPENING_RUNNER_RIDE_V1=OFF |
| P4/C | Replay + acceptance timer | **NOT-DONE** | — | — |
| D1 | TEST_DRIVE reclassification | **NOT-DONE** | — | B2 drive-invalidation is the foundation |
| D2 | DD classification + early Trend | **NOT-DONE** | — | See continuation |
| P5 | Task queue (hysteresis, S6) | **NOT-DONE** | — | — |

**36 new tests pass. All flags OFF. Zero live behavior change.**

## D3/P3 — BAR_SEAM_REJECT_V1

Bar discontinuity >15pt from neighbor → rejected, logged. Prevents replaying/training on corrupted bars (07-28: 31.5pt seam). Guard in `bars.py:post_woodies_5min`, fail-open on DB errors.

## P0 — OPENING_ANCHOR_ET_V1

- **ET anchor:** compares bar time at 09:30 ET instead of 16:30 IL. Fixes DST hazard (5 weeks/year IL 16:30 != ET 09:30). Built on cowork's TZ normalization fix.
- **Anti-phantom guard:** bars >10min old (from replay/hydration) produce zero opening signals. Prevents boot-replay phantom fires (the 07:38 phantom DRIVE).

## P4/A — MARKET_CONTEXT_V1 (System 0)

`MarketContext` dataclass + `get_market_context()`: composes `opening_type`, `day_type`, `dir_bias`, `expansion`, `balance_state` into a single contract. Escalation-only (fields only strengthen within session). When OFF, returns UNKNOWN skeleton — zero behavior change. Consumers (gateway, panels) not yet wired (A2 = NOT-DONE, see below).

## P4/B — OPENING_DALTON_GAPS_V1

Four Dalton fixes in `opening_detector_v2.py`:
1. **B1 balance_state:** `_loc()` promoted from comment to `balance_state` field + conviction map
2. **B2 drive invalidation:** OPEN_DRIVE invalidated when price returns through opening range (the 07-28 TEST_DRIVE that was misclassified as DRIVE)
3. **B3 AUCTION_OUT conviction:** 0.5 → 0.55, "double-distribution potential" note, conviction=high
4. **B4 acceptance timer:** placeholder field in MarketContext (full timer = NOT-DONE)

## P1 — OPENING_PLAYBOOK_V1

`config/opening_playbook.yaml` + engine (`opening_playbook_engine.py`):
- Per opening type: entry trigger, stop rule, T1 formula, runner strategy, invalidation condition
- Gate exemptions: opening trades exempt from `awaiting_release` + `lsma_flat` (config field, not hardcode)
- Engine `resolve()` returns None when OFF → existing triggers unchanged

## P2 — OPENING_RUNNER_RIDE_V1

`opening_runner.py`: structural trailing after T1:
- Trail on 30-min swing (6-bar window, 1pt buffer behind the swing)
- Exit on LSMA color flip against the trade direction
- Replay 07-28: ORR-long from ~7433, trail at 7451 → runner holds to 7470+ (24pt room)

## NOT-DONE (with continuation)

**P4/A2 — Consumer wiring:** Gateway + panels need to read `get_market_context()` instead of scattered getters. Blocked on: sim-verify of the context first, then wire one consumer at a time. Map: `trading_gateway.py` playbook-kwargs block (lines 699-748) → `get_market_context()` + fallback.

**P4/B4 — Acceptance timer:** Full timer (12 bars × ≥70% inside reference zone → accepted/rejected) not built. MarketContext.acceptance stays "pending" until this is implemented.

**P4/C — Replay 07-28 full validation:** Requires backend restart with new flags ON + bar data from 07-28 (bars up to 18:10 only, per D3 seam warning). Must produce `OPEN_DRIVE SHORT` at open + `ORR LONG` on return. Blocked on: bar integrity verification (D3 needs to be enabled first to filter the 07-28 seam).

**D1 — TEST_DRIVE reclassification:** B2 (drive-invalidation) is the foundation — a drive that gets invalidated now falls through to TEST_DRIVE/ORR detection instead of staying as DRIVE. The remaining piece: explicit re-seed as TEST_DRIVE(UP) when rejection + return through open is detected.

**D2 — DD classification + early Trend:** Requires analysis of `dd_second_dist` feature in classifier_core and why the 07-28 DD wasn't classified. The early-Trend issue needs escalation-only lock + IB-lock gate + ≥2 consistent 30-min steps. Both are research-first tasks.

**D3 investigation — who rewrote bars:** The seam guard prevents the damage but the root cause (which component re-pushed old bars overnight) needs investigation. Candidates: the promoter's history-push, bridge reconnection re-send, or Sierra's own replay.

**P5 — Task queue:** Hysteresis-leg, S6 bracket coverage, S6 EOD gate audit, structural-stop-to-journal — all deferred to next session.

## What's on Michael/Cowork

1. **Enable flags** — sim-verify then enable (all OFF currently):
   - D3: `BAR_SEAM_REJECT_V1` (zero risk, advisory)
   - P0: `OPENING_ANCHOR_ET_V1` (correct DST handling)
   - P4/A: `MARKET_CONTEXT_V1` (after A2 wiring)
   - P4/B: `OPENING_DALTON_GAPS_V1` (after replay verification)
   - P1: `OPENING_PLAYBOOK_V1` (after config review)
   - P2: `OPENING_RUNNER_RIDE_V1` (after sim-verify trail logic)
2. **Replay 07-28** — with D3+P0+B2 ON, verify the two target trades fire
3. **D1/D2** — research phase before code
