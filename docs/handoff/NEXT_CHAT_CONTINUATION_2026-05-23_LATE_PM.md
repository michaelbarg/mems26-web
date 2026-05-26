# Next-chat continuation prompt · 2026-05-23 LATE PM

**Date generated:** 2026-05-23 22:10 IL
**Author:** Cursor agent
**For:** Michael (paste into the next chat to resume cleanly)
**Replaces:** `NEXT_CHAT_CONTINUATION_2026-05-23_PM.md` (19:10)

---

## TL;DR

3 Pkgs shipped + G3 PASSed in this session: **Pkg 1 (Adaptive Stop) · Pkg 2a (OFA Entry signal) · Pkg 2bc (OFA Config + belly_dominance + lookback + validators)**. S2 D-091 is now ~50% complete (Pipeline 1 packages 0, 1, 2a, 2bc done · 3a/3b/3c · 4a/4b · 5a/5b/5c · 6 · 8 remain). Backend full suite green at 531 passed · 2 skipped. **🟡 Unexpected commit `dd9c34f` (S1 EXIT_V6 NeuE+NeuC split) arrived without Cursor handoff** — needs Michael clarification + G3 retro. Pipeline 5 still gated on CC P5-0 audit + D-093 Q1/Q2.

---

## Paste-this prompt for the next chat

> Resume MEMS26 pre-LIVE work from 2026-05-23 LATE PM. Read these in order before anything else:
>
> 1. `docs/plans/STATUS_BOARD.md` (current build queue · all 4 Pkgs PASSED ✅ · open Pkgs queued)
> 2. `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` (V2 master plan)
> 3. `docs/decisions/D-091_S2_LIVE_SCOPE.md` (S2 LIVE scope · corrected formulas · Floor semantics Option A)
> 4. `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` (Pipeline 5 · 9 packages · 2 sub-decisions Q1/Q2 deferred)
> 5. CLAUDE.md + `.cursor/rules/mems26-pre-live-protocol.mdc` (guardrails · pre-LIVE 4-axis UAT discipline)
> 6. Last 3 commit diffs: `git show dd5e2f2` (Pkg 1) · `git show 847bb40` (Pkg 2a) · `git show dfdf91f` (Pkg 2bc) · `git show dd9c34f` (S1 EXIT_V6 · out-of-band)
>
> Top-of-queue decisions waiting on Michael:
> 1. **🟡 Investigate `dd9c34f`** — S1 EXIT_V6 NeuE+NeuC split arrived without Cursor handoff. 7 files in `backend/v9/systems/day_type/` (including new `neutral_classifier.py`). Author: Michael Barg. Likely Michael directly instructed CC outside our chat. Needs: (a) confirmation it was intentional · (b) retro G3 review · (c) integration into STATUS_BOARD as Pkg 3a-pre work.
> 2. **D-093.Q1** Gateway canonical (after CC P5-0a audit report — handoff not yet drafted)
> 3. **D-093.Q2** Sierra DEMO account identifier
> 4. **Redis migration mode** for Pkg 0 (`scripts/pkg0_redis_migrate.py` · rename vs drop)
> 5. **10 P-W open questions** on S4 Woodies (Pipeline 2 build-start gate)
> 6. **S1 Day Type verify report** (Pipeline 3) — may be partially addressed by dd9c34f
> 7. **S3 Footprint verify report** incl. O-4 audit (Pipeline 4)
> 8. **G4 smoke trade** for Pkg 1 + 2a + 2bc end-to-end (DB only · no Sierra)
>
> Do NOT start a new Pkg before G3-reviewing dd9c34f and choosing the next Pipeline target.

---

## Current state snapshot · what changed since 19:10

### Pipeline 1 · S2 D-091

| Pkg | State | Commit | Tests |
|-----|-------|--------|-------|
| **0** · Path B deletion | ✅ G3 PASS | `1c805ea` | 5613 LOC deleted |
| **1** · Adaptive Stop Engine | ✅ G3 PASS (this session) | `dd5e2f2` | 18 new |
| **2a** · OFA Entry signal + family mapping | ✅ G3 PASS (this session) | `847bb40` | 20 (was 9 · +11) |
| **2bc** · OFA Config + belly_dominance + lookback + validators | ✅ G3 PASS (this session) | `dfdf91f` | 29 patterns + 13 validators + 14 footprint (+23 net) |
| 3a-c · Layer 4 (day-type targets · trail · contract split) | ⏳ DEP on EXIT_V6 (potentially addressed by `dd9c34f`) | — | — |
| 4a-b · Risk Rules (3 critical + 4 tightening) | ⏳ DEP on Pkg 3 | — | — |
| 5a-c · Patterns (Inv H&S + Double + Flag) | ⏳ Spec locked (Bulkowski lock 3) · independent | — | — |
| 6 · TradeManager hook-based | ⏳ LAST · DEP on ALL above | — | — |
| 8 · Quality V2 | ⏳ DEP on Authority Table | — | — |

