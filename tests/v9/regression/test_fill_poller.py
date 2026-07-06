"""Offline round-trip test for the Pipeline 5 fill poller (Phase B) — NO orders placed.

Mocks the TradeManager and feeds fill events (as the Sierra DLL would write to
trade_fills.json) → asserts the poller drives on_fill / on_target_hit / on_stop_hit
with the Sierra fill price. Proves the backend half of the DEMO round-trip works
before any real (sim) order is armed.

if reverted -> RED because: reverting the ENTRY->on_fill fix makes the entry path
set entry_price directly (no state transition) and test_entry_fill_calls_on_fill fails.
"""
from backend.v9.services.fill_poller import FillPoller


class _MockTM:
    def __init__(self):
        self.calls = []
        self._active = []

    def get_active_trades(self):
        return self._active

    def on_fill(self, trade_id, price):
        self.calls.append(("on_fill", trade_id, price))

    def on_target_hit(self, trade_id, target, fill_ts=None, fill_price=None):
        self.calls.append(("on_target_hit", trade_id, target))

    def on_stop_hit(self, trade_id, fill_ts=None, fill_price=None):
        self.calls.append(("on_stop_hit", trade_id))


class _T:
    def __init__(self, tid, mode="demo"):
        self.id = tid
        self.mode = mode


def _fill(kind, order_id=5001, price=7450.0):
    return {"kind": kind, "order_id": order_id, "price": price, "ts": 1700000000}


def test_entry_fill_calls_on_fill():
    tm = _MockTM(); p = FillPoller(trade_manager=tm); p.register_order(5001, 42)
    p._process_fill(_fill("ENTRY", price=7450.25))
    assert ("on_fill", 42, 7450.25) in tm.calls


def test_t1_fill_calls_on_target_hit():
    tm = _MockTM(); p = FillPoller(trade_manager=tm); p.register_order(5001, 42)
    p._process_fill(_fill("T1", price=7455.0))
    assert ("on_target_hit", 42, "T1") in tm.calls


def test_stop_fill_calls_on_stop_hit():
    tm = _MockTM(); p = FillPoller(trade_manager=tm); p.register_order(5001, 42)
    p._process_fill(_fill("STOP", price=7440.0))
    assert ("on_stop_hit", 42) in tm.calls


def test_unregistered_order_falls_back_to_single_active_trade():
    # One-trade-at-a-time (Michael's rule): the fallback maps the fill to the
    # single active trade — correct because there is never more than one.
    tm = _MockTM(); tm._active = [_T(99)]
    p = FillPoller(trade_manager=tm)  # no register_order called
    p._process_fill(_fill("ENTRY", order_id=6001, price=7400.0))
    assert ("on_fill", 99, 7400.0) in tm.calls


def test_no_trade_manager_is_safe():
    p = FillPoller(trade_manager=None)
    p._process_fill(_fill("ENTRY"))  # must not crash


def test_no_match_no_active_is_safe():
    tm = _MockTM()  # no map, no active trades
    p = FillPoller(trade_manager=tm)
    p._process_fill(_fill("ENTRY"))
    assert tm.calls == []  # nothing driven, no crash


def test_unknown_kind_is_safe():
    tm = _MockTM(); p = FillPoller(trade_manager=tm); p.register_order(5001, 42)
    p._process_fill(_fill("WAT"))
    assert tm.calls == []
