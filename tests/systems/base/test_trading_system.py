"""Tests for BaseV9TradingSystem abstract class enforcement."""

import pytest
from backend.v9.systems.base.trading_system import BaseV9TradingSystem, SystemType
from backend.v9.systems.base.context_provider import ContextProviderSystem
from backend.v9.systems.base.decision_maker import DecisionMakerSystem


class TestBaseV9TradingSystem:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseV9TradingSystem()

    def test_concrete_subclass_works(self):
        class TestSystem(BaseV9TradingSystem):
            system_id = 99
            name = "test"
            system_type = SystemType.FIRING

            def process(self, event):
                return {"event_type": "test.output", "data": event}

        sys = TestSystem()
        assert sys.system_id == 99
        assert sys.system_type == SystemType.FIRING
        result = sys.process({"price": 100})
        assert result["event_type"] == "test.output"

    def test_subscribe_returns_channels(self):
        class TestSystem(BaseV9TradingSystem):
            system_id = 1
            name = "test"
            subscribed_channels = ["mems26:events:bar.5min", "mems26:events:price.tick"]

            def process(self, event):
                return None

        sys = TestSystem()
        assert len(sys.subscribe()) == 2
        assert "mems26:events:bar.5min" in sys.subscribe()

    def test_persist_default_noop(self):
        class TestSystem(BaseV9TradingSystem):
            system_id = 1
            name = "test"

            def process(self, event):
                return None

        sys = TestSystem()
        sys.persist({"data": "test"})  # Should not raise

    def test_repr(self):
        class TestSystem(BaseV9TradingSystem):
            system_id = 1
            name = "day_type"
            system_type = SystemType.FIRING

            def process(self, event):
                return None

        sys = TestSystem()
        assert "day_type" in repr(sys)
        assert "FIRING" in repr(sys)


class TestContextProviderSystem:
    def test_type_is_observing(self):
        assert ContextProviderSystem.system_type == SystemType.OBSERVING

    def test_concrete_subclass(self):
        class TPOSystem(ContextProviderSystem):
            system_id = 5
            name = "tpo"

            def process(self, event):
                return None

        sys = TPOSystem()
        assert sys.system_type == SystemType.OBSERVING


class TestDecisionMakerSystem:
    def test_type_is_firing(self):
        assert DecisionMakerSystem.system_type == SystemType.FIRING

    def test_concrete_subclass(self):
        class FiveMinSystem(DecisionMakerSystem):
            system_id = 2
            name = "five_min"

            def process(self, event):
                return {"event_type": "system.five_min.setup", "direction": "LONG"}

        sys = FiveMinSystem()
        assert sys.system_type == SystemType.FIRING
        result = sys.process({"bar": {}})
        assert result["direction"] == "LONG"
