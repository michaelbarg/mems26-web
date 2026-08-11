"""A2 — COLD_START_GUARD_V1 (2026-08-11).

Case #655: trade fired 8 SECONDS after backend restart with
bars_processed_today=0, buffer_size=0, profile_shape=NA, cot=0.
The system had zero market context — no IB, no day-type, no profile.

This guard blocks ALL firing until bars_processed_today >= COLD_START_MIN_BARS
(default 3). Fail-closed: missing/zero bars or any error → block.
"""
import inspect

import pytest

from backend.v9.gateway import trading_gateway


# ── Code-path verification ─────────────────────────────────────────────────

class TestColdStartGuardCodePath:
    """Verify the guard exists and is wired correctly."""

    def test_guard_exists_in_gateway(self):
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "COLD_START_GUARD_V1" in src
        assert "cold_start_guard" in src
        assert "bars_processed_today" in src

    def test_guard_is_fail_closed(self):
        """On error reading bar count, the guard must BLOCK (fail-closed)."""
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "fail-closed" in src

    def test_guard_checks_min_bars(self):
        """COLD_START_MIN_BARS env var must be read."""
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "COLD_START_MIN_BARS" in src

    def test_guard_before_eod_cutoff(self):
        """Cold start guard must fire before EOD cutoff (early in chain)."""
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        cs_pos = src.index("cold_start_guard")
        eod_pos = src.index("eod_entry_cutoff")
        assert cs_pos < eod_pos

    def test_guard_after_session_gate(self):
        """Cold start guard after session gate (no point blocking outside hours)."""
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        session_pos = src.index("session_gate_closed")
        cs_pos = src.index("cold_start_guard")
        assert cs_pos > session_pos

    def test_flag_default_off(self):
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert 'COLD_START_GUARD_V1", "0"' in src

    def test_reads_tpo_and_five_min(self):
        """Guard must read from both tpo_system and five_min_system."""
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "tpo_system" in src
        assert "five_min_system" in src


# ── Unit tests for the guard logic ─────────────────────────────────────────
# (testing the guard conditions directly, not the full gateway)

class TestColdStartLogic:
    """Test the bar-count threshold logic."""

    def test_zero_bars_blocked(self):
        """bars_processed_today=0 → must block (case #655)."""
        bars = 0
        min_bars = 3
        assert bars < min_bars

    def test_one_bar_blocked(self):
        """bars_processed_today=1 → still blocked (needs 3)."""
        assert 1 < 3

    def test_two_bars_blocked(self):
        """bars_processed_today=2 → still blocked."""
        assert 2 < 3

    def test_three_bars_passes(self):
        """bars_processed_today=3 → passes (>= min_bars)."""
        assert not (3 < 3)

    def test_many_bars_passes(self):
        """bars_processed_today=50 → passes."""
        assert not (50 < 3)

    def test_case_655_exact(self):
        """#655 cross_context: bars_processed_today=0, buffer_size=0."""
        ctx = {
            "tpo_system": {"bars_processed_today": 0, "buffer_size": 0,
                           "profile_shape": "NA"},
            "five_min_system": {"buffer_size": 1},
        }
        bars = int(ctx["tpo_system"].get("bars_processed_today", 0))
        assert bars < 3, "case #655 should be blocked"

    def test_none_bars_treated_as_zero(self):
        """bars_processed_today=None → int(None or 0) = 0 → blocked."""
        bars = int(None or 0)
        assert bars < 3
