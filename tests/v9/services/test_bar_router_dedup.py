"""BarRouter is now transparent (no dedup). Dedup moved to per-system.

These tests verify BarRouter passes ALL pushes through — subscribers
handle their own dedup for bar counting while receiving live OHLC updates.
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


class TestBarRouterTransparent:
    def test_same_ts_all_dispatched(self, router):
        """5 pushes with same ts → handler called 5× (transparent)."""
        handler = AsyncMock(__qualname__="test_handler")
        router.subscribe("5min", handler)

        for _ in range(5):
            _run(router.publish("5min", {"ts": "2026-05-29T14:00:00", "close": 7580}))

        assert handler.call_count == 5

    def test_different_ts_all_dispatched(self, router):
        """3 pushes with different ts → handler called 3×."""
        handler = AsyncMock(__qualname__="test_handler")
        router.subscribe("5min", handler)

        _run(router.publish("5min", {"ts": "2026-05-29T14:00:00", "close": 7580}))
        _run(router.publish("5min", {"ts": "2026-05-29T14:05:00", "close": 7582}))
        _run(router.publish("5min", {"ts": "2026-05-29T14:10:00", "close": 7581}))

        assert handler.call_count == 3

    def test_per_topic_isolation(self, router):
        """Same ts on different topics → both dispatched."""
        h1 = AsyncMock(__qualname__="h1")
        h2 = AsyncMock(__qualname__="h2")
        router.subscribe("5min", h1)
        router.subscribe("woodies_5min", h2)

        _run(router.publish("5min", {"ts": "2026-05-29T14:00:00"}))
        _run(router.publish("woodies_5min", {"ts": "2026-05-29T14:00:00"}))

        assert h1.call_count == 1
        assert h2.call_count == 1
