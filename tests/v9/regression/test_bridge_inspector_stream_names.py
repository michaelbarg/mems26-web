"""Verify that every table_name in STREAM_CHECKS actually exists in the DB.

Prevents false 'DEAD' reports from stream-name/table-name mismatches.
"""
import pytest
from backend.v9.systems.build_status.bridge_inspector import STREAM_CHECKS
from backend.v9.db.read import read_one


@pytest.mark.parametrize("label,table,ts_col,threshold", STREAM_CHECKS)
def test_stream_table_exists_in_db(label, table, ts_col, threshold):
    """Each STREAM_CHECKS table must exist in the DB (Postgres).
    We don't require data — just that the table is queryable."""
    try:
        row = read_one(f"SELECT 1 FROM {table} LIMIT 1")
        # row can be None (empty table) — that's OK, the table exists
    except Exception as e:
        err = str(e)
        if "does not exist" in err or "UndefinedTable" in err:
            pytest.fail(
                f"STREAM_CHECKS label='{label}' references table '{table}' "
                f"which does not exist in the DB. Fix the table name."
            )
        # Other errors (connection, etc.) are not table-name issues
        pytest.skip(f"DB error (not a table-name issue): {err[:80]}")


def test_stream_labels_match_bridge_push_names():
    """Labels should match what the bridge actually pushes (for UI clarity)."""
    labels = {s[0] for s in STREAM_CHECKS}
    # These are the corrected names that match bridge stream names
    assert "bars_5min" in labels, "Should be 'bars_5min' not '5min_bars'"
    assert "tpo" in labels, "Should be 'tpo' not 'tpo_bars'"
    assert "tick_reversal_15" in labels, "Should be 'tick_reversal_15' not 'tick_reversal'"
    # Old wrong names should NOT be present
    assert "5min_bars" not in labels
    assert "tpo_bars" not in labels
    assert "tick_reversal" not in labels
