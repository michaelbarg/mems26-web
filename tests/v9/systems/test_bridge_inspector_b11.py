"""B-11 regression: bridge_inspector must ORDER BY {ts_col}, not rowid.

rowid is a SQLite-ism; Postgres has no rowid column, causing every stream
to return 'column "rowid" does not exist' → false DEAD/BLOCKED/0-armed.

This test guarantees that reverting to rowid turns RED.
"""

import re

from pathlib import Path

INSPECTOR = Path(__file__).resolve().parents[3] / (
    "backend/v9/systems/build_status/bridge_inspector.py"
)


def test_no_rowid_in_order_by():
    """ORDER BY rowid must never appear — PG doesn't have it (B-11)."""
    source = INSPECTOR.read_text()
    matches = re.findall(r"ORDER BY\s+rowid", source, re.IGNORECASE)
    assert matches == [], (
        f"B-11 regression: found {len(matches)} 'ORDER BY rowid' in "
        f"bridge_inspector.py — must use ORDER BY {{ts_col}} for PG compat"
    )


def test_order_by_uses_ts_col():
    """Both queries must ORDER BY {ts_col} (interpolated from STREAM_CHECKS)."""
    source = INSPECTOR.read_text()
    # The f-string pattern: ORDER BY {ts_col} DESC
    order_clauses = re.findall(r"ORDER BY\s+\{ts_col\}\s+DESC", source)
    assert len(order_clauses) == 2, (
        f"Expected 2 'ORDER BY {{ts_col}} DESC' clauses, found {len(order_clauses)}"
    )
