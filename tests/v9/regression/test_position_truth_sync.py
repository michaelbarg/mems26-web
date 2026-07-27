"""POSITION_TRUTH_SYNC_V1 — the system must know WHEN a trade is open and when
it is not (Michael 2026-07-27: "המערכת לא מסמנת מתי יש עסקה ומתי אין").

Sierra's own net position is the truth; our bookkeeping follows it both ways:
  • Sierra holds a position + our trade PENDING → mark FILLED (the entry-fill
    line never arrives — the deployed DLL leaves trade_fills.json empty)
  • Sierra FLAT past grace → close the trade (SIERRA_FLAT) + free the slot
  • stale/unknown Sierra state → no-op (Rule 1: never invent a fill or a close)
"""
import time

import pytest

import backend.v9.services.fill_poller as fp


class _T:
    def __init__(self, tid, state="PENDING", mode="live", entry=7456.0, age_s=999):
        self.id = tid
        self.state = state
        self.mode = mode
        self.entry_price = entry

        class _C:
            def __init__(self, ts): self._ts = ts
            def timestamp(self): return self._ts
        self.created_at = _C(time.time() - age_s)


class _TM:
    def __init__(self, trades):
        self._trades = trades
        self.filled = []
        self.closed = []
    def get_active_trades(self):
        return list(self._trades)
    def on_fill(self, tid, px):
        self.filled.append((tid, px))
        for t in self._trades:
            if t.id == tid:
                t.state = "FILLED"
    def close_trade(self, tid, reason, exit_price=None, **kw):
        self.closed.append((tid, reason))


def _poller(tm, monkeypatch, qty, avg=7456.0):
    p = fp.FillPoller.__new__(fp.FillPoller)
    p._tm = tm
    p._flat_since = None
    p._gateway = None
    monkeypatch.setattr(fp, "_t", time, raising=False)
    import backend.v9.services.sierra_position_reconciler as rec
    monkeypatch.setattr(rec, "_sierra_state_qty", lambda: qty)
    monkeypatch.setattr(rec, "_sierra_state_avg_price", lambda: avg)
    monkeypatch.setattr(p, "_notify_gateway_close", lambda *a, **k: None, raising=False)
    return p


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("POSITION_TRUTH_SYNC_V1", "1")
    monkeypatch.setenv("POSITION_TRUTH_GRACE_S", "0.05")


def test_sierra_holds_position_marks_pending_filled(monkeypatch):
    """The core miss: Sierra is long 4, our trade sits PENDING → must become FILLED."""
    tm = _TM([_T(541)])
    p = _poller(tm, monkeypatch, qty=4, avg=7456.0)
    p._sync_position_truth()
    assert tm.filled == [(541, 7456.0)]
    assert tm._trades[0].state == "FILLED"


def test_sierra_flat_closes_stale_trade_after_grace(monkeypatch):
    """The other half: Sierra flat (stop hit) → the trade must be CLOSED, not
    left as a phantom that later triggers a false naked-stop alarm."""
    tm = _TM([_T(539, state="FILLED")])
    p = _poller(tm, monkeypatch, qty=0)
    p._sync_position_truth()            # 1st sighting arms the grace timer
    assert tm.closed == []
    time.sleep(0.06)
    p._sync_position_truth()            # past grace → close
    assert tm.closed == [(539, "SIERRA_FLAT")]


def test_flat_within_grace_does_not_close(monkeypatch):
    tm = _TM([_T(539, state="FILLED")])
    p = _poller(tm, monkeypatch, qty=0)
    p._sync_position_truth()
    p._sync_position_truth()            # immediately again — still inside grace
    assert tm.closed == []


def test_brand_new_trade_not_closed_while_filling(monkeypatch):
    """Real-world shape: Sierra has been FLAT for a while (grace already
    elapsed), then a NEW order is placed. The brand-new trade must NOT be closed
    just because the position has not registered yet — otherwise the sync would
    kill every entry at birth."""
    tm = _TM([_T(542, state="PENDING", age_s=0)])
    p = _poller(tm, monkeypatch, qty=0)
    p._flat_since = time.time() - 60.0   # Sierra flat long before this trade
    p._sync_position_truth()
    assert tm.closed == []               # young trade survives


def test_unknown_age_trade_not_closed(monkeypatch):
    """Age unknown → treated as too young to close (fail-safe direction)."""
    t = _T(543, state="FILLED")
    t.created_at = None
    tm = _TM([t])
    p = _poller(tm, monkeypatch, qty=0)
    p._flat_since = time.time() - 60.0
    p._sync_position_truth()
    assert tm.closed == []


def test_stale_sierra_state_is_noop(monkeypatch):
    """qty None (stale/missing file) → neither fill nor close (Rule 1)."""
    tm = _TM([_T(541), _T(539, state="FILLED")])
    p = _poller(tm, monkeypatch, qty=None)
    p._sync_position_truth()
    time.sleep(0.06)
    p._sync_position_truth()
    assert tm.filled == [] and tm.closed == []


def test_flag_off_is_noop(monkeypatch):
    monkeypatch.delenv("POSITION_TRUTH_SYNC_V1", raising=False)
    tm = _TM([_T(541)])
    p = _poller(tm, monkeypatch, qty=4)
    p._sync_position_truth()
    assert tm.filled == []


def test_shadow_trades_never_touched(monkeypatch):
    tm = _TM([_T(540, mode="shadow")])
    p = _poller(tm, monkeypatch, qty=0)
    p._sync_position_truth()
    time.sleep(0.06)
    p._sync_position_truth()
    assert tm.closed == [] and tm.filled == []


def test_position_reappearing_resets_flat_timer(monkeypatch):
    """Flat → position again → the close timer must reset (no stale close)."""
    tm = _TM([_T(541, state="FILLED")])
    p = _poller(tm, monkeypatch, qty=0)
    p._sync_position_truth()
    assert p._flat_since is not None
    import backend.v9.services.sierra_position_reconciler as rec
    monkeypatch.setattr(rec, "_sierra_state_qty", lambda: 4)
    p._sync_position_truth()
    assert p._flat_since is None and tm.closed == []
