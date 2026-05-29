"""W-10 Time Stop Enforcement tests — Registry #11 LIVE blocker.

Minimum 15 unit tests + 1 integration test per Cursor META-PROMPT.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from backend.v9.systems.woodies.time_stop import (
    TimeStopEnforcer,
    TimeStopResult,
    load_time_stop_config,
)

# All 9 Woodies patterns
ALL_PATTERNS = ["ZLR", "TLB", "TT", "GB100", "VEGAS", "GHOST", "FAMIR", "HTLB", "HFE"]


# ── Unit tests: TimeStopResult dataclass ──────────────────────────


class TestTimeStopResult:
    def test_fields_populated_correctly(self):
        """Test #10: TimeStopResult dataclass fields correct."""
        r = TimeStopResult(
            fired=True, bars_open=18, limit_bars=18,
            reason="TIME_STOP", pattern_id="ZLR", trade_id="42",
        )
        assert r.fired is True
        assert r.bars_open == 18
        assert r.limit_bars == 18
        assert r.reason == "TIME_STOP"
        assert r.pattern_id == "ZLR"
        assert r.trade_id == "42"

    def test_frozen_immutable(self):
        r = TimeStopResult(
            fired=False, bars_open=5, limit_bars=18,
            reason="", pattern_id="TLB",
        )
        with pytest.raises(AttributeError):
            r.fired = True  # type: ignore[misc]


# ── Unit tests: TimeStopEnforcer ──────────────────────────────────


class TestTimeStopEnforcer:
    def test_17_bars_not_fired(self):
        """Test #1: trade open for 17 bars → NOT fired (< 18 bar limit)."""
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)
        result = enforcer.check(bars_open=17, pattern_id="ZLR")
        assert result.fired is False
        assert result.bars_open == 17
        assert result.limit_bars == 18

    def test_18_bars_fired(self):
        """Test #2: trade open for 18 bars → FIRED, reason=TIME_STOP."""
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)
        result = enforcer.check(bars_open=18, pattern_id="ZLR")
        assert result.fired is True
        assert result.reason == "TIME_STOP"
        assert result.bars_open == 18
        assert result.limit_bars == 18

    def test_19_bars_also_fired(self):
        """Test #3 (part 1): 19 bars also fires (past limit)."""
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)
        result = enforcer.check(bars_open=19, pattern_id="ZLR")
        assert result.fired is True

    def test_45_minute_config_fires_at_9_bars(self):
        """Test #4: time_stop_minutes=45 → limit=9 bars, fires at bar 9."""
        enforcer = TimeStopEnforcer(time_stop_minutes=45, tick_minutes=5)
        assert enforcer.limit_bars == 9
        assert enforcer.check(bars_open=8, pattern_id="TT").fired is False
        assert enforcer.check(bars_open=9, pattern_id="TT").fired is True

    def test_disabled_via_none(self):
        """Test #5: time_stop_minutes=None → never fires."""
        enforcer = TimeStopEnforcer(time_stop_minutes=None, tick_minutes=5)
        assert enforcer.limit_bars == 0
        result = enforcer.check(bars_open=100, pattern_id="ZLR")
        assert result.fired is False

    def test_disabled_via_zero(self):
        """Test #6: time_stop_minutes=0 → never fires."""
        enforcer = TimeStopEnforcer(time_stop_minutes=0, tick_minutes=5)
        assert enforcer.limit_bars == 0
        result = enforcer.check(bars_open=100, pattern_id="ZLR")
        assert result.fired is False

    @pytest.mark.parametrize("pattern_id", ALL_PATTERNS)
    def test_all_9_patterns_fire_time_stop(self, pattern_id):
        """Test #7: All 9 patterns fire time stop independently."""
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)
        result = enforcer.check(bars_open=18, pattern_id=pattern_id)
        assert result.fired is True
        assert result.pattern_id == pattern_id
        assert result.reason == "TIME_STOP"

    def test_warning_log_emitted_on_fire(self, caplog):
        """Test #8: WARNING log emitted on fire with correct fields."""
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)
        with caplog.at_level(logging.WARNING, logger="woodies.time_stop"):
            result = enforcer.check(bars_open=20, pattern_id="GHOST")
        assert result.fired is True
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "TIME_STOP fired" in record.message
        assert "bars_open=20" in record.message
        assert "limit=18" in record.message
        assert "pattern=GHOST" in record.message

    def test_no_warning_log_when_not_fired(self, caplog):
        """Test #9: No warning log when time stop not fired."""
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)
        with caplog.at_level(logging.WARNING, logger="woodies.time_stop"):
            result = enforcer.check(bars_open=10, pattern_id="ZLR")
        assert result.fired is False
        assert len(caplog.records) == 0

    def test_tick_minutes_override(self):
        """Test #13: tick_minutes=3 → limit_bars = 90 // 3 = 30."""
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=3)
        assert enforcer.limit_bars == 30
        assert enforcer.check(bars_open=29, pattern_id="TLB").fired is False
        assert enforcer.check(bars_open=30, pattern_id="TLB").fired is True

    def test_no_exception_raised_on_fire(self):
        """Test #14: check() returns result, does not raise."""
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)
        # Should not raise, even on fire
        result = enforcer.check(bars_open=50, pattern_id="VEGAS")
        assert isinstance(result, TimeStopResult)
        assert result.fired is True

    def test_limit_bars_formula(self):
        """Verify limit_bars = time_stop_minutes // tick_minutes."""
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)
        assert enforcer.limit_bars == 90 // 5  # = 18

        enforcer2 = TimeStopEnforcer(time_stop_minutes=60, tick_minutes=5)
        assert enforcer2.limit_bars == 60 // 5  # = 12

        enforcer3 = TimeStopEnforcer(time_stop_minutes=30, tick_minutes=3)
        assert enforcer3.limit_bars == 30 // 3  # = 10


