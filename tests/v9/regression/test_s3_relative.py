"""S3 relative mode tests — flag ON produces volume/ATR-scaled values."""

import backend.v9.shared.atr as atr_mod


def _set_flag(monkeypatch, on: bool):
    monkeypatch.setattr(atr_mod, "S3_RELATIVE", on)
    import backend.v9.systems.footprint.signals.stacked_imbalance as si
    import backend.v9.systems.footprint.detectors as det
    if hasattr(si, "S3_RELATIVE"):
        monkeypatch.setattr(si, "S3_RELATIVE", on)
    if hasattr(det, "S3_RELATIVE"):
        monkeypatch.setattr(det, "S3_RELATIVE", on)


# ---------- Flag OFF: absolute values ----------

def test_flag_off_min_level_vol(monkeypatch):
    """Flag OFF still uses volume-relative (always-relative, Michael 2026-06-01)."""
    _set_flag(monkeypatch, False)
    from backend.v9.systems.footprint.signals.stacked_imbalance import get_min_level_vol
    assert get_min_level_vol(median_level_vol=100.0) == 30.0  # 0.3 × 100


def test_flag_off_range_ticks(monkeypatch):
    _set_flag(monkeypatch, False)
    from backend.v9.systems.footprint.detectors import get_range_ticks
    assert get_range_ticks(atr_5m=2.0) == 15.0


# ---------- Flag ON: relative ----------

def test_flag_on_min_level_vol(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.footprint.signals.stacked_imbalance import get_min_level_vol
    result = get_min_level_vol(median_level_vol=100.0)
    assert result == 30.0  # 0.3 × 100


def test_flag_on_range_ticks(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.footprint.detectors import get_range_ticks
    result = get_range_ticks(atr_5m=2.0)
    assert result == 2.0  # 1.0 × 2.0


# ---------- Flag ON but input missing: fallback ----------

def test_flag_on_no_median_falls_back(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.footprint.signals.stacked_imbalance import get_min_level_vol
    assert get_min_level_vol(median_level_vol=0.0) == 10


def test_flag_on_no_atr_falls_back(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.footprint.detectors import get_range_ticks
    assert get_range_ticks(atr_5m=None) == 15.0


# ---------- Functional: stacked_imbalance unchanged with flag OFF ----------

def test_stacked_imbalance_detection_unchanged(monkeypatch):
    """Flag OFF: detection with original MIN_LEVEL_VOL produces same result."""
    _set_flag(monkeypatch, False)
    from backend.v9.systems.footprint.signals.stacked_imbalance import detect_stacked_imbalance
    levels = [
        {"price": 5200.0 + i * 0.25, "ask_vol": 30, "bid_vol": 10}
        for i in range(5)
    ]
    bar = {"c": 5201.0}
    result = detect_stacked_imbalance(levels, bar)
    assert result is not None
    assert result["direction"] == "LONG"
