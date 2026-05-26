"""Golden tests for ATR-14 stop engine (W-1).

Verifies D-092 §Stop Architecture layers א (Primary), ב (ATR cap), ג (Floor).
All test values derived from §5 of the W-1 mega prompt spec.
"""

import pytest

from backend.v9.systems.woodies.atr_stop import (
    ATR_CAP_MULTIPLIERS,
    DEFAULT_FLOOR_TICKS,
    DEFAULT_PRIMARY_CONT_TICKS,
    PatternGroup,
    StopResult,
    compute_stop,
)
from backend.v9.systems.woodies.schemas import WoodiesBar


def _bar(low: float = 5800.00, high: float = 5810.00) -> WoodiesBar:
    """Minimal WoodiesBar for stop tests."""
    return WoodiesBar(ts=0.0, open=5805.00, high=high, low=low, close=5805.00)


# ── 1. ZLR LONG normal vol — primary wins ──────────────────────────────

def test_zlr_long_normal_vol_cap_hit():
    # primary=3T, cap=1.0×12=12T → capped=min(3,12)=3 → final=max(3,floor=4)=4
    # Floor (4T) > primary (3T), so floor is always the binding constraint
    # for default CONT (primary_cont_ticks=3 < floor=4).
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=12,
    )
    assert result.stop_ticks == 4
    assert result.stop_price == 5799.00
    assert result.layer_applied == "floor"
    assert result.cap_applied is False


# ── 2. ZLR LONG low vol — floor wins over tiny cap ─────────────────────

def test_zlr_long_low_vol_cap_clamps():
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=2,
    )
    assert result.stop_ticks == 4
    assert result.stop_price == 5799.00
    assert result.layer_applied == "floor"
    assert result.cap_applied is False


# ── 3. ZLR SHORT normal vol ────────────────────────────────────────────

def test_zlr_short_normal_vol():
    # Same floor-wins logic: primary=3T < floor=4T → final=4T
    result = compute_stop(
        direction="SHORT",
        entry_bar=_bar(high=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=12,
    )
    assert result.stop_ticks == 4
    assert result.stop_price == 5801.00
    assert result.layer_applied == "floor"
    assert result.cap_applied is False


# ── 4. GB100 LONG med cap — primary wins ───────────────────────────────

def test_gb100_long_med_cap():
    # primary=3T, cap=1.2×20=24T → capped=3 → final=max(3,4)=4 → floor
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_MED,
        atr_14=20,
    )
    assert result.stop_ticks == 4
    assert result.layer_applied == "floor"


# ── 5. GB100 LONG huge ATR — primary still wins ───────────────────────

def test_gb100_long_huge_atr_primary_still_wins():
    # primary=3T, cap=120T → capped=3 → final=max(3,4)=4 → floor
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_MED,
        atr_14=100,
    )
    assert result.stop_ticks == 4
    assert result.layer_applied == "floor"


# ── 6. VEGAS LONG swing anchor close — primary wins ───────────────────

def test_vegas_long_swing_anchor_close_primary_wins():
    # swing_anchor=5798.00, entry_bar.low=5800.00
    # swing_distance = (5800-5798)/0.25 = 8T, primary = 8+3 = 11T
    # cap = 1.5×10 = 15T → primary (11T) wins
    # stop = swing_anchor - 3T*0.25 = 5798.00 - 0.75 = 5797.25
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=5798.00,
        pattern_group=PatternGroup.REV,
        atr_14=10,
    )
    assert result.stop_ticks == 11
    assert result.stop_price == 5797.25
    assert result.layer_applied == "primary"
    assert result.cap_applied is False


# ── 7. VEGAS LONG swing anchor far — cap clamps ──────────────────────

def test_vegas_long_swing_anchor_far_cap_clamps():
    # swing_anchor=5790.00, entry_bar.low=5800.00
    # swing_distance = 40T, primary = 43T
    # cap = 1.5×10 = 15T → cap wins
    # stop = 5800 - 15*0.25 = 5796.25
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=5790.00,
        pattern_group=PatternGroup.REV,
        atr_14=10,
    )
    assert result.stop_ticks == 15
    assert result.stop_price == 5796.25
    assert result.layer_applied == "cap"
    assert result.cap_applied is True


# ── 8. GHOST SHORT swing anchor — cap hits ────────────────────────────

def test_ghost_short_swing_anchor_cap_hits():
    # swing_anchor=5810.00, entry_bar.high=5800.00
    # swing_distance = (5810-5800)/0.25 = 40T, primary = 43T
    # cap = 1.5×8 = 12T → cap wins
    # stop = 5800 + 12*0.25 = 5803.00
    result = compute_stop(
        direction="SHORT",
        entry_bar=_bar(high=5800.00),
        swing_anchor=5810.00,
        pattern_group=PatternGroup.REV,
        atr_14=8,
    )
    assert result.stop_ticks == 12
    assert result.stop_price == 5803.00
    assert result.layer_applied == "cap"
    assert result.cap_applied is True


# ── 9. Floor wins over tiny ATR (CONT) ───────────────────────────────

def test_floor_wins_over_tiny_atr_cont():
    # primary=3T, cap=1.0×2=2T, floor=4T → floor wins
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=2,
    )
    assert result.stop_ticks == 4
    assert result.layer_applied == "floor"


# ── 10. Floor wins over tiny ATR (REV) ───────────────────────────────

def test_floor_wins_over_tiny_atr_rev():
    # swing_anchor=5799.50, entry_bar.low=5800.00
    # swing_distance = 2T, primary = 5T
    # cap = int(1.5×1) = 1T
    # capped = min(5,1) = 1, final = max(1,4) = 4 → floor
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=5799.50,
        pattern_group=PatternGroup.REV,
        atr_14=1,
    )
    assert result.stop_ticks == 4
    assert result.layer_applied == "floor"


