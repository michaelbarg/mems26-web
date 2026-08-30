"""T-159: TPO history snapshotter must write TZ-aware timestamps.

The old code wrote naive UTC strings ("2026-08-27 14:30:00") which PG
timestamptz interprets in session TZ (+03) → 3h shift. Fix: +00:00 suffix.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.v9.services.tpo_history_snapshotter import TPOHistorySnapshotter

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def test_slot_ts_str_includes_tz():
    """The timestamp string must include +00:00 (not naive)."""
    et = datetime(2026, 8, 27, 10, 0, 0, tzinfo=ET)  # 10:00 ET = 14:00 UTC
    ts_str = TPOHistorySnapshotter.slot_start_ts_str(et)
    assert "+00:00" in ts_str, (
        f"T-159: timestamp must be TZ-aware, got naive: {ts_str}")
    assert "14:00:00" in ts_str, (
        f"T-159: 10:00 ET should be 14:00 UTC, got: {ts_str}")


def test_slot_ts_str_never_naive():
    """Regression: the old format was '%Y-%m-%d %H:%M:%S' (no TZ)."""
    et = datetime(2026, 8, 28, 9, 30, 0, tzinfo=ET)  # RTH open
    ts_str = TPOHistorySnapshotter.slot_start_ts_str(et)
    # Must not be a bare datetime without timezone
    assert ts_str.endswith("+00:00"), (
        f"T-159 REGRESSION: naive timestamp will shift +3h in PG: {ts_str}")


def test_slot_ts_str_dst_aware():
    """EDT (summer, -4h) vs EST (winter, -5h) must produce correct UTC."""
    # Summer: 10:00 EDT = 14:00 UTC
    summer = datetime(2026, 7, 15, 10, 0, 0, tzinfo=ET)
    assert "14:00:00+00:00" in TPOHistorySnapshotter.slot_start_ts_str(summer)

    # Winter: 10:00 EST = 15:00 UTC
    winter = datetime(2026, 1, 15, 10, 0, 0, tzinfo=ET)
    assert "15:00:00+00:00" in TPOHistorySnapshotter.slot_start_ts_str(winter)
