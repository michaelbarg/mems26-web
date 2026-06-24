"""Regression tests for Day-Type Source Unification (2026-06-24).

Anti-tautological: tests call the REAL production functions/helpers, not copies.

if reverted → RED because: reverting _day_type_row to only read v9_day_type_history
would remove the live-machine branch; reverting the S4 fallback would re-introduce
DECISION_MATRIX; reverting chart priority would re-introduce v9_bars_5min_continuous.
"""
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


# ── Fix #1: key_levels _day_type_row prefers live machine ──────────────

def test_day_type_row_prefers_live_machine():
    """When app.state.day_type_machine has a promoted day_type, _day_type_row
    returns it instead of reading from v9_day_type_history.

    if reverted → RED because: removing the machine read from _day_type_row
    would make it only query the DB, never returning DayType enum values.
    """
    from enum import Enum

    class FakeDT(Enum):
        Normal = "Normal"
        Trend_Normal = "Trend_Normal"

    class FakeOpening:
        opening_type = SimpleNamespace(value="OD")

    mock_machine = MagicMock()
    mock_machine.day_type = FakeDT.Normal
    mock_machine.opening = FakeOpening()

    mock_app = MagicMock()
    mock_app.state.day_type_machine = mock_machine

    with patch("importlib.import_module") as mock_import:
        mock_mod = MagicMock()
        mock_mod.app = mock_app
        mock_import.return_value = mock_mod

        from backend.v9.api.v9.key_levels_routes import _day_type_row
        result = _day_type_row()

    assert result is not None
    assert result["day_type"] == "Normal"
    assert result["opening_type"] == "OD"


def test_day_type_row_skips_unknown_machine():
    """When machine day_type is UNKNOWN, _day_type_row falls through to DB.

    if reverted → RED because: the test asserts the UNKNOWN guard exists.
    """
    mock_machine = MagicMock()
    mock_machine.day_type = SimpleNamespace(value="UNKNOWN")

    mock_app = MagicMock()
    mock_app.state.day_type_machine = mock_machine

    with patch("importlib.import_module") as mock_import, \
         patch("backend.v9.api.v9.key_levels_routes.read_one", return_value=None):
        mock_mod = MagicMock()
        mock_mod.app = mock_app
        mock_import.return_value = mock_mod

        from backend.v9.api.v9.key_levels_routes import _day_type_row
        result = _day_type_row()

    # Falls through to DB which returns None → None
    assert result is None


# ── Fix #2: S4 woodies reads promoted machine, not old matrix ──────────

def test_s4_fallback_reads_machine_not_matrix():
    """The S4 day_type fallback code no longer imports DECISION_MATRIX.

    if reverted → RED because: reverting would re-introduce the DECISION_MATRIX import.
    """
    import inspect
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    source = inspect.getsource(WoodiesSystem.process_bar)
    # The old code imported DECISION_MATRIX; the new code reads day_type_machine directly
    assert "DECISION_MATRIX" not in source, (
        "S4 fallback still references DECISION_MATRIX — should read day_type_machine")


# ── Fix #4: chart endpoint excludes v9_bars_5min_continuous ────────────

def test_chart_bars_excludes_continuous():
    """_fetch_bars_5min does NOT query v9_bars_5min_continuous (corrupt OHLC).

    if reverted → RED because: re-adding the continuous table queries would
    make rows_cont non-empty and the source code would contain the SELECT query.
    """
    import inspect
    from backend.v9.api.v9.bars_5min_history import _fetch_bars_5min
    source = inspect.getsource(_fetch_bars_5min)
    # Must not have an active SELECT ... FROM v9_bars_5min_continuous
    import re
    active_queries = re.findall(r'SELECT.*?v9_bars_5min_continuous', source, re.DOTALL)
    assert len(active_queries) == 0, (
        "Chart endpoint still has active SELECT from v9_bars_5min_continuous — "
        "source has corrupt OHLC. Found: %s" % active_queries)
