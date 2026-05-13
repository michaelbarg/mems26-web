"""Tests for System 6: Killzone Engine.

Covers:
- All 11 zones with boundary times
- DST transitions (EDT vs EST)
- Gate logic (blocked, quality, config overrides)
- Half-day / holiday
- Edge cases from spec Section 7
"""

import pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from backend.v9.systems.killzone.zones import ZONES, ZONE_BY_NAME, Zone
from backend.v9.systems.killzone.detector import get_current_zone, get_killzone_status
from backend.v9.systems.killzone.gate import is_gate_open

ET = ZoneInfo("America/New_York")


def _utc_from_et(year, month, day, hour, minute, second=0):
    """Create a UTC datetime from ET components."""
    et_dt = datetime(year, month, day, hour, minute, second, tzinfo=ET)
    return et_dt.astimezone(timezone.utc)


# ══════════════════════════════════════════════════════════════
# Zone definitions
# ══════════════════════════════════════════════════════════════

class TestZoneDefinitions:
    def test_exactly_11_zones(self):
        assert len(ZONES) == 11

    def test_zone_names(self):
        expected = [
            "PRE_MARKET", "NY_OPEN_VOLATILITY", "NY_OPEN_IB", "NY_PRIME",
            "PRE_LUNCH", "LUNCH", "PM_RECOVERY", "PM_PRIME",
            "CLOSE_APPROACH", "CLOSE_FINAL", "AFTER_HOURS",
        ]
        assert [z.name for z in ZONES] == expected

    def test_all_zones_in_lookup(self):
        for z in ZONES:
            assert z.name in ZONE_BY_NAME
            assert ZONE_BY_NAME[z.name] is z

    def test_zone_is_frozen(self):
        with pytest.raises(AttributeError):
            ZONES[0].name = "HACKED"

    def test_sizing_modifiers(self):
        expected = {
            "PRE_MARKET": 0.25,
            "NY_OPEN_VOLATILITY": 0.5,
            "NY_OPEN_IB": 1.0,
            "NY_PRIME": 1.0,
            "PRE_LUNCH": 0.5,
            "LUNCH": 0.0,
            "PM_RECOVERY": 0.5,
            "PM_PRIME": 1.0,
            "CLOSE_APPROACH": 0.5,
            "CLOSE_FINAL": 0.0,
            "AFTER_HOURS": 0.0,
        }
        for z in ZONES:
            assert z.sizing_modifier == expected[z.name], f"{z.name} sizing wrong"

    def test_blocked_defaults(self):
        blocked = {"LUNCH", "CLOSE_FINAL", "AFTER_HOURS"}
        for z in ZONES:
            if z.name in blocked:
                assert z.is_blocked_default, f"{z.name} should be blocked"
            else:
                assert not z.is_blocked_default, f"{z.name} should not be blocked"

    def test_quality_values(self):
        for z in ZONES:
            assert z.quality in ("HIGH", "MEDIUM", "LOW", "OFF"), f"{z.name} bad quality"

    def test_volatility_values(self):
        for z in ZONES:
            assert z.volatility in ("VERY_HIGH", "HIGH", "MEDIUM", "LOW"), f"{z.name} bad vol"


# ══════════════════════════════════════════════════════════════
# Zone detection — all 11 zones
# ══════════════════════════════════════════════════════════════

class TestZoneDetection:
    """Test get_current_zone at key times (EDT — summer 2026)."""

    # Summer 2026: EDT (UTC-4). June 15 is a Monday.
    DAY = (2026, 6, 15)

    def test_pre_market_early(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 6, 0))
        assert z.name == "PRE_MARKET"

    def test_pre_market_end(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 9, 29, 59))
        assert z.name == "PRE_MARKET"

    def test_ny_open_volatility_start(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 9, 30, 0))
        assert z.name == "NY_OPEN_VOLATILITY"

    def test_ny_open_volatility_end(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 9, 44, 59))
        assert z.name == "NY_OPEN_VOLATILITY"

    def test_ny_open_ib(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 9, 45))
        assert z.name == "NY_OPEN_IB"

    def test_ny_open_ib_end(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 10, 29, 59))
        assert z.name == "NY_OPEN_IB"

    def test_ny_prime(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 10, 30))
        assert z.name == "NY_PRIME"

    def test_ny_prime_mid(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 11, 0))
        assert z.name == "NY_PRIME"

    def test_pre_lunch(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 11, 30))
        assert z.name == "PRE_LUNCH"

    def test_lunch(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 12, 0))
        assert z.name == "LUNCH"

    def test_lunch_mid(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 12, 30))
        assert z.name == "LUNCH"

    def test_pm_recovery(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 13, 0))
        assert z.name == "PM_RECOVERY"

    def test_pm_prime(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 14, 0))
        assert z.name == "PM_PRIME"

    def test_close_approach(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 15, 0))
        assert z.name == "CLOSE_APPROACH"

    def test_close_final(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 15, 45))
        assert z.name == "CLOSE_FINAL"

    def test_close_final_end(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 15, 59, 59))
        assert z.name == "CLOSE_FINAL"

    def test_after_hours_start(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 16, 0))
        assert z.name == "AFTER_HOURS"

    def test_after_hours_midnight(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 0, 0))
        assert z.name == "AFTER_HOURS"

    def test_after_hours_3am(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 3, 0))
        assert z.name == "AFTER_HOURS"

    def test_after_hours_4_59(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 4, 59))
        assert z.name == "AFTER_HOURS"

    def test_pre_market_exactly_5am(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 5, 0))
        assert z.name == "PRE_MARKET"


