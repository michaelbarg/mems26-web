"""Tests for BaseV9TradingSystem abstract class enforcement."""

import pytest
from backend.v9.systems.base.trading_system import BaseV9TradingSystem, SystemType, HydrationResult
from backend.v9.systems.base.context_provider import ContextProviderSystem
from backend.v9.systems.base.decision_maker import DecisionMakerSystem


def _make_system(**overrides):
    """Helper: create a minimal concrete system with hydrate() + process()."""
    attrs = {
        "system_id": 99,
        "name": "test",
        "system_type": SystemType.FIRING,
        "process": lambda self, event: None,
        "hydrate": lambda self: HydrationResult(success=True, reached_state="READY"),
        **overrides,
    }
    return type("TestSystem", (BaseV9TradingSystem,), attrs)()


class TestBaseV9TradingSystem:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseV9TradingSystem()

    def test_concrete_subclass_works(self):
        sys = _make_system(
            process=lambda self, event: {"event_type": "test.output", "data": event}
        )
        assert sys.system_id == 99
        result = sys.process({"price": 100})
        assert result["event_type"] == "test.output"

    def test_subscribe_returns_channels(self):
        sys = _make_system(
            subscribed_channels=["mems26:events:bar.5min", "mems26:events:price.tick"]
        )
        assert len(sys.subscribe()) == 2

    def test_persist_default_noop(self):
        sys = _make_system()
        sys.persist({"data": "test"})  # Should not raise

    def test_repr(self):
        sys = _make_system(system_id=1, name="day_type", system_type=SystemType.FIRING)
        assert "day_type" in repr(sys)
        assert "FIRING" in repr(sys)

    def test_hydrate_is_abstract(self):
        assert BaseV9TradingSystem.hydrate.__isabstractmethod__

    def test_hydrate_returns_result(self):
        sys = _make_system()
        result = sys.hydrate()
        assert isinstance(result, HydrationResult)
        assert result.success is True
        assert result.reached_state == "READY"

    def test_cannot_instantiate_without_hydrate(self):
        """A subclass that implements process() but NOT hydrate() should fail."""
        with pytest.raises(TypeError):
            type("Bad", (BaseV9TradingSystem,), {
                "process": lambda self, event: None,
            })()


class TestHydrationResult:
    def test_defaults(self):
        r = HydrationResult(success=True, reached_state="A1")
        assert r.bars_replayed == 0
        assert r.confidence == 0.0
        assert r.notes == ""
        assert r.error is None

    def test_failure(self):
        r = HydrationResult(success=False, reached_state="ERROR", error="DB unavailable")
        assert not r.success
        assert r.error == "DB unavailable"


class TestContextProviderSystem:
    def test_type_is_observing(self):
        assert ContextProviderSystem.system_type == SystemType.OBSERVING

    def test_concrete_subclass(self):
        sys = type("TPO", (ContextProviderSystem,), {
            "system_id": 5, "name": "tpo",
            "process": lambda self, e: None,
            "hydrate": lambda self: HydrationResult(success=True, reached_state="READY"),
        })()
        assert sys.system_type == SystemType.OBSERVING


class TestDecisionMakerSystem:
    def test_type_is_firing(self):
        assert DecisionMakerSystem.system_type == SystemType.FIRING

    def test_concrete_subclass(self):
        sys = type("FiveMin", (DecisionMakerSystem,), {
            "system_id": 2, "name": "five_min",
            "process": lambda self, e: {"direction": "LONG"},
            "hydrate": lambda self: HydrationResult(success=True, reached_state="READY"),
        })()
        assert sys.system_type == SystemType.FIRING
        assert sys.process({})["direction"] == "LONG"
