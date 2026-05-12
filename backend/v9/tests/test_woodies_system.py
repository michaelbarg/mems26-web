"""Tests for WoodiesSystem."""
from backend.v9.systems.woodies.cci import cci, typical_price


def test_typical_price():
    bar = {"high": 102, "low": 98, "close": 100}
    assert typical_price(bar) == 100


def test_cci_insufficient_bars():
    bars = [{"high": 100, "low": 99, "close": 99.5}]
    assert cci(bars, period=14) is None


def test_cci_with_enough_bars():
    bars = [{"high": 100 + i * 0.5, "low": 99 + i * 0.5, "close": 99.5 + i * 0.5} for i in range(20)]
    v = cci(bars, period=14)
    assert v is not None
    assert v > 0


def test_cci_zero_volatility():
    bars = [{"high": 100, "low": 100, "close": 100} for _ in range(20)]
    v = cci(bars, period=14)
    assert v == 0.0


def test_woodies_hydrate():
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    sys = WoodiesSystem()
    r = sys.hydrate()
    assert r.success


def test_woodies_zlc_signal_detected():
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    sys = WoodiesSystem()
    signal_type, direction, strength = sys._classify_signal(current=10, previous=-5)
    assert signal_type == "ZLC_BULL"
    assert direction == "LONG"
    assert strength == 3


def test_woodies_zlc_bear():
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    sys = WoodiesSystem()
    signal_type, direction, strength = sys._classify_signal(current=-10, previous=5)
    assert signal_type == "ZLC_BEAR"
    assert direction == "SHORT"


def test_woodies_extends_base():
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    from backend.v9.systems.base.trading_system import BaseV9TradingSystem
    assert issubclass(WoodiesSystem, BaseV9TradingSystem)


def test_woodies_subscribes():
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    sys = WoodiesSystem()
    assert "5min" in sys.subscribed_bar_types()
    assert "tick_reversal_15" in sys.subscribed_bar_types()