# ══════════════════════════════════════════════════════════════
# DST — EST (winter) vs EDT (summer)
# ══════════════════════════════════════════════════════════════

class TestDST:
    """Zones must be correct regardless of DST state."""

    def test_winter_est_ny_prime(self):
        """January = EST (UTC-5). 10:30 ET = 15:30 UTC."""
        utc = _utc_from_et(2026, 1, 15, 10, 30)
        z = get_current_zone(utc)
        assert z.name == "NY_PRIME"
        # Verify the UTC offset is -5
        et = utc.astimezone(ET)
        assert et.utcoffset() == timedelta(hours=-5)

    def test_summer_edt_ny_prime(self):
        """July = EDT (UTC-4). 10:30 ET = 14:30 UTC."""
        utc = _utc_from_et(2026, 7, 15, 10, 30)
        z = get_current_zone(utc)
        assert z.name == "NY_PRIME"
        et = utc.astimezone(ET)
        assert et.utcoffset() == timedelta(hours=-4)

    def test_dst_spring_forward_day(self):
        """March 8, 2026: clocks spring forward at 2 AM.
        09:30 ET should still be NY_OPEN_VOLATILITY."""
        utc = _utc_from_et(2026, 3, 8, 9, 30)
        z = get_current_zone(utc)
        assert z.name == "NY_OPEN_VOLATILITY"

    def test_dst_fall_back_day(self):
        """Nov 1, 2026: clocks fall back at 2 AM.
        09:30 ET should still be NY_OPEN_VOLATILITY."""
        utc = _utc_from_et(2026, 11, 1, 9, 30)
        z = get_current_zone(utc)
        assert z.name == "NY_OPEN_VOLATILITY"

    def test_utc_boundary_summer(self):
        """In EDT, AFTER_HOURS 16:00 ET = 20:00 UTC."""
        utc = datetime(2026, 7, 15, 20, 0, 0, tzinfo=timezone.utc)
        z = get_current_zone(utc)
        assert z.name == "AFTER_HOURS"

    def test_utc_boundary_winter(self):
        """In EST, AFTER_HOURS 16:00 ET = 21:00 UTC."""
        utc = datetime(2026, 1, 15, 21, 0, 0, tzinfo=timezone.utc)
        z = get_current_zone(utc)
        assert z.name == "AFTER_HOURS"


# ══════════════════════════════════════════════════════════════
# Spec Section 7 — exact boundary test scenarios
# ══════════════════════════════════════════════════════════════

class TestSpecBoundaries:
    """Test scenarios from spec Section 7."""
    DAY = (2026, 6, 15)

    def test_09_29_59_pre_market(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 9, 29, 59))
        assert z.name == "PRE_MARKET"

    def test_09_30_00_ny_open(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 9, 30, 0))
        assert z.name == "NY_OPEN_VOLATILITY"

    def test_12_00_00_lunch(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 12, 0, 0))
        assert z.name == "LUNCH"

    def test_15_45_00_close_final(self):
        z = get_current_zone(_utc_from_et(*self.DAY, 15, 45, 0))
        assert z.name == "CLOSE_FINAL"


# ══════════════════════════════════════════════════════════════
# Status output
# ══════════════════════════════════════════════════════════════

