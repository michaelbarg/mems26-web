"""T-527 (BRIEF §3.4, fix-agent 18.10) — SIERRA_FLAT on an entry that never happened.

Books, 18.10: 13 live rows closed as SIERRA_FLAT, 1 with pnl_sierra, 5 with pnl_usd=0/BE (pre-T-160
synthesized zeros), 7 UNPRICED. Four of them (#571 #955 #979 #1220) have entry_ts NULL, no
quality.sierra_order_id (no submit-ack), no DLL ENTRY fill within ±3 min and no broker round-trip:
POSITION_TRUTH closed a PENDING order that Sierra never held, and the books call it an unpriced
trade. Root: the SIERRA_FLAT close path treats "never filled" like "filled and flattened".

POSITION_TRUTH_UNFILLED_CANCEL_V1 (default OFF = byte-identical): a PENDING trade with no
submit-ack, Sierra flat past grace → the same SIERRA_FLAT close, outcome CANCELLED (P8 precedent
for ORDER_FAILED), quality.never_filled=True, pnl stays NULL (T-160). Nothing priced or invented.
"""
import time

import pytest

import backend.v9.services.fill_poller as fp


class _T:
    def __init__(self, tid, state="PENDING", mode="live", age_s=999, quality=None):
        self.id = tid
        self.state = state
        self.mode = mode
        self.entry_price = 7701.0
        self.quality = dict(quality) if quality is not None else {}

        class _C:
            def __init__(self, ts): self._ts = ts
            def timestamp(self): return self._ts
        self.created_at = _C(time.time() - age_s)


class _TM:
    """Records every close_trade call WITH its keyword arguments (the existing
    test_position_truth_sync fixture drops **kw — the override is the point here)."""
    def __init__(self, trades):
        self._trades = trades
        self.filled = []
        self.closed = []
    def get_active_trades(self):
        return list(self._trades)
    def on_fill(self, tid, px):
        self.filled.append((tid, px))
    def close_trade(self, tid, reason, exit_price=None, **kw):
        self.closed.append((tid, reason, exit_price, dict(kw)))


def _poller(tm, monkeypatch, qty=0):
    p = fp.FillPoller.__new__(fp.FillPoller)
    p._tm = tm
    p._flat_since = time.time() - 60.0   # Sierra flat long before the trade (grace elapsed)
    p._gateway = None
    import backend.v9.services.sierra_position_reconciler as rec
    monkeypatch.setattr(rec, "_sierra_state_qty", lambda: qty)
    monkeypatch.setattr(rec, "_sierra_state_avg_price", lambda: None)
    monkeypatch.setattr(p, "_notify_gateway_close", lambda *a, **k: None, raising=False)
    return p


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("POSITION_TRUTH_SYNC_V1", "1")
    monkeypatch.setenv("POSITION_TRUTH_GRACE_S", "0.05")
    monkeypatch.delenv("POSITION_TRUTH_UNFILLED_CANCEL_V1", raising=False)


# ── the #1220 shape: PENDING 21 s, no submit-ack, Sierra flat ──────────────────────────────────

def test_flag_off_is_byte_identical_plain_sierra_flat(monkeypatch):
    """Default: the close call is exactly the historical one — no override kw, quality untouched."""
    t = _T(1220, quality={"trigger": "OPENING_DRIVE", "contracts": 3})
    tm = _TM([t])
    _poller(tm, monkeypatch)._sync_position_truth()
    assert tm.closed == [(1220, "SIERRA_FLAT", None, {})]
    assert t.quality == {"trigger": "OPENING_DRIVE", "contracts": 3}


def test_flag_on_unacked_pending_closes_cancelled(monkeypatch):
    """ON: same SIERRA_FLAT close, outcome CANCELLED, never_filled marked; no price invented."""
    monkeypatch.setenv("POSITION_TRUTH_UNFILLED_CANCEL_V1", "1")
    t = _T(1220, quality={"trigger": "OPENING_DRIVE", "contracts": 3})
    tm = _TM([t])
    _poller(tm, monkeypatch)._sync_position_truth()
    assert tm.closed == [(1220, "SIERRA_FLAT", None, {"outcome_override": "CANCELLED"})]
    assert t.quality["never_filled"] is True
    assert "T-527" in t.quality["never_filled_reason"]
    assert t.quality["trigger"] == "OPENING_DRIVE" and t.quality["contracts"] == 3   # nothing dropped
    assert tm.filled == []


def test_flag_on_acked_pending_keeps_plain_sierra_flat(monkeypatch):
    """ON: a PENDING trade WITH a submit-ack may have filled and been flattened — not ours to cancel."""
    monkeypatch.setenv("POSITION_TRUTH_UNFILLED_CANCEL_V1", "1")
    t = _T(3140, quality={"sierra_order_id": 11431})
    tm = _TM([t])
    _poller(tm, monkeypatch)._sync_position_truth()
    assert tm.closed == [(3140, "SIERRA_FLAT", None, {})]
    assert "never_filled" not in t.quality


def test_flag_on_filled_trade_keeps_plain_sierra_flat(monkeypatch):
    """ON: a FILLED trade that Sierra flattened (T-10 EOD, stop) is a real trade — plain SIERRA_FLAT,
    its price belongs to the broker record (activity stream / broker_truth), never to this path."""
    monkeypatch.setenv("POSITION_TRUTH_UNFILLED_CANCEL_V1", "1")
    t = _T(939, state="FILLED", quality={"sierra_order_id": 10810})
    tm = _TM([t])
    _poller(tm, monkeypatch)._sync_position_truth()
    assert tm.closed == [(939, "SIERRA_FLAT", None, {})]
    assert "never_filled" not in t.quality


def test_flag_on_young_unacked_pending_is_not_touched(monkeypatch):
    """ON must not widen the close: a brand-new un-acked PENDING (still filling) survives the pass."""
    monkeypatch.setenv("POSITION_TRUTH_UNFILLED_CANCEL_V1", "1")
    t = _T(542, age_s=0)
    tm = _TM([t])
    _poller(tm, monkeypatch)._sync_position_truth()
    assert tm.closed == [] and "never_filled" not in t.quality


def test_flag_on_sierra_holds_position_no_close(monkeypatch):
    """ON changes nothing on the position-held branch: an un-acked PENDING is neither filled (K1e)
    nor cancelled while Sierra holds a position."""
    monkeypatch.setenv("POSITION_TRUTH_UNFILLED_CANCEL_V1", "1")
    t = _T(652)
    tm = _TM([t])
    _poller(tm, monkeypatch, qty=3)._sync_position_truth()
    assert tm.closed == [] and tm.filled == [] and t.state == "PENDING"
