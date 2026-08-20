"""I-58 regression — Sierra fills must reach the RIGHT trade, never the shadow twin.

Live incident (2026-07-02 18:10, trades 275/276): T1/T2/STOP fills carried
per-contract order IDs that were never added to FillPoller._order_map → the
"most recent active" fallback attributed them to the SHADOW twin (275).
Result: demo 276 never saw T1 → no smart-BE → stuck open → manual close.

Fixes under test:
1. ENTRY fill maps ALL per-contract order ids (c1/c2/c3 target+stop) → trade.
2. Fallback for unmapped ids considers ONLY demo/live trades (never shadow);
   drops loudly when none.
"""
import pytest

from backend.v9.services.fill_poller import FillPoller


class _FakeTrade:
    def __init__(self, tid, mode):
        self.id = tid
        self.mode = mode
        self.pnl_usd = 0.0
        self.direction = "SHORT"


class _FakeTM:
    def __init__(self, trades):
        self._trades = trades
        self.fills = []
        self.target_hits = []
        self.stop_hits = []
        self.sierra_ids = {}

    def on_fill(self, trade_id, price):
        self.fills.append((trade_id, price))

    # **_kw absorbs the poller's T-62 per-leg fill_qty/order_id
    def on_target_hit(self, trade_id, kind, fill_ts=None, fill_price=None, **_kw):
        self.target_hits.append((trade_id, kind))

    def on_stop_hit(self, trade_id, fill_ts=None, fill_price=None, **_kw):
        self.stop_hits.append(trade_id)

    def set_sierra_order_ids(self, trade_id, ids):
        self.sierra_ids[trade_id] = ids

    def get_active_trades(self):
        return self._trades

    def _get_trade(self, trade_id):
        for t in self._trades:
            if t.id == trade_id:
                return t
        return self._trades[-1]


def _entry_fill(order_id, **cids):
    f = {"kind": "ENTRY", "order_id": order_id, "price": 7534.75, "ts": 1783005004}
    f.update(cids)
    return f


def test_per_contract_ids_are_mapped_and_route_to_the_right_trade():
    """The 275/276 scenario: after ENTRY, a T1 fill with c1_target_id must hit
    the DEMO trade — not fall back to the shadow twin (fails on pre-I-58 code)."""
    shadow = _FakeTrade(275, "shadow")
    demo = _FakeTrade(276, "demo")
    tm = _FakeTM([shadow, demo])
    fp = FillPoller(trade_manager=tm)
    fp.register_order(8293, 276)  # entry order registered at command-write

    fp._process_fill(_entry_fill(8293, c1_target_id=8288, c1_stop_id=8294,
                                 c2_target_id=8291, c2_stop_id=8295,
                                 c3_target_id=8292, c3_stop_id=8296))
    # T1 fill arrives with the per-contract target id — NOT the entry id
    fp._process_fill({"kind": "T1", "order_id": 8288, "price": 7530.75, "ts": 1783005030})

    assert tm.target_hits == [(276, "T1")], (
        "T1 fill must route to the demo trade via the per-contract id map (I-58)"
    )


def test_unmapped_fill_never_hits_shadow():
    """Unmapped order id + only a SHADOW trade active → fill dropped (not misrouted)."""
    shadow = _FakeTrade(275, "shadow")
    tm = _FakeTM([shadow])
    fp = FillPoller(trade_manager=tm)

    fp._process_fill({"kind": "STOP", "order_id": 9999, "price": 7545.25, "ts": 1783005116})

    assert tm.stop_hits == [], "a Sierra fill must never be attributed to a shadow trade"


def test_unmapped_fill_falls_back_to_demo_only():
    """Unmapped id with both twins active → fallback picks the demo, not the shadow."""
    shadow = _FakeTrade(275, "shadow")
    demo = _FakeTrade(276, "demo")
    tm = _FakeTM([shadow, demo])
    fp = FillPoller(trade_manager=tm)

    fp._process_fill({"kind": "STOP", "order_id": 9999, "price": 7545.25, "ts": 1783005116})

    assert tm.stop_hits == [276], "fallback must be demo/live-only (I-58)"
