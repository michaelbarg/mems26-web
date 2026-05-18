"""Tests for BarRouter.publish_threadsafe (P27.5c)."""
import asyncio
import logging
import threading
import time
from unittest.mock import AsyncMock, patch

import pytest


def _make_router():
    """Create a BarRouter with a fresh event loop bound."""
    from backend.v9.services.bar_router import BarRouter
    router = BarRouter()
    return router


def test_publish_threadsafe_dispatches_to_main_loop():
    """publish_threadsafe from a background thread delivers to subscribed handler on main loop."""
    from backend.v9.services.bar_router import BarRouter

    router = BarRouter()
    handler = AsyncMock(__qualname__="test_handler")
    router.subscribe("foo", handler)

    loop = asyncio.new_event_loop()
    router.bind_main_loop(loop)

    delivered = threading.Event()

    async def _wait_for_delivery():
        deadline = time.time() + 2.0
        while not handler.called and time.time() < deadline:
            await asyncio.sleep(0.05)
        delivered.set()

    def _bg_thread():
        # Small delay to ensure loop is running
        time.sleep(0.1)
        router.publish_threadsafe("foo", {"price": 100})

    t = threading.Thread(target=_bg_thread, daemon=True)
    t.start()

    loop.run_until_complete(_wait_for_delivery())
    loop.close()

    assert handler.called, "Handler was not called via publish_threadsafe"
    event = handler.call_args[0][0]
    assert event.payload["price"] == 100
    assert event.bar_type == "foo"


def test_publish_threadsafe_warns_when_unbound(caplog):
    """When main_loop is not bound, publish_threadsafe logs a warning and still delivers."""
    from backend.v9.services.bar_router import BarRouter

    router = BarRouter()
    handler = AsyncMock(__qualname__="test_fallback_handler")
    router.subscribe("bar", handler)

    # No bind_main_loop called — _main_loop is None
    with caplog.at_level(logging.WARNING, logger="backend.v9.services.bar_router"):
        router.publish_threadsafe("bar", {"x": 1})

    # Wait for fallback thread to complete
    time.sleep(0.5)

    assert "main_loop not bound" in caplog.text
    assert handler.called, "Fallback thread should still deliver"
