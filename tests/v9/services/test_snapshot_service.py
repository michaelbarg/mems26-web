"""CrossSystemSnapshotService tests — snapshot capture at trade events.

Tests: all systems available, partial availability, snapshot stored in trade,
snapshot structure validation.
"""

import json
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Set env before any backend imports
os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.v9.db.session import Base
from backend.v9.db.models.trades import V9Trade
from backend.v9.services.snapshot_service.snapshot import (
    CrossSystemSnapshotService,
    SYSTEM_NAMES,
    REDIS_KEY_TEMPLATE,
)
from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.trade_manager.events import TradeEventEmitter


# ── Sample system state fixtures ─────────────────────────────────

SAMPLE_STATES = {
    1: {
        "day_type": "TREND_UP",
        "confidence": 0.85,
        "classification_ts": "2026-05-10T14:00:00Z",
        "open_range": {"high": 5250.0, "low": 5240.0},
        "ib_range": {"high": 5255.0, "low": 5238.0},
        "rotation_count": 3,
    },
    2: {
        "active_patterns": ["BULL_FLAG"],
        "last_signal": {"direction": "LONG", "ts": "2026-05-10T14:20:00Z"},
        "current_bar": {"o": 5246.0, "h": 5247.25, "l": 5245.5, "c": 5246.75},
    },
    3: {
        "current_imbalance": "BUY",
        "absorption_signal": None,
        "zlr_signal": "LONG",
        "last_3_bars_delta": [120, -45, 200],
    },
    4: {
        "cci_value": 142.5,
        "trend_state": "BULL",
        "active_patterns": ["ZERO_LINE_REJECT"],
        "last_zero_line_cross": "2026-05-10T13:45:00Z",
    },
    5: {
        "poc": 5245.0,
        "vah": 5252.0,
        "val": 5238.0,
        "shape": "P_SHAPE",
        "current_price_zone": "ABOVE_POC",
    },
    6: {
        "active_zone": "US_OPEN",
        "intensity": 0.9,
        "minutes_into_zone": 25,
        "next_zone": "US_MID",
        "next_zone_in_minutes": 95,
    },
}

SAMPLE_MARKET = {
    "price": 5246.75,
    "volume_5min": 832,
    "ohlc_current_bar": {"o": 5246.0, "h": 5247.25, "l": 5245.5, "c": 5246.75},
}


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def mock_redis_full():
    """Redis mock that returns data for all 6 systems + market."""
    redis = MagicMock()

    def get_side_effect(key):
        # Check system keys
        for sys_id, name in SYSTEM_NAMES.items():
            if key == REDIS_KEY_TEMPLATE.format(name=name):
                return json.dumps(SAMPLE_STATES[sys_id]).encode("utf-8")
        # Check market key
        if key == "mems26:v9:market:latest":
            return json.dumps(SAMPLE_MARKET).encode("utf-8")
        return None

    redis.get.side_effect = get_side_effect
    return redis


@pytest.fixture
def mock_redis_partial():
    """Redis mock that returns data for systems 1, 2, 4 only."""
    redis = MagicMock()
    available = {1, 2, 4}

    def get_side_effect(key):
        for sys_id, name in SYSTEM_NAMES.items():
            if key == REDIS_KEY_TEMPLATE.format(name=name):
                if sys_id in available:
                    return json.dumps(SAMPLE_STATES[sys_id]).encode("utf-8")
                return None
        if key == "mems26:v9:market:latest":
            return json.dumps(SAMPLE_MARKET).encode("utf-8")
        return None

    redis.get.side_effect = get_side_effect
    return redis


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_setup():
    return {
        "firing_system": 2,
        "direction": "LONG",
        "stop": 5240.0,
        "t1": 5250.0,
        "t2": 5255.0,
        "t3": 5260.0,
    }


# ── Tests ────────────────────────────────────────────────────────

