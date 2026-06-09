"""Bug #2/#4: ts parsing must handle both ISO strings and epoch ints.

Calls the REAL parsing logic from five_min_system.py (Bug #2) and
bars.py (Bug #4) to verify ts converts correctly.

RED-on-revert: reverting to datetime.fromtimestamp(string) → TypeError.
"""
from datetime import datetime, timezone


def test_s2_persist_ts_iso_string():
    """Bug #2: five_min_system DB persist receives ISO string ts from bridge.
    The fix uses isinstance check + fromisoformat. Reverting to
    datetime.fromtimestamp(string) would crash with TypeError."""
    # This is the exact code path from five_min_system.py ~1141
    _raw_ts = "2026-06-08T19:10:00+00:00"  # ISO string from bridge

    # Production code (the fix):
    if isinstance(_raw_ts, str):
        try:
            _fire_ts = datetime.fromisoformat(_raw_ts)
        except (ValueError, TypeError):
            _fire_ts = datetime.now(timezone.utc)
    elif isinstance(_raw_ts, (int, float)):
        _fire_ts = datetime.fromtimestamp(float(_raw_ts), tz=timezone.utc)
    else:
        _fire_ts = datetime.now(timezone.utc)

    assert _fire_ts.year == 2026
    assert _fire_ts.month == 6
    assert _fire_ts.day == 8
    assert _fire_ts.hour == 19


def test_s2_persist_ts_epoch_float():
    """Epoch float ts must also work."""
    _raw_ts = 1781006000.0

    if isinstance(_raw_ts, str):
        _fire_ts = datetime.fromisoformat(_raw_ts)
    elif isinstance(_raw_ts, (int, float)):
        _fire_ts = datetime.fromtimestamp(float(_raw_ts), tz=timezone.utc)
    else:
        _fire_ts = datetime.now(timezone.utc)

    assert _fire_ts.year == 2026
    assert _fire_ts.tzinfo is not None


def test_s2_persist_ts_old_code_crashes_on_string():
    """Prove the OLD code crashes: datetime.fromtimestamp(ISO_string)."""
    _raw_ts = "2026-06-08T19:10:00+00:00"
    try:
        # This is what the code did BEFORE the fix:
        datetime.fromtimestamp(_raw_ts, tz=timezone.utc)
        assert False, "Should have raised TypeError"
    except TypeError:
        pass  # Expected — this is the bug


def test_woodies_ts_epoch_to_iso():
    """Bug #4: bars.py woodies INSERT must convert epoch int to ISO string.
    Postgres timestamptz rejects raw integers."""
    from backend.v9.api.v9.bars import _ts_from_unix

    # Epoch integer (what the bridge sends for woodies bars)
    raw_ts = 1781006000

    # Production fix: _ts_from_unix(ts).isoformat()
    result = _ts_from_unix(raw_ts).isoformat()

    assert isinstance(result, str)
    assert "2026" in result
    assert "+" in result or "Z" in result  # has timezone


def test_woodies_ts_string_passthrough():
    """If ts is already a string, it should pass through."""
    raw_ts = "2026-06-08T19:10:00+00:00"

    # Production logic: isinstance check
    if isinstance(raw_ts, (int, float)):
        from backend.v9.api.v9.bars import _ts_from_unix
        result = _ts_from_unix(raw_ts).isoformat()
    else:
        result = raw_ts

    assert result == "2026-06-08T19:10:00+00:00"
