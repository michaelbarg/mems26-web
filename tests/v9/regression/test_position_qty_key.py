"""Phase 0 AC — sierra_state.json uses 'position_qty', never 'position_quantity'.

Verifies:
1. The actual export file uses the correct key.
2. All Python readers in backend/ and scripts/ reference 'position_qty', not
   the misspelled 'position_quantity' (which returns None → false-flat).
"""

import json
import subprocess
import os
import pathlib
import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
EXPORT_PATH = pathlib.Path(os.path.expanduser(
    "~/SierraChart_Data/v9_export/sierra_state.json"
))


def test_sierra_state_json_uses_position_qty():
    """The live export file must contain 'position_qty', not 'position_quantity'."""
    if not EXPORT_PATH.exists():
        pytest.skip("sierra_state.json not present on this machine")
    data = json.loads(EXPORT_PATH.read_text())
    assert "position_qty" in data, "position_qty key missing from sierra_state.json"
    assert "position_quantity" not in data, (
        "position_quantity should NOT exist — readers would silently get None"
    )


def test_no_python_code_reads_position_quantity():
    """No .py file in backend/ or scripts/ should reference 'position_quantity'."""
    result = subprocess.run(
        ["grep", "-rn", "position_quantity", "--include=*.py",
         str(REPO / "backend"), str(REPO / "scripts")],
        capture_output=True, text=True,
    )
    hits = [
        line for line in result.stdout.strip().splitlines()
        if line and not line.strip().startswith("#")  # ignore comments
    ]
    assert len(hits) == 0, (
        f"Found {len(hits)} references to 'position_quantity' "
        f"(should be 'position_qty'):\n" + "\n".join(hits)
    )
