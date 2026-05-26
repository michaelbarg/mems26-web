# MEGA PROMPT · Package W-1 · ATR-14 Stop Engine

**Produced by:** Claude Desktop · 2026-05-25 IL · for CC · reviewed by CD (per INDEX §6)
**Final reviewer:** Cursor (batch · after all 10 packages CD_PASSED)
**Spec authority:** D-092 LOCKED 2026-05-23 §Stop Architecture + Sheet C §6.1 + Researcher §4

---

## ⚠️ Read this before starting

You are Claude Code (CC). You execute this prompt single-shot. W-1 is **greenfield** — a brand-new ATR-14 stop engine module. **No wiring to patterns in W-1** (that's W-6's scope). W-1 builds and tests the engine in isolation; W-6 will later call it.

Prerequisite: W-0 codebase audit (`docs/reports/PIPELINE_2_S4_AUDIT.md`) must be CD_PASSED before W-1 starts. CC reads the W-0 audit specifically §3.3(a) ATR-14 cross-cut conclusion to confirm "no ATR-14 calc exists in woodies/" before writing greenfield.

---

## §1 · Spec authority (verbatim, locked)

### §1.1 · D-092 LOCKED · Stop Architecture · ATR-14 based

> | Layer | Rule | Notes |
> |---|---|---|
> | **א · Primary CONT** | 2-3 ticks beyond entry-bar low/high | Liran's "momentum trade" rule |
> | **א · Primary REV** | Beyond last swing extreme | per-pattern anchor (cup low · right shoulder · failed-ZLR bar · horizontal bar · extreme bar) |
> | **ב · ATR cap CONT** (ZLR/TLB/TT) | **1.0× ATR-14** ≈ 8-16 ticks | normal vol |
> | **ב · ATR cap medium** (GB100/HTLB) | **1.2× ATR-14** ≈ 10-20 ticks | |
> | **ב · ATR cap REV** (VEGAS/GHOST/FAMIR/HFE) | **1.5× ATR-14** ≈ 12-24 ticks | |
> | **ג · Floor** | **4 ticks** (MES tick-noise floor) | 1T = 0.25pt = $1.25 |
>
> **Trail logic:** After T1 → BE+1T · After T2 → trail last-bar low/high (Liran ladder) · Also trail when TCCI crosses CCI-14 against position.

**Trail logic is W-9 scope (LiranExitLadderRule). W-1 implements ONLY the initial stop calculation (Layers א + ב + ג).**

### §1.2 · Sheet C §6.1 · Stop Strategy (verbatim)

> | Layer | Rule |
> |---|---|
> | Primary rule · CONT | 2–3 ticks beyond entry-bar low (long) / high (short) — Liran's "momentum trade" rule. Patterns: ZLR, TLB, TT, GB100. |
> | Primary rule · REV | Beyond the last swing extreme — for VEGAS: cup low · GHOST: right shoulder · FAMIR: failed-ZLR signal bar · HTLB: horizontal breakout bar · HFE: extreme bar. |
> | ATR cap · CONT (ZLR/TLB/TT) | 1.0 × ATR-14 (5-min) → ≈ 8–16 ticks in normal vol (daily ATR 40–55 pts). |
> | ATR cap · medium (GB100/HTLB) | 1.2 × ATR-14 → ≈ 10–20 ticks. |
> | ATR cap · REV (VEGAS/GHOST/FAMIR/HFE) | 1.5 × ATR-14 → ≈ 12–24 ticks. |
> | Floor | Never tighter than 4 ticks (MES tick-noise floor; 1T = 0.25pt = $1.25). |

### §1.3 · Researcher §4 · MES 5-min ATR-14 baseline (informational)

> No first-party publisher (CME, Barchart, NinjaTrader) reports a 5-min ATR-14 for MES specifically. Triangulated from Young Money Investments' cited daily ATR range of 40–65 points for ES during 2024–2025 normal conditions, plus practitioner conventions, the defensible derived range is:
>
> - **Normal vol (daily ATR 40–55 pts):** 5-min ATR-14 ≈ **2–4 points = 8–16 ticks**
> - **Elevated vol (daily ATR 60+):** 5-min ATR-14 ≈ **5–8 points = 20–32 ticks**
> - **Low-vol/chop (daily ATR 20–35):** 5-min ATR-14 ≈ **1.5–2.5 points = 6–10 ticks**
>
> This sets the ATR-cap multipliers on Sheet C §6.1.

