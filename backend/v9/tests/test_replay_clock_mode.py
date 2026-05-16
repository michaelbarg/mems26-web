"""Prompt 26a — Replay Clock Mode."""
import asyncio
from datetime import datetime, timezone

import pytest

from backend.v9.api.v9.clock_routes import get_clock_now
from backend.v9.common.session_classifier import Session, SessionClassifier
from backend.v9.services import market_clock
from backend.v9.services.bar_router import BarRouter
from backend.v9.systems.killzone.killzone_system import KillzoneSystem


@pytest.fixture(autouse=True)
def _reset_clock():
    market_clock.set_clock_mode("REALTIME")
    market_clock.reset_replay_timestamp()
    yield
    market_clock.set_clock_mode("REALTIME")
    market_clock.reset_replay_timestamp()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_realtime_mode_preserves_current_clock_behavior():
    state = market_clock.current_clock_state()

    assert state.mode == market_clock.ClockMode.REALTIME
    assert state.status == market_clock.ClockStatus.READY
    assert market_clock.now_et().tzinfo is not None
    assert market_clock.is_rth_open(datetime(2026, 5, 12, 14, 0, tzinfo=timezone.utc)) is True


def test_replay_mode_returns_latest_bar_timestamp_as_market_time():
    market_clock.set_clock_mode("REPLAY")
    market_clock.update_replay_timestamp("2026-05-12T14:00:00Z", source="test_bar")

    state = market_clock.current_clock_state()

    assert state.status == market_clock.ClockStatus.READY
    assert state.now_utc.isoformat() == "2026-05-12T14:00:00+00:00"
    assert state.now_et.hour == 10
    assert state.source == "test_bar"


def test_replay_mode_missing_timestamp_is_pending_not_realtime_fallback():
    market_clock.set_clock_mode("REPLAY")

    state = market_clock.current_clock_state()

    assert state.status == market_clock.ClockStatus.PENDING
    assert state.now_utc is None
    assert state.reason == "replay_clock_enabled_but_no_replay_timestamp"
    with pytest.raises(market_clock.MarketClockPendingError):
        market_clock.now_et()


def test_killzone_uses_replay_timestamp_in_replay_mode():
    market_clock.set_clock_mode("REPLAY")
    market_clock.update_replay_timestamp("2026-05-12T14:00:00Z")

    sys = KillzoneSystem()
    result = sys.hydrate()

    assert result.success is True
    assert sys.current_state["clock_mode"] == "REPLAY"
    assert sys.current_state["current_zone"]["name"] == "NY_OPEN"


def test_session_classifier_uses_replay_timestamp_in_replay_mode():
    market_clock.set_clock_mode("REPLAY")
    market_clock.update_replay_timestamp("2026-05-12T13:45:00Z")

    info = SessionClassifier().classify()

    assert info.session == Session.FIRST_HOUR
    assert info.et_time.hour == 9
    assert info.et_time.minute == 45


def test_day_type_session_minutes_use_replay_timestamp():
    market_clock.set_clock_mode("REPLAY")
    market_clock.update_replay_timestamp("2026-05-12T14:45:00Z")

    assert market_clock.minutes_since_rth_open() == 75


def test_bar_router_updates_replay_clock_and_tags_session_from_bar_timestamp():
    market_clock.set_clock_mode("REPLAY")
    router = BarRouter()
    received = []

    async def handler(event):
        received.append(event)

    router.subscribe("5min", handler)
    _run(router.publish("5min", {"bar_id": "r1", "ts": 1778592900.0, "close": 100}, mode="REPLAY"))

    state = market_clock.current_clock_state()
    assert state.status == market_clock.ClockStatus.READY
    assert state.now_et.hour == 9
    assert state.now_et.minute == 35
    assert state.source == "bar_router.5min"
    assert received[0].session == Session.FIRST_HOUR.value


def test_clock_endpoint_does_not_activate_shadow_demo_or_live():
    market_clock.set_clock_mode("REPLAY")
    market_clock.update_replay_timestamp("2026-05-12T14:00:00Z")

    response = get_clock_now()

    assert response["mode"] == "REPLAY"
    assert "shadow" not in response
    assert "demo" not in response
    assert "live" not in response