### Pipeline 5 · Sierra Order Routing

All 9 packages queued · P5-0 verify-first audit not yet handed off (deferred from 19:10 plan).

### Backend test suite baseline

531 passed · 2 skipped (was 517 · +14 net from Pkg 2bc · all S3 + validator additive tests).

### Unexpected · commit `dd9c34f` (out-of-band)

```
dd9c34f feat(s1): EXIT_V6 fix · split Neutral into NeuE+NeuC per D-091.Q1
Author: Michael Barg <service@passparto.co.il>
Date:   Sat May 23 20:38:14 2026 +0300

Files (7):
  backend/v9/layer3/entry_executor.py              | 6 LOC
  backend/v9/systems/day_type/api.py               | 14 LOC
  backend/v9/systems/day_type/compliance_manifest.yaml | 6 LOC
  backend/v9/systems/day_type/neutral_classifier.py | 59 LOC (NEW)
  backend/v9/systems/day_type/schemas.py            | 6 LOC
  backend/v9/systems/day_type/state_machine.py      | 32 LOC
  backend/v9/systems/day_type/targets_table.py      | 92 LOC
```

**Interpretation:** Michael likely instructed CC directly outside the supervised Cursor flow to address open Strategic Stop #4 (EXIT_V6 fix for 7 day types). Author of commit matches Michael's email · co-authored by Claude Opus 4.6. NOT documented in any STATUS_BOARD amendment by Cursor before this session.

**Action needed next chat:**
1. Confirm with Michael it was intentional.
2. Retro G3 review (4-axis: existence of tests · no regression · spec match · no scope creep).
3. Update STATUS_BOARD with retro entry · mark Strategic Stop #4 as RESOLVED if appropriate.
4. Update D-091.Q1 references if this commit addresses them.

---

## Strategic stops waiting on Michael (8)

| # | Item | Blocks |
|---|------|--------|
| 1 | **🟡 dd9c34f review** — confirm + retro G3 + STATUS_BOARD entry | Day-Type strategic stop #4 closure |
| 2 | D-093.Q1 Gateway canonical | P5-1 onward |
| 3 | D-093.Q2 Sierra DEMO account ID | P5-3 onward |
| 4 | Redis migration mode for Pkg 0 | minor · backlog |
| 5 | 10 P-W open questions on S4 Woodies | Pipeline 2 start |
| 6 | S1 Day Type verify report | Pipeline 3 · possibly partially addressed by dd9c34f |
| 7 | S3 Footprint verify report (incl. O-4 audit) | Pipeline 4 |
| 8 | G4 smoke trade for Pkg 1 + 2a + 2bc | Pre-SHADOW gate |

---

## Files created/modified this session (for git-stash awareness)

### Files committed by CC (via Michael)

| Commit | Files | LOC |
|--------|-------|-----|
| `dd5e2f2` (Pkg 1) | 2 files (`adaptive_stop.py` NEW · `five_min_system.py`) | +500 |
| `dd9c34f` (S1 EXIT_V6) | 7 files in `day_type/` (incl. `neutral_classifier.py` NEW) | +200 |
| `847bb40` (Pkg 2a) | 2 files (`five_min_system.py` · `test_five_min_patterns.py`) | +147/-5 |
| `dfdf91f` (Pkg 2bc) | 5 files (S2 · S3 · 2 test files) | +382/-45 |

### Cursor-authored docs (not committed)

- `docs/handoff/DESKTOP_PKG2A_OFA_ENTRY_HANDOFF.md` (Pkg 2a handoff · used)
- `docs/handoff/DESKTOP_PKG2BC_OFA_CONFIG_HANDOFF.md` (Pkg 2bc handoff · used)
- `docs/handoff/ZOHAR_PKG2BC_SPEC_CLARIFICATION.md` (drafted but self-resolved by Michael · not sent)
- `docs/plans/STATUS_BOARD.md` (8 new amendments)
- `docs/handoff/NEXT_CHAT_CONTINUATION_2026-05-23_LATE_PM.md` (this file)

---

## What Cursor will do next chat