### §1.4 · Pattern groupings for ATR cap selection

Three groups · derived from §1.1 + §1.2:

```
CONT_TIGHT  (1.0× ATR cap):  ZLR, TLB, TT
CONT_MED    (1.2× ATR cap):  GB100, HTLB
REV         (1.5× ATR cap):  VEGAS, GHOST, FAMIR, HFE
```

Note: HTLB is "REV-ish" per D-092 §Scope but its ATR cap is **medium (1.2×)** per Sheet C §6.1, not REV (1.5×). The pattern's reversal/continuation classification and its ATR cap multiplier are independent dimensions. W-1 uses the ATR cap multiplier dimension only.

### §1.5 · Stop computation logic (derived from §1.1-§1.4)

For each call to `compute_stop(...)`:

```
1. primary_distance_ticks =
     CONT direction → 3 ticks (Liran "2-3T" · we use upper bound 3T as default)
     REV  direction → distance from entry to swing_anchor (in ticks)

2. cap_multiplier =
     CONT_TIGHT → 1.0
     CONT_MED   → 1.2
     REV        → 1.5

3. cap_distance_ticks = cap_multiplier * atr_14   (atr_14 already in ticks)

4. capped_distance_ticks = min(primary_distance_ticks, cap_distance_ticks)

5. final_distance_ticks = max(capped_distance_ticks, floor_ticks)
   # floor_ticks defaults to 4

6. stop_price =
     LONG  → entry_bar.low  - (final_distance_ticks * tick_size)   for CONT
     SHORT → entry_bar.high + (final_distance_ticks * tick_size)   for CONT
     LONG  → swing_anchor   - (final_distance_ticks * tick_size)   for REV  (cap-applied case)
                                                                    OR
             swing_anchor - 3 ticks                                  for REV  (primary-applied case)
     [mirror for SHORT REV]

7. layer_applied =
     "primary" if final_distance_ticks == primary_distance_ticks (and not == floor)
     "cap"     if final_distance_ticks == cap_distance_ticks     (and not == floor)
     "floor"   if final_distance_ticks == floor_ticks
     # tie-breaker: if primary == cap, layer_applied = "primary" (since cap was hit-but-not-needed)
```

CC implements this exact algorithm. The 15+ golden tests in §5 verify each branch.

---

## §2 · Existing code surfaces (READ-ONLY)

### §2.1 · W-0 audit prerequisite

Before writing W-1 code, CC reads:

```
docs/reports/PIPELINE_2_S4_AUDIT.md  (W-0 output · CD_PASSED before W-1 starts)
```

Specifically:
- §3.3(a) **ATR-14 cross-cut conclusion** — confirms no ATR-14 calc exists in `backend/v9/systems/woodies/`
- §3.5 **W-1 readiness verdict** — confirms classification = DEFER (greenfield)

If W-0 audit found an existing ATR-14 calc elsewhere (e.g., in `backend/v9/systems/five_min/` or `backend/v9/shared/`), CC reads it and decides whether to import or reimplement. **Do not duplicate** — per `.cursor/rules/mems26-pre-live-protocol.mdc` step 2 "audit what already exists."

### §2.2 · Schemas dependency

CC reads `backend/v9/systems/woodies/schemas.py` to confirm the existence of:
- `WoodiesBar` dataclass (or equivalent · the bar shape with open/high/low/close)
- `PatternId` enum (the 9 pattern IDs ZLR/TLB/TT/GB100/VEGAS/GHOST/FAMIR/HTLB/HFE)
- `Direction` enum or Literal (LONG/SHORT)

**Per §5 lesson #1 (MANDATORY):** quote the field list of `WoodiesBar` and the values of `PatternId` with line numbers in the self-report. Do NOT cite from memory.

If any of these types are missing or named differently, **STOP** and report — do not invent.

### §2.3 · No other existing code is consumed by W-1

`compute_stop()` is a pure function. It does not subscribe to events, does not read from DB, does not call patterns. The caller (W-6) provides everything as arguments.

---

## §3 · SCOPE — exactly these files

### WRITE NEW:

```
backend/v9/systems/woodies/atr_stop.py
tests/v9/systems/test_atr_stop.py
```

