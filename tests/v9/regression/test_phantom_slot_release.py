"""T-178 + T-177 regression — the phantom-heal path must release the live slot
AND persist the close.

Incident (2026-08-31, live money, account 37138283):
  17:00  #877 closed with reason=phantom_reconcile
  17:45  first live candidate dropped: live_blocked_by=live_slot_occupied
  ...    5 candidates dropped, ZERO alarms
  21:07  an UNPLANNED restart cleared it (live_slot is in-memory)

Root: `_gw.on_trade_close(...)` sat INSIDE `if _cancel_detect:`, and
MANUAL_CANCEL_DETECT_V1 defaults to 0 -> the phantom_reconcile branch never
reached it. Third occurrence of the class (I-57 08.07; a partial fix on
2026-08-18 was placed inside the same `if`).

The tell it was an indentation slip, not a decision: the payload carried
`"CANCELLED" if _cancel_detect else "CLOSED"` -- a dead branch, because
_cancel_detect is always True inside that block.

Anti-tautological: these drive the REAL reconcile_position() and the REAL
TradeManager.close_trade(). No string or inspect assertions. Each test is
written so that reverting the fix makes it FAIL, not error.

NOTE ON THE OLD TEST: tests/v9/regression/test_slot_release_all_paths.py has
existed since 2026-08-20 and its name promises "all paths" -- it covers the
FillPoller paths only and never touched the reconciler. A test whose name
promises coverage it does not have is worse than no test. This file closes
that specific hole.
"""
import os

import pytest

import backend.v9.services.sierra_position_reconciler as R


class _FakeTrade:
    def __init__(self, tid=877, mode="live"):
        self.id = tid
        self.mode = mode
        self.state = "PARTIAL"
        self.outcome = None
        self.direction = "SHORT"
        self.pnl_usd = None


class _FakeTM:
    def __init__(self, trades):
        self._trades = trades
        self.closed = []

    def get_active_trades(self):
        return [t for t in self._trades if t.state not in ("CLOSED", "CANCELLED")]

    def close_trade(self, trade_id, reason=None):
        self.closed.append((trade_id, reason))
        for t in self._trades:
            if t.id == trade_id:
                t.state = "CLOSED"


class _FakeGateway:
    def __init__(self):
        self.closes = []

    def on_trade_close(self, payload):
        self.closes.append(payload)


@pytest.fixture
def flat_sierra(monkeypatch):
    """Sierra reports flat: qty=0, no working orders, fresh state file."""
    monkeypatch.setattr(R, "_sierra_state_qty", lambda: 0)
    monkeypatch.setattr(R, "_sierra_state_working", lambda: 0)
    monkeypatch.setattr(R, "_sierra_state_orders", lambda: [])
    monkeypatch.setenv("PHANTOM_HEAL_V1", "1")
    # the streak counter is module-global; reset between tests
    R._phantom_flat_streak = 0
    yield


def _drive_until_heal(tm, gw, monkeypatch=None, tries=6):
    """Poll reconcile_position until the heal fires (needs N flat streaks).

    The gateway is INJECTED, not imported: it lives only on
    app.state.trading_gateway, which is why the old
    `from ...trading_gateway import get_gateway` could never work.
    """
    for _ in range(tries):
        R.reconcile_position(tm, gateway=gw)
        if tm.closed:
            break
    return tm.closed


# --------------------------------------------------------------------------
# T-178 : the bug that blocked live trading for 3.3 hours
# --------------------------------------------------------------------------

def test_phantom_reconcile_releases_the_live_slot(flat_sierra, monkeypatch):
    """THE regression. MANUAL_CANCEL_DETECT_V1 is OFF (its default) -> this is
    the phantom_reconcile path, exactly what ran on 2026-08-31.

    Reverting the fix (moving on_trade_close back inside `if _cancel_detect:`)
    makes gw.closes stay empty and this test FAIL.
    """
    monkeypatch.delenv("MANUAL_CANCEL_DETECT_V1", raising=False)
    trade = _FakeTrade(877, mode="live")
    tm, gw = _FakeTM([trade]), _FakeGateway()

    assert _drive_until_heal(tm, gw, monkeypatch), "heal never fired"

    assert gw.closes, (
        "T-178: phantom_reconcile closed the trade but NEVER notified the "
        "gateway -> live_slot stays occupied and every live fire is silently "
        "dropped. This is the 2026-08-31 incident."
    )
    payload = gw.closes[0]
    assert payload["trade_id"] == 877
    assert payload["mode"] == "live"
    # dead-branch check: on the phantom path the outcome must NOT be CANCELLED
    assert payload["outcome"] == "CLOSED"
    assert payload["reason"] == "phantom_heal"


