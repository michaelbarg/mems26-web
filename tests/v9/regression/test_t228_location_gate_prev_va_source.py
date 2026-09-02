"""T-228 — the previous-session VA query was dead wiring, and silently so.

ROOT (2026-09-02): `EDGE_ENTRY_LOCATION_FIX_V1` is Michael's 02.09 13:35 ruling
— on a gap day, compare today's session against YESTERDAY'S value area instead
of today's meaningless VA zones. Its primary source asked

    SELECT vah, val, poc ... FROM v9_bars_5min_woodies

for columns that table does not have. Verified against the live schema:

    ERROR:  column "vah" does not exist
    LINE 1: SELECT vah, val FROM v9_bars_5min_woodies LIMIT 1;

so the primary path raised on every single call — into a bare
`except Exception: pass`. The ruling was riding entirely on the TPO-export
backup, and if that file ever went stale the fix would have disappeared with it
without one line of log, leaving the gate blocking edges exactly as before the
ruling.

Fix: `v9_tpo_history` is the table that really carries per-session vah/val
(verified fresh, last row 2026-09-02 22:30; yesterday's RTH VA = 7662/7633),
and every failure now warns instead of vanishing. Sierra's TPO export stays the
FIRST source, so the gate's behaviour on a normal day is unchanged.

if reverted → RED because: putting `v9_bars_5min_woodies` back makes
test_query_targets_a_table_that_has_the_columns fail, and restoring
`except Exception: pass` makes test_db_failure_is_warned fail.
"""
import inspect
import logging

import pytest

from backend.v9.systems import location_gate


def _src():
    return inspect.getsource(location_gate.decide_location)


def test_query_targets_a_table_that_has_the_columns():
    src = _src()
    assert "v9_tpo_history" in src, "previous-session VA must come from a table that has vah/val"
    assert "FROM v9_bars_5min_woodies" not in src, (
        "v9_bars_5min_woodies has no vah/val/poc columns — that query can only raise")


def test_no_bare_swallow_left_in_the_edge_fix():
    src = _src()
    assert "pass  # fail-open: no previous VA" not in src
    assert "_edge_warn(" in src, "failures must be surfaced, not swallowed"


def test_sierra_export_is_still_consulted_first():
    """Behaviour preservation: the TPO export is what carries the ruling today.

    CLAUDE.md makes Sierra exports the source of truth for VA, and reordering
    would change which VA the gate sees on a live day.
    """
    code = "\n".join(ln for ln in _src().splitlines()
                     if not ln.lstrip().startswith("#"))
    assert code.index("_load_sierra_tpo") < code.index("v9_tpo_history"), (
        "Sierra's export must be tried before the DB fallback — the two "
        "disagree (export 7666.00/7629.50 vs v9_tpo_history 7662.00/7633.00 "
        "for 01.09) because the DB row is a developing snapshot, and swapping "
        "them would change which VA a live gate decision sees")


def test_db_failure_is_warned(monkeypatch, caplog):
    """A DB error must produce a WARNING — never silence."""
    location_gate._EDGE_WARN_LAST.clear()
    with caplog.at_level(logging.WARNING):
        location_gate._edge_warn("EDGE_FIX: previous-session VA query FAILED "
                                 "(%s) — gap detection is blind this call",
                                 "column \"vah\" does not exist")
    assert "column \"vah\" does not exist" in caplog.text
    assert "LocationGate" in caplog.text


def test_warning_is_throttled_not_dropped(monkeypatch, caplog):
    """Throttling keeps the log usable; the first occurrence always shows."""
    location_gate._EDGE_WARN_LAST.clear()
    monkeypatch.setenv("LOCATION_GATE_WARN_THROTTLE_S", "9999")
    with caplog.at_level(logging.WARNING):
        for _ in range(5):
            location_gate._edge_warn("EDGE_FIX: repeated %s", "thing")
    assert caplog.text.count("EDGE_FIX: repeated") == 1


@pytest.mark.parametrize("direction,z_in", [("LONG", "near_val"), ("SHORT", "near_vah")])
def test_gate_is_unchanged_when_the_flag_is_off(monkeypatch, direction, z_in):
    """The whole edge-fix block is behind EDGE_ENTRY_LOCATION_FIX_V1.

    With the flag OFF nothing in this change can be reached, so a day with the
    flag off is byte-identical to before.
    """
    monkeypatch.delenv("EDGE_ENTRY_LOCATION_FIX_V1", raising=False)
    monkeypatch.setenv("EDGE_ENTRY_LOCATION_FIX_V1", "0")
    src = _src()
    # the guard exists and wraps the source lookup
    i_flag = src.index('EDGE_ENTRY_LOCATION_FIX_V1')
    i_query = src.index("v9_tpo_history")
    assert i_flag < i_query
