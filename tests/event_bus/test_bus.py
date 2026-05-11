"""Tests for Event Bus — publish + subscribe roundtrip.

These tests hit the real Upstash Redis instance (credentials from .env).
"""

import os
import time

import pytest

from backend.v9.event_bus.bus import EventBus
from backend.v9.event_bus.channels import CH_PRICE_TICK
from backend.v9.event_bus.publisher import publish_event, get_bus
from backend.v9.event_bus.subscriber import StreamSubscriber
from backend.v9.event_bus.correlation import new_session_id, get_session_id
from backend.v9.event_bus.schemas.price import PriceTick


# Use a test-specific channel to avoid polluting production streams
TEST_CHANNEL = "mems26:test:events:price.tick"


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def cleanup_stream(bus):
    """Clean up test stream after each test."""
    yield
    bus._cmd(["DEL", TEST_CHANNEL])


class TestEventBusPublish:
    def test_publish_returns_entry_id(self, bus, cleanup_stream):
        event = PriceTick(price=5412.25, bid=5412.00, ask=5412.50)
        entry_id = bus.publish(TEST_CHANNEL, event)
        assert entry_id is not None
        assert "-" in entry_id  # Redis stream IDs are "timestamp-seq"

    def test_publish_multiple(self, bus, cleanup_stream):
        for i in range(5):
            event = PriceTick(price=5412.25 + i * 0.25)
            bus.publish(TEST_CHANNEL, event)
        length = bus.stream_length(TEST_CHANNEL)
        assert length == 5

    def test_stream_length(self, bus, cleanup_stream):
        assert bus.stream_length(TEST_CHANNEL) == 0
        event = PriceTick(price=5412.25)
        bus.publish(TEST_CHANNEL, event)
        assert bus.stream_length(TEST_CHANNEL) == 1


class TestEventBusRead:
    def test_read_entries(self, bus, cleanup_stream):
        event = PriceTick(price=5412.25, bid=5412.00, ask=5412.50)
        bus.publish(TEST_CHANNEL, event)

        entries = bus.read(TEST_CHANNEL, last_id="0", count=10)
        assert len(entries) == 1
        entry_id, fields = entries[0]
        assert fields["event_type"] == "price.tick"
        assert "data" in fields

    def test_read_deserialize(self, bus, cleanup_stream):
        event = PriceTick(price=5412.25, bid=5412.00, ask=5412.50)
        bus.publish(TEST_CHANNEL, event)

        entries = bus.read(TEST_CHANNEL, last_id="0", count=10)
        _, fields = entries[0]
        restored = PriceTick.from_stream_dict(fields)
        assert restored.price == 5412.25
        assert restored.bid == 5412.00
        assert restored.event_type == "price.tick"


class TestPublishHelper:
    def test_publish_event_infers_channel(self, cleanup_stream):
        """publish_event should auto-route price.tick to the right channel."""
        event = PriceTick(price=5412.25)
        # This publishes to the real CH_PRICE_TICK channel
        result = publish_event(event)
        assert result is not None


class TestCorrelation:
    def test_new_session_id(self):
        sid = new_session_id()
        assert len(sid) == 12

    def test_session_id_persists(self):
        sid1 = new_session_id()
        sid2 = get_session_id()
        assert sid1 == sid2

    def test_new_session_changes_id(self):
        sid1 = new_session_id()
        sid2 = new_session_id()
        assert sid1 != sid2


class TestSubscriber:
    def test_poll_once(self, bus, cleanup_stream):
        """Subscriber.poll_once picks up published events."""
        received = []

        def handler(entry_id, fields):
            received.append(fields)

        sub = StreamSubscriber(TEST_CHANNEL, handler, bus=bus, poll_interval=0.05)

        # Publish then poll
        event = PriceTick(price=5412.25)
        bus.publish(TEST_CHANNEL, event)

        count = sub.poll_once()
        assert count == 1
        assert len(received) == 1
        assert received[0]["event_type"] == "price.tick"

    def test_subscriber_start_stop(self, bus, cleanup_stream):
        """Start/stop lifecycle works without errors."""
        received = []
        sub = StreamSubscriber(
            TEST_CHANNEL, lambda eid, f: received.append(f),
            bus=bus, poll_interval=0.2,
        )
        sub.start()

        # Give subscriber time to initialize (XREVRANGE call)
        time.sleep(1.5)

        # Publish while subscriber is running
        event = PriceTick(price=5412.25)
        bus.publish(TEST_CHANNEL, event)
        # Upstash REST round trips are slow (~1s each), need enough time
        time.sleep(3.0)

        sub.stop()
        assert len(received) >= 1