class TestCaptureAllSystems:
    """All 6 systems return data from Redis."""

    def test_all_systems_present(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry", firing_system_id=2)

        assert "systems" in snap
        for sys_id in range(1, 7):
            key = str(sys_id)
            assert key in snap["systems"], f"System {sys_id} missing"
            assert "status" not in snap["systems"][key], (
                f"System {sys_id} should have data, not status"
            )

    def test_system_1_day_type_fields(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry")
        sys1 = snap["systems"]["1"]
        assert sys1["day_type"] == "TREND_UP"
        assert sys1["confidence"] == 0.85

    def test_system_4_woodies_fields(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry")
        sys4 = snap["systems"]["4"]
        assert sys4["cci_value"] == 142.5
        assert sys4["trend_state"] == "BULL"

    def test_market_state_present(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry")
        assert "market" in snap
        assert snap["market"]["price"] == 5246.75

    def test_trigger_and_firing_system(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry", firing_system_id=2)
        assert snap["trigger"] == "entry"
        assert snap["firing_system_id"] == 2

    def test_captured_ts_present(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry")
        assert "captured_ts" in snap
        # Validate ISO format
        datetime.fromisoformat(snap["captured_ts"])


class TestPartialAvailability:
    """Some systems unavailable — snapshot still valid."""

    def test_unavailable_systems_marked(self, mock_redis_partial):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_partial)
        snap = svc.capture("entry", firing_system_id=1)

        # Systems 1, 2, 4 have data
        for sys_id in (1, 2, 4):
            assert "status" not in snap["systems"][str(sys_id)]

        # Systems 3, 5, 6 are unavailable
        for sys_id in (3, 5, 6):
            assert snap["systems"][str(sys_id)] == {"status": "unavailable"}

    def test_no_redis_all_unavailable(self):
        svc = CrossSystemSnapshotService(redis_client=None)
        snap = svc.capture("entry")

        for sys_id in range(1, 7):
            assert snap["systems"][str(sys_id)] == {"status": "unavailable"}
        assert snap["market"] == {"status": "unavailable"}

    def test_redis_connection_error(self):
        redis = MagicMock()
        redis.get.side_effect = ConnectionError("Redis down")
        svc = CrossSystemSnapshotService(redis_client=redis)
        snap = svc.capture("entry")

        for sys_id in range(1, 7):
            assert snap["systems"][str(sys_id)] == {"status": "unavailable"}

    def test_redis_returns_invalid_json(self):
        redis = MagicMock()
        redis.get.return_value = b"not-valid-json"
        svc = CrossSystemSnapshotService(redis_client=redis)
        snap = svc.capture("entry")

        for sys_id in range(1, 7):
            assert snap["systems"][str(sys_id)] == {"status": "unavailable"}

    def test_redis_returns_non_dict(self):
        redis = MagicMock()
        redis.get.return_value = json.dumps([1, 2, 3]).encode("utf-8")
        svc = CrossSystemSnapshotService(redis_client=redis)
        snap = svc.capture("entry")

        for sys_id in range(1, 7):
            assert snap["systems"][str(sys_id)] == {"status": "unavailable"}


class TestSnapshotStoredInTrade:
    """Integration: accept_setup stores snapshot in cross_context."""

    def _find_snapshot(self, ctx, trigger):
        for entry in ctx:
            if entry.get("trigger") == trigger:
                return entry
        return None

    def test_cross_context_populated_on_accept(self, db, mock_redis_full, sample_setup):
        snapshot_svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        emitter = TradeEventEmitter(redis_client=None)
        manager = TradeManager(
            db=db,
            event_emitter=emitter,
            snapshot_service=snapshot_svc,
        )

        trade_id = manager.accept_setup(sample_setup, "shadow")
        trade = db.query(V9Trade).filter(V9Trade.id == trade_id).first()

        assert trade.cross_context is not None
        ctx = trade.cross_context
        assert isinstance(ctx, list)
        # cross_context has setup metadata [0] + snapshot service output [1]
        assert len(ctx) >= 2
        snapshot = self._find_snapshot(ctx, "entry")
        assert snapshot is not None, f"No entry snapshot. Triggers: {[e.get('trigger') for e in ctx]}"
        assert snapshot["firing_system_id"] == 2
        assert "systems" in snapshot
        assert "1" in snapshot["systems"]

    def test_cross_context_has_all_six(self, db, mock_redis_full, sample_setup):
        snapshot_svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        emitter = TradeEventEmitter(redis_client=None)
        manager = TradeManager(
            db=db,
            event_emitter=emitter,
            snapshot_service=snapshot_svc,
        )

        trade_id = manager.accept_setup(sample_setup, "shadow")
        trade = db.query(V9Trade).filter(V9Trade.id == trade_id).first()

        snapshot = self._find_snapshot(trade.cross_context, "entry")
        assert snapshot is not None
        systems = snapshot["systems"]
        for sys_id in range(1, 7):
            assert str(sys_id) in systems

    def test_cross_context_without_snapshot_service(self, db, sample_setup):
        """TradeManager without snapshot_service still works (backward compat)."""
        emitter = TradeEventEmitter(redis_client=None)
        manager = TradeManager(db=db, event_emitter=emitter)

        trade_id = manager.accept_setup(sample_setup, "shadow")
        trade = db.query(V9Trade).filter(V9Trade.id == trade_id).first()

        # cross_context has setup metadata but no snapshot (no snapshot service)
        ctx = trade.cross_context
        assert isinstance(ctx, list)
        assert len(ctx) == 1  # only setup metadata, no snapshot
        assert ctx[0].get("trigger") == f"system_{sample_setup['firing_system']}"


class TestSnapshotStructure:
    """Verify required keys present in snapshot."""

    def test_top_level_keys(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry", firing_system_id=1)

        required = {"captured_ts", "trigger", "firing_system_id", "systems", "market"}
        assert required.issubset(snap.keys())

    def test_systems_keys_are_string_ids(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry")

        expected_keys = {"1", "2", "3", "4", "5", "6"}
        assert set(snap["systems"].keys()) == expected_keys

    def test_trigger_values(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        for trigger in ("entry", "t1_hit", "t2_hit", "t3_hit", "stop_hit", "close"):
            snap = svc.capture(trigger)
            assert snap["trigger"] == trigger

    def test_firing_system_nullable(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry", firing_system_id=None)
        assert snap["firing_system_id"] is None

    def test_snapshot_is_serializable(self, mock_redis_full):
        svc = CrossSystemSnapshotService(redis_client=mock_redis_full)
        snap = svc.capture("entry", firing_system_id=2)
        # Must be JSON-serializable for JSONB storage
        serialized = json.dumps(snap)
        deserialized = json.loads(serialized)
        assert deserialized == snap
