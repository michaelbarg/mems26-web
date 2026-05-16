"""Test HFE (Hook From Extreme) pattern detector — pattern #9 of 9."""
import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

from backend.v9.systems.woodies.schemas import WoodiesBar
from backend.v9.systems.woodies.patterns.hfe import detect, PATTERN_ID


def _bar(cci_14: float, close: float = 7500, high: float = 7501, low: float = 7499) -> WoodiesBar:
    return WoodiesBar(
        ts=0, open=close - 0.5, high=high, low=low, close=close, volume=100,
        cci_14=cci_14, cci_6_tcci=cci_14 * 0.8, ema_34=7500, lsma_value=7500,
        swi_value=0, czi_value=0, trend_state="GRAY", predictor_next_cci=0,
        zlr_detected=False, zlr_direction="NONE",
    )


def test_hfe_up_from_negative_extreme():
    """CCI drops to -220, then hooks back up to -100 → HFE UP (LONG)."""
    bars = [
        _bar(-50), _bar(-100), _bar(-180), _bar(-220),  # extreme at bar 3
        _bar(-170), _bar(-120), _bar(-80),                # hooking up
    ]
    result = detect(bars)
    assert result is not None, "Expected HFE UP pattern"
    assert result.direction == "LONG"
    assert result.pattern_id == "HFE"
    assert result.details is not None
    assert "HFE UP" in result.details.get("reasoning_notes", "")


def test_hfe_down_from_positive_extreme():
    """CCI reaches +210, then hooks back down to +100 → HFE DOWN (SHORT)."""
    bars = [
        _bar(50), _bar(120), _bar(180), _bar(210),  # extreme at bar 3
        _bar(160), _bar(110), _bar(80),               # hooking down
    ]
    result = detect(bars)
    assert result is not None, "Expected HFE DOWN pattern"
    assert result.direction == "SHORT"
    assert "HFE DOWN" in result.details.get("reasoning_notes", "")


def test_no_hfe_when_no_extreme():
    """CCI stays in ±100 range → no HFE."""
    bars = [_bar(30), _bar(50), _bar(80), _bar(60), _bar(40)]
    result = detect(bars)
    assert result is None


def test_no_hfe_when_no_hook():
    """CCI hits extreme but doesn't hook back → no HFE."""
    bars = [
        _bar(-50), _bar(-150), _bar(-220),
        _bar(-210), _bar(-205),  # stays near extreme, no real hook
    ]
    result = detect(bars)
    assert result is None  # hook_distance < 50


def test_no_hfe_insufficient_bars():
    """Less than 4 bars → no detection."""
    bars = [_bar(-220), _bar(-100)]
    result = detect(bars)
    assert result is None


if __name__ == "__main__":
    test_hfe_up_from_negative_extreme()
    test_hfe_down_from_positive_extreme()
    test_no_hfe_when_no_extreme()
    test_no_hfe_when_no_hook()
    test_no_hfe_insufficient_bars()
    print("✅ All 5 HFE tests passed")
