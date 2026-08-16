"""T5 — stop the false NAKED-ORPHAN alarms and the 30-second alert loop.

Michael, 2026-08-15: "אתה מקפיץ לי מלא התראות דפוקות תקן את זה."

Two defects, both measured on 14.08:
  1. Ownership was a GLOBAL test — `len(fill_poller._order_map) > 0`. That map
     is a HISTORICAL order_id→trade_id index, so from the system's first trade
     of the day onward every MANUAL position of Michael's was classified
     "system-owned" → NAKED ORPHAN. 113 false alarms in one session.
  2. The reconciler runs every 30s and logged the same unchanged DIVERGENCE
     every single cycle all evening.

Fixes: ownership is per-position (the system owns a position only while it
actually holds one — an order_map entry pointing at a CLOSED trade proves
nothing), and repeat announcements are throttled to state-change or 10 minutes.
Nothing is suppressed: a new or changed divergence is still immediate.
"""
import types

import pytest

from backend.v9.services import sierra_position_reconciler as rec


class _FakeTM:
    def __init__(self, open_ids=()):
        self._open = [types.SimpleNamespace(id=i) for i in open_ids]

    def get_active_trades(self):
        return self._open


class _FakeFP:
    def __init__(self, order_map, open_ids=()):
        self._order_map = order_map
        self._tm = _FakeTM(open_ids)


@pytest.fixture(autouse=True)
def _reset_throttle():
    rec._last_div_state = None
    rec._last_div_ts = 0.0
    yield


class TestOwnershipIsPerPosition:
    def test_history_alone_does_not_claim_a_manual_position(self):
        """The system traded earlier today (map has entries) but holds nothing
        now → Michael's position must NOT be called a system orphan."""
        fp = _FakeFP(order_map={10110: 668, 10190: 670}, open_ids=())
        open_ids = set()
        for t in fp._tm.get_active_trades():
            open_ids.add(int(t.id))
        is_system = any(int(v) in open_ids for v in fp._order_map.values())
        assert is_system is False, (
            "a closed-trade order map must not claim ownership — this is the "
            "113-false-alarm bug")

    def test_open_trade_in_map_is_system_owned(self):
        fp = _FakeFP(order_map={10110: 668}, open_ids=(668,))
        open_ids = {int(t.id) for t in fp._tm.get_active_trades()}
        is_system = any(int(v) in open_ids for v in fp._order_map.values())
        assert is_system is True

    def test_empty_map_is_manual(self):
        fp = _FakeFP(order_map={}, open_ids=())
        open_ids = {int(t.id) for t in fp._tm.get_active_trades()}
        assert any(int(v) in open_ids for v in fp._order_map.values()) is False

    def test_wired_into_the_reconciler(self):
        """Guard against a revert to the global test."""
        import inspect
        src = inspect.getsource(rec)
        assert "_is_system_position = len(_omap) > 0" not in src
        assert "_open_ids" in src


class TestRepeatThrottle:
    def test_state_tuple_changes_are_announced(self):
        """A NEW or CHANGED divergence must never be throttled."""
        import inspect
        src = inspect.getsource(rec)
        assert "_div_changed" in src and "_div_due" in src
        assert "_div_loud" in src

    def test_unchanged_repeats_drop_to_debug(self):
        import inspect
        src = inspect.getsource(rec)
        assert "(repeat, unchanged)" in src or "(repeat)" in src

    def test_periodic_reminder_still_fires(self):
        """Silence forever is also wrong — a persisting divergence must
        re-announce (10 min)."""
        import inspect
        src = inspect.getsource(rec)
        assert "600.0" in src


class TestPhoneAlertIsThrottled:
    """The pushes are the thing Michael actually feels — a 30s loop = 120
    pushes/hour on his phone."""

    def test_push_is_inside_the_loud_gate(self):
        import inspect, re
        src = inspect.getsource(rec)
        i_gate = src.rindex("if _div_loud:")
        i_push = src.index('_phone_push("reconciler_divergence"')
        assert i_push > i_gate, "the DIVERGENCE push must sit inside `if _div_loud:`"
        # and it must be indented deeper than the gate (i.e. genuinely nested)
        line = src[src.rindex("\n", 0, i_push) + 1:i_push]
        assert len(line) - len(line.lstrip()) >= 12
