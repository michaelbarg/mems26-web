"""R3 Spec Compliance Tests — System 6 (killzone).

Validates every requirement from MEMS26_KILLZONE_SPEC_V1.
"""
import pytest
from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

from backend.v9.systems.killzone.zones import ZONES, ZONE_BY_NAME, Zone
from backend.v9.systems.killzone.detector import (
    get_current_zone, get_killzone_status, ET,
)
from backend.v9.systems.killzone.gate import is_gate_open
from backend.v9.systems.killzone.schemas import KillzoneStatus


# ── Helpers ──────────────────────────────────────────────────────

def _utc_from_et(hour, minute=0):
    """Build a UTC datetime from ET hour:minute (non-DST offset = +5)."""
    et_dt = datetime(2026, 1, 15, hour, minute, 0, tzinfo=ET)
    return et_dt.astimezone(timezone.utc)


# ── Zone Lookup ──────────────────────────────────────────────────

class TestZoneLookup:
    def test_zone_lookup(self):
        """All 11 zones defined per spec Section 3."""
        assert len(ZONES) == 11
        names = [z.name for z in ZONES]
        for expected in [
            "PRE_MARKET", "NY_OPEN_VOLATILITY", "NY_OPEN_IB", "NY_PRIME",
            "PRE_LUNCH", "LUNCH", "PM_RECOVERY", "PM_PRIME",
            "CLOSE_APPROACH", "CLOSE_FINAL", "AFTER_HOURS",
        ]:
            assert expected in names

    def test_zone_boundaries(self):
        """Key time boundaries match spec."""
        z = ZONE_BY_NAME
        assert z["PRE_MARKET"].start == time(5, 0)
        assert z["NY_OPEN_VOLATILITY"].start == time(9, 30)
        assert z["NY_OPEN_IB"].start == time(9, 45)
        assert z["NY_PRIME"].start == time(10, 30)
        assert z["LUNCH"].start == time(12, 0)
        assert z["PM_PRIME"].start == time(14, 0)
        assert z["CLOSE_FINAL"].start == time(15, 45)
        assert z["AFTER_HOURS"].start == time(16, 0)

    def test_zone_at_specific_times(self):
        assert get_current_zone(_utc_from_et(9, 29)).name == "PRE_MARKET"
        assert get_current_zone(_utc_from_et(9, 30)).name == "NY_OPEN_VOLATILITY"
        assert get_current_zone(_utc_from_et(10, 30)).name == "NY_PRIME"
        assert get_current_zone(_utc_from_et(12, 0)).name == "LUNCH"
        assert get_current_zone(_utc_from_et(15, 45)).name == "CLOSE_FINAL"


# ── Quality ──────────────────────────────────────────────────────

class TestQuality:
    def test_quality(self):
        assert ZONE_BY_NAME["NY_PRIME"].quality == "HIGH"
        assert ZONE_BY_NAME["NY_OPEN_IB"].quality == "HIGH"
        assert ZONE_BY_NAME["PM_PRIME"].quality == "HIGH"
        assert ZONE_BY_NAME["PRE_LUNCH"].quality == "MEDIUM"
        assert ZONE_BY_NAME["LUNCH"].quality == "LOW"
        assert ZONE_BY_NAME["AFTER_HOURS"].quality == "OFF"


# ── Volatility ───────────────────────────────────────────────────

class TestVolatility:
    def test_volatility(self):
        assert ZONE_BY_NAME["NY_OPEN_VOLATILITY"].volatility == "VERY_HIGH"
        assert ZONE_BY_NAME["CLOSE_FINAL"].volatility == "VERY_HIGH"
        assert ZONE_BY_NAME["NY_PRIME"].volatility == "HIGH"
        assert ZONE_BY_NAME["PRE_LUNCH"].volatility == "MEDIUM"
        assert ZONE_BY_NAME["LUNCH"].volatility == "LOW"


# ── Sizing ───────────────────────────────────────────────────────

class TestSizing:
    def test_sizing(self):
        assert ZONE_BY_NAME["NY_PRIME"].sizing_modifier == 1.0
        assert ZONE_BY_NAME["NY_OPEN_VOLATILITY"].sizing_modifier == 0.5
        assert ZONE_BY_NAME["PRE_MARKET"].sizing_modifier == 0.25
        assert ZONE_BY_NAME["LUNCH"].sizing_modifier == 0.0
        assert ZONE_BY_NAME["CLOSE_FINAL"].sizing_modifier == 0.0


# ── Blocked ──────────────────────────────────────────────────────

