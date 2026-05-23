"""Tests for EventDispatcher — Phase A.1-A.3 routing layer.

Coverage targets:
- register_system: systems added to routing table
- route_bar_to_correct_system: woodies bar goes to WoodiesSystem only
- multiple_subscribers: cumulative_delta goes to day_type AND chart_5min
- signal_forwarded_to_gateway: mock gateway receives signal
- observer_no_trade_signal: tick_reversal analyze returns None
- unknown_stream_ignored: bar for unknown stream does not crash
- system_error_doesnt_crash_dispatcher: one system throws, others still receive
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from backend.v9.systems.base_system import BaseSystem, Signal
from backend.v9.services.event_dispatcher.dispatcher import EventDispatcher


# ── Test fixtures ───────────────────────────────────────────────


class FiringSystemStub(BaseSystem):
    """Stub firing system that returns a Signal on analyze()."""
    subscribed_streams = ["woodies_5min"]
    system_id = 4
    name = "woodies_stub"

    def __init__(self, signal: Optional[Signal] = None):
        self._signal = signal
        self.calls: List[tuple] = []

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        self.calls.append((stream_name, bar))
        return self._signal


class ObserverStub(BaseSystem):
    """Stub observer that always returns None."""
    subscribed_streams = ["tick_reversal_15", "tick_reversal_12", "footprint"]
    system_id = 3
    name = "tick_reversal_stub"

    def __init__(self):
        self.calls: List[tuple] = []

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        self.calls.append((stream_name, bar))
        return None


class MultiStreamStub(BaseSystem):
    """Stub system subscribed to cumulative_delta."""
    subscribed_streams = ["cumulative_delta"]
    system_id = 1
    name = "day_type_stub"

    def __init__(self):
        self.calls: List[tuple] = []

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        self.calls.append((stream_name, bar))
        return None


class MultiStreamStub2(BaseSystem):
    """Second stub also subscribed to cumulative_delta."""
    subscribed_streams = ["cumulative_delta"]
    system_id = 2
    name = "chart_5min_stub"

    def __init__(self):
        self.calls: List[tuple] = []

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        self.calls.append((stream_name, bar))
        return None


class CrashingSystem(BaseSystem):
    """System that always raises an exception."""
    subscribed_streams = ["cumulative_delta"]
    system_id = 99
    name = "crashing_stub"

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        raise RuntimeError("intentional test crash")


class GateStub(BaseSystem):
    """Stub gate system with no subscribed streams."""
    subscribed_streams = []
    system_id = 6
    name = "killzone_stub"

    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        return None


# ── Tests ───────────────────────────────────────────────────────


class TestRegisterSystem:
    """test_register_system: systems added to routing table."""

    def test_single_system_registered(self):
        dispatcher = EventDispatcher()
        system = FiringSystemStub()
        dispatcher.register_system(system)

        table = dispatcher.get_routing_table()
        assert "woodies_5min" in table
        assert 4 in table["woodies_5min"]

    def test_multiple_systems_registered(self):
        dispatcher = EventDispatcher()
        dispatcher.register_system(FiringSystemStub())
        dispatcher.register_system(ObserverStub())

        table = dispatcher.get_routing_table()
        assert 4 in table["woodies_5min"]
        assert 3 in table["tick_reversal_15"]
        assert 3 in table["tick_reversal_12"]
        assert 3 in table["footprint"]

    def test_registered_systems_dict(self):
        dispatcher = EventDispatcher()
        dispatcher.register_system(FiringSystemStub())
        dispatcher.register_system(ObserverStub())

        systems = dispatcher.get_registered_systems()
        assert systems[4] == "woodies_stub"
        assert systems[3] == "tick_reversal_stub"

    def test_duplicate_registration_skipped(self):
        dispatcher = EventDispatcher()
        system = FiringSystemStub()
        dispatcher.register_system(system)
        dispatcher.register_system(system)

        table = dispatcher.get_routing_table()
        assert len(table["woodies_5min"]) == 1

    def test_gate_no_streams(self):
        dispatcher = EventDispatcher()
        dispatcher.register_system(GateStub())

        table = dispatcher.get_routing_table()
        # No streams in table for gate system
        assert len(table) == 0
        # But it is registered
        assert 6 in dispatcher.get_registered_systems()


class TestRouteBarToCorrectSystem:
    """test_route_bar_to_correct_system: woodies bar goes to WoodiesSystem only."""

    def test_woodies_bar_only_to_woodies(self):
        dispatcher = EventDispatcher()
        woodies = FiringSystemStub()
        observer = ObserverStub()
        dispatcher.register_system(woodies)
        dispatcher.register_system(observer)

        bar = {"ts": 1234, "o": 100, "h": 101, "l": 99, "c": 100.5}
        dispatcher.on_bar_received("woodies_5min", bar)

        assert len(woodies.calls) == 1
        assert woodies.calls[0] == ("woodies_5min", bar)
        assert len(observer.calls) == 0

    def test_tick_reversal_bar_only_to_tick_reversal(self):
        dispatcher = EventDispatcher()
        woodies = FiringSystemStub()
        observer = ObserverStub()
        dispatcher.register_system(woodies)
        dispatcher.register_system(observer)

        bar = {"ts": 1234, "o": 100, "h": 101, "l": 99, "c": 100.5}
        dispatcher.on_bar_received("tick_reversal_15", bar)

        assert len(woodies.calls) == 0
        assert len(observer.calls) == 1
        assert observer.calls[0] == ("tick_reversal_15", bar)


class TestMultipleSubscribers:
    """test_multiple_subscribers: cumulative_delta goes to day_type AND chart_5min."""

    def test_cumulative_delta_to_both_systems(self):
        dispatcher = EventDispatcher()
        sys1 = MultiStreamStub()
        sys2 = MultiStreamStub2()
        dispatcher.register_system(sys1)
        dispatcher.register_system(sys2)

        bar = {"ts": 5678, "delta": 42.0}
        dispatcher.on_bar_received("cumulative_delta", bar)

        assert len(sys1.calls) == 1
        assert len(sys2.calls) == 1
        assert sys1.calls[0] == ("cumulative_delta", bar)
        assert sys2.calls[0] == ("cumulative_delta", bar)

    def test_routing_table_shows_both(self):
        dispatcher = EventDispatcher()
        dispatcher.register_system(MultiStreamStub())
        dispatcher.register_system(MultiStreamStub2())

        table = dispatcher.get_routing_table()
        assert sorted(table["cumulative_delta"]) == [1, 2]


class TestSignalForwardedToGateway:
    """test_signal_forwarded_to_gateway: mock gateway receives signal."""

    def test_signal_forwarded(self):
        mock_gateway = MagicMock()
        dispatcher = EventDispatcher(gateway=mock_gateway)

        signal = Signal(
            system_id=4,
            classification="ZLR",
            direction="LONG",
            confidence=0.85,
            entry_price=5100.0,
            stop=5095.0,
            targets=[5105.0, 5110.0, 5115.0],
        )
        system = FiringSystemStub(signal=signal)
        dispatcher.register_system(system)

        dispatcher.on_bar_received("woodies_5min", {"ts": 1})

        mock_gateway.route_setup.assert_called_once()
        call_args = mock_gateway.route_setup.call_args
        setup = call_args[0][0]
        sys_id = call_args[0][1]

        assert sys_id == 4
        assert setup["firing_system"] == 4
        assert setup["direction"] == "LONG"
        assert setup["stop"] == 5095.0
        assert setup["t1"] == 5105.0
        assert setup["t2"] == 5110.0
        assert setup["t3"] == 5115.0

    def test_no_gateway_no_crash(self):
        dispatcher = EventDispatcher(gateway=None)
        signal = Signal(
            system_id=4, classification="ZLR", direction="LONG", confidence=0.8,
        )
        system = FiringSystemStub(signal=signal)
        dispatcher.register_system(system)

        # Should not raise
        signals = dispatcher.on_bar_received("woodies_5min", {"ts": 1})
        assert len(signals) == 1

    def test_gateway_error_doesnt_crash(self):
        mock_gateway = MagicMock()
        mock_gateway.route_setup.side_effect = RuntimeError("gateway down")
        dispatcher = EventDispatcher(gateway=mock_gateway)

        signal = Signal(
            system_id=4, classification="ZLR", direction="LONG", confidence=0.8,
        )
        system = FiringSystemStub(signal=signal)
        dispatcher.register_system(system)

        # Should not raise even though gateway errors
        signals = dispatcher.on_bar_received("woodies_5min", {"ts": 1})
        assert len(signals) == 1

    def test_signal_returned_in_list(self):
        dispatcher = EventDispatcher()
        signal = Signal(
            system_id=4, classification="ZLR", direction="SHORT", confidence=0.75,
        )
        system = FiringSystemStub(signal=signal)
        dispatcher.register_system(system)

        result = dispatcher.on_bar_received("woodies_5min", {"ts": 1})
        assert len(result) == 1
        assert result[0].direction == "SHORT"
        assert result[0].classification == "ZLR"


class TestObserverNoTradeSignal:
    """test_observer_no_trade_signal: tick_reversal analyze returns markers not trade signals."""

    def test_observer_returns_none(self):
        dispatcher = EventDispatcher()
        observer = ObserverStub()
        dispatcher.register_system(observer)

        result = dispatcher.on_bar_received("tick_reversal_15", {"ts": 1})
        assert result == []
        assert len(observer.calls) == 1

    def test_observer_no_gateway_call(self):
        mock_gateway = MagicMock()
        dispatcher = EventDispatcher(gateway=mock_gateway)
        observer = ObserverStub()
        dispatcher.register_system(observer)

        dispatcher.on_bar_received("footprint", {"ts": 1})
        mock_gateway.route_setup.assert_not_called()


class TestUnknownStreamIgnored:
    """test_unknown_stream_ignored: bar for unknown stream does not crash."""

    def test_unknown_stream_empty_result(self):
        dispatcher = EventDispatcher()
        dispatcher.register_system(FiringSystemStub())

        # "nonexistent_stream" is not subscribed by anyone
        result = dispatcher.on_bar_received("nonexistent_stream", {"ts": 1})
        assert result == []

    def test_empty_dispatcher_no_crash(self):
        dispatcher = EventDispatcher()
        result = dispatcher.on_bar_received("anything", {"ts": 1})
        assert result == []


class TestSystemErrorDoesntCrashDispatcher:
    """test_system_error_doesnt_crash_dispatcher: one system throws, others still receive."""

    def test_crashing_system_doesnt_stop_others(self):
        dispatcher = EventDispatcher()
        crashing = CrashingSystem()
        healthy = MultiStreamStub()
        healthy2 = MultiStreamStub2()

        dispatcher.register_system(crashing)
        dispatcher.register_system(healthy)
        dispatcher.register_system(healthy2)

        bar = {"ts": 999}
        # Should not raise despite crashing system
        result = dispatcher.on_bar_received("cumulative_delta", bar)

        # Both healthy systems received the bar
        assert len(healthy.calls) == 1
        assert len(healthy2.calls) == 1
        assert result == []

    def test_error_logged(self, caplog):
        dispatcher = EventDispatcher()
        dispatcher.register_system(CrashingSystem())

        import logging
        with caplog.at_level(logging.ERROR):
            dispatcher.on_bar_received("cumulative_delta", {"ts": 1})

        assert any("error in system 99" in r.message for r in caplog.records)


class TestThreadSafety:
    """Verify dispatcher handles concurrent bar arrivals."""

    def test_concurrent_dispatch(self):
        dispatcher = EventDispatcher()
        sys1 = MultiStreamStub()
        sys2 = MultiStreamStub2()
        dispatcher.register_system(sys1)
        dispatcher.register_system(sys2)

        errors = []

        def send_bars(count, offset):
            try:
                for i in range(count):
                    dispatcher.on_bar_received(
                        "cumulative_delta", {"ts": offset + i}
                    )
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=send_bars, args=(50, 0)),
            threading.Thread(target=send_bars, args=(50, 1000)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(sys1.calls) == 100
        assert len(sys2.calls) == 100


class TestSignalDataclass:
    """Verify Signal dataclass fields."""

    def test_signal_defaults(self):
        sig = Signal(
            system_id=1,
            classification="TREND_DAY",
            direction="LONG",
            confidence=0.9,
        )
        assert sig.entry_price is None
        assert sig.stop is None
        assert sig.targets is None
        assert sig.metadata == {}

    def test_signal_full(self):
        sig = Signal(
            system_id=4,
            classification="ZLR",
            direction="SHORT",
            confidence=0.85,
            entry_price=5100.0,
            stop=5105.0,
            targets=[5095.0, 5090.0, 5085.0],
            metadata={"pattern_id": "ZLR"},
        )
        assert sig.targets[0] == 5095.0
        assert sig.metadata["pattern_id"] == "ZLR"


class TestBaseSystemContract:
    """Verify BaseSystem ABC contract."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseSystem()

    def test_stub_implements_contract(self):
        system = FiringSystemStub()
        assert hasattr(system, "subscribed_streams")
        assert hasattr(system, "system_id")
        assert hasattr(system, "name")
        assert hasattr(system, "analyze")


