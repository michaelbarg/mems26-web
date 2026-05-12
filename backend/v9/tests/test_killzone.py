"""Tests for KillzoneSystem."""
from datetime import datetime
import pytz
from backend.v9.systems.killzone.definitions import current_killzone, next_killzone, KILLZONES
from backend.v9.systems.killzone.killzone_system import KillzoneSystem
from backend.v9.systems.base.trading_system import BaseV9TradingSystem

ET = pytz.timezone('America/New_York')


def _et(h, m):
    return ET.localize(datetime(2026, 5, 12, h, m))


def test_ny_open_at_10am():
    cz = current_killzone(_et(10, 0))
    assert cz["name"] == "NY_OPEN"
    assert cz["edge_class"] == "high"


def test_asia_at_midnight():
    cz = current_killzone(_et(0, 30))
    assert cz["name"] == "ASIA"
    assert cz["edge_class"] == "low"


def test_asia_at_20():
    cz = current_killzone(_et(20, 0))
    assert cz["name"] == "ASIA"


def test_next_zone_from_midday():
    nz = next_killzone(_et(12, 0))
    assert nz["name"] == "NY_PM"
    assert nz["starts_in_minutes"] > 0


def test_minutes_remaining_positive():
    cz = current_killzone(_et(10, 0))
    assert cz["minutes_remaining"] > 0
    assert cz["minutes_remaining"] <= 360


def test_killzone_extends_base():
    assert issubclass(KillzoneSystem, BaseV9TradingSystem)


def test_killzone_hydrate():
    sys = KillzoneSystem()
    r = sys.hydrate()
    assert r.success
    assert sys.current_state["running"] is True


def test_killzone_no_bar_subscriptions():
    sys = KillzoneSystem()
    assert sys.subscribed_bar_types() == []
