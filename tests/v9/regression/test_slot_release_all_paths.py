"""I-57 regression — every full-close path must reach gateway.on_trade_close.

Root incident (2026-07-02, trades 271/272): Sierra-driven FillPoller closes
(STOP fill) bypassed on_trade_close → demo slot stayed occupied (blocked all
subsequent demo orders) + cooldown never counted the stops (guards blind —
same root as I-48 / D-guards-bus from 06-29).

Anti-tautological: these tests drive the REAL FillPoller._process_fill and the
REAL TradingGateway._selfheal_demo_slot logic — no string/inspect assertions.
"""
import types

import pytest

from backend.v9.services.fill_poller import FillPoller


class _FakeTrade:
    def __init__(self, tid):
        self.id = tid
        self.mode = "demo"
        self.pnl_usd = -142.5
        self.direction = "SHORT"


class _FakeTM:
    def __init__(self, tid=272):
        self._trade = _FakeTrade(tid)
        self.stop_hits = []
        self.target_hits = []

    def on_stop_hit(self, trade_id, fill_ts=None, fill_price=None):
        self.stop_hits.append(trade_id)

    def on_target_hit(self, trade_id, kind, fill_ts=None, fill_price=None):
        self.target_hits.append((trade_id, kind))

    def get_active_trades(self):
        return [self._trade]

    def _get_trade(self, trade_id):
        return self._trade


class _FakeGateway:
    def __init__(self):
        self.closes = []

    def on_trade_close(self, payload):
        self.closes.append(payload)


def test_fillpoller_stop_fill_notifies_gateway():
    """Sierra STOP fill → gateway.on_trade_close MUST be called (fails on pre-I-57 code)."""
    tm = _FakeTM(272)
    gw = _FakeGateway()
    fp = FillPoller(trade_manager=tm, gateway=gw)
    fp.register_order(9001, 272)

    fp._process_fill({"kind": "STOP", "order_id": 9001, "price": 7592.75, "ts": 1783001599})

    assert tm.stop_hits == [272]
    assert len(gw.closes) == 1, "STOP fill must notify the gateway (I-57)"
    payload = gw.closes[0]
    assert payload["trade_id"] == 272
    assert payload["outcome"] == "STOP"
    assert payload["mode"] == "demo"


def test_fillpoller_t3_fill_notifies_gateway():
    """Sierra T3 fill (full close) → gateway notified with outcome=T3."""
    tm = _FakeTM(300)
    gw = _FakeGateway()
    fp = FillPoller(trade_manager=tm, gateway=gw)
    fp.register_order(9002, 300)

    fp._process_fill({"kind": "T3", "order_id": 9002, "price": 7600.0, "ts": 1783001600})

    assert tm.target_hits == [(300, "T3")]
    assert len(gw.closes) == 1 and gw.closes[0]["outcome"] == "T3"


def test_fillpoller_t1_fill_does_not_notify():
    """Partial close (T1) must NOT free the slot."""
    tm = _FakeTM(301)
    gw = _FakeGateway()
    fp = FillPoller(trade_manager=tm, gateway=gw)
    fp.register_order(9003, 301)

    fp._process_fill({"kind": "T1", "order_id": 9003, "price": 7590.0, "ts": 1783001601})

    assert gw.closes == []


def test_gateway_selfheal_frees_stale_demo_slot(monkeypatch):
    """Slot pointing at a DB-CLOSED trade → _selfheal_demo_slot frees it (fails on pre-I-57 code)."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway.__new__(TradingGateway)  # no full init — unit-test the heal only
    gw.demo_slot = {"trade_id": 272, "direction": "SHORT", "mode": "demo"}

    import backend.v9.gateway.trading_gateway as tg_mod
    # monkeypatch the read used inside the method
    import backend.v9.db.read as read_mod
    monkeypatch.setattr(read_mod, "read_one", lambda sql, params: {"state": "CLOSED"})

    gw._selfheal_demo_slot()
    assert gw.demo_slot is None, "self-heal must free a slot whose trade is CLOSED in DB"


def test_gateway_selfheal_keeps_open_trade_slot(monkeypatch):
    """Slot pointing at a genuinely OPEN trade → heal must NOT touch it."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway.__new__(TradingGateway)
    slot = {"trade_id": 273, "direction": "LONG", "mode": "demo"}
    gw.demo_slot = slot

    import backend.v9.db.read as read_mod
    monkeypatch.setattr(read_mod, "read_one", lambda sql, params: {"state": "PARTIAL"})

    gw._selfheal_demo_slot()
    assert gw.demo_slot is slot


def test_gateway_selfheal_fail_open_on_db_error(monkeypatch):
    """DB error during heal → slot kept (fail-open), no exception."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway.__new__(TradingGateway)
    slot = {"trade_id": 274, "direction": "LONG", "mode": "demo"}
    gw.demo_slot = slot

    import backend.v9.db.read as read_mod

    def _boom(sql, params):
        raise RuntimeError("db down")

    monkeypatch.setattr(read_mod, "read_one", _boom)

    gw._selfheal_demo_slot()  # must not raise
    assert gw.demo_slot is slot
