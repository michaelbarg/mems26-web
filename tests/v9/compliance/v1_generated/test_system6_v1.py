"""V1 gap tests for System 6 (killzone).

Each test asserts a specific spec requirement that is NOT met in code.
Failures are EXPECTED — they prove drift.
"""
import pytest
from datetime import datetime, time, timezone
from backend.v9.systems.killzone.detector import (
    get_current_zone, get_killzone_status,
)
from backend.v9.systems.killzone.zones import ZONES, ZONE_BY_NAME, Zone
from backend.v9.systems.killzone.gate import is_gate_open


# -- GAP: News event quality override ---

class TestNewsEventQualityOverride:
    """Spec Section 6 Edge Case 4: Override quality to LOW for +/-15 min
    around FOMC/NFP events. Not implemented.
    """

    def test_killzone_status_accepts_news_events(self):
        """Spec: get_killzone_status must accept news_events parameter."""
        import inspect
        sig = inspect.signature(get_killzone_status)
        params = list(sig.parameters.keys())
        assert "news_events" in params or "scheduled_events" in params, (
            f"Spec Section 6 Edge Case 4: get_killzone_status must accept "
            f"news event parameter to override quality to LOW. "
            f"Current params: {params}"
        )


# -- GAP: PRE_MARKET should be blocked for live trading ---

class TestPreMarketBlocking:
    """Spec Section 3: PRE_MARKET notes say 'Watch only (no live trading)'.
    Code sets is_blocked_default=False with sizing=0.25.
    For LIVE mode, PRE_MARKET should be blocked.
    """

    def test_pre_market_blocked_by_default(self):
        """Spec: PRE_MARKET should be blocked (watch only, no live trading)."""
        zone = ZONE_BY_NAME["PRE_MARKET"]
        # Spec says "Watch only (no live trading)" = should be blocked
        # Code has is_blocked_default=False
        assert zone.is_blocked_default is True, (
            f"Spec: PRE_MARKET = 'Watch only (no live trading)'. "
            f"is_blocked_default should be True, got {zone.is_blocked_default}"
        )


# -- GAP: Half-day zone time scaling ---

class TestHalfDayZoneScaling:
    """Spec Section 6 Edge Case 1: Half-day sessions scale ALL zones
    to 50% duration. Code only blocks after 13:00.
    """

    def test_half_day_scales_zone_times(self):
        """Spec: Half-day should recalculate zone boundaries, not just block."""
        from zoneinfo import ZoneInfo
        ET = ZoneInfo("America/New_York")

        # At 11:00 ET on half-day, PM_PRIME should already be active
        # (scaled from 14:00-15:00 to ~11:30-12:15 proportionally)
        dt_1100 = datetime(2026, 11, 27, 11, 0, 0, tzinfo=ET)
        dt_utc = dt_1100.astimezone(timezone.utc)

        status = get_killzone_status(
            dt_utc,
            is_holiday_half_day=True,
            is_trading_day=True,
        )
        # On a half-day at 11:00, we should be in a scaled zone
        # Currently code does NOT scale zones, so this tests the gap
        assert status.get("session_phase") != "PRIME" or \
               status.get("current_killzone") != "NY_PRIME", (
            "At 11:00 ET on half-day, zones should be scaled to 50% duration. "
            f"Got zone={status.get('current_killzone')}, "
            f"phase={status.get('session_phase')}"
        )


# -- Verify correct zone definitions ---

class TestZoneDefinitionsMatchSpec:
    """Verify all 11 zones match spec Section 3 definitions."""

    def test_zone_count_is_11(self):
        """Spec: exactly 11 killzones defined."""
        assert len(ZONES) == 11, (
            f"Spec defines 11 killzones, got {len(ZONES)}"
        )

    def test_ny_prime_quality_high(self):
        """Spec: NY_PRIME quality = HIGH."""
        zone = ZONE_BY_NAME["NY_PRIME"]
        assert zone.quality == "HIGH"

    def test_lunch_blocked_default(self):
        """Spec: LUNCH blocked by default."""
        zone = ZONE_BY_NAME["LUNCH"]
        assert zone.is_blocked_default is True

    def test_close_final_blocked_default(self):
        """Spec: CLOSE_FINAL blocked by default."""
        zone = ZONE_BY_NAME["CLOSE_FINAL"]
        assert zone.is_blocked_default is True

    def test_pm_prime_sizing_full(self):
        """Spec: PM_PRIME sizing = 1.0 (FULL)."""
        zone = ZONE_BY_NAME["PM_PRIME"]
        assert zone.sizing_modifier == 1.0

    def test_lunch_sizing_zero(self):
        """Spec: LUNCH sizing = 0.0 (blocked)."""
        zone = ZONE_BY_NAME["LUNCH"]
        assert zone.sizing_modifier == 0.0

    def test_ny_open_volatility_quality_medium(self):
        """Spec: NY_OPEN_VOLATILITY quality = MEDIUM."""
        zone = ZONE_BY_NAME["NY_OPEN_VOLATILITY"]
        assert zone.quality == "MEDIUM"

    def test_ny_open_ib_quality_high(self):
        """Spec: NY_OPEN_IB quality = HIGH."""
        zone = ZONE_BY_NAME["NY_OPEN_IB"]
        assert zone.quality == "HIGH"


# -- Gate function quality filter ---

class TestGateQualityFilter:
    """Spec Section 4 Q5: Min quality threshold filters zones."""

    def test_gate_blocks_low_quality_when_min_good(self):
        """Spec: min_quality=GOOD should block LOW zones."""
        from zoneinfo import ZoneInfo
        ET = ZoneInfo("America/New_York")

        # 5:30 AM ET = PRE_MARKET (LOW quality)
        dt = datetime(2026, 5, 10, 5, 30, 0, tzinfo=ET).astimezone(timezone.utc)
        result = is_gate_open(dt, min_quality="MEDIUM")
        assert result is False, (
            "PRE_MARKET (LOW quality) should be blocked when min_quality=MEDIUM"
        )

    def test_gate_allows_high_quality_when_min_good(self):
        """Spec: min_quality=GOOD should allow HIGH zones."""
        from zoneinfo import ZoneInfo
        ET = ZoneInfo("America/New_York")

        # 10:45 AM ET = NY_PRIME (HIGH quality)
        dt = datetime(2026, 5, 12, 10, 45, 0, tzinfo=ET).astimezone(timezone.utc)
        result = is_gate_open(dt, min_quality="MEDIUM")
        assert result is True, (
            "NY_PRIME (HIGH quality) should be allowed when min_quality=MEDIUM"
        )
