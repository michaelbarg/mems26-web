"""CVD Context Classifier tests — 8 scenarios (one per state) per LOCKED 16c."""
from datetime import datetime
from backend.v9.shared.cvd_context import CVDContextClassifier, CVDState

TS = datetime(2026, 5, 15, 10, 30, 0)
c = CVDContextClassifier()


def test_confirmation_bull():
    e = c.classify(TS, price_delta_bar=1.5, cvd_value=5000, cvd_slope=200, has_volume_spike=False)
    assert e.state == CVDState.CONFIRMATION_BULL


def test_confirmation_bear():
    e = c.classify(TS, price_delta_bar=-1.5, cvd_value=-3000, cvd_slope=-200, has_volume_spike=False)
    assert e.state == CVDState.CONFIRMATION_BEAR


def test_divergence_bull():
    e = c.classify(TS, price_delta_bar=-1.5, cvd_value=2000, cvd_slope=100, has_volume_spike=False)
    assert e.state == CVDState.DIVERGENCE_BULL


def test_divergence_bear():
    e = c.classify(TS, price_delta_bar=1.5, cvd_value=-1000, cvd_slope=-100, has_volume_spike=False)
    assert e.state == CVDState.DIVERGENCE_BEAR


def test_absorption_bull():
    e = c.classify(TS, price_delta_bar=-0.1, cvd_value=-5000, cvd_slope=-300, has_volume_spike=True)
    assert e.state == CVDState.ABSORPTION_BULL
    assert "sellers absorbed" in e.reasoning


def test_absorption_bear():
    e = c.classify(TS, price_delta_bar=0.1, cvd_value=5000, cvd_slope=300, has_volume_spike=True)
    assert e.state == CVDState.ABSORPTION_BEAR
    assert "buyers absorbed" in e.reasoning


def test_mechanical():
    e = c.classify(TS, price_delta_bar=0.5, cvd_value=100, cvd_slope=20, has_volume_spike=True)
    assert e.state == CVDState.MECHANICAL
    assert "mechanical" in e.reasoning


def test_neutral():
    e = c.classify(TS, price_delta_bar=0.1, cvd_value=50, cvd_slope=20, has_volume_spike=False)
    assert e.state == CVDState.NEUTRAL