def test_manual_cancel_still_releases_the_slot(flat_sierra, monkeypatch):
    """The pre-existing manual-cancel behaviour must not regress: it books
    CANCELLED (a manual cancel is not a loss) and still frees the slot."""
    monkeypatch.setenv("MANUAL_CANCEL_DETECT_V1", "1")
    trade = _FakeTrade(881, mode="live")
    tm, gw = _FakeTM([trade]), _FakeGateway()

    assert _drive_until_heal(tm, gw, monkeypatch), "heal never fired"

    assert gw.closes, "manual_cancel path lost its slot release"
    assert gw.closes[0]["outcome"] == "CANCELLED"
    assert gw.closes[0]["reason"] == "manual_cancel"
    assert trade.outcome == "CANCELLED", "manual cancel must book CANCELLED"


def test_killswitch_restores_old_behaviour(flat_sierra, monkeypatch):
    """PHANTOM_SLOT_RELEASE_V1=0 must reproduce the old (broken) path exactly,
    so the change is reversible without a deploy."""
    monkeypatch.delenv("MANUAL_CANCEL_DETECT_V1", raising=False)
    monkeypatch.setenv("PHANTOM_SLOT_RELEASE_V1", "0")
    tm, gw = _FakeTM([_FakeTrade(890, mode="live")]), _FakeGateway()

    assert _drive_until_heal(tm, gw, monkeypatch), "heal never fired"
    assert not gw.closes, "killswitch did not restore the old behaviour"


def test_shadow_trades_never_touch_the_live_slot(flat_sierra, monkeypatch):
    """Safety: a shadow trade must never reach close_trade or the gateway."""
    monkeypatch.delenv("MANUAL_CANCEL_DETECT_V1", raising=False)
    tm, gw = _FakeTM([_FakeTrade(999, mode="shadow")]), _FakeGateway()

    for _ in range(6):
        R.reconcile_position(tm, gateway=gw)

    assert not tm.closed, "shadow trade was healed as if it were live"
    assert not gw.closes, "shadow trade touched the live slot"


# --------------------------------------------------------------------------
# T-177 : the close that lived only in memory
# --------------------------------------------------------------------------

def test_unpriced_close_is_flushed_to_the_db():
    """T-160's UNPRICED branch returned BEFORE self._db.flush(), so the close
    existed only on the in-memory ORM object. get_active_trades() calls
    expire_all() and re-reads, saw PARTIAL again, and the heal re-fired -- 6
    times on 2026-08-31.

    It was NON-DETERMINISTIC: any later query in the same session triggers
    SQLAlchemy autoflush, so it sometimes persisted by accident (#939 did at
    22:10, which is why it looked fixed). Same code, two outcomes.

    Reverting the fix makes flush_calls == 0 and this test FAIL.
    """
    from backend.v9.services.trade_manager import manager as M

    calls = {"flush": 0, "emit": []}

    class _DB:
        def flush(self):
            calls["flush"] += 1

    class _Emitter:
        def emit(self, name, tid, payload):
            calls["emit"].append((name, tid, payload))

    class _Trade:
        id = 877
        mode = "live"
        state = "PARTIAL"
        quality = {}
        outcome = None
        pnl_usd = 65.0
        exit_price = None

    class _Machine:
        def transition(self, *_a, **_k):
            pass

    trade = _Trade()
    tm = M.TradeManager.__new__(M.TradeManager)
    tm._db = _DB()
    tm._emitter = _Emitter()
    tm._machines = {}
    tm._get_trade = lambda tid: trade
    tm._get_machine = lambda t: _Machine()
    tm._append_snapshot = lambda t, phase: None
    tm._cleanup_machine = lambda tid: None

    os.environ["PNL_REQUIRES_EXIT_PRICE_V1"] = "1"
    try:
        # THE REAL METHOD. Not a mirror of it.
        M.TradeManager.close_trade(
            tm, 877, reason="phantom_reconcile", exit_price=None)
    finally:
        os.environ.pop("PNL_REQUIRES_EXIT_PRICE_V1", None)

    # the branch must have been taken (proves the test exercises T-160's path)
    assert trade.pnl_usd is None and trade.outcome == "UNPRICED", (
        "the UNPRICED branch was not reached -- this test is not testing T-177"
    )
    assert calls["flush"] >= 1, (
        "T-177: the UNPRICED close was never flushed -> it lives only in "
        "memory, the row stays PARTIAL, and phantom-heal loops forever."
    )
    assert any(e[0] == "trade_closed" for e in calls["emit"]), (
        "T-177: consumers of trade_closed never learn about an UNPRICED close."
    )


def test_the_import_that_never_existed_is_gone():
    """The old code did `from backend.v9.gateway.trading_gateway import
    get_gateway`. That symbol HAS NEVER EXISTED, so the call raised ImportError
    every time and was swallowed -- meaning the slot was never released on
    EITHER path, not even manual_cancel. Guard against anyone re-adding it."""
    import backend.v9.gateway.trading_gateway as G
    assert not hasattr(G, "get_gateway"), (
        "someone added get_gateway -- re-check that the reconciler still takes "
        "the gateway by injection, not by import"
    )
    # scan CODE lines only -- the fix's own comment quotes the dead import
    code = [ln for ln in open(R.__file__, encoding="utf-8")
            if "import get_gateway" in ln and not ln.lstrip().startswith("#")]
    assert not code, f"the non-existent import is back in the reconciler: {code}"
