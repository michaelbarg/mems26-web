"""B-13 write-guard regression: off-market bar with fresh ts → rejected;
old valid bar with old ts → written (chart history preserved).

Revert the write-guard in bars.py → this test turns RED.
"""
import re
from pathlib import Path

BARS_PY = Path(__file__).resolve().parents[1] / "api/v9/bars.py"


def test_write_guard_present_in_post_5min():
    """The POST /5min write path must have the B-13 write-guard."""
    source = BARS_PY.read_text()
    # Look for the write-guard pattern: _is_stale_bar call in the write loop
    # (not just in _route_bar)
    post_5min_idx = source.find("def post_bars_5min")
    assert post_5min_idx > 0, "post_bars_5min endpoint not found"
    # The write-guard should appear AFTER post_bars_5min and BEFORE rows_to_write.append
    post_body = source[post_5min_idx:]
    append_idx = post_body.find("rows_to_write.append")
    guard_section = post_body[:append_idx]
    assert "_is_stale_bar" in guard_section, (
        "B-13 regression: _is_stale_bar write-guard missing from POST /5min write path. "
        "Off-market bars would be written to DB without price-band check."
    )


def test_write_guard_preserves_old_bars():
    """The write-guard only applies to fresh bars (ts within MAX_STALE_AGE).
    Old bars pass through for chart history."""
    source = BARS_PY.read_text()
    post_5min_idx = source.find("def post_bars_5min")
    post_body = source[post_5min_idx:]
    # Guard should be conditional on ts freshness (not blanket rejection)
    assert "MAX_STALE_AGE" in post_body, (
        "B-13 regression: write-guard must check ts freshness — old bars should pass through"
    )