### MODIFY EXISTING:

```
NONE
```

W-1 does NOT wire `atr_stop` into any pattern. That is W-6's scope. W-1 builds and tests the engine in isolation.

### FORBIDDEN — do NOT touch:

Per INDEX §7 forbidden surface (full list re-quoted):

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

W-1-specific additions:

```text
- backend/v9/systems/woodies/patterns/*.py              [W-6 wires patterns to atr_stop · not W-1]
- backend/v9/systems/woodies/pattern_engine.py          [W-6 orchestration]
- backend/v9/systems/woodies/dispatcher.py              [W-8 scope]
- backend/v9/systems/woodies/stages/*.py                [other packages scope]
- backend/v9/systems/woodies/yaml_loader.py             [W-8 scope]
```

---

## §4 · Required API

```python
# backend/v9/systems/woodies/atr_stop.py

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar  # CC verifies exists per §2.2


class PatternGroup(str, Enum):
    """ATR cap selector groups per D-092 §Stop Architecture."""
    CONT_TIGHT = "CONT_TIGHT"   # ZLR, TLB, TT       → 1.0× ATR-14
    CONT_MED   = "CONT_MED"     # GB100, HTLB        → 1.2× ATR-14
    REV        = "REV"          # VEGAS, GHOST, FAMIR, HFE  → 1.5× ATR-14


@dataclass(frozen=True)
class StopResult:
    """Result of stop computation."""
    stop_price: float           # final stop price (already includes tick-size)
    stop_ticks: int             # distance from anchor in ticks (positive integer)
    layer_applied: Literal["primary", "cap", "floor"]
    cap_applied: bool           # True if ATR cap was the binding constraint


# ATR cap multipliers per D-092 §1.1 + Sheet C §6.1
ATR_CAP_MULTIPLIERS: dict[PatternGroup, float] = {
    PatternGroup.CONT_TIGHT: 1.0,
    PatternGroup.CONT_MED:   1.2,
    PatternGroup.REV:        1.5,
}

# Floor per D-092 §1.1 layer ג (MES tick-noise floor)
DEFAULT_FLOOR_TICKS: int = 4

# Primary CONT distance per Sheet C §6.1 ("2-3 ticks") — we use upper bound 3T
DEFAULT_PRIMARY_CONT_TICKS: int = 3


def compute_stop(
    direction: Literal["LONG", "SHORT"],
    entry_bar: WoodiesBar,                      # for primary CONT (entry-bar low/high)
    swing_anchor: Optional[float],              # for primary REV (swing-extreme price) · None for CONT
    pattern_group: PatternGroup,                # ATR cap selector
    atr_14: float,                              # 5-min ATR-14, in TICKS (not points)
    tick_size: float = 0.25,                    # default = MES tick
    floor_ticks: int = DEFAULT_FLOOR_TICKS,     # default = 4
    primary_cont_ticks: int = DEFAULT_PRIMARY_CONT_TICKS,  # default = 3
) -> StopResult:
    """
    Compute the initial stop for an S4 Woodies CCI trade per D-092 §Stop Architecture.

    Raises:
        ValueError: if atr_14 is negative or zero.
        ValueError: if pattern_group == REV and swing_anchor is None.
        ValueError: if direction not in ("LONG", "SHORT").
    """
    ...
```

**Implementation notes:**

- `atr_14` is in **ticks** (not points). The caller is responsible for converting if needed. Document this in the docstring.
- `swing_anchor` is the **price** of the swing extreme (cup low / right shoulder / etc.), not a distance.
- `entry_bar.low` and `entry_bar.high` are **prices**.
- `tick_size` is injectable (0.25 default for MES · 0.25 also for ES · could be 0.01 for stocks future-proof).
- Negative or zero `atr_14` → `ValueError("atr_14 must be positive")` · no silent default.
- `pattern_group=REV` with `swing_anchor=None` → `ValueError("swing_anchor required for REV patterns")`.
- Module-level constants must be importable for tests to reference (`ATR_CAP_MULTIPLIERS`, `DEFAULT_FLOOR_TICKS`).

---

## §5 · Golden tests (must pass · minimum N=15)

Test file: `tests/v9/systems/test_atr_stop.py`

