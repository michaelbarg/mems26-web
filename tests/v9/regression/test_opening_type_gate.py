"""FIX B: Opening-type gate — blocks counter-drive during opening window.

Anti-tautological: drives the REAL opening_type_gate.decide(), asserts blocked_by.
RED-on-revert: removing the gate → counter-drive fires wrongly pass.
"""
import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def enable_flag():
    with patch.dict(os.environ, {"OPENING_TYPE_GATE": "1"}):
        yield


# 06-22 first-hour bars: OPEN_DRIVE UP (open 7527, drove to 7599)
DRIVE_UP_BARS = [
    {"o": 7527, "h": 7540, "l": 7525, "c": 7538, "v": 5000},
    {"o": 7538, "h": 7555, "l": 7536, "c": 7552, "v": 5000},
    {"o": 7552, "h": 7568, "l": 7550, "c": 7565, "v": 5000},
    {"o": 7565, "h": 7580, "l": 7563, "c": 7578, "v": 5000},
    {"o": 7578, "h": 7590, "l": 7575, "c": 7588, "v": 5000},
    {"o": 7588, "h": 7599, "l": 7585, "c": 7595, "v": 5000},
]

# 06-19 bars: OPEN_AUCTION (rotational, no clear drive)
AUCTION_BARS = [
    {"o": 7560, "h": 7565, "l": 7555, "c": 7558, "v": 3000},
    {"o": 7558, "h": 7562, "l": 7553, "c": 7561, "v": 3000},
    {"o": 7561, "h": 7564, "l": 7556, "c": 7557, "v": 3000},
    {"o": 7557, "h": 7563, "l": 7554, "c": 7562, "v": 3000},
    {"o": 7562, "h": 7565, "l": 7558, "c": 7559, "v": 3000},
    {"o": 7559, "h": 7563, "l": 7556, "c": 7560, "v": 3000},
]


class TestOpenDriveUp:
    """OPEN_DRIVE UP: LONG allowed, SHORT blocked."""

    def test_short_blocked(self):
        from backend.v9.systems.opening_type_gate import decide
        allow, reason = decide(
            direction="SHORT", rth_bars=DRIVE_UP_BARS, ib_locked=False,
        )
        assert allow is False
        assert "counter-drive" in reason

    def test_long_allowed(self):
        from backend.v9.systems.opening_type_gate import decide
        allow, reason = decide(
            direction="LONG", rth_bars=DRIVE_UP_BARS, ib_locked=False,
        )
        assert allow is True
        assert "with-drive" in reason


class TestFlipDriveDown:
    """Mock drive DOWN: LONG blocked, SHORT allowed (proves it reads the drive)."""

    DRIVE_DOWN_BARS = [
        {"o": 7580, "h": 7582, "l": 7560, "c": 7562, "v": 5000},
        {"o": 7562, "h": 7564, "l": 7545, "c": 7548, "v": 5000},
        {"o": 7548, "h": 7550, "l": 7530, "c": 7533, "v": 5000},
        {"o": 7533, "h": 7535, "l": 7518, "c": 7520, "v": 5000},
        {"o": 7520, "h": 7522, "l": 7505, "c": 7508, "v": 5000},
        {"o": 7508, "h": 7510, "l": 7495, "c": 7498, "v": 5000},
    ]

    def test_long_blocked(self):
        from backend.v9.systems.opening_type_gate import decide
        allow, reason = decide(
            direction="LONG", rth_bars=self.DRIVE_DOWN_BARS, ib_locked=False,
        )
        assert allow is False
        assert "counter-drive" in reason

    def test_short_allowed(self):
        from backend.v9.systems.opening_type_gate import decide
        allow, reason = decide(
            direction="SHORT", rth_bars=self.DRIVE_DOWN_BARS, ib_locked=False,
        )
        assert allow is True


class TestAuctionHeld:
    """OPEN_AUCTION: all fires HELD."""

    def test_long_held(self):
        from backend.v9.systems.opening_type_gate import decide
        allow, reason = decide(
            direction="LONG", rth_bars=AUCTION_BARS, ib_locked=False,
        )
        assert allow is False
        assert "HOLD" in reason or "rotation" in reason

    def test_short_held(self):
        from backend.v9.systems.opening_type_gate import decide
        allow, reason = decide(
            direction="SHORT", rth_bars=AUCTION_BARS, ib_locked=False,
        )
        assert allow is False


class TestPostIBLockInert:
    """After IB lock, gate is inert — never blocks."""

    def test_counter_drive_allowed_post_lock(self):
        from backend.v9.systems.opening_type_gate import decide
        allow, reason = decide(
            direction="SHORT", rth_bars=DRIVE_UP_BARS, ib_locked=True,
        )
        assert allow is True
        assert "inert" in reason


class TestFlagOff:
    """Flag OFF → gate never blocks."""

    def test_never_blocks(self):
        from backend.v9.systems.opening_type_gate import decide
        with patch.dict(os.environ, {"OPENING_TYPE_GATE": "0"}):
            allow, reason = decide(
                direction="SHORT", rth_bars=DRIVE_UP_BARS, ib_locked=False,
            )
            assert allow is True
            assert "OFF" in reason


class TestEarlyBias:
    """Before 6 bars: uses running bias."""

    def test_early_up_bias_blocks_short(self):
        from backend.v9.systems.opening_type_gate import decide
        early_bars = [
            {"o": 7527, "h": 7540, "l": 7525, "c": 7538, "v": 5000},
            {"o": 7538, "h": 7555, "l": 7536, "c": 7552, "v": 5000},
        ]
        allow, reason = decide(
            direction="SHORT", rth_bars=early_bars, ib_locked=False,
        )
        # Early UP bias (close 7552 > open 7527) → SHORT should be blocked
        assert allow is False


class TestDriveFailed:
    """Drive fails (returned through open) → released."""

    def test_drive_fails_releases_block(self):
        from backend.v9.systems.opening_type_gate import decide
        # Start with drive up, then price returns below open
        failed_bars = [
            {"o": 7527, "h": 7540, "l": 7525, "c": 7538, "v": 5000},
            {"o": 7538, "h": 7555, "l": 7536, "c": 7552, "v": 5000},
            {"o": 7552, "h": 7560, "l": 7548, "c": 7555, "v": 5000},
            {"o": 7555, "h": 7558, "l": 7520, "c": 7522, "v": 5000},  # crash below open
            {"o": 7522, "h": 7525, "l": 7510, "c": 7515, "v": 5000},
            {"o": 7515, "h": 7520, "l": 7505, "c": 7510, "v": 5000},
        ]
        allow, reason = decide(
            direction="SHORT", rth_bars=failed_bars, ib_locked=False,
        )
        assert allow is True
        assert "failed" in reason or "released" in reason