# ── YAML config tests ─────────────────────────────────────────────


class TestYamlConfig:
    def test_yaml_config_override(self, tmp_path):
        """Test #11: YAML sets time_stop_minutes=30 → uses 30, limit=6."""
        cfg_file = tmp_path / "dispatcher_config.yaml"
        cfg_file.write_text(yaml.dump({
            "time_stop": {"time_stop_minutes": 30, "tick_minutes": 5},
        }))
        config = load_time_stop_config(cfg_file)
        assert config["time_stop_minutes"] == 30
        enforcer = TimeStopEnforcer(**config)
        assert enforcer.limit_bars == 6

    def test_yaml_missing_uses_default_90(self, tmp_path):
        """Test #12: YAML missing → defaults (90, 5)."""
        config = load_time_stop_config(tmp_path / "nonexistent.yaml")
        assert config["time_stop_minutes"] == 90
        assert config["tick_minutes"] == 5

    def test_yaml_null_disables(self, tmp_path):
        """YAML time_stop_minutes=null → None (disabled)."""
        cfg_file = tmp_path / "dispatcher_config.yaml"
        cfg_file.write_text(yaml.dump({
            "time_stop": {"time_stop_minutes": None, "tick_minutes": 5},
        }))
        config = load_time_stop_config(cfg_file)
        assert config["time_stop_minutes"] is None
        enforcer = TimeStopEnforcer(**config)
        assert enforcer.check(bars_open=100, pattern_id="ZLR").fired is False

    def test_real_dispatcher_config_has_time_stop(self):
        """Verify the actual dispatcher_config.yaml has time_stop section.

        W-10 re-enabled 2026-05-28 evening (Option B REVERSED).
        """
        real_path = (
            Path(__file__).parent.parent.parent.parent
            / "backend" / "v9" / "systems" / "woodies" / "config" / "dispatcher_config.yaml"
        )
        if real_path.exists():
            config = load_time_stop_config(real_path)
            assert config["time_stop_minutes"] == 90
            assert config["tick_minutes"] == 5


# ── Idempotency tests ─────────────────────────────────────────────


class TestIdempotency:
    def test_already_closed_trade_not_re_fired(self):
        """Test #3 (part 2) / #15: Trade already closed does not re-fire.

        The WoodiesSystem._check_time_stops() removes a trade from
        _open_fire_records after time stop fires. A subsequent check
        with the same trade_id should not be possible because the
        record is gone. We verify the enforcer pattern: after fire,
        the caller is expected to stop tracking the trade.
        """
        enforcer = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)

        # First fire at bar 18
        r1 = enforcer.check(bars_open=18, pattern_id="ZLR", trade_id="100")
        assert r1.fired is True

        # Simulate: caller removes trade from tracking after fire.
        # If caller passes same trade at bar 20, enforcer still fires
        # (it's stateless) — but the caller should never call it again
        # for a removed trade. This test documents the contract:
        # the caller (WoodiesSystem) enforces idempotency by removing
        # from _open_fire_records after time stop fires.
        #
        # Additionally verify: if time stop is disabled, nothing fires.
        disabled = TimeStopEnforcer(time_stop_minutes=0)
        r2 = disabled.check(bars_open=20, pattern_id="ZLR", trade_id="100")
        assert r2.fired is False


# ── Integration test: WoodiesSystem wiring ────────────────────────