class TestKillzoneStatus:
    DAY = (2026, 6, 15)

    def test_status_schema_keys(self):
        s = get_killzone_status(_utc_from_et(*self.DAY, 10, 45))
        expected_keys = {
            "current_killzone", "killzone_id", "time_in_zone_min",
            "time_to_next_zone_min", "next_zone", "quality", "volatility",
            "sizing_modifier", "is_blocked", "block_reason", "is_trading_day",
            "session_phase",
        }
        assert set(s.keys()) == expected_keys

    def test_ny_prime_status(self):
        s = get_killzone_status(_utc_from_et(*self.DAY, 10, 53))
        assert s["current_killzone"] == "NY_PRIME"
        assert s["quality"] == "HIGH"
        assert s["volatility"] == "HIGH"
        assert s["sizing_modifier"] == 1.0
        assert s["is_blocked"] is False
        assert s["session_phase"] == "PRIME"
        assert s["next_zone"] == "PRE_LUNCH"
        assert s["time_in_zone_min"] == 23

    def test_lunch_blocked_default(self):
        s = get_killzone_status(_utc_from_et(*self.DAY, 12, 30))
        assert s["current_killzone"] == "LUNCH"
        assert s["is_blocked"] is True
        assert s["sizing_modifier"] == 0.0
        assert s["block_reason"] == "lunch_blocked"

    def test_lunch_unblocked_with_config(self):
        s = get_killzone_status(
            _utc_from_et(*self.DAY, 12, 30),
            trade_in_lunch=True,
        )
        assert s["current_killzone"] == "LUNCH"
        assert s["is_blocked"] is False
        assert s["sizing_modifier"] == 0.0  # quality LOW => still 0.0 sizing from zone

    def test_close_final_always_blocked(self):
        s = get_killzone_status(
            _utc_from_et(*self.DAY, 15, 50),
            trade_in_close=True,
        )
        assert s["is_blocked"] is True
        assert s["block_reason"] == "close_final"

    def test_holiday_blocks_all(self):
        s = get_killzone_status(
            _utc_from_et(*self.DAY, 10, 45),
            is_trading_day=False,
        )
        assert s["is_blocked"] is True
        assert s["block_reason"] == "holiday"
        assert s["sizing_modifier"] == 0.0

    def test_half_day_blocks_after_13(self):
        s = get_killzone_status(
            _utc_from_et(*self.DAY, 14, 0),
            is_holiday_half_day=True,
        )
        assert s["is_blocked"] is True
        assert s["block_reason"] == "half_day_closed"

    def test_half_day_ok_before_13(self):
        s = get_killzone_status(
            _utc_from_et(*self.DAY, 10, 45),
            is_holiday_half_day=True,
        )
        assert s["is_blocked"] is False

    def test_time_in_zone_minutes(self):
        # 15 minutes into NY_PRIME (10:30 + 15min = 10:45)
        s = get_killzone_status(_utc_from_et(*self.DAY, 10, 45))
        assert s["time_in_zone_min"] == 15

    def test_after_hours_status(self):
        s = get_killzone_status(_utc_from_et(*self.DAY, 20, 0))
        assert s["current_killzone"] == "AFTER_HOURS"
        assert s["is_blocked"] is True
        assert s["quality"] == "OFF"


# ══════════════════════════════════════════════════════════════
# Gate logic
# ══════════════════════════════════════════════════════════════

class TestGate:
    DAY = (2026, 6, 15)

    def test_gate_open_ny_prime(self):
        assert is_gate_open(_utc_from_et(*self.DAY, 10, 45)) is True

    def test_gate_closed_lunch(self):
        assert is_gate_open(_utc_from_et(*self.DAY, 12, 30)) is False

    def test_gate_closed_after_hours(self):
        assert is_gate_open(_utc_from_et(*self.DAY, 20, 0)) is False

    def test_gate_closed_close_final(self):
        assert is_gate_open(_utc_from_et(*self.DAY, 15, 50)) is False

    def test_gate_open_pre_market_low_quality(self):
        # PRE_MARKET quality=LOW, min_quality=LOW -> open
        assert is_gate_open(
            _utc_from_et(*self.DAY, 7, 0), min_quality="LOW"
        ) is True

    def test_gate_closed_pre_market_high_quality(self):
        # PRE_MARKET quality=LOW, min_quality=HIGH -> closed
        assert is_gate_open(
            _utc_from_et(*self.DAY, 7, 0), min_quality="HIGH"
        ) is False

    def test_gate_medium_quality_filter(self):
        # NY_OPEN_VOLATILITY quality=MEDIUM, min_quality=HIGH -> closed
        assert is_gate_open(
            _utc_from_et(*self.DAY, 9, 35), min_quality="HIGH"
        ) is False
        # min_quality=MEDIUM -> open
        assert is_gate_open(
            _utc_from_et(*self.DAY, 9, 35), min_quality="MEDIUM"
        ) is True

    def test_gate_holiday(self):
        assert is_gate_open(
            _utc_from_et(*self.DAY, 10, 45), is_trading_day=False
        ) is False

    def test_gate_lunch_override(self):
        assert is_gate_open(
            _utc_from_et(*self.DAY, 12, 30), trade_in_lunch=True
        ) is False  # Still false — sizing=0 for LUNCH zone

    def test_gate_block_first_15min(self):
        assert is_gate_open(
            _utc_from_et(*self.DAY, 9, 35),
            block_first_15min=True,
        ) is False


# ══════════════════════════════════════════════════════════════
# No gaps in zone coverage
# ══════════════════════════════════════════════════════════════

class TestCoverage:
    """Verify every minute of a 24-hour day maps to exactly one zone."""

    def test_full_day_coverage(self):
        """Walk every minute of June 15, 2026 and verify zone detection."""
        seen_zones = set()
        base = _utc_from_et(2026, 6, 15, 0, 0)
        for minute in range(24 * 60):
            t = base + timedelta(minutes=minute)
            z = get_current_zone(t)
            assert z is not None, f"No zone at minute {minute}"
            assert isinstance(z, Zone)
            seen_zones.add(z.name)

        # All 11 zones should appear (AFTER_HOURS covers 16:00-05:00)
        assert len(seen_zones) == 11, f"Missing zones: {set(z.name for z in ZONES) - seen_zones}"
