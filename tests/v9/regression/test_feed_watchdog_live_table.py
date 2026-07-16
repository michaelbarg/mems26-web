"""07-16 (Michael, live: "why no trades again") — feed_watchdog must read the
LIVE bars table, not the dead legacy one.

Root: _db_max_bar_age queried `v9_bars_5min` (frozen 22:55 yesterday, lag 1060min)
→ FEED_WATCHDOG HALT blocked EVERY live fire at the open. The canonical live
source (docs/SOURCE_OF_TRUTH.md) is `v9_bars_5min_woodies`. Source-pin test so an
accidental revert to the dead table is caught.
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "backend/v9/services/feed_watchdog.py"


def test_watchdog_queries_live_woodies_table():
    src = SRC.read_text(encoding="utf-8")
    m = re.search(r'read_scalar\(\s*"SELECT MAX\(ts\) FROM (\w+)"', src)
    assert m, "feed_watchdog MAX(ts) query not found"
    assert m.group(1) == "v9_bars_5min_woodies", (
        f"watchdog reads dead table '{m.group(1)}' — must be v9_bars_5min_woodies")


def test_no_dead_table_query_remains():
    src = SRC.read_text(encoding="utf-8")
    assert 'FROM v9_bars_5min"' not in src, "legacy dead-table query still present"
