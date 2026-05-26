# MEGA PROMPT · Package W-2 · Trend State Machine + YELLOW block

**Produced by:** Claude Desktop · 2026-05-25 IL · for CC · reviewed by CD (per INDEX §6)
**Final reviewer:** Cursor (batch · after all 10 packages CD_PASSED)
**Spec authority:** D-092 LOCKED 2026-05-23 §Trend State + Sheet C §6.3 + INTAKE v2 P-W5 LOCK A + DTV1 §A1 Strategic Gate

---

## ⚠️ Read this before starting

You are Claude Code (CC). You execute this prompt single-shot. W-2 is **ADAPT** — extend the existing `a1_strategic_gate.py` to honor YELLOW state as a BLOCK for ALL 9 patterns. The state machine itself (BLUE/RED/YELLOW/GRAY detection) may already exist in A1 or may need to be extracted to a separate `trend_state.py` — W-0 audit findings determine which.

**This package is a WIRING change.** Memorial Day §5 lessons apply FULL force (live Python repro mandatory · payload-vs-data discipline · real BarEvent class).

Prerequisite: W-0 codebase audit CD_PASSED · W-2 reads §3.4 drift #5 (a1_strategic_gate.py 5-color current state) and §3.5 W-2 readiness verdict before starting.

---

## §1 · Spec authority (verbatim, locked)

### §1.1 · D-092 LOCKED · Trend State Handling (4 states)

> | State | Rule | CONT | REV |
> |---|---|---|---|
> | **BLUE** uptrend | CCI > 50 + prev > 0 + SWI > 20 · Liran: ≥6 bars above ZL with ≥1 bar >+100 | ✅ FIRE | ❌ BLOCK |
> | **RED** downtrend | Mirror of BLUE | ✅ FIRE | ❌ BLOCK |
> | **YELLOW** transition (5th opposite bar) | **P-W5 LOCKED A · BLOCK ALL 9** (Wood WSI · Liran "next bar flip") | ❌ | ❌ |
> | **GRAY** chop / no trend | BLOCK or require confidence > 0.55 (current code) | ❌ | ❌ |

### §1.2 · Sheet C §6.3 · Trend State Handling (verbatim)

> | State | Rule |
> |---|---|
> | BLUE — uptrend confirmed | CCI > 50 + prev > 0 + SWI > 20. Liran: ≥6 bars above ZL with ≥1 bar >+100, ideally >+200. → CONT patterns FIRE, REV patterns BLOCK. |
> | RED — downtrend confirmed | Mirror of BLUE. → CONT patterns FIRE, REV patterns BLOCK. |
> | YELLOW — TRANSITION (5th opposite bar) | P-W5 OPEN: researcher's read = BLOCK ALL 9 PATTERNS. Either old trend is dying (CONT invalid) or new trend not locked (REV premature). Wood transcripts: "WSI = Wait, Sit, Inspect." A1 gate handling only GRAY is incomplete vs Spec V1's 4-state design. |
> | GRAY — chop / no trend | BLOCK by default, or require confidence > 0.55 per current code. Matches Liran: "market off" = don't trade. |

**Note:** Sheet C row 3 (YELLOW) still says "P-W5 OPEN" because the CSV is dated 23/5, two days before INTAKE v2 closed P-W5. **The INTAKE v2 LOCK A in §1.3 below is the operative authority.** Sheet C §6.3 is otherwise authoritative.

### §1.3 · INTAKE v2 LOCKED 2026-05-25 16:50 · P-W5 verbatim

> "YELLOW trend state (5th opposite bar) · BLOCK ALL 9 patterns · both CONT and REV. DTV1 Stage A1 (Strategic Gate) extended with `if trend_state == 'YELLOW': reject_all_patterns`. No pass-through · no reduced-confidence override. Wood 'WSI' + Liran 'next bar flip' doctrine. SHADOW frequency hit acceptable risk for V1; revisit in Phase B if too restrictive."

**Operative directive for W-2:** A1 strategic gate must return `direction_allowed = NONE` and `color = YELLOW` when YELLOW is detected · NO pattern (CONT or REV) may proceed past A1 in YELLOW.

### §1.4 · DTV1 v1.0 §A1 Strategic Gate (verbatim · the spec the existing code is built against)