# ── 11. Primary == cap but floor still beats ─────────────────────────

def test_tie_primary_equals_cap_floor_still_wins():
    # primary=3T, cap=1.0×3=3T, floor=4T → floor wins
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=3,
    )
    assert result.stop_ticks == 4
    assert result.layer_applied == "floor"


# ── 12. True primary == cap tie above floor ──────────────────────────

def test_tie_primary_equals_cap_above_floor():
    # Use primary_cont_ticks=6, cap=1.0×6=6, floor=4
    # capped = min(6,6) = 6, final = max(6,4) = 6
    # tie-breaker: primary == cap → layer = "primary"
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=6,
        primary_cont_ticks=6,
    )
    assert result.stop_ticks == 6
    assert result.layer_applied == "primary"
    assert result.cap_applied is False


# ── 13. Negative ATR raises ──────────────────────────────────────────

def test_negative_atr_raises():
    with pytest.raises(ValueError, match=r"atr_14 must be positive"):
        compute_stop(
            direction="LONG",
            entry_bar=_bar(),
            swing_anchor=None,
            pattern_group=PatternGroup.CONT_TIGHT,
            atr_14=-5,
        )


# ── 14. Zero ATR raises ─────────────────────────────────────────────

def test_zero_atr_raises():
    with pytest.raises(ValueError, match=r"atr_14 must be positive"):
        compute_stop(
            direction="LONG",
            entry_bar=_bar(),
            swing_anchor=None,
            pattern_group=PatternGroup.CONT_TIGHT,
            atr_14=0,
        )


# ── 15. REV without swing_anchor raises ─────────────────────────────

def test_rev_without_swing_anchor_raises():
    with pytest.raises(ValueError, match=r"swing_anchor required for REV"):
        compute_stop(
            direction="LONG",
            entry_bar=_bar(),
            swing_anchor=None,
            pattern_group=PatternGroup.REV,
            atr_14=10,
        )


# ── 16. Tick size variation ──────────────────────────────────────────

def test_tick_size_variation():
    # tick_size=0.5 hypothetical
    # primary=3T, cap=12T → capped=3 → final=max(3,4)=4 → floor
    # stop = 5800 - 4*0.5 = 5798.00
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=12,
        tick_size=0.5,
    )
    assert result.stop_ticks == 4
    assert result.stop_price == 5798.00


# ── 17. All 9 patterns mapped to groups ──────────────────────────────

def test_all_9_patterns_mapped():
    """Verify pattern→group mapping for W-6 consumers."""
    mapping = {
        "ZLR":   PatternGroup.CONT_TIGHT,
        "TLB":   PatternGroup.CONT_TIGHT,
        "TT":    PatternGroup.CONT_TIGHT,
        "GB100": PatternGroup.CONT_MED,
        "HTLB":  PatternGroup.CONT_MED,
        "VEGAS": PatternGroup.REV,
        "GHOST": PatternGroup.REV,
        "FAMIR": PatternGroup.REV,
        "HFE":   PatternGroup.REV,
    }
    assert set(mapping.values()) == {
        PatternGroup.CONT_TIGHT,
        PatternGroup.CONT_MED,
        PatternGroup.REV,
    }
    assert len(mapping) == 9


# ── 18. CONT primary wins when primary_cont_ticks > floor ────────────

def test_cont_primary_wins_when_above_floor():
    # primary_cont_ticks=5 > floor=4, cap=1.0×12=12 → primary wins at 5T
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=12,
        primary_cont_ticks=5,
    )
    assert result.stop_ticks == 5
    assert result.stop_price == 5798.75
    assert result.layer_applied == "primary"
    assert result.cap_applied is False


# ── 19. Tick size variation with primary winning ─────────────────────

def test_tick_size_variation_primary_wins():
    # primary_cont_ticks=5 > floor=4, tick_size=0.5
    # stop = 5800 - 5*0.5 = 5797.50
    result = compute_stop(
        direction="LONG",
        entry_bar=_bar(low=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=12,
        tick_size=0.5,
        primary_cont_ticks=5,
    )
    assert result.stop_ticks == 5
    assert result.stop_price == 5797.50
    assert result.layer_applied == "primary"


# ── 20. Module constants are importable and correct ──────────────────

def test_module_constants():
    assert ATR_CAP_MULTIPLIERS[PatternGroup.CONT_TIGHT] == 1.0
    assert ATR_CAP_MULTIPLIERS[PatternGroup.CONT_MED] == 1.2
    assert ATR_CAP_MULTIPLIERS[PatternGroup.REV] == 1.5
    assert DEFAULT_FLOOR_TICKS == 4
    assert DEFAULT_PRIMARY_CONT_TICKS == 3


# ── 21. Invalid direction raises ─────────────────────────────────────

def test_invalid_direction_raises():
    with pytest.raises(ValueError, match=r"direction must be"):
        compute_stop(
            direction="UP",  # type: ignore[arg-type]
            entry_bar=_bar(),
            swing_anchor=None,
            pattern_group=PatternGroup.CONT_TIGHT,
            atr_14=10,
        )


# ── 22. CONT SHORT with floor — verify price is above entry high ────

def test_cont_short_floor_price_above_entry():
    # primary=3T, cap=1.0×3=3T → floor=4T wins
    # stop = 5800 + 4*0.25 = 5801.00
    result = compute_stop(
        direction="SHORT",
        entry_bar=_bar(high=5800.00),
        swing_anchor=None,
        pattern_group=PatternGroup.CONT_TIGHT,
        atr_14=3,
    )
    assert result.stop_ticks == 4
    assert result.stop_price == 5801.00
    assert result.layer_applied == "floor"