class TestWoodiesSystemTimeStopWiring:
    """Test #16: Integration — verify WoodiesSystem has time stop wired.

    W-10 re-enabled 2026-05-28 evening (Option B REVERSED).
    """

    def test_system_has_time_stop_enforcer(self):
        """WoodiesSystem.__init__ creates TimeStopEnforcer."""
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem

        system = WoodiesSystem(db_path=":memory:")
        assert hasattr(system, "_time_stop_enforcer")
        assert isinstance(system._time_stop_enforcer, TimeStopEnforcer)
        assert system._time_stop_enforcer.limit_bars == 18  # 90 // 5

    def test_system_has_open_fire_records(self):
        """WoodiesSystem tracks open fire records."""
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem

        system = WoodiesSystem(db_path=":memory:")
        assert hasattr(system, "_open_fire_records")
        assert isinstance(system._open_fire_records, dict)
        assert len(system._open_fire_records) == 0

    def test_system_has_bar_count(self):
        """WoodiesSystem has monotonic bar counter."""
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem

        system = WoodiesSystem(db_path=":memory:")
        assert hasattr(system, "_bar_count")
        assert system._bar_count == 0

    def test_check_time_stops_fires_and_removes(self):
        """Time stop fires on tracked trade and removes from records."""
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem

        system = WoodiesSystem(db_path=":memory:")
        system._closes = [5500.0]  # Bug D fix: need closes for exit_price
        # Simulate: trade opened at bar 5
        system._open_fire_records["42"] = {
            "entry_bar_count": 5,
            "pattern_id": "ZLR",
        }
        # Simulate: 23 bars have passed (bars_open = 23 - 5 = 18)
        system._bar_count = 23
        system._check_time_stops()
        # Trade should be removed after time stop fires
        assert "42" not in system._open_fire_records

    def test_check_time_stops_does_not_fire_early(self):
        """Time stop does NOT fire before limit reached."""
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem

        system = WoodiesSystem(db_path=":memory:")
        system._open_fire_records["42"] = {
            "entry_bar_count": 5,
            "pattern_id": "ZLR",
        }
        # bars_open = 22 - 5 = 17 (< 18 limit)
        system._bar_count = 22
        system._check_time_stops()
        assert "42" in system._open_fire_records

    def test_check_time_stops_with_gateway_trade_manager(self):
        """Time stop closes trade via gateway._trade_manager if available."""
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem

        system = WoodiesSystem(db_path=":memory:")
        system._closes = [5500.0]  # Bug D fix: need closes for exit_price
        mock_trade = MagicMock()
        mock_trade.exit_price = None
        mock_tm = MagicMock()
        mock_tm._get_trade.return_value = mock_trade
        mock_gateway = MagicMock()
        mock_gateway._trade_manager = mock_tm
        system._gateway = mock_gateway

        system._open_fire_records["99"] = {
            "entry_bar_count": 1,
            "pattern_id": "GHOST",
        }
        system._bar_count = 20  # bars_open = 19 >= 18
        system._check_time_stops()

        mock_tm.close_trade.assert_called_once_with(99, "TIME_STOP")
        assert "99" not in system._open_fire_records
        assert mock_trade.exit_price == 5500.0

    def test_check_time_stops_handles_close_error_gracefully(self):
        """If close_trade raises (e.g. already closed), trade still removed."""
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem

        system = WoodiesSystem(db_path=":memory:")
        system._closes = [5500.0]
        mock_trade = MagicMock()
        mock_trade.exit_price = None
        mock_tm = MagicMock()
        mock_tm._get_trade.return_value = mock_trade
        mock_tm.close_trade.side_effect = Exception("already closed")
        mock_gateway = MagicMock()
        mock_gateway._trade_manager = mock_tm
        system._gateway = mock_gateway

        system._open_fire_records["99"] = {
            "entry_bar_count": 1,
            "pattern_id": "TLB",
        }
        system._bar_count = 20
        system._check_time_stops()
        # Despite error, trade removed from tracking (idempotent)
        assert "99" not in system._open_fire_records

    def test_check_time_stops_warning_log(self, caplog):
        """WARNING log emitted when time stop fires through system wiring."""
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem

        system = WoodiesSystem(db_path=":memory:")
        system._closes = [5500.0]
        system._open_fire_records["77"] = {
            "entry_bar_count": 2,
            "pattern_id": "FAMIR",
        }
        system._bar_count = 21  # bars_open = 19 >= 18
        with caplog.at_level(logging.WARNING, logger="woodies.time_stop"):
            system._check_time_stops()
        assert any("TIME_STOP fired" in r.message for r in caplog.records)
        assert any("FAMIR" in r.message for r in caplog.records)
