"""
Unit tests for multi-target outcome calculator.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from tools.multidim_sim.retro.outcome_calculator import compute_outcome_multi_target


def _ts(seconds: int) -> datetime:
    """Helper: base time + seconds offset."""
    return datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=seconds)


ENTRY_TS = _ts(0)


def _make_ticks(price_sequence: list) -> list:
    """Build ticks from (offset_sec, price) pairs. Each tick: H=L=C=price."""
    return [
        {"ts": _ts(sec), "high": p, "low": p, "close": p, "volume": 1}
        for sec, p in price_sequence
    ]


def _make_range_ticks(price_sequence: list) -> list:
    """Build ticks from (offset_sec, high, low) pairs."""
    return [
        {"ts": _ts(sec), "high": h, "low": l, "close": (h + l) / 2, "volume": 1}
        for sec, h, l in price_sequence
    ]


# ── LONG tests ────────────────────────────────────────────────────────────

class TestLongMultiTarget:

    def test_full_runner_c1_c2_c3(self):
        """LONG hits C1, C2, C3 in sequence."""
        ticks = _make_ticks([
            (5, 7250),   # entry area
            (10, 7255),  # C1 hit
            (15, 7260),  # C2 hit
            (20, 7270),  # C3 hit
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=7270,
            c3_enabled=True, direction="LONG",
        )
        assert r["outcome"] == "HIT_C3"
        assert r["c1_filled"] and r["c2_filled"] and r["c3_filled"]
        assert r["c1_pnl_pts"] == 5.0
        assert r["c2_pnl_pts"] == 10.0
        assert r["c3_pnl_pts"] == 20.0
        assert r["total_pnl_pts"] == 35.0

    def test_c1_c2_no_c3(self):
        """LONG hits C1 and C2, C3 not enabled (2 contracts)."""
        ticks = _make_ticks([
            (5, 7250),
            (10, 7255),  # C1
            (15, 7260),  # C2
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=None,
            c3_enabled=False, direction="LONG",
        )
        assert r["outcome"] == "HIT_C2"
        assert r["c1_filled"] and r["c2_filled"]
        assert not r["c3_filled"]
        assert r["total_pnl_pts"] == 15.0  # 5 + 10

    def test_c1_then_original_stop(self):
        """LONG hits C1, then reverts to original stop. C2/C3 lose full R."""
        ticks = _make_ticks([
            (5, 7252),
            (10, 7255),  # C1 hit — stop stays at 7245 (NO BE yet)
            (15, 7248),
            (20, 7245),  # original stop hit
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=7270,
            c3_enabled=True, direction="LONG",
        )
        assert r["outcome"] == "PARTIAL"
        assert r["c1_pnl_pts"] == 5.0    # C1 won
        assert r["c2_pnl_pts"] == -5.0   # stopped at original
        assert r["c3_pnl_pts"] == -5.0   # stopped at original
        assert r["total_pnl_pts"] == -5.0  # net: +5 -5 -5 = -5

    def test_c1_c2_then_be_stop(self):
        """LONG hits C1+C2, then reverts to BE. C3 exits at BE (0)."""
        ticks = _make_ticks([
            (5, 7255),   # C1 hit
            (10, 7260),  # C2 hit → NOW stop moves to BE (7250)
            (15, 7252),
            (20, 7250),  # BE stop hit
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=7270,
            c3_enabled=True, direction="LONG",
        )
        assert r["outcome"] == "HIT_C2"   # best achieved before stop
        assert r["c1_pnl_pts"] == 5.0
        assert r["c2_pnl_pts"] == 10.0
        assert r["c3_pnl_pts"] == 0.0     # BE
        assert r["total_pnl_pts"] == 15.0

    def test_full_stop_before_c1(self):
        """LONG hits stop before C1. All contracts lose."""
        ticks = _make_ticks([
            (5, 7248),
            (10, 7245),  # stop hit
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=7270,
            c3_enabled=True, direction="LONG",
        )
        assert r["outcome"] == "HIT_STOP"
        assert r["c1_pnl_pts"] == -5.0
        assert r["c2_pnl_pts"] == -5.0
        assert r["c3_pnl_pts"] == -5.0
        assert r["total_pnl_pts"] == -15.0

    def test_timeout_no_fill(self):
        """LONG: neither stop nor targets hit within timeout."""
        ticks = _make_ticks([
            (5, 7251),
            (10, 7249),
            (15, 7250),
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=None,
            c3_enabled=False, direction="LONG", timeout_minutes=1,
        )
        assert r["outcome"] == "TIMEOUT"
        assert not r["c1_filled"]

    def test_c1_c2_timeout_c3_runner(self):
        """LONG hits C1+C2, C3 runner times out at profit. BE protects C3."""
        ticks = _make_ticks([
            (5, 7255),   # C1
            (10, 7260),  # C2 → stop moves to BE
            (15, 7265),  # C3 not yet (target=7270)
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=7270,
            c3_enabled=True, direction="LONG", timeout_minutes=1,
        )
        assert r["outcome"] == "HIT_C2"
        assert r["c1_filled"] and r["c2_filled"] and not r["c3_filled"]
        # C3 times out at last price (7265), BE protects → max(0, 15) = 15
        assert r["c3_pnl_pts"] == 15.0


# ── SHORT tests ───────────────────────────────────────────────────────────

class TestShortMultiTarget:

    def test_full_stop(self):
        """SHORT hits stop before C1."""
        ticks = _make_ticks([
            (5, 7252),
            (10, 7255),  # stop hit
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7255,
            c1_target=7245, c2_target=7240, c3_target=None,
            c3_enabled=False, direction="SHORT",
        )
        assert r["outcome"] == "HIT_STOP"
        assert r["c1_pnl_pts"] == -5.0
        assert r["c2_pnl_pts"] == -5.0
        assert r["total_pnl_pts"] == -10.0

    def test_c1_c2_hit(self):
        """SHORT hits C1 and C2."""
        ticks = _make_ticks([
            (5, 7248),
            (10, 7245),  # C1
            (15, 7240),  # C2
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7255,
            c1_target=7245, c2_target=7240, c3_target=None,
            c3_enabled=False, direction="SHORT",
        )
        assert r["outcome"] == "HIT_C2"
        assert r["c1_pnl_pts"] == 5.0
        assert r["c2_pnl_pts"] == 10.0
        assert r["total_pnl_pts"] == 15.0

    def test_c1_then_original_stop(self):
        """SHORT hits C1, then reverts to original stop. C2 loses."""
        ticks = _make_ticks([
            (5, 7245),   # C1
            (10, 7252),
            (15, 7255),  # original stop (not BE — BE only after C2)
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7255,
            c1_target=7245, c2_target=7240, c3_target=None,
            c3_enabled=False, direction="SHORT",
        )
        assert r["outcome"] == "PARTIAL"
        assert r["c1_pnl_pts"] == 5.0
        assert r["c2_pnl_pts"] == -5.0  # full loss on C2


# ── Edge cases ────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_stop_wins_tie_with_c1(self):
        """When both stop and C1 in same tick, stop wins (conservative)."""
        ticks = _make_range_ticks([
            (5, 7255, 7245),  # high=C1, low=stop — both hit
        ])
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=None,
            c3_enabled=False, direction="LONG",
        )
        assert r["outcome"] == "HIT_STOP"

    def test_empty_ticks(self):
        """No ticks → TIMEOUT."""
        r = compute_outcome_multi_target(
            [], ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=None,
            c3_enabled=False, direction="LONG", timeout_minutes=1,
        )
        assert r["outcome"] == "TIMEOUT"

    def test_pnl_usd_correct(self):
        """Verify USD conversion: pts × $5."""
        ticks = _make_ticks([(5, 7245)])  # stop hit for LONG
        r = compute_outcome_multi_target(
            ticks, ENTRY_TS, entry_price=7250, stop_price=7245,
            c1_target=7255, c2_target=7260, c3_target=None,
            c3_enabled=False, direction="LONG",
        )
        assert r["total_pnl_usd"] == r["total_pnl_pts"] * 5.0
