"""L7 — 2-contract symmetry tests (2026-07-08).

Anti-tautological: each FAILS on the pre-fix code (verified by stashing):
  1. 2c stop-out P&L = 2 legs (old: 3 legs → −150% of the real loss).
  2. T2 CLOSES a 2-contract trade (old: PARTIAL forever — stuck slot).
  3. T3 close on 3c counts ALL 3 legs in the final P&L (old: close kept the
     PARTIAL-branch value — the T3 leg was never added).
  4. FillPoller frees the gateway slot when a 2c trade closes at T2 (old: T3-only).
  5. effective_contracts honors FIXED_CONTRACTS_2 precedence + legacy parsing.
Runnable standalone: `python3 test_l7_two_contract_symmetry.py`.
"""
import importlib.util
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

for _f in ("FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3", "LIVE_EXECUTION_V1"):
    os.environ.pop(_f, None)

from backend.v9.services.sierra_command import effective_contracts  # noqa: E402
from backend.v9.services.trade_manager.manager import TradeManager  # noqa: E402


class FakeDB:
    """Just enough Session for on_target_hit/_calculate_pnl paths."""

    def __init__(self, trade):
        self._trade = trade

    def query(self, *a, **k):
        return self

    def filter(self, *a, **k):
        return self

    def first(self):
        return self._trade

    def add(self, *a, **k):
        pass

    def flush(self):
        pass


def _trade(n_contracts, **over):
    base = dict(
        id=310, mode="shadow", direction="LONG", state="FILLED",
        entry_price=7500.0, stop=7496.0, t1=7504.0, t2=7508.0, t3=7512.0,
        t1_hit_ts=None, t2_hit_ts=None, t3_hit_ts=None, stop_hit_ts=None,
        exit_ts=None, exit_reason=None, exit_price=None, outcome=None,
        pnl_usd=None, pnl_r=None, cross_context=None, firing_system=2,
        quality={"contracts": n_contracts, "initial_stop": 7496.0},
    )
    base.update(over)
    return SimpleNamespace(**base)


def _tm(trade):
    return TradeManager(db=FakeDB(trade))


# 1 — 2c stop-out: exactly 2 P&L legs + 2-contract risk denominator.
def test_stop_out_pnl_two_legs():
    t = _trade(2, state="CLOSED", exit_reason="STOP_HIT", exit_price=7496.0)
    _tm(t)._calculate_pnl(t)
    # 2 × (7496−7500) × $5 = −$40 (old code: 3 legs → −$60)
    assert t.pnl_usd == -40.0, t.pnl_usd
    assert t.pnl_r == -1.0, t.pnl_r  # −40 / (2 × $20)


# 2 — T2 closes a 2-contract trade.
def test_t2_closes_two_contract_trade():
    t = _trade(2)
    tm = _tm(t)
    tm.on_target_hit(310, "T1", fill_ts=datetime.now(timezone.utc))
    assert t.state == "PARTIAL"
    tm.on_target_hit(310, "T2", fill_ts=datetime.now(timezone.utc))
    assert t.state == "CLOSED", f"2c trade must CLOSE at T2, got {t.state}"
    assert t.exit_reason == "T2_HIT"
    # c1@T1 (4pt) + c2@T2 (8pt) = 12pt × $5 = $60 · R = 60/(2×20) = 1.5
    assert t.pnl_usd == 60.0 and t.pnl_r == 1.5, (t.pnl_usd, t.pnl_r)
    assert t.outcome == "WIN"


# 3 — 3c T3 close: final P&L counts all three legs (undercount fix).
def test_t3_close_counts_all_three_legs():
    t = _trade(3)
    tm = _tm(t)
    now = datetime.now(timezone.utc)
    tm.on_target_hit(310, "T1", fill_ts=now)
    tm.on_target_hit(310, "T2", fill_ts=now)
    assert t.state == "PARTIAL"  # 3c stays open through T2 (unchanged)
    tm.on_target_hit(310, "T3", fill_ts=now)
    assert t.state == "CLOSED" and t.exit_reason == "T3_HIT"
    # (4+8+12)pt × $5 = $120 · R = 120/(3×20) = 2.0 (old: kept $60 partial value)
    assert t.pnl_usd == 120.0 and t.pnl_r == 2.0, (t.pnl_usd, t.pnl_r)


# 4 — FillPoller frees the slot when the manager closes at T2 (2c).
def test_fill_poller_frees_slot_on_t2_close():
    _FP = os.path.join(_REPO, "backend", "v9", "services", "fill_poller.py")
    spec = importlib.util.spec_from_file_location("fp_l7", _FP)
    fp = importlib.util.module_from_spec(spec)
    sys.modules["fp_l7"] = fp
    spec.loader.exec_module(fp)

    trade = SimpleNamespace(id=311, mode="live", state="PARTIAL",
                            direction="LONG", pnl_usd=60.0)

    class TM:
        # **_kw: the poller also passes fill_qty/order_id (T-62 per-leg fills).
        # A stub that pins the signature turns an interface addition into a
        # swallowed TypeError inside _process_fill's catch-all.
        def on_target_hit(self, trade_id, kind, fill_ts=None, fill_price=None,
                          **_kw):
            if kind == "T2":
                trade.state = "CLOSED"  # what the L7 manager now does for 2c

        def _get_trade(self, trade_id):
            return trade

        def get_active_trades(self):
            return [trade]

    class GW:
        def __init__(self):
            self.closed = []

        def on_trade_close(self, payload):
            self.closed.append(payload)

    p = fp.FillPoller(trade_manager=TM(), gateway=GW())
    p.register_order(9001, 311)
    p._process_fill({"kind": "T2", "order_id": 9001, "price": 7508.0, "ts": 2})
    assert p._gateway.closed, "gateway close must fire on 2c T2 full-close"
    assert p._gateway.closed[0]["trade_id"] == 311


# 5 — effective_contracts: _2 precedence + legacy parsing preserved.
def test_effective_contracts():
    try:
        assert effective_contracts({"contracts": 3}) == 3
        assert effective_contracts({"metadata": {"sizing": 3}}) == 3
        assert effective_contracts({"size": "half"}) == 2
        assert effective_contracts({}) == 1  # unknown → floor 1
        os.environ["FIXED_CONTRACTS_2"] = "1"
        assert effective_contracts({"contracts": 3}) == 2  # _2 wins
        os.environ["FIXED_CONTRACTS_3"] = "1"
        assert effective_contracts({"contracts": 1}) == 2  # _2 precedence over _3
        os.environ.pop("FIXED_CONTRACTS_2")
        assert effective_contracts({"contracts": 1}) == 3  # _3 alone
    finally:
        os.environ.pop("FIXED_CONTRACTS_2", None)
        os.environ.pop("FIXED_CONTRACTS_3", None)


# 6 — trade_contract_count fallback chain (quality → env → 3).
def test_trade_contract_count_fallbacks():
    from backend.v9.services.trade_manager.manager import trade_contract_count
    try:
        assert trade_contract_count(SimpleNamespace(quality={"contracts": 2})) == 2
        os.environ["FIXED_CONTRACTS_2"] = "1"
        assert trade_contract_count(SimpleNamespace(quality={})) == 2  # env fallback
        os.environ.pop("FIXED_CONTRACTS_2")
        assert trade_contract_count(SimpleNamespace(quality=None)) == 3  # legacy
    finally:
        os.environ.pop("FIXED_CONTRACTS_2", None)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok - {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL - {t.__name__}: {e!r}")
    print(f"\ntest_l7_two_contract_symmetry.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
