"""Tests for W14 Risk Validator — >90% coverage target.

Tests cover all LIVE mode caps and SHADOW/DEMO bypass behavior.
"""

import pytest
from datetime import datetime

import pytz

from backend.v9.services.risk_validator.validator import (
    AccountState,
    RiskValidator,
    CUTOFF_TIME_ET,
    DAILY_LOSS_CAP_USD,
    MAX_POSITION_SIZE,
    MAX_TRADES_PER_DAY,
    CONSECUTIVE_LOSS_LIMIT,
    STANDARD_SIZE,
)
from backend.v9.services.risk_validator.news_calendar import (
    is_in_news_window,
    NEWS_BLOCK_WINDOW_MINUTES,
)

ET = pytz.timezone("US/Eastern")


def _make_time(hour: int, minute: int, date_str: str = "2026-06-15") -> datetime:
    """Helper: create ET-aware datetime for testing."""
    dt = datetime.strptime(f"{date_str} {hour:02d}:{minute:02d}", "%Y-%m-%d %H:%M")
    return ET.localize(dt)


def _setup() -> dict:
    """Minimal valid setup dict."""
    return {"system_id": 1, "direction": "LONG"}


# ─────────────────────────────────────────────────────────────────────
# test_shadow_demo_bypass
# ─────────────────────────────────────────────────────────────────────


class TestShadowDemoBypass:
    """SHADOW and DEMO modes ALWAYS return (allowed=True, rejection_reason=None)."""

    def test_shadow_always_allowed(self):
        rv = RiskValidator()
        # Even with maxed-out counters, SHADOW bypasses
        rv.daily_loss_usd = 9999.0
        rv.daily_trades_count = 100
        rv.consecutive_losses = 50
        rv._stopped_for_day = True
        state = AccountState(mode="SHADOW")
        allowed, reason = rv.check_setup(_setup(), state)
        assert allowed is True
        assert reason is None

    def test_demo_always_allowed(self):
        rv = RiskValidator()
        rv.daily_loss_usd = 9999.0
        rv._stopped_for_day = True
        state = AccountState(mode="DEMO")
        allowed, reason = rv.check_setup(_setup(), state)
        assert allowed is True
        assert reason is None

    def test_shadow_case_insensitive(self):
        rv = RiskValidator()
        state = AccountState(mode="shadow")
        allowed, reason = rv.check_setup(_setup(), state)
        assert allowed is True

    def test_demo_case_insensitive(self):
        rv = RiskValidator()
        state = AccountState(mode="demo")
        allowed, reason = rv.check_setup(_setup(), state)
        assert allowed is True

    def test_unknown_mode_rejected(self):
        rv = RiskValidator()
        state = AccountState(mode="PAPER")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False
        assert "Unknown mode" in reason


# ─────────────────────────────────────────────────────────────────────
# test_after_1430_blocks
# ─────────────────────────────────────────────────────────────────────


class TestAfter1430Blocks:
    """No new LIVE trades after 14:30 ET."""

    def test_1429_allowed(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(14, 29))
        assert allowed is True
        assert reason is None

    def test_1430_blocked(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(14, 30))
        assert allowed is False
        assert "14:30" in reason

    def test_1500_blocked(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(15, 0))
        assert allowed is False
        assert "cutoff" in reason.lower()

    def test_0930_allowed(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(9, 30))
        assert allowed is True


# ─────────────────────────────────────────────────────────────────────
# test_news_window_blocks
# ─────────────────────────────────────────────────────────────────────