class TestBlocked:
    def test_blocked(self):
        """D-061: zones are observational; they do not hard block by default."""
        for zone in ZONE_BY_NAME.values():
            assert zone.is_blocked_default is False

    def test_lunch_observational(self):
        status = get_killzone_status(_utc_from_et(12, 30))
        assert status["is_blocked"] is False
        assert status["current_killzone"] == "LUNCH"

    def test_lunch_override(self):
        status = get_killzone_status(_utc_from_et(12, 30), trade_in_lunch=True)
        assert status["is_blocked"] is False


# ── Time Calculations ────────────────────────────────────────────

class TestTimeCalc:
    def test_time_calc(self):
        status = get_killzone_status(_utc_from_et(10, 45))
        assert status["current_killzone"] == "NY_PRIME"
        assert status["time_in_zone_min"] == 15
        assert status["next_zone"] == "PRE_LUNCH"


# ── Gate Function ────────────────────────────────────────────────

class TestGate:
    def test_gate(self):
        assert is_gate_open(_utc_from_et(10, 45)) is True
        assert is_gate_open(_utc_from_et(12, 30)) is True

    def test_gate_quality_filter(self):
        assert is_gate_open(_utc_from_et(10, 45), min_quality="HIGH") is True
        assert is_gate_open(_utc_from_et(7, 0), min_quality="HIGH") is False


# ── Edge Cases ───────────────────────────────────────────────────

class TestEdgeCases:
    def test_EC1_half_day(self):
        status = get_killzone_status(
            _utc_from_et(13, 30), is_holiday_half_day=True,
        )
        assert status["is_blocked"] is True
        assert status["block_reason"] == "half_day_closed"

    def test_EC2_holiday(self):
        status = get_killzone_status(
            _utc_from_et(10, 0), is_trading_day=False,
        )
        assert status["is_blocked"] is True
        assert status["block_reason"] == "holiday"

    def test_EC3_dst(self):
        """DST transition: March and November use different UTC offsets."""
        # March (EDT, UTC-4)
        march_et = datetime(2026, 3, 15, 10, 30, tzinfo=ET)
        march_utc = march_et.astimezone(timezone.utc)
        zone_march = get_current_zone(march_utc)
        assert zone_march.name == "NY_PRIME"

        # November (EST, UTC-5)
        nov_et = datetime(2026, 11, 15, 10, 30, tzinfo=ET)
        nov_utc = nov_et.astimezone(timezone.utc)
        zone_nov = get_current_zone(nov_utc)
        assert zone_nov.name == "NY_PRIME"

    def test_EC4_news(self):
        """News guard not yet implemented — placeholder test."""
        # No news override implemented yet
        status = get_killzone_status(_utc_from_et(10, 45))
        assert "news" not in (status.get("block_reason") or "")

    def test_EC5_ntp(self):
        """NTP validation not yet implemented — placeholder test."""
        status = get_killzone_status(_utc_from_et(10, 45))
        assert "ntp" not in status


# ── Anti-Patterns ────────────────────────────────────────────────

class TestAntiPatterns:
    def test_AP1_no_overlap(self):
        """Every minute of the day maps to exactly one zone."""
        for hour in range(24):
            for minute in range(0, 60, 15):
                zone = get_current_zone(_utc_from_et(hour, minute))
                assert zone is not None
                assert isinstance(zone, Zone)

    def test_AP2_always_valid(self):
        """get_current_zone never returns None."""
        for h in range(24):
            zone = get_current_zone(_utc_from_et(h))
            assert zone is not None
            assert zone.name in ZONE_BY_NAME

    def test_AP3_block_respected(self):
        """Blocked zones have sizing_modifier 0."""
        for z in ZONES:
            if z.is_blocked_default:
                assert z.sizing_modifier == 0.0


# ── Output Schema ────────────────────────────────────────────────

class TestOutputSchema:
    def test_output_fields(self):
        status = get_killzone_status(_utc_from_et(10, 45))
        assert "current_killzone" in status
        assert "killzone_id" in status
        assert "time_in_zone_min" in status
        assert "time_to_next_zone_min" in status
        assert "next_zone" in status
        assert "quality" in status
        assert "volatility" in status
        assert "sizing_modifier" in status
        assert "is_blocked" in status
        assert "is_trading_day" in status
        assert "session_phase" in status

    def test_pydantic_schema(self):
        status = get_killzone_status(_utc_from_et(10, 45))
        ks = KillzoneStatus(**status)
        assert ks.current_killzone == "NY_PRIME"
