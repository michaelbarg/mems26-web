"""T-213: MODIFY goes to the wrong Sierra order on T0 trades.

With has_t0=true, DLL targets are offset: T0→c1, T1→c2, T2→c3, T3→c4.
But 4 code sites mapped 1:1 (t1→c1_target_id), sending MODIFY to the
wrong order. #942: t2 "moved" in books to 7669, broker order didn't
move, price passed at 7673 — zero fill.

The fix: _target_order_key respects T0 offset via _ladder_group_for.
"""
import types
import pytest

from backend.v9.services.trade_manager.manager import TradeManager


def _mk_trade(has_t0=True, contracts=4):
    t = types.SimpleNamespace()
    t.id = 942
    t.mode = "live"
    t.direction = "LONG"
    t.entry_price = 7660.25
    t.stop = 7651.0
    t.t1 = 7667.75
    t.t2 = 7675.50
    t.t3 = 7683.25
    t.t1_hit_ts = None
    t.t2_hit_ts = None
    t.t3_hit_ts = None
    q = {"contracts": contracts}
    if has_t0:
        q["has_t0"] = True
        q["t0_target_pts"] = 3.0
    q["c1_target_id"] = 10001  # T0 scalp order
    q["c2_target_id"] = 10002  # real T1 order
    q["c3_target_id"] = 10003  # real T2 order
    q["c4_target_id"] = 10004  # real T3 order
    t.quality = q
    t.cross_context = []
    return t


class TestT0Offset:
    """With has_t0=true, target order IDs shift +1."""

    def test_t1_maps_to_c2_with_t0(self):
        """has_t0=true: t1 → c2_target_id (not c1)."""
        t = _mk_trade(has_t0=True)
        key = TradeManager._target_order_key(t, "t1")
        assert key == "c2_target_id", f"t1 should → c2 with T0, got {key}"

    def test_t2_maps_to_c3_with_t0(self):
        """has_t0=true: t2 → c3_target_id."""
        t = _mk_trade(has_t0=True)
        key = TradeManager._target_order_key(t, "t2")
        assert key == "c3_target_id", f"t2 should → c3 with T0, got {key}"

    def test_t3_maps_to_c4_with_t0(self):
        """has_t0=true: t3 → c4_target_id."""
        t = _mk_trade(has_t0=True)
        key = TradeManager._target_order_key(t, "t3")
        assert key == "c4_target_id", f"t3 should → c4 with T0, got {key}"


class TestNoT0:
    """Without T0, mapping is 1:1 (byte-identical to old behavior)."""

    def test_t1_maps_to_c1_without_t0(self):
        t = _mk_trade(has_t0=False)
        key = TradeManager._target_order_key(t, "t1")
        assert key == "c1_target_id", f"t1 should → c1 without T0, got {key}"

    def test_t2_maps_to_c2_without_t0(self):
        t = _mk_trade(has_t0=False)
        key = TradeManager._target_order_key(t, "t2")
        assert key == "c2_target_id"

    def test_t3_maps_to_c3_without_t0(self):
        t = _mk_trade(has_t0=False)
        key = TradeManager._target_order_key(t, "t3")
        assert key == "c3_target_id"


class TestMutation:
    """Reverting to 1:1 mapping must fail."""

    def test_mutation_t1_with_t0_not_c1(self):
        """If someone reverts to t1→c1, this fails."""
        t = _mk_trade(has_t0=True)
        key = TradeManager._target_order_key(t, "t1")
        assert key != "c1_target_id", (
            "MUTATION: t1 with T0 mapped to c1 — sends MODIFY to T0 scalp "
            "order instead of the real T1. This is the #942 bug.")

    def test_mutation_order_id_value(self):
        """The actual order_id value must reflect the offset."""
        t = _mk_trade(has_t0=True)
        key = TradeManager._target_order_key(t, "t1")
        oid = t.quality.get(key)
        assert oid == 10002, (
            f"T1 order_id should be 10002 (c2), got {oid} from key {key}")
