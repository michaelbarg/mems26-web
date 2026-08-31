"""T-183: a live slot that blocks fires while holding nothing must ALARM.

Live finding 2026-08-31: the live path was blocked SILENTLY for ~3.5h
(17:45→21:07). The books were closed in the DB but gateway.live_slot stayed
occupied, so every new live fire was refused with live_blocked_by=
"live_slot_occupied" — and nothing said so. Third instance of the class:
I-57 (07-08, patched at ONE call site in trades.py) and T-178 (08-31).

Why the existing reconcile missed it — the finding this test pins down:
MISMATCH_PHANTOM_SLOT requires `slot_occupied and not db_open and
tm_in_position is False`. `db_open_ids` is built from `state NOT IN ('CLOSED')`
with NO mode filter, so the SHADOW trades firing all evening kept db_open True
→ the phantom branch never ran. Instead it fell through to the naked-stop path
and logged 403 CRITICAL "NAKED_STOP_SUSPECT — in position" lines, i.e. the
opposite of the truth. Raw evidence: grep -c PHANTOM_SLOT backend.err.log → 0.

test_shadow_trades_do_not_mask_a_stuck_slot is the anti-regression for exactly
that masking. Removing the `mode IN ('live','demo')` filter in
gather_stuck_slot, or the dwell threshold in evaluate_stuck_slot, turns these
RED.
"""
import pytest

from backend.v9.services import reconcile as rc
from backend.v9.services.reconcile import (
    STUCK_SLOT_THRESHOLD_S,
    evaluate_stuck_slot,
    gather_stuck_slot,
)

T0 = 1_000_000.0


# ------------------------------------------------------------- pure verdict

def test_free_slot_is_never_stuck():
    st = evaluate_stuck_slot(slot_occupied=False, slot_trade_id=None,
                             live_open_ids=[], stuck_since=None, now=T0)
    assert st.stuck is False and st.alarm is False


def test_slot_holding_a_genuinely_open_trade_is_healthy():
    st = evaluate_stuck_slot(slot_occupied=True, slot_trade_id=939,
                             live_open_ids=[939], stuck_since=None, now=T0)
    assert st.stuck is False and st.alarm is False
    assert st.stuck_since is None       # nothing to remember


def test_stuck_slot_below_threshold_does_not_alarm_yet():
    """A fresh mismatch is an entry/fill race, not a blockage."""
    st = evaluate_stuck_slot(slot_occupied=True, slot_trade_id=939,
                             live_open_ids=[], stuck_since=T0, now=T0 + 60)
    assert st.stuck is True
    assert st.alarm is False
    assert st.stuck_since == T0         # dwell clock started and is carried


def test_stuck_slot_past_threshold_alarms():
    st = evaluate_stuck_slot(slot_occupied=True, slot_trade_id=939,
                             live_open_ids=[], stuck_since=T0,
                             now=T0 + STUCK_SLOT_THRESHOLD_S + 1)
    assert st.stuck is True and st.alarm is True
    assert "LIVE PATH BLOCKED" in st.detail
    assert "939" in st.detail


def test_the_actual_0831_blackout_alarms():
    """The real shape: slot holds #939, closed in the books, 3.5h elapsed."""
    st = evaluate_stuck_slot(slot_occupied=True, slot_trade_id=939,
                             live_open_ids=[], stuck_since=T0,
                             now=T0 + 3.5 * 3600)
    assert st.alarm is True
    assert st.stuck_seconds == pytest.approx(12600.0)


def test_unreadable_slot_id_still_alarms():
    """T-187's dict/scalar trap must not become a blind spot here."""
    st = evaluate_stuck_slot(slot_occupied=True, slot_trade_id=None,
                             live_open_ids=[], stuck_since=T0,
                             now=T0 + STUCK_SLOT_THRESHOLD_S + 1)
    assert st.stuck is True and st.alarm is True
    assert "no readable trade_id" in st.detail


def test_recovery_clears_the_dwell_clock():
    """Once the slot is released the alarm state must reset, not latch."""
    st = evaluate_stuck_slot(slot_occupied=False, slot_trade_id=None,
                             live_open_ids=[], stuck_since=T0,
                             now=T0 + 99999)
    assert st.stuck is False and st.alarm is False and st.stuck_since is None


# --------------------------------------------- the masking that hid it live

def _fake_gateway(slot_trade_id=939):
    class _GW:
        live_slot = {"trade_id": str(slot_trade_id), "mode": "live"}
        demo_slot = None
    return _GW()


def test_shadow_trades_do_not_mask_a_stuck_slot(monkeypatch):
    """THE 08-31 regression: open SHADOW rows must not make the slot look fine.

    gather_stuck_slot must query live/demo only. If the mode filter is dropped,
    the shadow rows come back, the slot id is not among them anyway... so this
    asserts on the QUERY itself, which is where the masking lived.
    """
    seen = {}

    def _fake_read_all(sql, params):
        seen["sql"] = " ".join(sql.split())
        return []                      # no OPEN LIVE trades — books are closed

    monkeypatch.setattr("backend.v9.db.read.read_all", _fake_read_all)

    st = gather_stuck_slot(_fake_gateway(), stuck_since=T0 - 3600)

    assert "mode IN ('live','demo')" in seen["sql"], (
        "gather_stuck_slot must exclude shadow rows — open shadow trades are "
        "exactly what masked MISMATCH_PHANTOM_SLOT on 2026-08-31")
    assert st.stuck is True and st.alarm is True


def test_db_read_failure_is_not_reported_as_stuck(monkeypatch):
    """Rule 1: a failed read is honest 'unknown', never a fabricated alarm."""
    def _boom(sql, params):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("backend.v9.db.read.read_all", _boom)
    st = gather_stuck_slot(_fake_gateway(), stuck_since=T0 - 3600)
    assert st.stuck is False and st.alarm is False
    assert "unknown" in st.detail


def test_gather_reads_dict_shaped_slot(monkeypatch):
    """The slot is a dict since 08-08 (ef01d040) — the T-187 shape trap."""
    monkeypatch.setattr("backend.v9.db.read.read_all", lambda sql, p: [{"id": 939}])
    st = gather_stuck_slot(_fake_gateway(939), stuck_since=None)
    assert st.slot_trade_id == 939
    assert st.stuck is False, "slot holds a genuinely open live trade"


# ------------------------------------------------------- alert-only contract

def test_alarm_never_touches_the_execution_path():
    """The whole point: this observes, it must not release or write.

    A future edit that 'helpfully' auto-frees the slot has to delete this.
    """
    import inspect
    src = inspect.getsource(rc.evaluate_stuck_slot) + inspect.getsource(rc.gather_stuck_slot)
    for forbidden in ("live_slot =", "demo_slot =", "on_trade_close",
                      "safe_execute", "write_exit", "FLATTEN", "commit("):
        assert forbidden not in src, (
            f"stuck-slot check must be ALERT-ONLY; found {forbidden!r}")
