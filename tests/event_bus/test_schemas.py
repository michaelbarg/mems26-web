"""Tests for Event Bus schema models."""

import json
import time

from backend.v9.event_bus.schemas.base import BaseEvent
from backend.v9.event_bus.schemas.price import PriceTick, PriceSnapshot


class TestBaseEvent:
    def test_create_with_defaults(self):
        e = BaseEvent(event_type="test.event")
        assert e.event_type == "test.event"
        assert len(e.correlation_id) == 12
        assert e.ts_ms > 0
        assert e.version == "1.0"

    def test_to_stream_dict(self):
        e = BaseEvent(event_type="test.event", source="unit_test")
        d = e.to_stream_dict()
        assert d["event_type"] == "test.event"
        assert d["source"] == "unit_test"
        assert "data" in d
        # All values must be strings for Redis Streams
        for k, v in d.items():
            assert isinstance(v, str), f"key {k} has non-string value: {type(v)}"

    def test_roundtrip_serialization(self):
        e = BaseEvent(event_type="test.roundtrip", source="unit_test")
        d = e.to_stream_dict()
        e2 = BaseEvent.from_stream_dict(d)
        assert e2.event_type == e.event_type
        assert e2.correlation_id == e.correlation_id
        assert e2.ts_ms == e.ts_ms


class TestPriceTick:
    def test_create_minimal(self):
        t = PriceTick(price=5412.25)
        assert t.event_type == "price.tick"
        assert t.price == 5412.25
        assert t.source == "bridge.live_price"

    def test_create_full(self):
        t = PriceTick(price=5412.25, bid=5412.00, ask=5412.50, last_size=3.0)
        assert t.spread == 0.50
        assert t.bid == 5412.00
        assert t.last_size == 3.0

    def test_spread_none_when_missing(self):
        t = PriceTick(price=5412.25)
        assert t.spread is None

    def test_to_stream_dict_has_price(self):
        t = PriceTick(price=5412.25)
        d = t.to_stream_dict()
        assert d["price"] == "5412.25"

    def test_roundtrip(self):
        t = PriceTick(price=5412.25, bid=5412.00, ask=5412.50)
        d = t.to_stream_dict()
        t2 = PriceTick.from_stream_dict(d)
        assert t2.price == t.price
        assert t2.bid == t.bid
        assert t2.ask == t.ask


class TestPriceSnapshot:
    def test_create(self):
        s = PriceSnapshot(price=5412.25, vwap=5410.00)
        assert s.event_type == "price.snapshot"
        assert s.vwap == 5410.00
