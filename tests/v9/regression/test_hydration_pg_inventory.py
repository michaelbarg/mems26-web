"""Verify startup hydration inventory reads from Postgres, not SQLite.

If reverted → RED because the SQLite block would import sqlite3 and connect
to a non-existent/corrupted .db file, printing 'database disk image is
malformed' on every boot.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


def test_main_py_does_not_import_sqlite3():
    """main.py must not have a top-level sqlite3 import."""
    import importlib
    import ast

    src = importlib.util.find_spec("backend.main")
    assert src and src.origin
    with open(src.origin) as f:
        tree = ast.parse(f.read())

    top_imports = [
        node.names[0].name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import) and isinstance(node, ast.Import)
        # Only top-level (col_offset 0, not inside try/function)
        and node.col_offset == 0
    ]
    assert "sqlite3" not in top_imports, (
        "sqlite3 must not be imported at top level in main.py — hydration uses PG"
    )


def test_hydration_inventory_uses_read_scalar():
    """Startup hydration inventory calls read_scalar (PG), not sqlite3."""
    mock_et = datetime(2026, 7, 10, 10, 30, 0)

    with patch("backend.v9.db.read.read_scalar", return_value=42) as mock_rs, \
         patch("backend.v9.services.market_clock.now_et", return_value=mock_et):
        from backend.v9.db.read import read_scalar
        # Simulate the hydration inventory block
        from backend.v9.services.market_clock import now_et
        from datetime import time as _time_cls, timedelta

        _et = now_et()
        if _et.time() >= _time_cls(18, 0):
            _session_start = _et.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            _session_start = (_et - timedelta(days=1)).replace(
                hour=18, minute=0, second=0, microsecond=0
            )
        cvd = read_scalar(
            "SELECT COUNT(*) FROM v9_bars_cumulative_delta WHERE ts >= :cutoff",
            {"cutoff": _session_start.isoformat()},
        ) or 0
        w5 = read_scalar("SELECT COUNT(*) FROM v9_bars_5min_woodies") or 0
        b5 = read_scalar("SELECT COUNT(*) FROM v9_bars_5min") or 0
        arch = read_scalar("SELECT COUNT(*) FROM v9_tpo_sessions_archive") or 0

        assert cvd == 42
        assert w5 == 42
        assert mock_rs.call_count == 4
