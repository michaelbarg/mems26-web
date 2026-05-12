"""Tests for 5-min system — hydration, mode transition, state."""

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/mems26_test.db")
os.environ.setdefault("BRIDGE_TOKEN", "test")

import pytest
from backend.v9.systems.five_min.five_min_system import FiveMinSystem, FiveMinMode
from backend.v9.systems.base.trading_system import HydrationResult, BaseV9TradingSystem
from backend.v9.db.session import init_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


class TestFiveMinSystemClass:
    def test_extends_base(self):
        assert issubclass(FiveMinSystem, BaseV9TradingSystem)

    def test_system_id(self):
        sys = FiveMinSystem()
        assert sys.system_id == 2
        assert sys.name == "five_min"
        assert sys.color == "#06b6d4"

    def test_hydrate_not_abstract(self):
        assert not getattr(FiveMinSystem.hydrate, '__isabstractmethod__', False)


class TestFiveMinHydration:
    def test_hydrate_returns_result(self):
        sys = FiveMinSystem()
        r = sys.hydrate()
        assert isinstance(r, HydrationResult)
        assert r.success is True

    def test_hydrate_idempotent(self):
        sys = FiveMinSystem()
        r1 = sys.hydrate()
        r2 = sys.hydrate()
        assert r1.reached_state == r2.reached_state

    def test_hydrate_sets_mode(self):
        sys = FiveMinSystem()
        sys.hydrate()
        assert sys.mode in [
            FiveMinMode.WAITING_OPEN,
            FiveMinMode.FIRST_HOUR_TACTICAL,
            FiveMinMode.DAY_TYPE_MODE,
            FiveMinMode.MARKET_CLOSED,
            FiveMinMode.LIVE_ONLY,
        ]

    def test_get_state_after_hydration(self):
        sys = FiveMinSystem()
        sys.hydrate()
        state = sys.get_state()
        assert "running" in state
        assert "mode" in state
        assert "hydrated" in state
        assert state["hydrated"] is True


class TestFiveMinProcess:
    def test_process_unknown_event(self):
        sys = FiveMinSystem()
        sys.hydrate()
        result = sys.process({"event_type": "unknown.event"})
        assert result is None

    def test_process_bar_increments_buffer(self):
        sys = FiveMinSystem()
        sys.hydrate()
        initial = sys.buffer_size
        sys.process({"event_type": "bar.5min", "open": 100, "close": 101})
        assert sys.buffer_size == initial + 1


class TestFiveMinModeTransition:
    def test_mode_transition_on_late_bar(self):
        """D-080: time-based transition at 10:30 ET."""
        sys = FiveMinSystem()
        sys.mode = FiveMinMode.FIRST_HOUR_TACTICAL
        sys._hydrated = True
        # Simulate a bar at 10:35 ET (ts in ms, ~1700000000000 range)
        # Use a timestamp that's clearly after 10:30 ET
        import time
        from datetime import datetime, timezone, timedelta
        et = timezone(timedelta(hours=-4))
        bar_time = datetime(2026, 5, 12, 10, 35, 0, tzinfo=et)
        ts_ms = int(bar_time.timestamp() * 1000)
        sys.process({"event_type": "bar.5min", "ts_ms": ts_ms})
        assert sys.mode == FiveMinMode.DAY_TYPE_MODE