1. **Investigate dd9c34f first** — `git show dd9c34f` · check it didn't break tests · ask Michael to confirm intent.
2. If `dd9c34f` was intentional: retro G3 review · update STATUS_BOARD · close Strategic Stop #4.
3. Then ask Michael which Pkg next from these candidates:
   - **Pkg 5a** (Inv H&S + H&S Top) · pre-LIVE pattern · independent · lock 3
   - **P5-0 Gateway audit** (Pipeline 5) · draft `DESKTOP_PIPELINE5_P5-0_HANDOFF.md`
   - **G4 smoke trade** for Pkg 1 + 2a + 2bc (DB-only end-to-end verification)
4. If new spec drift discovered during retro · STOP and report (do not absorb silently).

---

## Critical context preserved across sessions

### Lines 205-207 (now 215-217) byte-identical rule

The chronic toxicity comment in `five_min_system.py`:
```
# Delegate to existing chart_5min detector for pattern detection
# (integration point — full wiring in future prompts)
return None
```

Was originally at lines 205-207. After Pkg 2bc added 8 module constants near top of file, the block shifted to lines 215-217 (content unchanged). The rule is **content byte-identical**, not line-number identical. Any future Pkg handoff must reference this block by content-match (e.g., `grep -E "Delegate to existing chart_5min detector"`) not by line number.

### Family mapping (Pkg 2a · DO NOT REGRESS)

Line ~569 of `five_min_system.py`:
```python
family = "Reactive" if kind == "REACTIVE" else "OFA"  # INITIATIVE → OFA family (D-091)
```

NOT `kind in ("REACTIVE_LONG", "REACTIVE_SHORT")` — this was the bug from Pkg 1 G3, fixed in Pkg 2a. Any future change to detector `kind` values must update this mapping.

### Pkg 2bc module constants (DO NOT REGRESS)

In `five_min_system.py` after imports:
```python
DROP_THRESHOLD_PCT = 0.10
EXPANSION_MIN_PT = 1.5
EXPANSION_MAX_PT = 1.75
POC_RETURN_TOLERANCE_PT = 0.5
MIN_BARS_REQUIRED = 7   # 4 pattern + 3 lookback
LOOKBACK_BARS = 3
LOOKBACK_MAX_VOL_RATIO = 0.6
BELLY_DOMINANCE_RATIO = 1.5
```

These are SHADOW-soak-calibratable. Do not change defaults without updating `test_constants_have_documented_defaults` in `test_five_min_patterns.py`.

### S3 forces_history (Pkg 2bc · additive · do not remove)

`FootprintSystem._forces_history` list cap 7 · exposed via `current_state["forces_history"]`. S2 reads `forces_history[-2]` for bar 3 belly ratio. If S3 schema changes, S2's `_get_belly_ratio_from_footprint` must update.

### Graceful degradation (production safety)

`belly_dominance_ratio` returns None when `forces_history` is empty or insufficient. S2 treats None as PASS (skip check) not REJECT. This prevents S2 from silently stopping all fires if S3 has transient state issues. Tested explicitly in `test_reactive_long_passes_when_forces_history_unavailable`.

---

## Useful command quick-reference

```bash
# Run all pre-LIVE test suites · should all be green
BRIDGE_TOKEN=dummy python3 -m pytest tests/atomic/test_five_min_patterns.py -q           # 29 expected
BRIDGE_TOKEN=dummy python3 -m pytest tests/v9/systems/test_five_min/ -q                  # 18 expected (Pkg 1)
BRIDGE_TOKEN=dummy python3 -m pytest backend/v9/shared/tests/test_pre_fire_validator.py -q # 13 expected
BRIDGE_TOKEN=dummy python3 -m pytest backend/v9/tests/test_footprint_system.py -q        # 14 expected
BRIDGE_TOKEN=dummy python3 -m pytest backend/v9/tests/ -q                                # 531 expected

# Verify chronic toxicity block byte-identical (content match · ignore line number)
sed -n '/Delegate to existing chart_5min detector/,/return None$/p' backend/v9/systems/five_min/five_min_system.py

# Smoke boot
BRIDGE_TOKEN=dummy python3 -c "
from backend.v9.systems.five_min.five_min_system import FiveMinSystem
from backend.v9.systems.footprint.footprint_system import FootprintSystem
FiveMinSystem(); FootprintSystem()
print('smoke OK')"

# Check open commits
git log --oneline -10
```

---

*End of continuation prompt · paste-ready · 2026-05-23 22:10 IL*