```python
import pytest
from backend.v9.systems.woodies.atr_stop import (
    compute_stop,
    PatternGroup,
    StopResult,
    ATR_CAP_MULTIPLIERS,
    DEFAULT_FLOOR_TICKS,
)
from backend.v9.systems.woodies.schemas import WoodiesBar  # CC verifies real class
```

### Required test cases (CC may add more, never fewer than 15):

```
1. test_zlr_long_normal_vol_cap_hit:
   entry_bar.low=5800.00 · direction=LONG · pattern_group=CONT_TIGHT · atr_14=12 ticks
   → primary = 3T · cap = 1.0×12 = 12T · winner = primary (3T < 12T)
   → expected: stop_ticks=3, stop_price=5799.25, layer_applied="primary", cap_applied=False

2. test_zlr_long_low_vol_cap_clamps:
   entry_bar.low=5800.00 · direction=LONG · pattern_group=CONT_TIGHT · atr_14=2 ticks
   → primary = 3T · cap = 1.0×2 = 2T · winner = cap (2T < 3T) · but floor = 4T overrides
   → expected: stop_ticks=4, stop_price=5799.00, layer_applied="floor", cap_applied=False
   # floor wins · cap_applied is False because the floor is what actually constrained

3. test_zlr_short_normal_vol:
   entry_bar.high=5800.00 · direction=SHORT · pattern_group=CONT_TIGHT · atr_14=12 ticks
   → expected: stop_ticks=3, stop_price=5800.75, layer_applied="primary", cap_applied=False

4. test_gb100_long_med_cap:
   entry_bar.low=5800.00 · direction=LONG · pattern_group=CONT_MED · atr_14=20 ticks
   → primary = 3T · cap = 1.2×20 = 24T · winner = primary (3T)
   → expected: stop_ticks=3, layer_applied="primary"

5. test_gb100_long_huge_atr_primary_still_wins:
   entry_bar.low=5800.00 · direction=LONG · pattern_group=CONT_MED · atr_14=100 ticks
   → primary = 3T · cap = 1.2×100 = 120T · primary wins by far
   → expected: stop_ticks=3, layer_applied="primary"

6. test_vegas_long_swing_anchor_close_cap_clamps:
   entry_bar.low=5800.00 · direction=LONG · pattern_group=REV · atr_14=10 ticks · swing_anchor=5798.00
   → primary distance (entry to swing_anchor) = (5800-5798)/0.25 = 8T
   → cap = 1.5×10 = 15T
   → winner = primary (8T < 15T)
   → expected: stop_ticks=8, stop_price=5798.00 minus the configured margin
   # Per §1.5 step 6 REV primary case: stop = swing_anchor - 3 ticks  (long REV)
   # BUT: Sheet C §6.1 says "3T beyond" the swing extreme
   # So when primary_distance = swing_to_entry distance + 3T margin? OR is primary just "stop AT swing - 3T"?
   # CC: implement the simpler interpretation: stop = swing_anchor - 3T (long REV)
   # then stop_ticks = (entry - stop) / tick_size = (5800.00 - 5797.25)/0.25 = 11T
   # WAIT — re-check Sheet A row 6 VEGAS: "3T beyond last swing extreme (REV rule)"
   # So stop_price = swing_anchor - (3T * tick_size) for LONG REV
   # stop_ticks_from_entry = (entry_bar.low - stop_price) / tick_size = (5800 - 5797.25)/0.25 = 11T
   # cap = 1.5×10 = 15T → primary (11T) wins
   → expected: stop_ticks=11, stop_price=5797.25, layer_applied="primary"

7. test_vegas_long_swing_anchor_far_cap_clamps:
   entry_bar.low=5800.00 · direction=LONG · pattern_group=REV · atr_14=10 ticks · swing_anchor=5790.00
   → distance to swing = (5800-5790)/0.25 = 40T · primary = 40+3 = 43T (3T beyond)
   → cap = 1.5×10 = 15T
   → winner = cap (15T < 43T)
   → expected: stop_ticks=15, stop_price=5800-(15*0.25)=5796.25, layer_applied="cap", cap_applied=True

8. test_ghost_short_swing_anchor_cap_hits:
   entry_bar.high=5800.00 · direction=SHORT · pattern_group=REV · atr_14=8 · swing_anchor=5810.00
   → distance to swing = (5810-5800)/0.25 = 40T · primary = 40+3 = 43T
   → cap = 1.5×8 = 12T
   → winner = cap (12T < 43T)
   → expected: stop_ticks=12, stop_price=5803.00, layer_applied="cap", cap_applied=True

9. test_floor_wins_over_tiny_atr_cont:
   entry_bar.low=5800.00 · direction=LONG · pattern_group=CONT_TIGHT · atr_14=2 ticks
   # already in test 2 · but here verify with primary explicitly equal to floor
   → primary=3T · cap=2T · floor=4T → floor wins
   → expected: stop_ticks=4, layer_applied="floor"

10. test_floor_wins_over_tiny_atr_rev:
    entry_bar.low=5800.00 · direction=LONG · pattern_group=REV · atr_14=1 tick · swing_anchor=5799.50
    → distance to swing = 2T · primary = 5T · cap = 1.5T → 2T (rounded? CC handles)
    # cap_distance_ticks = 1.5 × 1 = 1.5 ticks · need to decide round/floor/ceil
    # IMPLEMENTATION DECISION: use floor() to be conservative on cap
    # so cap_ticks = 1, primary_ticks = 5, floor_ticks = 4
    # winner among (5, 1, 4) → minimum of (primary=5, cap=1) = 1, then max with floor 4 = 4
    → expected: stop_ticks=4, layer_applied="floor"

11. test_tie_primary_equals_cap_layer_is_primary:
    entry_bar.low=5800.00 · direction=LONG · pattern_group=CONT_TIGHT · atr_14=3 ticks
    → primary=3T · cap=1.0×3=3T · floor=4T
    → winner = floor (since 3 < 4 for both primary and cap, floor takes over)
    → expected: stop_ticks=4, layer_applied="floor"
    # NOTE: this is actually a floor test · primary==cap but floor still beats them

12. test_tie_primary_equals_cap_above_floor:
    entry_bar.low=5800.00 · direction=LONG · pattern_group=CONT_TIGHT · atr_14=5 ticks
    → primary=3T · cap=1.0×5=5T · floor=4T
    → min(primary, cap) = min(3, 5) = 3 · max(3, floor=4) = 4 → floor still wins
    → expected: stop_ticks=4, layer_applied="floor"
    # for layer="primary" to win, primary must be > floor (≥5T) AND ≤ cap
    # so a true "primary == cap > floor" tie test:
    # CONT_TIGHT primary=6T (custom), cap=1.0×6=6T, floor=4T → tie at 6T
    # but our default primary is 3T, not configurable per test arg... 
    # CC: include a test that passes primary_cont_ticks=6 explicitly to force this scenario

13. test_negative_atr_raises:
    direction=LONG · pattern_group=CONT_TIGHT · atr_14=-5 · entry_bar valid
    → expected: ValueError matching r"atr_14 must be positive"

14. test_zero_atr_raises:
    atr_14=0 → ValueError (same message)

15. test_rev_without_swing_anchor_raises:
    direction=LONG · pattern_group=REV · atr_14=10 · swing_anchor=None
    → expected: ValueError matching r"swing_anchor required for REV"

16. test_tick_size_variation_es:
    # ES has tick_size = 0.25 same as MES, but a non-default tick to verify injection
    # Use tick_size = 0.5 hypothetical
    entry_bar.low=5800.00 · direction=LONG · pattern_group=CONT_TIGHT · atr_14=12 · tick_size=0.5
    → primary=3T · 3T × 0.5 = 1.50 · stop_price = 5800.00 - 1.50 = 5798.50
    → expected: stop_ticks=3, stop_price=5798.50

17. test_all_9_patterns_mapped:
    # Sanity: every pattern's expected group is one of CONT_TIGHT/CONT_MED/REV
    # Build a mapping dict in test and assert each of 9 maps to a valid group
    # This documents the pattern → group mapping for W-6 consumers
    mapping = {
        "ZLR": PatternGroup.CONT_TIGHT,
        "TLB": PatternGroup.CONT_TIGHT,
        "TT":  PatternGroup.CONT_TIGHT,
        "GB100": PatternGroup.CONT_MED,
        "HTLB":  PatternGroup.CONT_MED,
        "VEGAS": PatternGroup.REV,
        "GHOST": PatternGroup.REV,
        "FAMIR": PatternGroup.REV,
        "HFE":   PatternGroup.REV,
    }
    assert set(mapping.values()) == {PatternGroup.CONT_TIGHT, PatternGroup.CONT_MED, PatternGroup.REV}
    assert len(mapping) == 9
```

