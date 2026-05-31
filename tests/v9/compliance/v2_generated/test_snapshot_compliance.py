"""V2 Audit — Snapshot compliance tests.

Verifies cross_context schema matches V1.1 spec exactly, and that
snapshots are captured at every trade event per Section 2.2.

Spec: MEMS26_SPEC_COMPLIANCE_AND_CROSS_SYSTEM_SNAPSHOT_LOCKED V1.1
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.v9.services.snapshot_service.snapshot import (
    CrossSystemSnapshotService,
    SYSTEM_NAMES,
    SYSTEM_FIELDS,
)
from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.trade_manager.state_machine import TradeState
from backend.v9.db.models.trades import V9Trade


# ── Fixtures ────────────────────────────────────────────────────────


def _make_redis_with_data():
    """Create a mock Redis with sample data for all 6 systems + market."""
    store = {
        "mems26:v9:day_type:latest": json.dumps({
            "day_type": "TREND_UP", "confidence": 0.85,
            "classification_ts": "2026-05-10T10:30:00Z",
            "open_range": {"high": 5250.0, "low": 5245.0},
            "ib_range": {"high": 5252.0, "low": 5244.0},
            "rotation_count": 3,
        }),
        "mems26:v9:five_min:latest": json.dumps({
            "active_patterns": ["3BR"], "last_signal": "LONG",
            "current_bar": {"o": 5246.0, "h": 5247.25, "l": 5245.5, "c": 5246.75},
        }),
        "mems26:v9:tick_reversal:latest": json.dumps({
            "current_imbalance": 1.2, "absorption_signal": "NONE",
            "zlr_signal": "NONE", "last_3_bars_delta": [10, -5, 8],
        }),
        "mems26:v9:woodies:latest": json.dumps({
            "cci_value": 45.3, "trend_state": "BULL",
            "active_patterns": ["ZLR"], "last_zero_line_cross": "2026-05-10T10:15:00Z",
        }),
        "mems26:v9:tpo:latest": json.dumps({
            "poc": 5248.0, "vah": 5253.0, "val": 5243.0,
            "shape": "NORMAL", "current_price_zone": "VALUE",
        }),
        "mems26:v9:killzone:latest": json.dumps({
            "active_zone": "NY_RTH_2", "intensity": "HIGH",
            "minutes_into_zone": 35, "next_zone": "NY_RTH_3",
            "next_zone_in_minutes": 25,
        }),
        "mems26:v9:market:latest": json.dumps({
            "price": 5246.75, "volume_5min": 832,
            "ohlc_current_bar": {"o": 5246.0, "h": 5247.25, "l": 5245.5, "c": 5246.75},
        }),
    }
    redis = MagicMock()
    redis.get.side_effect = lambda key: store.get(key)
    return redis


def _make_db_session():
    """Create a mock DB session that tracks trades by id."""
    session = MagicMock()
    trades = {}
    trade_counter = [0]

    def add(obj):
        pass

    def flush():
        # Assign id on first flush if not set
        for t in trades.values():
            pass

    session.add.side_effect = lambda obj: _register_trade(obj, trades, trade_counter)
    session.flush.side_effect = lambda: None
    session.query.return_value.filter.return_value.first.side_effect = lambda: None

    return session, trades


def _register_trade(obj, trades, counter):
    counter[0] += 1
    obj.id = counter[0]
    trades[obj.id] = obj


def _make_setup():
    return {
        "firing_system": 2,
        "direction": "LONG",
        "stop": 5240.0,
        "t1": 5250.0,
        "t2": 5255.0,
        "t3": 5260.0,
        "entry_price": 5246.0,
    }


# ── Task 1: cross_context schema compliance ─────────────────────────


class TestSnapshotSchema:
    """Verify CrossSystemSnapshotService.capture() output matches V1.1 spec."""

    def test_capture_returns_required_top_level_fields(self):
        """V1.1 Section 2.1: captured_ts, trigger, firing_system_id, systems, market."""
        redis = _make_redis_with_data()
        svc = CrossSystemSnapshotService(redis_client=redis)
        result = svc.capture("entry", firing_system_id=2)

        assert "captured_ts" in result, "Missing captured_ts"
        assert "trigger" in result, "Missing trigger"
        assert "firing_system_id" in result, "Missing firing_system_id"
        assert "systems" in result, "Missing systems"
        assert "market" in result, "Missing market"

    def test_capture_trigger_value_passthrough(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("t1_hit", firing_system_id=1)
        assert result["trigger"] == "t1_hit"

    def test_capture_firing_system_id_passthrough(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=4)
        assert result["firing_system_id"] == 4

    def test_captured_ts_is_iso_format(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        # Must parse as ISO datetime
        dt = datetime.fromisoformat(result["captured_ts"])
        assert dt.tzinfo is not None, "captured_ts must be timezone-aware"

    def test_all_6_system_keys_present(self):
        """V1.1 Section 2.1: systems dict must have keys '1' through '6'."""
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        systems = result["systems"]
        for i in range(1, 7):
            assert str(i) in systems, f"Missing system key '{i}'"

    def test_system_keys_are_string_ids(self):
        """Keys must be string '1'-'6', not int."""
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        for key in result["systems"]:
            assert isinstance(key, str), f"System key {key} should be string"

    def test_market_state_present_and_dict(self):
        """V1.1 Section 2.1: market state must be present."""
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        assert isinstance(result["market"], dict)

    def test_market_state_has_price_fields(self):
        """V1.1 Section 2.1: market has price, volume_5min, ohlc_current_bar."""
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        market = result["market"]
        assert "price" in market
        assert "volume_5min" in market
        assert "ohlc_current_bar" in market

    def test_unavailable_system_returns_status_dict(self):
        """If system has no data, returns {status: 'unavailable'}."""
        redis = MagicMock()
        redis.get.return_value = None
        svc = CrossSystemSnapshotService(redis_client=redis)
        result = svc.capture("entry", firing_system_id=2)
        for i in range(1, 7):
            assert result["systems"][str(i)] == {"status": "unavailable"}

    def test_no_redis_returns_unavailable(self):
        """If Redis client is None, all systems return unavailable."""
        svc = CrossSystemSnapshotService(redis_client=None)
        result = svc.capture("entry", firing_system_id=2)
        for i in range(1, 7):
            assert result["systems"][str(i)] == {"status": "unavailable"}
        assert result["market"] == {"status": "unavailable"}


class TestSystemFieldsSpec:
    """V1.1 Section 2.3: verify per-system state schemas match spec."""

    def test_system1_day_type_fields(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        sys1 = result["systems"]["1"]
        for field in ("day_type", "confidence", "classification_ts",
                      "open_range", "ib_range", "rotation_count"):
            assert field in sys1, f"System 1 missing field: {field}"

    def test_system2_five_min_fields(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        sys2 = result["systems"]["2"]
        for field in ("active_patterns", "last_signal", "current_bar"):
            assert field in sys2, f"System 2 missing field: {field}"

    def test_system3_tick_reversal_fields(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        sys3 = result["systems"]["3"]
        for field in ("current_imbalance", "absorption_signal",
                      "zlr_signal", "last_3_bars_delta"):
            assert field in sys3, f"System 3 missing field: {field}"

    def test_system4_woodies_fields(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        sys4 = result["systems"]["4"]
        for field in ("cci_value", "trend_state", "active_patterns",
                      "last_zero_line_cross"):
            assert field in sys4, f"System 4 missing field: {field}"

    def test_system5_tpo_fields(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        sys5 = result["systems"]["5"]
        for field in ("poc", "vah", "val", "shape", "current_price_zone"):
            assert field in sys5, f"System 5 missing field: {field}"

    def test_system6_killzone_fields(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        sys6 = result["systems"]["6"]
        for field in ("active_zone", "intensity", "minutes_into_zone",
                      "next_zone", "next_zone_in_minutes"):
            assert field in sys6, f"System 6 missing field: {field}"


# ── Task 2: Trace trade events — snapshot at each ───────────────────


class TestTradeEventSnapshotCapture:
    """Verify every trade event captures a cross-system snapshot."""

    def _make_manager(self):
        """Create a TradeManager with mock DB, emitter, and snapshot service."""
        redis = _make_redis_with_data()
        snapshot_svc = CrossSystemSnapshotService(redis_client=redis)

        db = MagicMock()
        trade_store = {}
        counter = [0]

        def mock_add(obj):
            counter[0] += 1
            obj.id = counter[0]
            trade_store[obj.id] = obj

        db.add.side_effect = mock_add
        db.flush.side_effect = lambda: None

        # Intercept query().filter().first() to look up from trade_store
        def mock_filter(*args):
            # Try to find the trade_id from the filter arg
            # Return a mock with .first() that searches trade_store
            result = MagicMock()
            # We use a closure trick: look at all trades, return the latest
            # The real filter uses V9Trade.id == trade_id, we check args
            result.first.side_effect = lambda: self._find_trade(trade_store, args)
            # For get_active_trades filter chain
            result.filter.return_value = result
            result.all.return_value = []
            return result

        db.query.return_value.filter.side_effect = mock_filter

        manager = TradeManager(
            db=db,
            event_emitter=MagicMock(),
            snapshot_service=snapshot_svc,
        )
        return manager, trade_store, db

    @staticmethod
    def _find_trade(trade_store, filter_args):
        """Extract trade_id from SQLAlchemy filter clause and look up."""
        if filter_args:
            clause = filter_args[0]
            try:
                # SQLAlchemy BinaryExpression: clause.right is BindParameter
                right = clause.right
                trade_id = getattr(right, 'value', None) or getattr(right, 'effective_value', None)
                if trade_id is not None and trade_id in trade_store:
                    return trade_store[trade_id]
            except (AttributeError, TypeError):
                pass
            # Try .in_() style (for get_active_trades)
            try:
                if hasattr(clause, 'clauses'):
                    # It's an in_() — return all matching
                    return None
            except (AttributeError, TypeError):
                pass
        # Fallback: return last trade added
        if trade_store:
            return list(trade_store.values())[-1]
        return None

    def _setup_trade(self, manager, trade_store, db):
        """Create and fill a trade, return trade_id."""
        setup = _make_setup()
        trade_id = manager.accept_setup(setup, "shadow")
        trade = trade_store[trade_id]

        # Fill it
        manager.on_fill(trade_id, 5246.0)
        return trade_id, trade

    def _find_snapshot(self, cross_context, trigger):
        """Find the snapshot entry with given trigger in cross_context list."""
        for entry in cross_context:
            if entry.get("trigger") == trigger:
                return entry
        return None

    def test_entry_captures_snapshot(self):
        """accept_setup must capture snapshot with trigger='entry'."""
        manager, trade_store, db = self._make_manager()
        setup = _make_setup()
        trade_id = manager.accept_setup(setup, "shadow")

        trade = trade_store[trade_id]
        assert trade.cross_context is not None, "cross_context not set at entry"
        assert isinstance(trade.cross_context, list), "cross_context must be array"
        assert len(trade.cross_context) >= 1, "cross_context must have entries"
        # cross_context[0] is setup metadata, [1] is snapshot service output
        snapshot = self._find_snapshot(trade.cross_context, "entry")
        assert snapshot is not None, \
            f"No entry snapshot found. Triggers: {[e.get('trigger') for e in trade.cross_context]}"

    def test_entry_snapshot_has_6_systems(self):
        manager, trade_store, db = self._make_manager()
        trade_id = manager.accept_setup(_make_setup(), "shadow")
        trade = trade_store[trade_id]
        snapshot = self._find_snapshot(trade.cross_context, "entry")
        assert snapshot is not None, "Entry snapshot not found"
        systems = snapshot["systems"]
        for i in range(1, 7):
            assert str(i) in systems, f"Entry snapshot missing system {i}"

    def test_entry_snapshot_has_market(self):
        manager, trade_store, db = self._make_manager()
        trade_id = manager.accept_setup(_make_setup(), "shadow")
        trade = trade_store[trade_id]
        snapshot = self._find_snapshot(trade.cross_context, "entry")
        assert snapshot is not None, "Entry snapshot not found"
        assert "market" in snapshot

    def test_t1_hit_captures_snapshot(self):
        """on_target_hit('T1') must append snapshot with trigger='t1_hit'."""
        manager, trade_store, db = self._make_manager()
        trade_id, trade = self._setup_trade(manager, trade_store, db)

        initial_count = len(trade.cross_context)
        manager.on_target_hit(trade_id, "T1")

        assert len(trade.cross_context) > initial_count, \
            "T1 hit did not append snapshot"
        # Find snapshot by trigger (state machine may also append transition logs)
        snapshot = self._find_snapshot(trade.cross_context, "t1_hit")
        assert snapshot is not None, \
            f"t1_hit snapshot not found. Triggers: {[e.get('trigger', 'N/A') for e in trade.cross_context]}"
        assert "systems" in snapshot
        assert "market" in snapshot

    def test_t2_hit_captures_snapshot(self):
        """on_target_hit('T2') must append snapshot with trigger='t2_hit'."""
        manager, trade_store, db = self._make_manager()
        trade_id, trade = self._setup_trade(manager, trade_store, db)

        manager.on_target_hit(trade_id, "T1")
        count_after_t1 = len(trade.cross_context)
        manager.on_target_hit(trade_id, "T2")

        assert len(trade.cross_context) > count_after_t1, \
            "T2 hit did not append snapshot"
        last = trade.cross_context[-1]
        assert last["trigger"] == "t2_hit"

    def test_t3_hit_captures_snapshot(self):
        """on_target_hit('T3') must append snapshot with trigger='t3_hit'."""
        manager, trade_store, db = self._make_manager()
        trade_id, trade = self._setup_trade(manager, trade_store, db)

        manager.on_target_hit(trade_id, "T1")
        manager.on_target_hit(trade_id, "T2")
        count_after_t2 = len(trade.cross_context)
        manager.on_target_hit(trade_id, "T3")

        assert len(trade.cross_context) > count_after_t2, \
            "T3 hit did not append snapshot"
        last = trade.cross_context[-1]
        assert last["trigger"] == "t3_hit"

    def test_stop_hit_captures_snapshot(self):
        """on_stop_hit must append snapshot with trigger='stop_hit'."""
        manager, trade_store, db = self._make_manager()
        trade_id, trade = self._setup_trade(manager, trade_store, db)

        initial_count = len(trade.cross_context)
        manager.on_stop_hit(trade_id)

        assert len(trade.cross_context) > initial_count, \
            "Stop hit did not append snapshot"
        last = trade.cross_context[-1]
        assert last["trigger"] == "stop_hit"
        assert "systems" in last

    def test_close_captures_snapshot(self):
        """close_trade must append snapshot with trigger='close'."""
        manager, trade_store, db = self._make_manager()
        trade_id, trade = self._setup_trade(manager, trade_store, db)

        initial_count = len(trade.cross_context)
        manager.close_trade(trade_id, "MANUAL")

        assert len(trade.cross_context) > initial_count, \
            "Close did not append snapshot"
        last = trade.cross_context[-1]
        assert last["trigger"] == "close"

    def test_full_lifecycle_accumulates_snapshots(self):
        """Full trade: setup_meta + entry + T1 + T2 + T3 snapshots accumulated."""
        manager, trade_store, db = self._make_manager()
        trade_id, trade = self._setup_trade(manager, trade_store, db)

        manager.on_target_hit(trade_id, "T1")
        manager.on_target_hit(trade_id, "T2")
        manager.on_target_hit(trade_id, "T3")

        # cross_context accumulates: setup_meta + entry_snapshot + t1 + t2 + t3
        # Verify all expected triggers are present (order may vary for meta)
        triggers = [s.get("trigger") for s in trade.cross_context]
        for expected in ("entry", "t1_hit", "t2_hit", "t3_hit"):
            assert expected in triggers, \
                f"Expected trigger '{expected}' in {triggers}"


# ── Task 3: DB model integrity checks ──────────────────────────────


class TestV9TradeModel:
    """Verify V9Trade model column definitions match spec."""

    def test_cross_context_field_exists(self):
        assert hasattr(V9Trade, "cross_context"), "V9Trade missing cross_context"

    def test_cross_context_is_json_type(self):
        from sqlalchemy import JSON
        col = V9Trade.__table__.columns["cross_context"]
        # JsonColumn is JSON with JSONB variant
        assert isinstance(col.type, JSON), \
            f"cross_context should be JSON/JSONB, got {type(col.type)}"

    def test_mode_not_nullable(self):
        col = V9Trade.__table__.columns["mode"]
        assert col.nullable is False, "mode must be NOT NULL"

    def test_firing_system_not_nullable(self):
        col = V9Trade.__table__.columns["firing_system"]
        assert col.nullable is False, "firing_system must be NOT NULL"

    def test_direction_not_nullable(self):
        col = V9Trade.__table__.columns["direction"]
        assert col.nullable is False, "direction must be NOT NULL"

    def test_state_not_nullable(self):
        col = V9Trade.__table__.columns["state"]
        assert col.nullable is False, "state must be NOT NULL"

    def test_state_has_default(self):
        col = V9Trade.__table__.columns["state"]
        assert col.default is not None, "state must have default value"

    def test_required_bracket_fields_exist(self):
        """Per 3-Mode spec Section 6: stop, T1, T2, T3 are per-trade fields."""
        for name in ("stop", "t1", "t2", "t3"):
            assert name in V9Trade.__table__.columns, f"Missing column: {name}"

    def test_timestamp_columns_are_timezone_aware(self):
        """entry_ts, exit_ts, created_at, updated_at should be tz-aware."""
        for name in ("entry_ts", "exit_ts", "created_at", "updated_at"):
            col = V9Trade.__table__.columns[name]
            assert col.type.timezone is True, \
                f"{name} must be timezone-aware DateTime"

    def test_pnl_fields_exist(self):
        for name in ("pnl_usd", "pnl_r"):
            assert name in V9Trade.__table__.columns, f"Missing column: {name}"


# ── SYSTEM_NAMES mapping integrity ──────────────────────────────────


class TestSystemNamesMapping:
    """Verify SYSTEM_NAMES matches MASTER_DEV_SKILL naming."""

    def test_has_6_systems(self):
        assert len(SYSTEM_NAMES) == 6

    def test_system_1_is_day_type(self):
        assert SYSTEM_NAMES[1] == "day_type"

    def test_system_2_is_five_min(self):
        assert SYSTEM_NAMES[2] == "five_min"

    def test_system_3_is_tick_reversal(self):
        assert SYSTEM_NAMES[3] == "tick_reversal"

    def test_system_4_is_woodies(self):
        assert SYSTEM_NAMES[4] == "woodies"

    def test_system_5_is_tpo(self):
        assert SYSTEM_NAMES[5] == "tpo"

    def test_system_6_is_killzone(self):
        assert SYSTEM_NAMES[6] == "killzone"
