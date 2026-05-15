"""Volume Spike Detector tests — 5 scenarios per LOCKED 16b spec."""
from datetime import datetime, timedelta
from backend.v9.shared.volume_spike import VolumeSpikeDetector

BASE = datetime(2026, 5, 15, 9, 30, 0)  # RTH open


def _ts(offset_min):
    return BASE + timedelta(minutes=offset_min)


def test_skip_first_6_bars():
    """First 6 bars after RTH open should not produce events."""
    d = VolumeSpikeDetector()
    for i in range(6):
        result = d.detect_spike(10000, _ts(i * 5))
        assert result is None, f"Bar {i+1} should be skipped"


def test_no_spike_below_threshold():
    """Normal volume (z < 2.0) should not trigger spike."""
    d = VolumeSpikeDetector()
    for i in range(26):
        d.detect_spike(100, _ts(i * 5))
    result = d.detect_spike(150, _ts(135))
    assert result is None


def test_spike_at_threshold():
    """Volume far above mean (z >= 2.0) should trigger spike."""
    d = VolumeSpikeDetector()
    for i in range(6):
        d.detect_spike(100, _ts(i * 5))
    vols = [95, 105, 98, 102, 97, 103, 96, 104, 99, 101,
            95, 105, 98, 102, 97, 103, 96, 104, 99, 101]
    for i, v in enumerate(vols):
        d.detect_spike(v, _ts(30 + i * 5))
    result = d.detect_spike(200, _ts(130))
    assert result is not None
    assert result.is_spike is True
    assert result.z_score >= 2.0


def test_outside_rth_returns_none():
    """Non-RTH bars (e.g. 02:00 ET) should return None."""
    d = VolumeSpikeDetector()
    result = d.detect_spike(10000, datetime(2026, 5, 15, 2, 0, 0))
    assert result is None


def test_session_reset_clears_state():
    """After reset, detector starts fresh."""
    d = VolumeSpikeDetector()
    for i in range(30):
        d.detect_spike(100, _ts(i * 5))
    assert d._bar_index_in_session > 0
    d.reset_session()
    assert d._bar_index_in_session == 0
    assert len(d._window) == 0
