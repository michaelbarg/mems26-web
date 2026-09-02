"""EDGE_ENTRY_LOCATION_FIX_V1: gap-day edge redefinition.

On gap-down days (31.08, 01.09), the entire session traded below VAL.
location_gate classified every entry as "below_value" — which PASSES for
LONG but BLOCKS for SHORT. Result: SHORT@ceiling never fired (0 live).

The fix: when the session is entirely outside yesterday's VA, redefine
edge zones using the developing balance (IB/session high/low).

Anchor 01.09: DOUBLE_TOP_AA_SHORT @7640.25 blocked by location_gate
because zone="below_value" (below yesterday's VAL 7681). With the fix,
the developing ceiling (session_high 7673.75) is the edge → "near_vah".

Anchor 31.08: tqrה-כפולה @7696.25 — price below yesterday's VAL 7714.75,
but the developing ceiling was session_high 7708.25.
"""
import os
from unittest.mock import patch

import pytest
from backend.v9.systems.location_gate import decide_location, zone_of


# 01.09 parameters: gap-down, entire session below yesterday's VAL
LEVELS_0109 = {
    "vah": 7693.50,   # yesterday's VAH
    "val": 7681.00,   # yesterday's VAL
    "ib_width": 28.75,
    "ib_high": 7667.25,
    "ib_low": 7638.50,
    "session_high": 7673.75,  # developing day high
    "session_low": 7621.50,
}


class TestGapDayEdgeRedefinition:
    """On gap-down days, edges = developing balance, not yesterday's VA."""

    def test_without_fix_short_blocked(self):
        """Without the fix: SHORT @7640.25 → below_value → BLOCKED."""
        with patch.dict(os.environ, {
            "DAYTYPE_LOCATION_GATE": "1",
            "EDGE_ENTRY_LOCATION_FIX_V1": "0",
            "REV_EDGE_DAY_STRUCTURE_V1": "0",
        }):
            allow, reason = decide_location(
                family="REV", direction="SHORT",
                day_type="Neutral_Center",
                entry_price=7640.25,
                levels=LEVELS_0109)
        assert not allow, f"Without fix, SHORT@below_value should be blocked: {reason}"

    def test_with_fix_short_at_developing_ceiling_passes(self):
        """With the fix: SHORT near developing ceiling → near_vah → pass.
        Uses previous session VA from DB/TPO to detect the gap."""
        with patch.dict(os.environ, {
            "DAYTYPE_LOCATION_GATE": "1",
            "EDGE_ENTRY_LOCATION_FIX_V1": "1",
            "REV_EDGE_DAY_STRUCTURE_V1": "0",
        }):
            # Mock: previous session VA (yesterday's) is above today's range
            with patch("backend.v9.db.read.read_one", return_value={
                "vah": 7693.50, "val": 7681.00  # yesterday's VA
            }):
                allow, reason = decide_location(
                    family="REV", direction="SHORT",
                    day_type="Neutral_Center",
                    entry_price=7670.00,  # near developing VAH (session_high 7673.75)
                    levels=LEVELS_0109,
                    recent_bars=[
                        {"high": 7674.0, "low": 7665.0, "close": 7667.0},
                    ])
        assert allow, f"With fix, SHORT near developing ceiling should pass: {reason}"

    def test_flag_off_byte_identical(self):
        """Flag OFF → same result as before (blocked)."""
        with patch.dict(os.environ, {
            "DAYTYPE_LOCATION_GATE": "1",
            "EDGE_ENTRY_LOCATION_FIX_V1": "0",
            "REV_EDGE_DAY_STRUCTURE_V1": "0",
        }):
            allow, reason = decide_location(
                family="REV", direction="SHORT",
                day_type="Normal",
                entry_price=7640.25,
                levels=LEVELS_0109)
        assert not allow

    def test_0109_1735_ceiling_short_passes(self):
        """01.09 17:35: ceiling 7673.00 → SHORT near developing VAH passes.
        The candle research says this was worth +18 pts.
        Anchor: the 21:15 block of DOUBLE_TOP_AA_SHORT must pass."""
        with patch.dict(os.environ, {
            "DAYTYPE_LOCATION_GATE": "1",
            "EDGE_ENTRY_LOCATION_FIX_V1": "1",
            "REV_EDGE_DAY_STRUCTURE_V1": "1",
        }):
            with patch("backend.v9.db.read.read_one", return_value={
                "vah": 7693.50, "val": 7681.00  # yesterday's VA
            }):
                allow, reason = decide_location(
                    family="REV", direction="SHORT",
                    day_type="Neutral_Center",
                    entry_price=7665.75,
                    levels={
                        "vah": 7660.00,  # TODAY's developing VA (small)
                        "val": 7640.00,
                        "ib_width": 28.75,
                        "ib_high": 7667.25,
                        "session_high": 7673.75,
                        "session_low": 7621.50,
                        "day_high": 7673.75,
                    },
                    recent_bars=[
                        {"high": 7673.75, "low": 7662.0, "close": 7665.75},
                        {"high": 7673.00, "low": 7665.0, "close": 7668.0},
                    ],
                )
        assert allow, (
            f"01.09 17:35 ceiling SHORT should pass with EDGE_FIX: {reason}")

    def test_mid_range_short_still_blocked(self):
        """Same gap day, but SHORT in the MIDDLE of the range → still blocked.
        Candle research: '7687.25 אמצע = רעש'."""
        with patch.dict(os.environ, {
            "DAYTYPE_LOCATION_GATE": "1",
            "EDGE_ENTRY_LOCATION_FIX_V1": "1",
            "REV_EDGE_DAY_STRUCTURE_V1": "0",
        }):
            with patch("backend.v9.db.read.read_one", return_value={
                "vah": 7693.50, "val": 7681.00  # yesterday's VA
            }):
                allow, reason = decide_location(
                    family="REV", direction="SHORT",
                    day_type="Neutral_Center",
                    entry_price=7650.00,  # mid-range
                    levels=LEVELS_0109,
                )
        assert not allow, (
            f"Mid-range SHORT should still be blocked even on gap day: {reason}")

    def test_non_gap_day_unchanged(self):
        """When price IS inside yesterday's range, no redefinition occurs."""
        levels = {
            "vah": 7693.50, "val": 7681.00, "ib_width": 28.75,
            "session_high": 7690.00,  # INSIDE yesterday's VA
            "session_low": 7670.00,
        }
        with patch.dict(os.environ, {
            "DAYTYPE_LOCATION_GATE": "1",
            "EDGE_ENTRY_LOCATION_FIX_V1": "1",
            "REV_EDGE_DAY_STRUCTURE_V1": "0",
        }):
            # SHORT at mid-range → should still be blocked (no gap)
            allow, reason = decide_location(
                family="REV", direction="SHORT",
                day_type="Normal",
                entry_price=7685.0,
                levels=levels)
        # Not a gap day → original zones apply → mid-range SHORT blocked
        assert not allow, f"Non-gap: SHORT at mid should still be blocked: {reason}"