class TestRealWrappers:
    """Integration tests with the actual system wrappers (import verification)."""

    def test_all_wrappers_import(self):
        from backend.v9.systems.wrappers import (
            DayTypeSystem, TickReversalSystem,
            WoodiesSystem, TPOSystem, KillzoneSystem,
        )
        systems = [
            DayTypeSystem(),
            TickReversalSystem(),
            WoodiesSystem(),
            TPOSystem(),
            KillzoneSystem(),
        ]
        for s in systems:
            assert isinstance(s, BaseSystem)
            assert s.system_id > 0
            assert s.name != ""

    def test_wrapper_subscriptions(self):
        from backend.v9.systems.wrappers import (
            DayTypeSystem, TickReversalSystem,
            WoodiesSystem, TPOSystem, KillzoneSystem,
        )
        assert DayTypeSystem.subscribed_streams == ["cumulative_delta", "volume_profile"]
        assert TickReversalSystem.subscribed_streams == ["tick_reversal_15", "tick_reversal_12", "footprint"]
        assert WoodiesSystem.subscribed_streams == ["woodies_5min"]
        assert TPOSystem.subscribed_streams == ["volume_profile"]
        assert KillzoneSystem.subscribed_streams == []

    def test_full_dispatcher_wiring(self):
        from backend.v9.systems.wrappers import (
            DayTypeSystem, TickReversalSystem,
            WoodiesSystem, TPOSystem, KillzoneSystem,
        )
        dispatcher = EventDispatcher()
        for sys_cls in [DayTypeSystem, TickReversalSystem,
                        WoodiesSystem, TPOSystem, KillzoneSystem]:
            dispatcher.register_system(sys_cls())

        table = dispatcher.get_routing_table()
        assert table["cumulative_delta"] == [1]
        assert sorted(table["volume_profile"]) == [1, 5]
        assert table["woodies_5min"] == [4]
        assert table["tick_reversal_15"] == [3]
        assert table["tick_reversal_12"] == [3]
        assert table["footprint"] == [3]

        registered = dispatcher.get_registered_systems()
        assert len(registered) == 5

    def test_observer_returns_none_on_real_bar(self):
        from backend.v9.systems.wrappers import TickReversalSystem
        sys = TickReversalSystem()
        result = sys.analyze("tick_reversal_15", {
            "ts": "1234567890", "o": 100, "h": 101, "l": 99, "c": 100.5,
            "vol": 50, "ask_vol": 30, "bid_vol": 20,
        })
        assert result is None

    def test_gate_returns_none(self):
        from backend.v9.systems.wrappers import KillzoneSystem
        sys = KillzoneSystem()
        result = sys.analyze("anything", {})
        assert result is None

    def test_tpo_returns_none(self):
        from backend.v9.systems.wrappers import TPOSystem
        sys = TPOSystem()
        result = sys.analyze("volume_profile", {
            "ts": 123, "bars": [{"poc_vol": 100, "vah": 5100, "val": 5090}],
        })
        assert result is None
