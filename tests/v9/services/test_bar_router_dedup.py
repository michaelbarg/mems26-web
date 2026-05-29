"""Regression: BarRouter deduplicates pushes with the same bar ts.

The bridge pushes every ~3s with the same building bar. Without dedup,
subscribers see each bar 20× per 5-min period → all bar counters inflate
(TIME_STOP fires in 52s, opening type detected on 3 fake bars, etc.).
"""
import asyncio
from unittest.mock import AsyncMock

import pytest

from backend.v9.services.bar_router import BarRouter


@pytest.fixture
def router():
    return BarRouter()


def _run(coro):
    return asyncio.run(coro)


class TestBarRouterDedup:
    def test_same_ts_dispatched_once(self, router):
        """5 pushes with same ts → handler called once."""
        handler = AsyncMock(__qualname__="test_handler")
        router.subscribe("5min", handler)

        for _ in range(5):
            _run(router.publish("5min", {"ts": "2026-05-29T14:00:00", "close": 7580}))

        assert handler.call_count == 1
        assert router._stats["deduped"] == 4

    def test_different_ts_dispatched_each(self, router):
        """3 pushes with different ts → handler called 3×."""
        handler = AsyncMock(__qualname__="test_handler")
        router.subscribe("5min", handler)

        _run(router.publish("5min", {"ts": "2026-05-29T14:00:00", "close": 7580}))
        _run(router.publish("5min", {"ts": "2026-05-29T14:05:00", "close": 7582}))
        _run(router.publish("5min", {"ts": "2026-05-29T14:10:00", "close": 7581}))

        assert handler.call_count == 3
        assert router._stats["deduped"] == 0

    def test_dedup_is_per_topic(self, router):
        """Same ts on different topics → both dispatched."""
        h1 = AsyncMock(__qualname__="h1")
        h2 = AsyncMock(__qualname__="h2")
        router.subscribe("5min", h1)
        router.subscribe("woodies_5min", h2)

        _run(router.publish("5min", {"ts": "2026-05-29T14:00:00"}))
        _run(router.publish("woodies_5min", {"ts": "2026-05-29T14:00:00"}))

        assert h1.call_count == 1
        assert h2.call_count == 1

    def test_new_ts_after_dedup_dispatches(self, router):
        """After dedup, a new ts dispatches normally."""
        handler = AsyncMock(__qualname__="test_handler")
        router.subscribe("5min", handler)

        # 3 dupes
        for _ in range(3):
            _run(router.publish("5min", {"ts": "100"}))
        # new ts
        _run(router.publish("5min", {"ts": "200"}))

        assert handler.call_count == 2
        assert router._stats["deduped"] == 2
