"""FAILED_BREAK detector tests + flag-OFF mutation test."""
import pytest
from backend.v9.systems.failed_break import detect_failed_break, build_failed_break_setup


def _bars(data):
    """Convert [(o,h,l,c), ...] to bar dicts."""
    return [{"o": o, "h": h, "l": l, "c": c, "v": 100} for o, h, l, c in data]


def test_flag_off_no_detection(monkeypatch):
    """Flag OFF → no wiring runs (the five_min_system block is flag-gated)."""
    monkeypatch.delenv("FAILED_BREAK_VA_V1", raising=False)
    import os
    assert os.getenv("FAILED_BREAK_VA_V1") is None


def test_upper_failed_break_detected():
    """Probe above VAH, close back inside → SHORT candidate."""
    # 12 bars of history + attempt bar (probes above 100) + failure bar (closes below 100)
    history = _bars([(95, 98, 94, 97)] * 12)
    attempt = {"o": 98, "h": 101.5, "l": 97, "c": 98.5, "v": 200}  # probed above VAH=100
    failure = {"o": 98, "h": 99, "l": 96.5, "c": 97, "v": 150}     # closed back inside, lower half
    bars = history + [attempt, failure]
    result = detect_failed_break(bars, edge_high=100.0, edge_low=90.0, edge_label="VA")
    assert result is not None
    assert result["direction"] == "SHORT"
    assert result["failed_extreme"] == 101.5
    assert result["entry"] == 97.0


def test_lower_failed_break_detected():
    """Probe below VAL, close back inside → LONG candidate."""
    history = _bars([(95, 98, 94, 97)] * 12)
    attempt = {"o": 92, "h": 93, "l": 88.5, "c": 91.5, "v": 200}  # probed below VAL=90
    failure = {"o": 91, "h": 94, "l": 90.5, "c": 93, "v": 150}     # closed back inside, upper half
    bars = history + [attempt, failure]
    result = detect_failed_break(bars, edge_high=100.0, edge_low=90.0, edge_label="VA")
    assert result is not None
    assert result["direction"] == "LONG"
    assert result["failed_extreme"] == 88.5


def test_no_probe_no_detection():
    """Bar stays inside range → no detection."""
    history = _bars([(95, 98, 94, 97)] * 12)
    bar1 = {"o": 95, "h": 98, "l": 93, "c": 96, "v": 100}
    bar2 = {"o": 96, "h": 97, "l": 94, "c": 95, "v": 100}
    bars = history + [bar1, bar2]
    result = detect_failed_break(bars, edge_high=100.0, edge_low=90.0, edge_label="VA")
    assert result is None


def test_acceptance_no_detection():
    """Probe AND acceptance (new high on return bar) → not a failed break."""
    history = _bars([(95, 98, 94, 97)] * 12)
    attempt = {"o": 99, "h": 101, "l": 98, "c": 100.5, "v": 200}
    confirm = {"o": 100, "h": 102, "l": 99.5, "c": 101, "v": 200}  # NEW high → acceptance
    bars = history + [attempt, confirm]
    result = detect_failed_break(bars, edge_high=100.0, edge_low=90.0, edge_label="VA")
    assert result is None  # ch=102 > ph=101 → not a failed break


def test_already_fired_blocks():
    """Same side doesn't fire twice."""
    history = _bars([(95, 98, 94, 97)] * 12)
    attempt = {"o": 98, "h": 101, "l": 97, "c": 98, "v": 200}
    failure = {"o": 98, "h": 99, "l": 96, "c": 97, "v": 150}
    bars = history + [attempt, failure]
    fired = {"FB_HIGH_VA"}
    result = detect_failed_break(bars, 100.0, 90.0, edge_label="VA", already_fired=fired)
    assert result is None


def test_build_setup_routable():
    """Built setup has all gateway-required fields."""
    trigger = {
        "type": "FB_HIGH_VA", "direction": "SHORT", "entry": 97.0,
        "stop": 102.5, "edge_high": 100.0, "edge_low": 90.0,
        "poc": 95.0, "failed_extreme": 101.5,
        "target_poc": 95.0, "target_opposite": 90.0,
    }
    setup = build_failed_break_setup(trigger)
    assert setup["direction"] == "SHORT"
    assert setup["entry_price"] == 97.0
    assert setup["stop"] == 102.5
    assert setup["t1"] is not None
    assert setup["firing_system"] == 2
    assert setup["metadata"]["shadow_only"] is True