class TestNewsWindowBlocks:
    """FOMC/CPI/NFP +/-10 min blocks LIVE trades."""

    def test_fomc_exact_time_blocked(self):
        # FOMC on 2026-05-06 at 14:00 ET
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        now = _make_time(14, 0, "2026-05-06")
        allowed, reason = rv.check_setup(_setup(), state, now_et=now)
        assert allowed is False
        assert "FOMC" in reason

    def test_fomc_minus_10_blocked(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        now = _make_time(13, 50, "2026-05-06")
        allowed, reason = rv.check_setup(_setup(), state, now_et=now)
        assert allowed is False
        assert "FOMC" in reason

    def test_fomc_plus_10_blocked(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        now = _make_time(14, 10, "2026-05-06")
        allowed, reason = rv.check_setup(_setup(), state, now_et=now)
        assert allowed is False

    def test_fomc_minus_11_allowed(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        now = _make_time(13, 49, "2026-05-06")
        allowed, reason = rv.check_setup(_setup(), state, now_et=now)
        assert allowed is True

    def test_cpi_blocked(self):
        # CPI on 2026-05-12 at 08:30 ET
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        now = _make_time(8, 30, "2026-05-12")
        allowed, reason = rv.check_setup(_setup(), state, now_et=now)
        assert allowed is False
        assert "CPI" in reason

    def test_nfp_blocked(self):
        # NFP on 2026-05-01 at 08:30 ET
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        now = _make_time(8, 35, "2026-05-01")
        allowed, reason = rv.check_setup(_setup(), state, now_et=now)
        assert allowed is False
        assert "NFP" in reason

    def test_no_event_allowed(self):
        # 2026-06-15 has no event at 10:00
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        now = _make_time(10, 0, "2026-06-15")
        allowed, reason = rv.check_setup(_setup(), state, now_et=now)
        assert allowed is True

    def test_is_in_news_window_utility(self):
        # Direct test of news_calendar utility
        now = _make_time(14, 5, "2026-05-06")
        blocked, desc = is_in_news_window(now)
        assert blocked is True
        assert "FOMC" in desc

    def test_is_in_news_window_clear(self):
        now = _make_time(10, 0, "2026-06-15")
        blocked, desc = is_in_news_window(now)
        assert blocked is False
        assert desc is None


# ─────────────────────────────────────────────────────────────────────
# test_loss_cap_blocks
# ─────────────────────────────────────────────────────────────────────


class TestLossCapBlocks:
    """Daily loss cap of $250 blocks further LIVE trades."""

    def test_under_cap_allowed(self):
        rv = RiskValidator()
        rv.daily_loss_usd = 200.0
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is True

    def test_at_cap_blocked(self):
        rv = RiskValidator()
        rv.daily_loss_usd = 250.0
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False
        assert "loss cap" in reason.lower()

    def test_over_cap_blocked(self):
        rv = RiskValidator()
        rv.daily_loss_usd = 300.0
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False

    def test_loss_accumulates_via_record(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        rv.record_trade_result("t1", -130.0)
        rv.record_trade_result("t2", -130.0)
        # Now at $260 loss, should block
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False
        assert "loss cap" in reason.lower() or "consecutive" in reason.lower()


# ─────────────────────────────────────────────────────────────────────
# test_trade_count_blocks
# ─────────────────────────────────────────────────────────────────────


class TestTradeCountBlocks:
    """Max 5 trades/day in LIVE mode."""

    def test_under_limit_allowed(self):
        rv = RiskValidator()
        rv.daily_trades_count = 4
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is True

    def test_at_limit_blocked(self):
        rv = RiskValidator()
        rv.daily_trades_count = 5
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False
        assert "trades/day" in reason.lower()

    def test_over_limit_blocked(self):
        rv = RiskValidator()
        rv.daily_trades_count = 10
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False

    def test_count_increments_on_record(self):
        rv = RiskValidator()
        for i in range(5):
            rv.record_trade_result(f"t{i}", 50.0)  # all winners
        assert rv.daily_trades_count == 5
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False


# ─────────────────────────────────────────────────────────────────────
# test_size_cap
# ─────────────────────────────────────────────────────────────────────


class TestSizeCap:
    """Max position size is 2 contracts; >standard requires override."""

    def test_standard_size_allowed(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE", requested_size=1)
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is True

    def test_max_size_with_override_allowed(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE", requested_size=2, manual_override=True)
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is True

    def test_over_max_blocked(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE", requested_size=3)
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False
        assert "exceeds max" in reason.lower()

    def test_non_standard_without_override_blocked(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE", requested_size=2, manual_override=False)
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False
        assert "manual override" in reason.lower()

    def test_non_standard_with_override_allowed(self):
        rv = RiskValidator()
        state = AccountState(mode="LIVE", requested_size=2, manual_override=True)
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is True


# ─────────────────────────────────────────────────────────────────────
# test_consecutive_losses_blocks
# ─────────────────────────────────────────────────────────────────────


class TestConsecutiveLossesBlocks:
    """2 consecutive losses -> STOP DAY."""

    def test_one_loss_allowed(self):
        rv = RiskValidator()
        rv.record_trade_result("t1", -50.0)
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        # 1 consecutive loss, limit is 2 -> still allowed
        assert allowed is True

    def test_two_losses_blocked(self):
        rv = RiskValidator()
        rv.record_trade_result("t1", -50.0)
        rv.record_trade_result("t2", -50.0)
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False
        assert "consecutive" in reason.lower()

    def test_win_resets_consecutive(self):
        rv = RiskValidator()
        rv.record_trade_result("t1", -50.0)
        rv.record_trade_result("t2", 100.0)  # win resets
        rv.record_trade_result("t3", -50.0)
        state = AccountState(mode="LIVE")
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        # Only 1 consecutive loss after the win
        assert allowed is True

    def test_stop_day_persists(self):
        rv = RiskValidator()
        rv.record_trade_result("t1", -50.0)
        rv.record_trade_result("t2", -50.0)
        # Day is stopped
        state = AccountState(mode="LIVE")
        allowed, _ = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False
        # Even if we somehow record a win, day stays stopped
        # (in practice no more trades would happen, but testing the flag)
        assert rv._stopped_for_day is True


# ─────────────────────────────────────────────────────────────────────
# test_daily_reset
# ─────────────────────────────────────────────────────────────────────


class TestDailyReset:
    """daily_reset() clears all counters at midnight ET."""

    def test_reset_clears_all(self):
        rv = RiskValidator()
        rv.daily_trades_count = 5
        rv.daily_loss_usd = 300.0
        rv.consecutive_losses = 3
        rv._stopped_for_day = True
        rv._trade_results["t1"] = -100.0

        rv.daily_reset()

        assert rv.daily_trades_count == 0
        assert rv.daily_loss_usd == 0.0
        assert rv.consecutive_losses == 0
        assert rv._stopped_for_day is False
        assert len(rv._trade_results) == 0

    def test_reset_allows_trading_again(self):
        rv = RiskValidator()
        rv.record_trade_result("t1", -130.0)
        rv.record_trade_result("t2", -130.0)
        state = AccountState(mode="LIVE")
        # Blocked
        allowed, _ = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is False

        # Reset
        rv.daily_reset()

        # Now allowed
        allowed, reason = rv.check_setup(_setup(), state, now_et=_make_time(10, 0))
        assert allowed is True
        assert reason is None


# ─────────────────────────────────────────────────────────────────────
# Integration / edge cases
# ─────────────────────────────────────────────────────────────────────


class TestIntegration:
    """Full flow and edge case tests."""

    def test_full_day_flow(self):
        """Simulate a realistic trading day."""
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        t = _make_time(10, 0)

        # Trade 1: win
        allowed, _ = rv.check_setup(_setup(), state, now_et=t)
        assert allowed is True
        rv.record_trade_result("t1", 75.0)

        # Trade 2: loss
        allowed, _ = rv.check_setup(_setup(), state, now_et=t)
        assert allowed is True
        rv.record_trade_result("t2", -80.0)

        # Trade 3: loss -> 2 consecutive -> STOP
        allowed, _ = rv.check_setup(_setup(), state, now_et=t)
        assert allowed is True
        rv.record_trade_result("t3", -90.0)

        # Trade 4: blocked (consecutive losses)
        allowed, reason = rv.check_setup(_setup(), state, now_et=t)
        assert allowed is False
        assert "consecutive" in reason.lower()

    def test_gating_order_time_before_news(self):
        """Time filter fires before news check."""
        rv = RiskValidator()
        state = AccountState(mode="LIVE")
        # FOMC day at 15:00 — should get time rejection, not news
        now = _make_time(15, 0, "2026-05-06")
        allowed, reason = rv.check_setup(_setup(), state, now_et=now)
        assert allowed is False
        assert "14:30" in reason  # time filter, not FOMC

    def test_record_trade_result_stores_pnl(self):
        rv = RiskValidator()
        rv.record_trade_result("abc123", -42.50)
        assert rv._trade_results["abc123"] == -42.50
        assert rv.daily_loss_usd == 42.50
        assert rv.daily_trades_count == 1

    def test_winning_trade_no_loss_accumulation(self):
        rv = RiskValidator()
        rv.record_trade_result("t1", 100.0)
        assert rv.daily_loss_usd == 0.0
        assert rv.consecutive_losses == 0
