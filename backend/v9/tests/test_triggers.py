"""TriggerDispatcher tests — 6 scenarios per trigger type."""

from backend.v9.systems.day_type.triggers import (
    TriggerDispatcher, TriggerEvent, TriggerType,
)


def _make_dispatcher_with_log():
    """Helper: create dispatcher + log list for captured events."""
    log = []
    d = TriggerDispatcher()
    return d, log


def test_bar_close_dispatches():
    """BAR_CLOSE trigger routes to registered handler."""
    d, log = _make_dispatcher_with_log()
    d.register(TriggerType.BAR_CLOSE, lambda e: log.append(e))
    result = d.on_bar_close(ts=1000.0, payload={"close": 7500})
    assert result is True
    assert len(log) == 1
    assert log[0].trigger_type == TriggerType.BAR_CLOSE
    assert log[0].payload == {"close": 7500}


def test_periodic_respects_interval():
    """PERIODIC trigger skips if interval not elapsed (1800s)."""
    d, log = _make_dispatcher_with_log()
    d.register(TriggerType.PERIODIC, lambda e: log.append(e))
    # First call always fires
    assert d.on_periodic(ts=1000.0) is True
    # Second call within 1800s should be skipped
    assert d.on_periodic(ts=1500.0) is False
    # After 1800s elapsed, should fire again
    assert d.on_periodic(ts=2800.0 + 1) is True
    assert len(log) == 2


def test_extension_dispatches():
    """EXTENSION trigger routes to registered handler."""
    d, log = _make_dispatcher_with_log()
    d.register(TriggerType.EXTENSION, lambda e: log.append(e))
    result = d.on_extension(ts=2000.0, payload={"direction": "UP"})
    assert result is True
    assert log[0].trigger_type == TriggerType.EXTENSION


def test_failed_ext_dispatches():
    """FAILED_EXT trigger routes to registered handler."""
    d, log = _make_dispatcher_with_log()
    d.register(TriggerType.FAILED_EXT, lambda e: log.append(e))
    result = d.on_failed_ext(ts=3000.0, payload={"direction": "DOWN"})
    assert result is True
    assert log[0].trigger_type == TriggerType.FAILED_EXT


def test_news_event_dispatches():
    """NEWS_EVENT trigger routes to registered handler."""
    d, log = _make_dispatcher_with_log()
    d.register(TriggerType.NEWS_EVENT, lambda e: log.append(e))
    result = d.on_news_event(ts=4000.0, payload={"headline": "FOMC"})
    assert result is True
    assert log[0].payload == {"headline": "FOMC"}


def test_volume_spike_dispatches():
    """VOLUME_SPIKE trigger routes to registered handler."""
    d, log = _make_dispatcher_with_log()
    d.register(TriggerType.VOLUME_SPIKE, lambda e: log.append(e))
    result = d.on_volume_spike(ts=5000.0, payload={"z_score": 3.1})
    assert result is True
    assert log[0].trigger_type == TriggerType.VOLUME_SPIKE
    assert log[0].payload["z_score"] == 3.1