> **Stage A1 — Strategic Gate**
>
> Type: 🎨 Woodies Core (independent decision)
>
> Purpose: Determine which trade direction is allowed today based on CCI 14 vs Zero Line behavior over 6+ bars.
>
> Inputs:
> - `cci_14_value` (float, current bar)
> - `cci_14_history` (last 10 bars)
> - `zero_line` (constant: 0)
>
> Logic:
> ```
> IF cci_14 > 0 for 6+ consecutive bars → color = BLUE → LONG allowed, SHORT blocked
> IF cci_14 < 0 for 6+ consecutive bars → color = RED → SHORT allowed, LONG blocked
> IF cci_14 crosses 0 frequently in last 10 bars → color = GREY → wait
> IF cci_14 changes from sustained trend to opposite → color = YELLOW → stand aside
> ELSE → color = INDETERMINATE → wait
> ```
>
> Outputs:
> - `direction_allowed`: LONG | SHORT | NONE
> - `color`: BLUE | RED | GREY | YELLOW | INDETERMINATE
>
> Terminal States from this stage:
> - 🟡 SKIP — color veto (GREY/YELLOW/INDETERMINATE)
>
> Edit notes:
> - To change persistence threshold (currently 6 bars), edit `bars_persistence_required` parameter.
> - To remove YELLOW state and merge into GREY, edit `yellow_detection: false`.

### §1.5 · DTV1 vs D-092 drift on color states

**Drift identified:** DTV1 §A1 enumerates 5 colors (BLUE/RED/GREY/YELLOW/INDETERMINATE). D-092 §Trend State + Sheet C §6.3 enumerate 4 states (BLUE/RED/YELLOW/GRAY). The 5th color (INDETERMINATE) does not appear in D-092.

**Resolution (per Pipeline V2 §0 authority hierarchy "latest in time wins" + D-092 LOCKED 23/5 is newer than DTV1 9/5):** D-092 4-state set is operative. INDETERMINATE collapses into GRAY semantically (both mean "wait · don't trade").

