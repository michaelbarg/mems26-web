"""Tests for hydration infrastructure (D-077)."""

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/mems26_test.db")
os.environ.setdefault("BRIDGE_TOKEN", "test")

from backend.v9.systems.base.trading_system import HydrationResult, BaseV9TradingSystem, SystemType
from backend.v9.systems.day_type.hydration import hydrate_day_type
from backend.v9.services.bar_ingestion import BarIngestionService
from backend.v9.db.session import init_db


class TestHydrationResult:
    def test_success(self):
        r = HydrationResult(success=True, reached_state="READY", bars_replayed=50)
        assert r.success
        assert r.bars_replayed == 50

    def test_failure(self):
        r = HydrationResult(success=False, reached_state="ERROR", error="DB down")
        assert not r.success
        assert r.error == "DB down"

    def test_defaults(self):
        r = HydrationResult(success=True, reached_state="A1")
        assert r.confidence == 0.0
        assert r.notes == ""
        assert r.error is None


class TestBarIngestionService:
    def test_start_stop(self):
        svc = BarIngestionService()
        assert not svc.is_running
        svc.start()
        assert svc.is_running
        svc.stop()
        assert not svc.is_running

    def test_bars_in_db(self):
        init_db()
        svc = BarIngestionService()
        count = svc.bars_in_db
        assert isinstance(count, int)
        assert count >= 0


class TestDayTypeHydration:
    def test_hydrate_returns_result(self):
        init_db()
        result = hydrate_day_type()
        assert isinstance(result, HydrationResult)
        assert result.success is True
        # Fresh start — no prior state
        assert result.reached_state == "A1"

    def test_hydrate_idempotent(self):
        """Calling hydrate twice should not break state."""
        r1 = hydrate_day_type()
        r2 = hydrate_day_type()
        assert r1.success == r2.success
        assert r1.reached_state == r2.reached_state


class TestAbstractHydrateEnforced:
    def test_missing_hydrate_raises(self):
        """System without hydrate() cannot be instantiated."""
        import pytest
        with pytest.raises(TypeError):
            type("Bad", (BaseV9TradingSystem,), {
                "process": lambda self, e: None,
            })()

    def test_with_hydrate_works(self):
        sys = type("Good", (BaseV9TradingSystem,), {
            "system_id": 1, "name": "test",
            "process": lambda self, e: None,
            "hydrate": lambda self: HydrationResult(success=True, reached_state="OK"),
        })()
        assert sys.hydrate().success
