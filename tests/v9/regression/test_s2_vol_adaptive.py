"""Regression — S2_VOL_ADAPTIVE volatile-regime relaxation (2026-06-12).

Anti-tautological: the integration test feeds a real bar sequence through the REAL
_detect_reactive — flag OFF must NOT detect (b4 closes between 75% and 100% of b3
range), flag ON must detect LONG. RED-on-revert: removing the threshold relaxation
or the regime check fails these.
"""
import pytest

from backend.v9.systems.five_min.five_min_system import (
    FiveMinSystem,
    reactive_confirm_threshold,
    vol_adaptive_active,
)


def _bar(o, h, l, c, v):
    return {"o": o, "h": h, "l": l, "c": c, "v": v}


# Volatile sequence (ranges ~10-12pt). LONG geometry perfect EXCEPT b4 closes at
# 7300 — beyond 75% of b3's range (7298.25) but NOT beyond b3's high (7301).
VOLATILE_NEAR_MISS = [
    _bar(7305, 7310, 7300, 7301, 100),   # lookback 1 (quiet vol)
    _bar(7301, 7306, 7296, 7298, 100),   # lookback 2
    _bar(7298, 7303, 7293, 7295, 100),   # lookback 3
    _bar(7300, 7301, 7289, 7290, 1000),  # b1: bearish, high vol
    _bar(7290, 7296, 7286, 7291, 50),    # b2: 95% volume drop
    _bar(7291, 7301, 7290, 7299, 200),   # b3: bullish, range 11 -> 75% level 7298.25
    _bar(7295, 7300.5, 7294, 7300, 300), # b4: bullish confirm, c=7300 < b3.h=7301
]

# Calm sequence (ranges ~2pt) — regime must stay NORMAL even with flag ON.
CALM = [_bar(7300 + i * 0.25, 7301 + i * 0.25, 7299 + i * 0.25, 7300.5 + i * 0.25, 100) for i in range(7)]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("S2_VOL_ADAPTIVE", raising=False)
    monkeypatch.delenv("S2_VSA_VOLUME", raising=False)  # classic 90%-drop path in tests
    monkeypatch.delenv("S2_REQUIRE_COT_AMT", raising=False)


class TestRegime:
    def test_flag_off_never_active(self):
        assert vol_adaptive_active(VOLATILE_NEAR_MISS) is False

    def test_flag_on_volatile_active(self, monkeypatch):
        monkeypatch.setenv("S2_VOL_ADAPTIVE", "1")
        assert vol_adaptive_active(VOLATILE_NEAR_MISS) is True

    def test_flag_on_calm_inactive(self, monkeypatch):
        monkeypatch.setenv("S2_VOL_ADAPTIVE", "1")
        assert vol_adaptive_active(CALM) is False


class TestThreshold:
    def test_non_adaptive_is_full_extreme(self):
        assert reactive_confirm_threshold(7301.0, 7290.0, "LONG", False) == 7301.0
        assert reactive_confirm_threshold(7301.0, 7290.0, "SHORT", False) == 7290.0

    def test_adaptive_is_75pct(self):
        assert reactive_confirm_threshold(7301.0, 7290.0, "LONG", True) == pytest.approx(7298.25)
        assert reactive_confirm_threshold(7301.0, 7290.0, "SHORT", True) == pytest.approx(7292.75)


class TestDetectReactiveIntegration:
    """Through the REAL detector — proves the wiring, not just the helpers."""

    def test_flag_off_no_detection(self):
        fm = FiveMinSystem()
        direction, conf, info = fm._detect_reactive(VOLATILE_NEAR_MISS)
        assert direction is None, (
            "flag OFF must keep the original full-extreme rule — "
            "got a detection, the relaxation leaked into default behavior"
        )

    def test_flag_on_detects_long(self, monkeypatch):
        monkeypatch.setenv("S2_VOL_ADAPTIVE", "1")
        fm = FiveMinSystem()
        direction, conf, info = fm._detect_reactive(VOLATILE_NEAR_MISS)
        assert direction == "LONG", (
            "volatile regime + 75%-confirm should detect this sequence — "
            "the adaptive threshold is not wired into _detect_reactive"
        )
        assert info.get("kind") == "REACTIVE"
