"""Tests for BarRouter."""
import asyncio
from backend.v9.services.bar_router import BarRouter, BarEvent


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestBarRouterSubscribeDispatch:
    def test_subscribe_and_dispatch(self):
        br = BarRouter()
        received = []

        async def handler(event):
            received.append(event)

        br.subscribe("test_bar", handler)
        _run(br.publish("test_bar", {"bar_id": "x1", "ts": "2026-05-12T10:00:00Z", "close": 100}))

        assert len(received) == 1
        assert received[0].bar_type == "test_bar"
        assert received[0].bar_id == "x1"

    def test_session_tagged(self):
        br = BarRouter()
        received = []

        async def handler(event):
            received.append(event)

        br.subscribe("test_bar", handler)
        _run(br.publish("test_bar", {"bar_id": "x2", "ts": "2026-05-12T10:00:00Z"}))

        assert received[0].session is not None
        assert received[0].session != ""

    def test_multiple_subscribers(self):
        br = BarRouter()
        counts = {"a": 0, "b": 0}

        async def handler_a(event):
            counts["a"] += 1
        async def handler_b(event):
            counts["b"] += 1

        br.subscribe("multi", handler_a)
        br.subscribe("multi", handler_b)
        _run(br.publish("multi", {"bar_id": "m1", "ts": "2026-05-12T10:00:00Z"}))

        assert counts["a"] == 1
        assert counts["b"] == 1

    def test_failed_handler_does_not_break_others(self):
        br = BarRouter()
        success_count = 0

        async def bad_handler(event):
            raise RuntimeError("intentional")

        async def good_handler(event):
            nonlocal success_count
            success_count += 1

        br.subscribe("test", bad_handler)
        br.subscribe("test", good_handler)
        _run(br.publish("test", {"bar_id": "t1", "ts": "2026-05-12T10:00:00Z"}))

        assert success_count == 1
        assert br.get_stats()["failed"] >= 1

    def test_get_stats_includes_subscribers(self):
        br = BarRouter()

        async def h(event): pass

        br.subscribe("foo", h)
        br.subscribe("bar", h)
        br.subscribe("bar", h)

        stats = br.get_stats()
        assert stats["subscribers"]["foo"] == 1
        assert stats["subscribers"]["bar"] == 2
