"""ATR-14 initial stop engine for S4 Woodies CCI trades.

Implements D-092 §Stop Architecture layers א (Primary), ב (ATR cap), ג (Floor).
Trail logic (W-9 LiranExitLadderRule) is out of scope — this module computes
only the initial stop price and distance.

Stop computation per D-092 + Sheet C §6.1:

| Layer              | Rule                                          |
|--------------------|-----------------------------------------------|
| Primary · CONT     | 3 ticks beyond entry-bar low/high             |
| Primary · REV      | 3 ticks beyond last swing extreme             |
| ATR cap · CONT     | 1.0 × ATR-14 (ZLR, TLB, TT)                  |
| ATR cap · medium   | 1.2 × ATR-14 (GB100, HTLB)                   |
| ATR cap · REV      | 1.5 × ATR-14 (VEGAS, GHOST, FAMIR, HFE)      |
| Floor              | 4 ticks (MES tick-noise floor)                |

The ``atr_14`` parameter must be supplied **in ticks** (not points).
The caller is responsible for unit conversion.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

from backend.v9.systems.woodies.schemas import WoodiesBar


class PatternGroup(str, Enum):
    """ATR cap selector groups per D-092 §Stop Architecture."""
    CONT_TIGHT = "CONT_TIGHT"   # ZLR, TLB, TT       → 1.0× ATR-14
    CONT_MED   = "CONT_MED"    # GB100, HTLB         → 1.2× ATR-14
    REV        = "REV"          # VEGAS, GHOST, FAMIR, HFE → 1.5× ATR-14


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

# Primary CONT distance per Sheet C §6.1 ("2-3 ticks") — upper bound 3T
DEFAULT_PRIMARY_CONT_TICKS: int = 3

# Primary REV margin — "3 ticks beyond swing extreme" per Sheet C §6.1
_REV_BEYOND_TICKS: int = 3


def compute_stop(
    direction: Literal["LONG", "SHORT"],
    entry_bar: WoodiesBar,
    swing_anchor: Optional[float],
    pattern_group: PatternGroup,
    atr_14: float,
    tick_size: float = 0.25,
    floor_ticks: int = DEFAULT_FLOOR_TICKS,
    primary_cont_ticks: int = DEFAULT_PRIMARY_CONT_TICKS,
) -> StopResult:
    """Compute the initial stop for an S4 Woodies CCI trade.

    Per D-092 §Stop Architecture:
    1. Compute primary distance (CONT: ``primary_cont_ticks``; REV: swing
       distance + 3 ticks beyond).
    2. Compute ATR cap distance (``multiplier × atr_14``).
    3. Take the tighter of primary and cap (``min``).
    4. Enforce floor (``max`` with ``floor_ticks``).

    Args:
        direction: "LONG" or "SHORT".
        entry_bar: The entry bar (uses ``.low`` for LONG, ``.high`` for SHORT).
        swing_anchor: Price of the swing extreme for REV patterns. Required
            when ``pattern_group == REV``, ignored otherwise.
        pattern_group: Determines ATR cap multiplier.
        atr_14: 5-min ATR-14 value **in ticks** (not points). Must be positive.
        tick_size: Dollar value per tick (default 0.25 for MES/ES).
        floor_ticks: Minimum stop distance in ticks (default 4).
        primary_cont_ticks: CONT primary distance in ticks (default 3).

    Returns:
        StopResult with stop_price, stop_ticks, layer_applied, and cap_applied.

    Raises:
        ValueError: If ``atr_14`` is not positive.
        ValueError: If ``pattern_group == REV`` and ``swing_anchor is None``.
        ValueError: If ``direction`` not in ("LONG", "SHORT").
    """
    # --- Validation ---
    if direction not in ("LONG", "SHORT"):
        raise ValueError(f"direction must be 'LONG' or 'SHORT', got '{direction}'")
    if atr_14 <= 0:
        raise ValueError("atr_14 must be positive")
    if pattern_group == PatternGroup.REV and swing_anchor is None:
        raise ValueError("swing_anchor required for REV patterns")

    # --- Step 1: Primary distance ---
    is_rev = pattern_group == PatternGroup.REV

    if is_rev:
        # REV: distance from entry anchor to swing extreme + 3 ticks beyond
        anchor_price = entry_bar.low if direction == "LONG" else entry_bar.high
        if direction == "LONG":
            swing_distance_ticks = int(round((anchor_price - swing_anchor) / tick_size))
        else:
            swing_distance_ticks = int(round((swing_anchor - anchor_price) / tick_size))
        primary_distance_ticks = swing_distance_ticks + _REV_BEYOND_TICKS
    else:
        # CONT: fixed N ticks beyond entry-bar low/high
        primary_distance_ticks = primary_cont_ticks

    # --- Step 2: ATR cap distance ---
    cap_multiplier = ATR_CAP_MULTIPLIERS[pattern_group]
    cap_distance_ticks = int(cap_multiplier * atr_14)  # floor() for conservative cap

    # --- Step 3: Tighter of primary and cap ---
    capped_distance_ticks = min(primary_distance_ticks, cap_distance_ticks)

    # --- Step 4: Enforce floor ---
    final_distance_ticks = max(capped_distance_ticks, floor_ticks)

    # --- Step 5: Determine which layer was binding ---
    if final_distance_ticks == floor_ticks and capped_distance_ticks < floor_ticks:
        layer_applied: Literal["primary", "cap", "floor"] = "floor"
        cap_applied = False
    elif capped_distance_ticks == cap_distance_ticks and cap_distance_ticks < primary_distance_ticks:
        layer_applied = "cap"
        cap_applied = True
    else:
        layer_applied = "primary"
        cap_applied = False

    # --- Step 6: Compute stop price ---
    if direction == "LONG":
        anchor = entry_bar.low
        stop_price = anchor - (final_distance_ticks * tick_size)
    else:
        anchor = entry_bar.high
        stop_price = anchor + (final_distance_ticks * tick_size)

    return StopResult(
        stop_price=round(stop_price, 10),  # avoid float drift
        stop_ticks=final_distance_ticks,
        layer_applied=layer_applied,
        cap_applied=cap_applied,
    )