CC documents any test where the spec is ambiguous (e.g., "should cap floor() or round()?") and applies the conservative interpretation noted in §1.5 / §4 implementation notes. Document the choice in the self-report.

---

## §6 · Allowed imports (whitelist · CC verifies each exists before use)

```python
# Standard library only:
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

# Existing internal:
from backend.v9.systems.woodies.schemas import WoodiesBar
# CC verifies via Read: schemas.py exposes a class named WoodiesBar (or equivalent — record actual name in self-report)

# Test file additional:
import pytest
```

**No other imports allowed.** Specifically:
- No `import logging` (compute_stop is pure · no logging needed · caller logs)
- No `numpy` / `pandas` (overkill for arithmetic)
- No `math` (basic arithmetic only)
- No imports from `patterns/*.py`, `pattern_engine.py`, `dispatcher.py`

If `WoodiesBar` doesn't exist or is named differently, **STOP** (§10 stop signal) · do not invent an alternative.

---

## §7 · Acceptance criteria

The package is complete only when ALL of these hold:

- [ ] `backend/v9/systems/woodies/atr_stop.py` exists with `compute_stop`, `PatternGroup`, `StopResult`, `ATR_CAP_MULTIPLIERS`, `DEFAULT_FLOOR_TICKS` exports
- [ ] `tests/v9/systems/test_atr_stop.py` exists with ≥15 tests covering all branches in §5
- [ ] `pytest tests/v9/systems/test_atr_stop.py -q` → all green · tail pasted in self-report
- [ ] `pytest tests/v9/systems/ -q` → still green (no regression in adjacent woodies tests)
- [ ] ReadLints on the two new files → 0 new warnings
- [ ] `rg "today_typical" backend/v9/systems/woodies/atr_stop.py` → 0 hits (this is S2's mechanism, NOT S4's)
- [ ] `rg "import .*atr_stop" backend/v9/systems/woodies/` → 0 hits OUTSIDE `tests/` (W-1 does NOT wire to patterns · W-6 will)
- [ ] `git diff --stat` shows only the two new files Added · no other M/D
- [ ] Forbidden surface untouched (verify via `git diff --name-only HEAD | grep -E "<forbidden patterns>"` returns nothing)
- [ ] Schemas.py field list quoted with line numbers in self-report (§5 lesson #1)
- [ ] Module-level constants (`ATR_CAP_MULTIPLIERS`, `DEFAULT_FLOOR_TICKS`) imported and used by tests (not duplicated as magic numbers)

---

## §8 · Constraints (must not violate)

### §8.1 · Memorial Day §5 lessons (MANDATORY)

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

**Application to W-1:**

- §5(a) applies to `WoodiesBar`: CC Reads `schemas.py` and quotes the WoodiesBar field list with line numbers in the self-report.
- §5(b) is N/A for W-1 — there is no event subscription, no wiring. `compute_stop` is a pure function.
- §5(c) is N/A — there is no wiring.
- §5(d) — CC's self-report includes pytest tail verbatim (not just "all passed").

### §8.2 · Pre-LIVE protocol (per `.cursor/rules/mems26-pre-live-protocol.mdc`)

- **Read the current code:** CC reads `schemas.py` before importing. Verify the type names match.
- **Audit what already exists:** W-0 §3.3(a) confirms no ATR-14 calc exists in woodies/. If CC finds one elsewhere during pre-write verification, STOP and report — do not duplicate.
- **Smallest correct change:** ONE module + ONE test file. No bonus refactoring of `schemas.py`. No new dependencies.
- **No silent failures:** negative/zero `atr_14` raises explicitly. REV without `swing_anchor` raises explicitly. No `return None` on bad input.

### §8.3 · Implementation-specific

- `compute_stop` is **pure** — no side effects, no I/O, no logging.
- All thresholds are **module constants**, not inline magic numbers.
- All raises use `ValueError` with descriptive messages (no `RuntimeError`, no `Exception` bare).
- Type hints on every parameter and return.
- Docstring includes the D-092 §Stop Architecture table verbatim (or a verbatim quote with source citation).

### §8.4 · "While I'm here" prohibited

- Do NOT add a stub for `update_trail` or `compute_break_even`. Trail is W-9 scope (LiranExitLadderRule).
- Do NOT add a CLI / runner / debug print.
- Do NOT touch any `__init__.py` to expose `atr_stop` at package level. W-6 will import from `backend.v9.systems.woodies.atr_stop` explicitly.

---

## §9 · Deliverable format

After completion, CC submits a structured self-report (Michael forwards to CD):

```text
# CC Self-Report · W-1 · ATR-14 Stop Engine

## 1. Files changed
A backend/v9/systems/woodies/atr_stop.py
A tests/v9/systems/test_atr_stop.py

## 2. Commit message
feat(woodies): W-1 ATR-14 stop engine · CONT 1.0× · MED 1.2× · REV 1.5× · floor 4T

## 3. Schemas.py field list (per §5 lesson #1)
Read backend/v9/systems/woodies/schemas.py · lines X-Y:
```
[paste WoodiesBar class definition VERBATIM with line numbers]
```
Confirmed: WoodiesBar has fields [list].
Confirmed: PatternId enum has 9 values [list].

## 4. Spec ambiguity encountered
[list cases where D-092 / Sheet C / Sheet A disagreed in a way the engine had to resolve]
[for each: state the interpretation chosen and the reasoning · do NOT silently pick · flag for CD]

## 5. Forbidden constraint violations
[must be empty]

## 6. Pytest output (tail 30 lines)
```
[paste verbatim · all 15+ tests · ALL GREEN]
```

## 7. Adjacent regression check
```
$ pytest tests/v9/systems/ -q
[paste tail · confirm no regression in other woodies tests]
```

## 8. ReadLints output
```
[paste verbatim on atr_stop.py and test_atr_stop.py · confirm 0 new warnings]
```

## 9. Forbidden surface check
```
$ git diff --name-only HEAD
backend/v9/systems/woodies/atr_stop.py
tests/v9/systems/test_atr_stop.py
$ rg "today_typical" backend/v9/systems/woodies/atr_stop.py
(no matches)
$ rg "import .*atr_stop" backend/v9/systems/woodies/
(no matches outside tests/)
```

## 10. Live Python repro
N/A · W-1 is a pure function · no event wiring · §5 lesson (b) does not apply.

## 11. Implementation decisions made (document for CD)
- Cap rounding: floor() vs round() vs ceil() for `cap_multiplier * atr_14`
- Layer tie-break: when primary == cap, layer_applied = "primary" (cap was hit-but-not-needed)
- REV primary distance: stop = swing_anchor ± (3 ticks × tick_size) per Sheet A row 6 "3T beyond"
- Pattern→group mapping documented in test_atr_stop.py test_all_9_patterns_mapped
```

---

## §10 · Stop signal

STOP and report to Michael (do NOT continue, do NOT guess) if any of these occur:

- `backend/v9/systems/woodies/schemas.py` does not exist OR `WoodiesBar` is not defined there OR `PatternId` enum is missing
- W-0 audit report (`docs/reports/PIPELINE_2_S4_AUDIT.md`) does not exist OR W-0 §3.3(a) found an existing ATR-14 calc that CC believes should be imported rather than reimplemented
- An existing `atr_stop.py` already exists in `backend/v9/systems/woodies/` (W-0 said it doesn't · if it does, the audit was wrong — STOP)
- D-092 / Sheet C numeric values in §1.1/§1.2 disagree with what's encoded in the actual `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv` (CC reads the CSV to verify before writing)
- An import in §6 whitelist doesn't resolve (e.g., `schemas` module name mismatch)
- Tests need fixtures (e.g., specific historical bars) that are impossible to construct from inline values

Output format if STOP triggered:
```
STOP — <reason> · need Michael decision on <specific question>
```

Do NOT leave a `TODO: ask Michael` in the code. Either the implementation is COMPLETE or STOP is the next action.

---

**End of MEGA PROMPT · W-1 · ATR-14 Stop Engine · 2026-05-25 IL · Claude Desktop**

*Greenfield · single module + tests · no wiring · self-report to Michael → CD review per INDEX §6 → W-2 starts on 🟢 PASS (W-2 also unblocks once W-0 PASS).*
