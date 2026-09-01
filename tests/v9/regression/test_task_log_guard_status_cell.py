"""Regression: task_log_guard must read the STATUS COLUMN, not the whole row.

Bug (2026-09-01, cowork). Check 4 ("closed items must be verifiable") tested
`"✅" in " ".join(row_cells)`. T-204's status is `🔴 פתוח`, but its description
contains "(1) רישום ✅ candidate_ledger" — a sub-stage marked done inside prose.
The guard therefore declared an OPEN item "marked ✅ but has no line in
STATUS_BOARD.md" and exited non-zero.

Why it mattered: task_log_guard runs inside fire_drill.py, i.e. before every
session and before the 15:30 pre-open sizing gate. A false failure there blocks
the trading day on a punctuation mark.

The fix must not weaken the check: an item whose STATUS cell is ✅ and that has
no STATUS_BOARD line must still fail. Both directions are asserted below.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "task_log_guard", ROOT / "scripts" / "task_log_guard.py")
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def _cells(row: str):
    """Parse one markdown row the way the guard does."""
    rows = guard._rows(row)
    assert rows, f"row did not parse: {row!r}"
    return rows[0]["cells"]


# --- the false positive that blocked the gate -----------------------------

def test_tick_in_description_is_not_a_closed_status():
    """T-204's shape: open status, ✅ used as a sub-stage marker in prose."""
    row = (
        "| T-204 | 🔴 **אין לולאת-למידה** — חמישה שלבים: (1) רישום ✅ "
        "`candidate_ledger` · (2) הכרעה 🟠 חסר · (3) צבירה ✅ נבנה היום · "
        "(4) שיפוט — לא קיים | 🔴 פתוח | cc | **הצעד הבא:** לבנות שלב 4 |"
    )
    status = guard._status_cell(_cells(row))
    assert status == "🔴 פתוח"
    assert "✅" not in status


def test_description_leading_with_a_marker_is_not_mistaken_for_the_status():
    """A long cell may also START with a marker — length is what separates it."""
    long_desc = "🔴 " + ("צריך לתקן את זה " * 20)
    row = f"| T-99 | {long_desc} | ✅ נסגר | cowork | הצעד הבא: כלום |"
    assert guard._status_cell(_cells(row)) == "✅ נסגר"


def test_row_with_embedded_pipes_still_finds_a_real_status():
    """5 real rows embed '|' in code spans; cells[1] lands on garbage there."""
    row = (
        "| T-177 | תיאור עם טבלה בפנים: `mode | live | shadow` ועוד טקסט "
        "| 🔴 פתוח | cc | **הצעד הבא:** לאמת |"
    )
    cells = _cells(row)
    assert len(cells) > 4, "this row is expected to mis-split"
    assert cells[1] != "🔴 פתוח", "cells[1] is garbage here — that is the point"
    assert guard._status_cell(cells) == "🔴 פתוח"


# --- the check must still bite --------------------------------------------

def test_genuinely_closed_status_is_still_detected():
    row = "| T-1 | תיאור רגיל בלי סימנים | ✅ | cowork | הצעד הבא: אין |"
    assert "✅" in guard._status_cell(_cells(row))


def test_no_status_marker_at_all_returns_empty():
    row = "| T-2 | תיאור בלי סטטוס | פתוח | cowork | הצעד הבא: אין |"
    assert guard._status_cell(_cells(row)) == ""


@pytest.mark.parametrize("marker", ["🔴", "🟠", "🟡", "🔵", "✅"])
def test_every_documented_marker_is_recognised(marker):
    row = f"| T-3 | תיאור | {marker} פתוח | cowork | הצעד הבא: אין |"
    assert guard._status_cell(_cells(row)).startswith(marker)


# --- end-to-end on the real log -------------------------------------------

def test_real_task_log_has_no_false_closed_items():
    """Every ✅-status row in the live log must have a STATUS_BOARD line.

    This is the assertion the guard itself makes; pinning it here means a
    regression in _status_cell shows up as a test failure, not as a blocked
    trading morning.
    """
    log = (ROOT / "docs" / "plans" / "TASK_LOG.md").read_text(encoding="utf-8")
    board = (ROOT / "docs" / "plans" / "STATUS_BOARD.md").read_text(
        encoding="utf-8", errors="replace")
    offenders = [
        r["id"] for r in guard._rows(log)
        if "✅" in guard._status_cell(r["cells"]) and r["id"] not in board
    ]
    assert offenders == [], f"closed with no board line: {offenders}"
