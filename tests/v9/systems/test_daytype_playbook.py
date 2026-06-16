"""Tests for the day-type playbook decision engine.

Anti-tautological: every test calls the production decide() which reads the REAL
config/daytype_playbook.yaml. Reverting a YAML cell flips the matching test RED
(noted per case), so the test proves the config drives behavior — not a copy.
"""
import pytest

from backend.v9.systems import daytype_playbook as P


@pytest.fixture(autouse=True)
def _reset():
    P.reset_cache()
    yield
    P.reset_cache()


def _on(mp):
    mp.setenv("DAYTYPE_PLAYBOOK", "1")
    P.reset_cache()


def _off(mp):
    mp.delenv("DAYTYPE_PLAYBOOK", raising=False)
    P.reset_cache()


def test_off_is_noop(monkeypatch):
    # GATE OFF → FULL for everything (zero change to current firing).
    _off(monkeypatch)
    d = P.decide("HFE_SHORT", "Trend_Normal", "SHORT", "RED")
    assert d.verdict == "FULL" and d.allow


def test_hfe_skip_on_trend(monkeypatch):
    # spec: HFE on a trend day = SKIP.  if reverted (YAML HFE.Trend_Normal->FULL) → RED
    _on(monkeypatch)
    d = P.decide("HFE_SHORT", "Trend_Normal", "SHORT", "RED")
    assert d.verdict == "SKIP" and not d.allow


def test_reactive_counter_trend_skip(monkeypatch):
    # REACTIVE short on an UP trend (trend_state BLUE) = counter-trend → SKIP.
    _on(monkeypatch)
    d = P.decide("REACTIVE_SHORT", "Trend_Normal", "SHORT", "BLUE")
    assert d.verdict == "SKIP"


def test_reactive_with_trend_ok(monkeypatch):
    # REACTIVE long on an UP trend = with-trend → allowed (FULL).
    _on(monkeypatch)
    d = P.decide("REACTIVE_LONG", "Trend_Normal", "LONG", "BLUE")
    assert d.verdict == "FULL" and d.allow


def test_reduced_sizes_down(monkeypatch):
    # spec: ZLR on Normal = SIZE-DOWN.  if reverted (ZLR.Normal->FULL) → RED
    _on(monkeypatch)
    d = P.decide("ZLR_LONG", "Normal", "LONG", "GRAY")
    assert d.verdict == "REDUCED" and d.contracts == 2


def test_unknown_pattern_fails_open(monkeypatch):
    # fail-open: an unmapped pattern is never blocked.
    _on(monkeypatch)
    d = P.decide("MYSTERY", "Trend_Normal", "LONG", "BLUE")
    assert d.verdict == "FULL"


def test_nontrend_skips_all(monkeypatch):
    _on(monkeypatch)
    assert P.decide("ZLR_LONG", "Nontrend", "LONG", "GRAY").verdict == "SKIP"
