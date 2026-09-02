"""CEILING_FLIP_SHORT_V1: reverse entry on double ceiling/floor failure.

Anchor 01.09 17:35: תקרה-כפולה 7673.00↔7673.00, Δ=0, 14 bars.
Confirm bar close 7665.75 (18:35 IL = the bar that broke the neckline).
The correct trade: SHORT @7665.75, stop above 7673.00+buffer, T1=POC.

From the candle research: this trade was worth +18 pts (+32 with runner).
"""
import os
from unittest.mock import patch

import pytest
from backend.v9.systems.ceiling_flip import build_flip_setup


# 01.09 ceiling data (from ceiling_floor_state detection)
CEILING_0109 = {
    "state": "CEILING_FAILED",
    "p1": 7673.00,
    "p2": 7673.00,
    "confirm_close": 7665.75,
    "confirm_bar_low": 7662.00,
    "confirm_level": 7667.25,  # neckline
    "edge_source": "SESSION_HIGH",
    "edge_price": 7673.75,
    "bars_between": 14,
    "signal_bar_ts": "2026-09-01T15:35:00+00:00",
    "atr": 7.5,
    "tol": 1.875,
}

ATR = 7.5
POC = 7654.00
VAL = 7638.50  # opposite edge (IB low)


class TestCeilingFlipShort:
    """Reverse SHORT on ceiling failure."""

    def test_0109_ceiling_fires_short(self):
        """01.09 17:35: CEILING_FAILED → SHORT setup."""
        setup = build_flip_setup(
            ceiling_floor=CEILING_0109,
            atr=ATR,
            poc=POC,
            opposite_edge=VAL,
        )
        assert setup is not None, "Should produce a SHORT setup"
        assert setup["direction"] == "SHORT"
        assert setup["entry_price"] == 7665.75  # confirm bar close
        assert setup["stop"] > 7673.00  # above the ceiling
        assert setup["t1"] == POC  # 7654.00
        assert setup["t2"] == VAL  # 7638.50

    def test_stop_above_ceiling_with_buffer(self):
        """Stop = max(P1,P2) + 0.2×ATR, capped at 1.5×ATR from entry."""
        setup = build_flip_setup(
            ceiling_floor=CEILING_0109,
            atr=ATR,
            poc=POC,
        )
        # max(7673, 7673) + 0.2×7.5 = 7673 + 1.5 = 7674.5
        assert setup["stop"] == 7674.50, f"Stop should be 7674.50, got {setup['stop']}"

    def test_floor_flip_long(self):
        """FLOOR_FAILED → LONG setup (exact mirror)."""
        floor = {
            "state": "FLOOR_FAILED",
            "p1": 7638.00,
            "p2": 7638.50,
            "confirm_close": 7645.00,
            "confirm_bar_high": 7648.00,
            "confirm_level": 7642.75,
            "edge_source": "IB_LOW",
            "signal_bar_ts": "2026-08-31T16:40:00+00:00",
        }
        setup = build_flip_setup(
            ceiling_floor=floor,
            atr=8.0,
            poc=7685.50,
            opposite_edge=7693.50,  # VAH
        )
        assert setup is not None
        assert setup["direction"] == "LONG"
        assert setup["entry_price"] == 7645.00
        assert setup["stop"] < 7638.00  # below the floor

    def test_no_state_returns_none(self):
        """Invalid state → None."""
        assert build_flip_setup(
            ceiling_floor={"state": "NONE"},
            atr=8.0,
        ) is None

    def test_missing_data_returns_none(self):
        """Missing P1/P2 → None (Rule 1)."""
        assert build_flip_setup(
            ceiling_floor={"state": "CEILING_FAILED", "p1": None, "p2": 7673.0,
                           "confirm_close": 7665.0},
            atr=8.0,
        ) is None

    def test_shadow_only_metadata(self):
        """Setup always has shadow_only=True until promoted."""
        setup = build_flip_setup(
            ceiling_floor=CEILING_0109,
            atr=ATR,
        )
        assert setup["metadata"]["shadow_only"] is True

    def test_wiring_exists_in_five_min(self):
        """Mutation: build_flip_setup is called from five_min_system."""
        import inspect, textwrap
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        source = textwrap.dedent(inspect.getsource(
            FiveMinSystem._maybe_ceiling_floor_state))
        assert "build_flip_setup" in source, (
            "MUTATION: CEILING_FLIP is not wired in five_min_system. "
            "The setup builder has no caller.")
        assert "CEILING_FLIP_SHORT_V1" in source, (
            "MUTATION: CEILING_FLIP_SHORT_V1 flag not checked in five_min_system.")

    def test_pattern_name(self):
        """Pattern = CEILING_FLIP_SHORT or CEILING_FLIP_LONG."""
        setup = build_flip_setup(
            ceiling_floor=CEILING_0109,
            atr=ATR,
        )
        assert setup["pattern"] == "CEILING_FLIP_SHORT"
        assert setup["classification"] == "CEILING_FLIP_SHORT"
