"""Tests for StreamHealthService (A.4 Stream Health)."""

import time
import pytest

from backend.v9.services.stream_health.health import (
    StreamHealthService,
    STREAM_NAMES,
)


@pytest.fixture
def svc():
    return StreamHealthService()


def test_record_push_updates_timestamp(svc):
    svc.record_push("footprint")
    result = svc.get_all_streams()
    fp = next(s for s in result["streams"] if s["name"] == "footprint")
    assert fp["last_push_ts"] is not None
    assert fp["push_count"] == 1


def test_status_green_when_fresh(svc):
    svc.record_push("footprint")
    result = svc.get_all_streams()
    fp = next(s for s in result["streams"] if s["name"] == "footprint")
    assert fp["color"] == "green"
    assert fp["status"] == "healthy"


def test_status_yellow_when_stale_10s(svc, monkeypatch):
    svc.record_push("footprint")
    # Simulate push 15 seconds ago
    with svc._lock:
        svc._streams["footprint"].last_bridge_push_ts = time.time() - 15
    # Invalidate cache
    svc._cache = None
    result = svc.get_all_streams()
    fp = next(s for s in result["streams"] if s["name"] == "footprint")
    assert fp["color"] == "yellow"
    assert fp["status"] == "degraded"


def test_status_red_when_stale_60s(svc):
    svc.record_push("footprint")
    with svc._lock:
        svc._streams["footprint"].last_bridge_push_ts = time.time() - 120
    svc._cache = None
    result = svc.get_all_streams()
    fp = next(s for s in result["streams"] if s["name"] == "footprint")
    assert fp["color"] == "red"
    assert fp["status"] == "stale"


def test_status_grey_when_all_stale(svc):
    """When ALL streams are stale > 5min, treat as market closed (grey)."""
    old_ts = time.time() - 600  # 10 minutes ago
    for name in STREAM_NAMES:
        svc.record_push(name)
        with svc._lock:
            svc._streams[name].last_bridge_push_ts = old_ts
    svc._cache = None
    result = svc.get_all_streams()
    for s in result["streams"]:
        assert s["color"] == "grey", f"{s['name']} should be grey, got {s['color']}"
        assert s["status"] == "market_closed"


def test_error_count_tracked(svc):
    svc.record_push("tpo")
    svc.record_error("tpo", "some error")
    svc.record_error("tpo", "another error")
    svc._cache = None
    result = svc.get_all_streams()
    tpo = next(s for s in result["streams"] if s["name"] == "tpo")
    assert tpo["error_count"] == 2
    # errors cause yellow
    assert tpo["color"] == "yellow"


def test_get_all_streams_returns_canonical_streams(svc):
    result = svc.get_all_streams()
    assert len(result["streams"]) == len(STREAM_NAMES)
    names = {s["name"] for s in result["streams"]}
    assert names == set(STREAM_NAMES)


def test_cache_returns_same_within_1s(svc):
    svc.record_push("footprint")
    r1 = svc.get_all_streams()
    svc.record_push("footprint")  # second push
    r2 = svc.get_all_streams()
    # Should be identical (cached)
    assert r1["ts"] == r2["ts"]
    fp1 = next(s for s in r1["streams"] if s["name"] == "footprint")
    fp2 = next(s for s in r2["streams"] if s["name"] == "footprint")
    assert fp1["push_count"] == fp2["push_count"]
