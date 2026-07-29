"""The opening-entry anchor must see the SAME clock in every ts format.

Michael 2026-07-29: yesterday's two big trades — the drive short at the open and
the reject long after it — were never signalled. Root: the open-bar anchor
compares hour:minute on a datetime parsed from the bar ts in WHATEVER timezone
the format implied (epoch → Israel, naive ISO → left as UTC). The real 16:30 IL
open bar arrived as naive "13:30" and was never recognised as the open; the
engine waited forever. Meanwhile boot-replays produced phantom OPENING_DRIVEs at
07:38 IL, all blocked by session_gate_closed.

These tests pin the normalisation contract directly on the source.
"""
import inspect
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IL = ZoneInfo("Asia/Jerusalem")


def _normalise(ts_raw):
    """Mirror of the fixed block in five_min_system."""
    if isinstance(ts_raw, (int, float)):
        return datetime.fromtimestamp(ts_raw / 1000 if ts_raw > 1e12 else ts_raw, tz=IL)
    p = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
    if p.tzinfo is None:
        p = p.replace(tzinfo=timezone.utc)
    return p.astimezone(IL)


OPEN_EPOCH = datetime(2026, 7, 29, 13, 30, tzinfo=timezone.utc).timestamp()


def test_epoch_open_bar_is_recognised():
    dt = _normalise(OPEN_EPOCH)
    assert (dt.hour, dt.minute) == (16, 30)


def test_naive_iso_utc_open_bar_is_recognised():
    """THE bug: naive '13:30' UTC parsed as 13:30 local → never the open."""
    dt = _normalise("2026-07-29T13:30:00")
    assert (dt.hour, dt.minute) == (16, 30)


def test_aware_iso_open_bar_is_recognised():
    dt = _normalise("2026-07-29T13:30:00+00:00")
    assert (dt.hour, dt.minute) == (16, 30)
    dt = _normalise("2026-07-29T16:30:00+03:00")
    assert (dt.hour, dt.minute) == (16, 30)


def test_all_formats_agree_on_the_same_instant():
    a = _normalise(OPEN_EPOCH)
    b = _normalise("2026-07-29T13:30:00")
    c = _normalise("2026-07-29T13:30:00Z")
    assert a == b == c


def test_source_normalises_naive_iso_as_utc():
    """Pin the fix in the real file, not just the mirror."""
    import backend.v9.systems.five_min.five_min_system as fm
    src = inspect.getsource(fm)
    assert "naive ISO from the bridge is UTC" in src
    assert "astimezone(_IL)" in src
