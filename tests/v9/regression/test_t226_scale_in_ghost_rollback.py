"""T-226 — a refused PLACE must unwind its own trade row.

ROOT (measured twice on 2026-09-02, the same chain word for word — #955 at
17:30 and #979 at 21:18:53): `_maybe_scale_in` creates the child row with
`accept_setup`, links it onto the parent, then calls `command_from_setup` and
THROWS THE RESULT AWAY. When a pre-send guard refuses the order the books keep
a live PENDING trade that never reached the market:

    21:18:53 Trade 979 created: mode=live sys=4 dir=LONG
    21:18:53 [SierraCmd] RISK_BUDGET: risk=11.1 pts -> raw=4.0 -> floor=4
    21:18:53 [SierraCmd] T-214: PLACE rejected — t3=None invalid on 4
             contracts. Every contract must have a target.
    21:19:14 [Reconciler] SYS-3 DIVERGENCE: TM says 8 contracts
             ['#971(live,LONG,4c)', '#979(live,LONG,4c)'], Sierra says 2

...then DIVERGENCE every 30 seconds until a containment guard cleaned up. The
containment worked; the cause did not go away, so it reproduces on every add.

if reverted → RED because: dropping the `_rollback_if_place_refused` call
leaves the child OPEN, which is exactly what the first test asserts against.
"""
from types import SimpleNamespace

import pytest

from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


class _FakeDB:
    def commit(self):
        pass

    def flush(self):
        pass


class _FakeTM:
    """Minimal TradeManager surface used by the rollback."""

    def __init__(self, child):
        self._db = _FakeDB()
        self._child = child
        self.closed = []

    def _get_trade(self, tid):
        return self._child if int(tid) == int(self._child.id) else None

    def close_trade(self, trade_id, reason, exit_price=None,
                    outcome_override=None):
        self.closed.append((int(trade_id), reason, outcome_override))
        self._child.state = "CLOSED"
        self._child.exit_reason = reason
        self._child.outcome = outcome_override


class _FakeGateway:
    def __init__(self):
        self.closes = []

    def on_trade_close(self, payload):
        self.closes.append(payload)


def _detector(tm, gw):
    d = BarLevelDetector.__new__(BarLevelDetector)
    d._tm = tm
    d._gateway = gw
    return d


def _child(**kw):
    t = SimpleNamespace(id=979, mode="live", direction="LONG", state="PENDING",
                        pnl_usd=None, quality={}, exit_reason=None,
                        outcome=None)
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def _parent():
    return SimpleNamespace(
        id=971, mode="live", direction="LONG", state="PARTIAL",
        quality={"scale_in_child_id": 979, "scale_in_added": 2})


# The literal T-214 refusal shape returned by sierra_command.command_from_setup
REFUSAL = {"rejected": True, "reason": "t3_missing",
           "detail": "t3=None on 4 contracts"}


def test_refused_place_cancels_the_child_and_frees_the_slot(caplog):
    child, parent = _child(), _parent()
    tm, gw = _FakeTM(child), _FakeGateway()
    with caplog.at_level("ERROR"):
        went_out = _detector(tm, gw)._rollback_if_place_refused(
            REFUSAL, 979, parent, "ScaleIn")

    assert went_out is False, "caller must not carry on as if the order shipped"
    # the ghost is gone
    assert child.state == "CANCELLED"
    assert tm.closed == [(979, "PLACE_REFUSED:t3_missing", "CANCELLED")]
    # the slot is released, so the next fire is not blocked by a row that
    # never existed at the broker
    assert gw.closes and gw.closes[0]["trade_id"] == 979
    assert gw.closes[0]["outcome"] == "PLACE_REFUSED:t3_missing"
    # and it was loud
    assert "T-226" in caplog.text and "PLACE REFUSED" in caplog.text


def test_parent_is_unlinked_so_it_stops_claiming_contracts():
    child, parent = _child(), _parent()
    _detector(_FakeTM(child), _FakeGateway())._rollback_if_place_refused(
        REFUSAL, 979, parent, "ScaleIn")
    assert "scale_in_child_id" not in parent.quality
    assert "scale_in_added" not in parent.quality
    assert parent.quality["scale_in_last_refused"] == {
        "child_id": 979, "reason": "t3_missing"}


@pytest.mark.parametrize("result", [
    None,                                  # pre-fix callers returned nothing
    {},                                    # no verdict
    {"rejected": False},                   # explicitly sent
    {"ok": True, "path": "cmd_000417.json"},
])
def test_a_successful_place_is_untouched(result):
    """Byte-identical behaviour for every path that actually places."""
    child, parent = _child(), _parent()
    tm, gw = _FakeTM(child), _FakeGateway()
    assert _detector(tm, gw)._rollback_if_place_refused(
        result, 979, parent, "ScaleIn") is True
    assert tm.closed == []
    assert gw.closes == []
    assert parent.quality["scale_in_child_id"] == 979
    assert child.state == "PENDING"


def test_rollback_failure_is_screamed_not_swallowed(caplog):
    """A botched rollback must never be silent — the ghost is still out there."""
    child, parent = _child(), _parent()

    class _Boom(_FakeTM):
        def close_trade(self, *a, **kw):
            raise RuntimeError("db wedged")

    with caplog.at_level("ERROR"):
        went_out = _detector(_Boom(child), _FakeGateway())._rollback_if_place_refused(
            REFUSAL, 979, parent, "ScaleIn")
    assert went_out is False
    assert "rollback of child 979 FAILED" in caplog.text
    assert "SYS-3 DIVERGENCE" in caplog.text


def test_both_add_on_paths_call_the_rollback():
    """Static proof that ScaleIn AND TrendUpgrade are both wired.

    TrendUpgrade is flag-OFF today; wiring it now means it can never ship the
    same ghost when the flag is turned on.
    """
    import inspect
    src = inspect.getsource(BarLevelDetector)
    assert src.count("_rollback_if_place_refused(") >= 3, (
        "expected the definition plus a call from _maybe_scale_in and from "
        "_maybe_trend_upgrade_add")
    for tag in ('"ScaleIn"', '"TrendUpgrade"'):
        assert tag in src