**Spelling normalization:** D-092 uses `GRAY` · DTV1 uses `GREY`. CC uses **`GRAY`** (D-092 spelling) consistently in code. If existing code uses `GREY`, normalize within W-2 scope (it's a string/enum value, not a behavioral change).

### §1.6 · DTV1 §A1 terminal contract (verbatim · what A3 expects)

> Terminal States from this stage:
> - 🟡 SKIP — color veto (GREY/YELLOW/INDETERMINATE)

Post-W-2: terminal becomes "🟡 SKIP — color veto (GRAY/YELLOW)" since INDETERMINATE folds into GRAY.

**A3 expects:** `direction_allowed in {LONG, SHORT, NONE}`. If `NONE`, A3 must return `pattern_matched=NONE` (the existing contract per DTV1 §A3 "Terminal States: 🟡 WAIT — no pattern matched"). W-2 ensures the YELLOW path produces `direction_allowed=NONE` · A3 then naturally yields no pattern.

---

## §2 · Existing code surfaces

### §2.1 · W-0 audit prerequisite

Before writing W-2 code, CC reads:

```
docs/reports/PIPELINE_2_S4_AUDIT.md  (W-0 output · CD_PASSED before W-2 starts)
```

Specifically:
- §3.4 **Drift #5** — current state of `stages/a1_strategic_gate.py` (was reported as 5-color including YELLOW at line 23 per meta-prompt §4.2 seed)
- §3.5 **W-2 readiness verdict** — KEEP / ADAPT / REPLACE classification + effort estimate
- §3.2 row for A1 — `wires_correctly_to_pattern_engine` field — does A1 output already flow correctly to A3?

If W-0 audit found the implementation drastically different from DTV1 §A1 (e.g., merged with another stage · embedded in `pattern_engine.py` rather than `stages/a1_strategic_gate.py`), this is a STOP signal per §10. Do not adapt blindly — audit first.

### §2.2 · Files CC reads with the Read tool (mandatory · per §5 lesson #1)

```
backend/v9/systems/woodies/stages/a1_strategic_gate.py    [the file W-2 modifies]
backend/v9/systems/woodies/schemas.py                      [WoodiesBar, PatternId, Direction]
backend/v9/systems/woodies/decision_tree.py                [orchestration · understand how A1 is invoked]
backend/v9/systems/woodies/pattern_engine.py               [verify how A3 consumes A1 output]
backend/v9/systems/woodies/stages/a3_pattern_detection.py  [verify the contract A1→A3]
backend/v9/systems/woodies/stages/__init__.py              [stage registry · if exists]
backend/v9/services/bar_router/__init__.py                 [if A1 subscribes to bar events via router — §5 lesson #2]
```

**CC must quote the following with line numbers in the self-report (§5 lesson #1):**

1. The current color enum (or string constant set) in `a1_strategic_gate.py`
2. The current YELLOW detection logic
3. The A1 return type / dataclass / dict shape
4. The point where A3 reads A1 output

### §2.3 · Optional refactor decision (driven by audit)

If the trend-state detection logic in `a1_strategic_gate.py` is large and self-contained (e.g., 100+ LOC with multiple helper functions), CC MAY extract it to a new `backend/v9/systems/woodies/trend_state.py` module imported by A1. This is **OPTIONAL** — only do it if it makes the YELLOW BLOCK extension cleaner.

If extraction is done:
- `trend_state.py` exposes `compute_trend_state(cci_14_value, cci_14_history) -> TrendState` and the `TrendState` enum
- `a1_strategic_gate.py` becomes a thin wrapper: call `compute_trend_state` · apply BLOCK semantics per state · emit terminal
- Both files counted in §3 WRITE/MODIFY

If extraction is NOT done:
- All W-2 changes go inside `a1_strategic_gate.py`
- §3 has only MODIFY (no NEW)

CC chooses the cleaner path · documents the choice in self-report §11. **No half-extractions** (don't move part of the logic and leave part behind).

---

## §3 · SCOPE — exactly these files

### MODIFY EXISTING:

```
backend/v9/systems/woodies/stages/a1_strategic_gate.py     [MANDATORY · extend BLOCK semantics for YELLOW · normalize INDETERMINATE → GRAY · normalize GREY → GRAY]
tests/v9/systems/test_woodies.py                            [IF A1 unit tests live here · or wherever audit identified them]
```

### WRITE NEW (CONDITIONAL on §2.3 decision):

```
backend/v9/systems/woodies/trend_state.py                   [ONLY if §2.3 extraction is chosen]
tests/v9/systems/test_a1_strategic_gate.py                  [unit tests for A1 + YELLOW BLOCK · 10+ tests]
tests/v9/systems/test_trend_state.py                        [ONLY if §2.3 extraction is chosen]
```

### MODIFY OPTIONAL (verify audit first):

```
backend/v9/systems/woodies/compliance_manifest.yaml         [IF it enumerates color states · update GREY/INDETERMINATE → GRAY · DO NOT change if it doesn't mention colors]
```

### FORBIDDEN — do NOT touch:

Per INDEX §7 full forbidden surface (re-quoted):

```text
- sc_study/MES_AI_DataExport.cpp                       [Stream A · locked 037b6a7]
- bridge/v9_streams/*                                   [bridge local-only · mems26-stability.mdc]
- ~/Library/LaunchAgents/com.mems26.bridge.plist        [stability rule]
- backend/v9/api/v9/tpo_routes.py:343-360               [Stream B reject-and-warn · locked 73a6acf]
- backend/v9/systems/five_min/five_min_system.py:on_day_type_event  [Fix #4A.1 · locked 9e698aa]
- backend/main.py:89 (bar_router.subscribe day_type_classification)  [locked 598b3a9]
- backend/v9/db/session.py (WAL + busy_timeout settings)             [already configured · D-074]
- frontend/                                              [Pipeline 2 is backend-only]
- backend/v9/systems/{five_min,day_type,footprint,layer0}/  [other systems · S2/S1/S3/S5]
- docs/spec_authority/*                                  [LOCKED · only D-XXX changes them]
- docs/decisions/D-*.md                                  [LOCKED · only new D-XXX changes them]
- MEGA_PROMPT_PW_DECISIONS_INTAKE.md                     [LOCKED 25/5 16:50]
```

W-2-specific additions:

```text
- backend/v9/systems/woodies/patterns/*.py              [W-2 does NOT touch patterns · gating is BEFORE pattern detection in A3 · W-6 wires patterns]
- backend/v9/systems/woodies/pattern_engine.py          [W-6 orchestration scope · do NOT modify]
- backend/v9/systems/woodies/dispatcher.py              [W-8 scope]
- backend/v9/systems/woodies/atr_stop.py                [W-1 deliverable · independent]
- backend/v9/systems/woodies/stages/a2_*.py             [W-3 scope — day-type touch-point]
- backend/v9/systems/woodies/stages/a3_*.py             [A3 reads A1 output · should NOT need changes · if it does, that's a STOP]
- backend/v9/systems/woodies/stages/a4_*.py through b14_*.py [other stages · not in W-2 scope]
```

---

## §4 · Required behavior

### §4.1 · TrendState enum (4 values · per D-092)

```python
class TrendState(str, Enum):
    BLUE   = "BLUE"    # uptrend confirmed
    RED    = "RED"     # downtrend confirmed
    YELLOW = "YELLOW"  # transition · 5th opposite bar
    GRAY   = "GRAY"    # chop / no trend
```

**No INDETERMINATE.** If existing code has it, collapse into GRAY. **Use spelling GRAY (D-092)** not GREY (DTV1).

### §4.2 · State detection logic

Per D-092 §Trend State + Sheet C §6.3 + DTV1 §A1 logic:

```
Given:
  cci_14_history = last N bars of CCI-14 values (N ≥ 10 needed for confident classification)
  current_cci_14 = cci_14_history[-1]
  swi (Sidewinder) = optional · if available, use as confirmation
  zero_line = 0

BLUE if:
  - ≥6 consecutive bars with cci_14 > 0  (DTV1)
  - AND ≥1 bar in last 10 with cci_14 > +100  (Liran Stage-1)
  - AND current_cci_14 > 50 + previous_cci_14 > 0 + (SWI > 20 if available)  (D-092)

RED (mirror of BLUE) if:
  - ≥6 consecutive bars with cci_14 < 0
  - AND ≥1 bar in last 10 with cci_14 < -100
  - AND current_cci_14 < -50 + previous_cci_14 < 0 + (SWI < -20 if available)

YELLOW if:
  - was BLUE or RED in previous classification AND
  - the current bar is the 5th consecutive bar in the OPPOSITE direction of the prior trend
  - (i.e., if was BLUE, count consecutive bars with cci_14 < 0 since the BLUE classification ended ·
     when that count reaches 5, classify YELLOW)

GRAY if:
  - none of BLUE / RED / YELLOW criteria met
  - this includes: cci_14 crossing 0 frequently in last 10 bars (DTV1 GREY criterion)
  - this includes: was BLUE/RED but <5 opposite bars yet (transition forming but not YELLOW)
  - this includes: was YELLOW for >N bars without new trend confirming (degrades to GRAY)
```

**The state machine requires memory of the previous classification** (to know when YELLOW transitions back to GRAY or to the new BLUE/RED). CC examines existing A1 code to see how state persistence is currently handled · preserves the mechanism · documents in self-report §11.

### §4.3 · A1 output contract (must match what A3 consumes)

```python
@dataclass
class StrategicGateResult:
    direction_allowed: Literal["LONG", "SHORT", "NONE"]
    color: TrendState                # BLUE / RED / YELLOW / GRAY
    terminal: Optional[str]          # None if proceed to A3 · "SKIP — color veto" if blocked
    metadata: dict                   # optional · for debugging (which criterion fired, etc.)
```

**Behavior table:**

| color | direction_allowed | terminal | A3 next step |
|---|---|---|---|
| BLUE | LONG | None | A3 proceeds (CONT patterns may fire LONG · REV patterns blocked by family rule in W-6/W-8) |
| RED | SHORT | None | A3 proceeds (CONT patterns may fire SHORT · REV blocked) |
| YELLOW | **NONE** | **"SKIP — color veto (YELLOW per P-W5)"** | **A3 returns no pattern · all 9 blocked** |
| GRAY | NONE | "SKIP — color veto (GRAY)" | A3 returns no pattern (current behavior) |

**Critical:** the YELLOW row is the W-2 change. Pre-W-2 behavior may have been: YELLOW → direction_allowed=NONE (already blocking) OR YELLOW → some pass-through (which is the bug P-W5 LOCK A fixes). CC documents pre-state in self-report §11 (what was YELLOW doing before).

### §4.4 · Stage-1 lock confirmation (Liran's criterion · per Sheet C §6.3)

Liran: BLUE requires ≥6 bars above ZL **with ≥1 bar >+100, ideally >+200**.

W-2 enforces the ≥1 bar >+100 minimum. The ">+200 ideal" is a quality nuance not a hard gate (CC does NOT add a separate "ideal" check · only the >+100 minimum).

If the current A1 code doesn't enforce the >+100 minimum, that's a behavioral change W-2 introduces (BLUE/RED stricter). Document the delta in self-report §11.

---

## §5 · Golden tests (must pass · minimum N=10)

Test file: `tests/v9/systems/test_a1_strategic_gate.py` (plus `test_trend_state.py` if §2.3 extraction chosen).

```python
import pytest
from backend.v9.systems.woodies.stages.a1_strategic_gate import StrategicGate, StrategicGateResult
# (or trend_state import if extracted)
from backend.v9.systems.woodies.schemas import TrendState  # or wherever defined post-W-2
```

### Required test cases:

```
1. test_blue_classification:
   cci_14_history = [10, 30, 60, 110, 90, 70, 80, 95, 105, 75]  # 9 above ZL, peak 110
   → expected: color=BLUE, direction_allowed=LONG, terminal=None
   # 9 consecutive above ZL ✓ · 1 bar >+100 (105) ✓ · current 75>50? YES · prev 105>0 ✓

2. test_blue_fails_no_plus100_touch:
   cci_14_history = [10, 30, 60, 80, 90, 70, 80, 95, 90, 75]  # 9 above ZL but max 95 (no >+100)
   → expected: color=GRAY (or whatever non-BLUE), direction_allowed=NONE
   # Liran Stage-1 fails — no bar >+100

3. test_blue_fails_under_6_bars:
   cci_14_history = [-10, -5, 0, 30, 60, 110, 105]  # only 4 consecutive above ZL after sign-flip
   → expected: color=GRAY, direction_allowed=NONE

4. test_red_classification:
   cci_14_history = [-10, -30, -60, -110, -90, -70, -80, -95, -105, -75]
   → expected: color=RED, direction_allowed=SHORT, terminal=None

5. test_yellow_transition_blue_to_red_direction:
   # Prior state was BLUE · then 5 consecutive bars opposite (cci < 0)
   # Setup: must establish BLUE first, then 5 opposite
   # CC: this requires state-machine memory · test passes prior_state=BLUE explicitly
   #     or simulates by feeding sequence
   cci_14_history_prior = [10, 30, 60, 110, 105, 80, 70, 75]  # establishes BLUE
   # then 5 bars opposite:
   cci_14_history_now =  [110, 105, 80, 70, 75, 30, -10, -30, -45, -60]  # bars 8-9-10-11-12 below ZL
   → expected on 5th opposite bar (cci_14=-60): color=YELLOW, direction_allowed=NONE, terminal="SKIP — color veto (YELLOW per P-W5)"

6. test_yellow_blocks_all_9_patterns:
   # parameterized over the 9 pattern IDs
   # When A1 returns YELLOW, no pattern can fire
   @pytest.mark.parametrize("pattern_id", ["ZLR", "TLB", "TT", "GB100", "VEGAS", "GHOST", "FAMIR", "HTLB", "HFE"])
   def test_yellow_blocks_pattern(pattern_id):
       # Setup YELLOW state
       # Run pattern_engine.detect_all_patterns OR direct A3 call
       # Assert no pattern fires of the parameterized type
       ...
   # 9 sub-tests in one parameterized · counts as 9 toward the 10-minimum

7. test_gray_classification_choppy:
   cci_14_history = [10, -5, 8, -3, 15, -10, 12, -8, 5, -2]  # frequent zero crosses
   → expected: color=GRAY, direction_allowed=NONE

8. test_gray_post_yellow_no_new_trend:
   # YELLOW degrades to GRAY if new trend doesn't confirm
   # Establish YELLOW · then feed 3 more bars without confirming RED
   → expected: color=GRAY (degraded), direction_allowed=NONE

9. test_red_to_blue_via_yellow:
   # Mirror of test_yellow_transition_blue_to_red_direction
   prior_state = RED
   then 5 consecutive bars cci > 0
   → expected on 5th bar: color=YELLOW, direction_allowed=NONE

10. test_indeterminate_collapses_to_gray:
    # IF the pre-W-2 code had INDETERMINATE, post-W-2 it returns GRAY for the same input
    # Test that no code path returns "INDETERMINATE" anywhere
    # rg verification handled in §7 acceptance criteria · this test asserts the enum

11. test_grey_spelling_normalized_to_gray:
    # If pre-W-2 used "GREY", post-W-2 returns "GRAY"
    # Direct assertion that TrendState.GRAY.value == "GRAY"
    assert TrendState.GRAY.value == "GRAY"
    assert not hasattr(TrendState, "GREY")
    assert not hasattr(TrendState, "INDETERMINATE")

12. test_yellow_terminal_message_cites_pw5:
    # The terminal string must reference P-W5 (or YELLOW · or both) so downstream logs make sense
    # Acceptance: terminal contains "YELLOW" and ("P-W5" or "color veto")
    setup YELLOW
    result = a1.evaluate(...)
    assert "YELLOW" in result.terminal
    assert ("P-W5" in result.terminal) or ("color veto" in result.terminal)
```

**Tests count for the ≥10 minimum:**
- 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12 = 11 explicit tests
- test 6 = parameterized · 9 sub-tests
- **Total: 20 effective tests** · well above minimum

### §5.1 · Tests that should still pass (regression)

Whatever existing A1 tests exist in `tests/v9/systems/test_woodies.py` or similar must continue to pass UNLESS the test asserted "YELLOW returns LONG/SHORT" (which would have been wrong pre-W-2). If a test fails because pre-W-2 YELLOW had wrong behavior, document it in self-report §11 — that's the bug fix, not regression.

---

## §6 · Allowed imports (whitelist · CC verifies each exists)

```python
# Standard library:
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional
import logging  # only if used for warnings · no logger.debug on failure paths

# Existing internal (CC verifies via Read):
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternId, Direction
# Direction may or may not be a separate enum · CC verifies actual schema

# If §2.3 extraction is chosen:
from backend.v9.systems.woodies.trend_state import compute_trend_state, TrendState

# Test file additional:
import pytest
```

**Explicitly forbidden imports:**
- `from backend.v9.systems.woodies.atr_stop import ...` (W-1 is unrelated · A1 doesn't compute stops)
- `from backend.v9.systems.woodies.patterns import ...` (A1 is BEFORE pattern detection · circular dependency risk)
- `from backend.v9.systems.woodies.dispatcher import ...` (W-8 scope)
- `from backend.v9.systems.five_min import ...` / `day_type import ...` / etc. (other systems · A1 is woodies-internal)

If `WoodiesBar` / `PatternId` / `Direction` / `TrendState` don't exist or are named differently, **STOP** (§10) · do not invent.

---

## §7 · Acceptance criteria

The package is complete only when ALL of these hold:

- [ ] `a1_strategic_gate.py` modified to honor YELLOW BLOCK semantics per §4.3
- [ ] No code path returns color=`"INDETERMINATE"` anywhere in woodies/ (`rg "INDETERMINATE" backend/v9/systems/woodies/` → 0 hits)
- [ ] No code path returns color=`"GREY"` anywhere in woodies/ (`rg "GREY" backend/v9/systems/woodies/` → 0 hits · only `GRAY`)
- [ ] All 12 golden tests pass · pytest tail pasted in self-report
- [ ] `pytest tests/v9/ -q` → all green · no regression
- [ ] ReadLints on modified/new files → 0 new warnings
- [ ] §2.3 extraction decision documented in self-report §11 (extracted or kept inline · with reasoning)
- [ ] If extracted: `trend_state.py` has ≥6 standalone tests in `test_trend_state.py`
- [ ] `git diff --stat` shows only intended file changes · no scope creep
- [ ] Forbidden surface untouched · verified by `git diff --name-only HEAD | grep -E "<forbidden patterns>"` → empty
- [ ] Schemas.py field list for WoodiesBar and PatternId quoted with line numbers in self-report (§5 lesson #1)
- [ ] **Live Python repro included in self-report** that imports REAL classes (not Fake) and proves: (a) feeding a YELLOW-triggering bar sequence to A1 returns `direction_allowed=NONE`, and (b) the downstream pattern_engine.detect_all_patterns (or equivalent) returns empty/no-pattern in that state.

---

## §8 · Constraints (must not violate)

### §8.1 · Memorial Day §5 lessons (MANDATORY · this IS wiring)

```text
a. For any new event subscription or wrapper that reads attribute X from an event,
   FIRST open the source dataclass with the Read tool and quote the field list with
   line numbers in your self-report (Deliverable §3). Do NOT cite from memory.

b. For any wiring fix (subscribe/dispatch/hook), include a live Python repro in
   the deliverable that imports the REAL production class (NOT a FakeEvent mock)
   and proves the production-visible side effect. Format:
     python3 -c "from <real module> import <real class>; ev = <real class>(...);
                 asyncio.run(<handler>(ev)); assert <side effect>"

c. Unit tests using fake/mock events are NOT sufficient proof that wiring works.
   Production-import repro is mandatory before claiming a wiring fix is GREEN.

d. Do NOT trust commit messages or status lines that say "GREEN" without seeing
   the live repro evidence inline in the report.
```

**Application to W-2 — ALL FOUR apply:**

- §5(a): CC Reads `schemas.py` (WoodiesBar fields), `bar_router/__init__.py` (BarEvent if A1 subscribes to bars), `a1_strategic_gate.py` current state. Quotes field lists and line numbers in self-report.
- §5(b): **Live Python repro mandatory.** CC writes a Python one-liner that:
  1. Imports the real `BarEvent` (or whatever bar shape is used) from production
  2. Constructs a sequence of bars that triggers YELLOW
  3. Feeds the sequence through the real A1 (or pattern_engine entry point)
  4. Asserts the production-visible result: `result.color == TrendState.YELLOW` and `result.direction_allowed == "NONE"`
  5. ALSO asserts that pattern_engine.detect_all_patterns (or equivalent) returns no pattern when fed the same YELLOW state
  
  Example format (CC adapts to actual module names per audit):
  ```bash
  python3 -c "
  import asyncio
  from backend.v9.systems.woodies.stages.a1_strategic_gate import StrategicGate
  from backend.v9.systems.woodies.schemas import WoodiesBar
  # Construct sequence: BLUE established, then 5 opposite bars
  bars = [...]  # real WoodiesBar instances
  gate = StrategicGate()
  for bar in bars:
      result = gate.evaluate(bar)
  print(f'color={result.color} direction={result.direction_allowed} terminal={result.terminal}')
  assert result.color.value == 'YELLOW'
  assert result.direction_allowed == 'NONE'
  "
  ```
  
  Paste full command + full output in self-report §10.

- §5(c): Unit tests using fake bars are insufficient. The live repro above uses real WoodiesBar instances (not mock dicts).

- §5(d): CC's self-report includes the full pytest tail (not just "all passed") AND the full live repro output (not just "asserts passed").

### §8.2 · Pre-LIVE protocol

- **Read the current code:** §2.2 mandatory reads · quote line numbers.
- **Audit what already exists:** W-0 §3.4 drift #5 + §3.5 W-2 readiness verdict · classify as ADAPT/REPLACE before writing.
- **Verify hypothesis with data:** the YELLOW BLOCK behavior is being added · verify pre-state by running existing A1 against a YELLOW-triggering sequence and confirming the bug (pass-through or missing block). Document the pre-state.
- **Confirm fix is not already there:** if A1 already returns NONE for YELLOW (existing code may already be correct), W-2 only normalizes naming (INDETERMINATE → GRAY · GREY → GRAY) and adds the explicit `(YELLOW per P-W5)` terminal message. Document.
- **Smallest correct change:** do NOT refactor A3-A7 · do NOT change pattern_engine.py · stay within A1 scope (+ optional trend_state.py extraction).

### §8.3 · No silent failures

- A1 must NOT swallow exceptions from upstream (bad bar data → raise, don't default to GRAY)
- Logging: `logger.warning("[a1] ...")` rate-limited for unusual transitions (e.g., YELLOW → GRAY degradation) · NO `logger.debug` on failure paths
- The terminal message for YELLOW must include "YELLOW" (not just "color veto") so downstream logs are diagnosable

### §8.4 · "While I'm here" prohibited

- Do NOT optimize the state-machine memory storage (if it's a list, leave it a list · do NOT introduce deque)
- Do NOT touch A3 or any later stage
- Do NOT modify `pattern_engine.py`
- Do NOT add new YAML config (W-8 scope · P-W9 E)
- Do NOT add metrics emission · do NOT add Prometheus counters · simplicity over observability for W-2
- Do NOT change the bars_persistence_required from 6 (DTV1 default)

### §8.5 · raw_confidence formulas untouched (per P-W8 v2 KEEP)

- W-2 does NOT touch any `patterns/*.py` file
- The 9 raw_confidence formulas remain code-as-truth per INTAKE v2 P-W8 v2
- This is enforced by §3 FORBIDDEN block · re-stated here for emphasis

---

## §9 · Deliverable format

After completion, CC submits a structured self-report (Michael forwards to CD):

```text
# CC Self-Report · W-2 · Trend State Machine + YELLOW block

## 1. Files changed
M backend/v9/systems/woodies/stages/a1_strategic_gate.py
A tests/v9/systems/test_a1_strategic_gate.py
[A backend/v9/systems/woodies/trend_state.py]              ← only if §2.3 extraction chosen
[A tests/v9/systems/test_trend_state.py]                    ← only if extraction chosen
[M backend/v9/systems/woodies/compliance_manifest.yaml]    ← only if it enumerated GREY/INDETERMINATE

## 2. Commit message
feat(woodies): W-2 trend state machine · YELLOW blocks all 9 patterns · normalize INDETERMINATE/GREY to GRAY · per P-W5 LOCK A

## 3. Schemas.py field list quoted (per §5 lesson #1)
Read backend/v9/systems/woodies/schemas.py · lines X-Y:
```
[paste WoodiesBar definition VERBATIM with line numbers]
[paste PatternId enum VERBATIM]
[paste TrendState enum if pre-existing OR document creation]
```

## 4. Pre-W-2 state documentation
[Quote a1_strategic_gate.py current color enum verbatim · current YELLOW detection logic · current A1 output shape · all with file:line citations]
[Specifically: what did YELLOW return pre-W-2? · pass-through? · already NONE? · what was the terminal message?]
[If extraction (§2.3) chosen: explain reasoning · which functions extracted to trend_state.py]

## 5. Spec ambiguity encountered
[List cases where D-092 / Sheet C / DTV1 / INTAKE v2 disagreed]
[For each: state the interpretation chosen · do NOT silently pick]
[Pre-flagged: Sheet C §6.3 still says "P-W5 OPEN" because CSV dated 23/5 · INTAKE v2 lock dated 25/5 wins. Document if any OTHER ambiguity found.]

## 6. Forbidden constraint violations
[must be empty]

## 7. Pytest output (tail 30 lines)
```
[paste verbatim · 12 tests + parameterized 9 = 20 effective · ALL GREEN]
```

## 8. Adjacent regression check
```
$ pytest tests/v9/ -q
[paste tail · confirm no regression]
```

## 9. ReadLints output
```
[paste verbatim for each modified/new file]
```

## 10. LIVE PYTHON REPRO (per §5 lesson b · MANDATORY)
```bash
$ python3 -c "
[full command verbatim · imports real WoodiesBar · real StrategicGate · real bar sequence]
[asserts result.color == YELLOW · direction_allowed == NONE]
[asserts pattern_engine.detect_all_patterns returns no-pattern in YELLOW state]
"
[paste full output verbatim · including any prints]
```

## 11. Implementation decisions (document for CD)
- §2.3 extraction: chosen / not chosen · reasoning
- INDETERMINATE handling: collapsed to GRAY · documented in code comment
- GREY → GRAY: count of replacements made · files touched
- Pre-W-2 YELLOW behavior: [pass-through / already-NONE / other] · per audit observation
- Stage-1 >+100 enforcement: was already enforced / newly enforced in W-2

## 12. Forbidden surface check
```
$ git diff --name-only HEAD
[only intended files listed]
$ rg "INDETERMINATE" backend/v9/systems/woodies/
(no matches)
$ rg "GREY" backend/v9/systems/woodies/
(no matches · only GRAY)
$ git diff --stat patterns/
[no changes · patterns/*.py untouched per §8.5]
```
```

---

## §10 · Stop signal

STOP and report to Michael (do NOT continue, do NOT guess) if any of these occur:

- W-0 audit report (`docs/reports/PIPELINE_2_S4_AUDIT.md`) does not exist OR §3.4/§3.5 entries for A1 are missing
- `a1_strategic_gate.py` does not exist · or trend-state logic is found in an unexpected location (e.g., `pattern_engine.py` directly · `decision_tree.py`) — different from DTV1 §A1 expectation
- A1 current return shape is incompatible with the contract in §4.3 (e.g., A1 returns a tuple instead of a dataclass · or doesn't expose `direction_allowed` at all)
- A3 (`a3_pattern_detection.py`) does NOT consume A1 output as expected · meaning W-2 changing A1 doesn't propagate · STOP, this is an architectural issue beyond W-2's scope
- Schemas.py doesn't have WoodiesBar (or whatever bar shape is used) · or naming differs · or fields are missing for the cci_14 history input
- An existing test asserts "YELLOW returns LONG" (or similar pre-W-2 behavior) and that test would need a value change not a fix — document and STOP for Michael decision (don't silently update assertions)
- Live Python repro reveals that the real bar event class has a different attribute (e.g., `.cci_value` vs `.cci_14`) — STOP, do not invent attribute access

Output format if STOP triggered:
```
STOP — <reason> · need Michael decision on <specific question>
```

Do NOT leave a `TODO: ask Michael` in the code. Either the implementation is COMPLETE or STOP is the next action.

---

**End of MEGA PROMPT · W-2 · Trend State Machine + YELLOW block · 2026-05-25 IL · Claude Desktop**

*ADAPT scope · A1 extended with YELLOW BLOCK semantics per P-W5 LOCK A · INDETERMINATE/GREY normalized to GRAY · §5 lessons MANDATORY (this is wiring · live Python repro required) · self-report to Michael → CD review per INDEX §6.*
