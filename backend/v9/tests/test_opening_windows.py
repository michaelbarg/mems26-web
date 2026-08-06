"""Tests for opening_windows — tiered time windows + drive location filter.

Invariants:
1. Each opening type has its own window (Drive fast, Auction slow)
2. Confidence ramps from DEVELOPING → CONFIRMED
3. Opening reclassification → STALE (low confidence)
4. Drive far from value = VALUE_DRIVEN
5. Drive at balance edge = EXHAUSTION_RISK
6. Non-drive types return None for location
"""

import pytest
from backend.v9.systems.opening_windows import (
    evaluate_window, evaluate_drive_location, evaluate_opening_live,
    WindowState,
)


class TestWindowPhases:
    def test_drive_confirmed_fast(self):
        """OPEN_DRIVE confirms after 3 bars (15 min)."""
        ws = evaluate_window(opening_type="OPEN_DRIVE", bars_since_open=3)
        assert ws.phase == "CONFIRMED"

    def test_drive_developing_at_1_bar(self):
        """OPEN_DRIVE at 1 bar is still developing."""
        ws = evaluate_window(opening_type="OPEN_DRIVE", bars_since_open=0)
        assert ws.phase == "DEVELOPING"
        assert ws.confidence_pct < 0.5

    def test_auction_slow_resolution(self):
        """OPEN_AUCTION_IN needs 6+ bars (30+ min)."""
        ws = evaluate_window(opening_type="OPEN_AUCTION_IN", bars_since_open=4)
        assert ws.phase == "DEVELOPING"
        ws6 = evaluate_window(opening_type="OPEN_AUCTION_IN", bars_since_open=12)
        assert ws6.phase == "CONFIRMED"

    def test_test_drive_medium_window(self):
        """OPEN_TEST_DRIVE: 2-4 bar window."""
        ws = evaluate_window(opening_type="OPEN_TEST_DRIVE", bars_since_open=1)
        assert ws.phase == "DEVELOPING"
        ws4 = evaluate_window(opening_type="OPEN_TEST_DRIVE", bars_since_open=4)
        assert ws4.phase == "CONFIRMED"

    def test_rejection_reverse_window(self):
        """OPEN_REJECTION_REVERSE: 3-6 bar window."""
        ws = evaluate_window(opening_type="OPEN_REJECTION_REVERSE", bars_since_open=2)
        assert ws.phase == "DEVELOPING"
        ws6 = evaluate_window(opening_type="OPEN_REJECTION_REVERSE", bars_since_open=6)
        assert ws6.phase == "CONFIRMED"

    def test_confidence_ramps_up(self):
        """Confidence increases with bars_elapsed."""
        c0 = evaluate_window(opening_type="OPEN_DRIVE", bars_since_open=0).confidence_pct
        c1 = evaluate_window(opening_type="OPEN_DRIVE", bars_since_open=1).confidence_pct
        c3 = evaluate_window(opening_type="OPEN_DRIVE", bars_since_open=3).confidence_pct
        c6 = evaluate_window(opening_type="OPEN_DRIVE", bars_since_open=6).confidence_pct
        assert c0 < c1 < c3 < c6

    def test_opening_changed_goes_stale(self):
        """Reclassified opening → STALE with low confidence."""
        ws = evaluate_window(opening_type="OPEN_DRIVE", bars_since_open=5,
                             opening_changed=True)
        assert ws.phase == "STALE"
        assert ws.confidence_pct <= 0.4

    def test_unknown_type_uses_default(self):
        """Unknown opening type uses default 3-6 bar window."""
        ws = evaluate_window(opening_type="UNKNOWN_TYPE", bars_since_open=6)
        assert ws.phase == "CONFIRMED"


class TestDriveLocation:
    def _b7(self, range_low=7400, range_high=7500, val=7420, vah=7480):
        return {
            "range": [range_low, range_high],
            "value": [val, vah],
        }

    def test_drive_up_above_value_is_value_driven(self):
        """Drive UP above VAH by >30% of value width → VALUE_DRIVEN."""
        b7 = self._b7(val=7420, vah=7480)  # width=60
        loc = evaluate_drive_location(
            opening_type="OPEN_DRIVE",
            open_price=7475, current_price=7510,  # 30pt above VAH
            balance7=b7,
        )
        assert loc == "VALUE_DRIVEN"

    def test_drive_down_below_value_is_value_driven(self):
        """Drive DOWN below VAL → VALUE_DRIVEN."""
        b7 = self._b7(val=7420, vah=7480)
        loc = evaluate_drive_location(
            opening_type="OPEN_DRIVE",
            open_price=7425, current_price=7390,  # 30pt below VAL
            balance7=b7,
        )
        assert loc == "VALUE_DRIVEN"

    def test_drive_at_vah_edge_is_exhaustion(self):
        """Drive near VAH at range edge → EXHAUSTION_RISK."""
        b7 = self._b7(range_low=7400, range_high=7485, val=7420, vah=7480)
        loc = evaluate_drive_location(
            opening_type="OPEN_DRIVE",
            open_price=7470, current_price=7483,  # near VAH (3pt) and near range_high
            balance7=b7,
        )
        assert loc == "EXHAUSTION_RISK"

    def test_non_drive_returns_none(self):
        """OPEN_AUCTION doesn't get drive location."""
        loc = evaluate_drive_location(
            opening_type="OPEN_AUCTION_IN",
            open_price=7450, current_price=7500,
            balance7=self._b7(),
        )
        assert loc is None

    def test_no_balance7_returns_none(self):
        """Missing balance7 → None (Rule-1)."""
        loc = evaluate_drive_location(
            opening_type="OPEN_DRIVE",
            open_price=7450, current_price=7500,
            balance7=None,
        )
        assert loc is None

    def test_test_drive_also_gets_location(self):
        """OPEN_TEST_DRIVE also contains 'DRIVE' → gets location check."""
        b7 = self._b7(val=7420, vah=7480)
        loc = evaluate_drive_location(
            opening_type="OPEN_TEST_DRIVE",
            open_price=7475, current_price=7510,
            balance7=b7,
        )
        assert loc == "VALUE_DRIVEN"


class TestLiveWrapper:
    def test_returns_all_fields(self):
        result = evaluate_opening_live(
            opening_type="OPEN_DRIVE", bars_since_open=5,
            open_price=7450, current_price=7500,
            balance7={"range": [7400, 7500], "value": [7420, 7480]},
        )
        assert "phase" in result
        assert "confidence" in result
        assert "drive_location" in result
        assert "window" in result
        assert result["phase"] == "CONFIRMED"

    def test_minimal_args(self):
        result = evaluate_opening_live(
            opening_type="OPEN_AUCTION_IN", bars_since_open=2,
        )
        assert result["phase"] == "DEVELOPING"
        assert result["drive_location"] is None
