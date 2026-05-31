"""S1-opening CVD mode tests — flag ON produces shadow labels, flag OFF unchanged."""

import backend.v9.shared.atr as atr_mod
from backend.v9.systems.day_type.schemas import BarInput, OpeningType


def _set_flag(monkeypatch, on: bool):
    monkeypatch.setattr(atr_mod, "S1_CVD_OPENING", on)
    import backend.v9.systems.day_type.detector as det
    monkeypatch.setattr(det, "S1_CVD_OPENING", on)


def _drive_bars():
    return [
        BarInput(ts=1, session_min=0, open=5200, high=5205, low=5200, close=5205),
        BarInput(ts=2, session_min=5, open=5205, high=5210, low=5205, close=5210),
        BarInput(ts=3, session_min=10, open=5210, high=5215, low=5210, close=5215),
    ]


# ---------- Flag OFF: original behavior, empty shadow ----------

def test_flag_off_returns_original(monkeypatch):
    _set_flag(monkeypatch, False)
    from backend.v9.systems.day_type.detector import detect_opening_type_cvd
    ot, d, c, shadow = detect_opening_type_cvd(
        _drive_bars(), footprint_deltas=[100, 150, 200],
    )
    assert ot == OpeningType.OPEN_DRIVE
    assert d == "UP"
    assert shadow == {}


def test_flag_off_no_deltas(monkeypatch):
    _set_flag(monkeypatch, False)
    from backend.v9.systems.day_type.detector import detect_opening_type_cvd
    ot, d, c, shadow = detect_opening_type_cvd(_drive_bars())
    assert ot == OpeningType.OPEN_DRIVE
    assert shadow == {}


# ---------- Flag ON: CVD becomes live classification ----------

def test_flag_on_drive_live(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.day_type.detector import detect_opening_type_cvd
    # Strong directional deltas (all positive) → PE high → CVD=DRIVE → live OPEN_DRIVE
    ot, d, c, shadow = detect_opening_type_cvd(
        _drive_bars(), footprint_deltas=[100, 150, 200],
    )
    # CVD DRIVE replaces original as live result
    assert ot == OpeningType.OPEN_DRIVE
    assert shadow["shadow_label"] == "DRIVE"
    assert shadow["cvd_is_live"] is True
    assert shadow["cvd_pe"] is not None
    assert shadow["cvd_pe"] > 0.6
    assert shadow["original_label"] == "OPEN_DRIVE"


def test_flag_on_auction_live(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.day_type.detector import detect_opening_type_cvd
    # Mixed deltas, low net → CVD=AUCTION → live OPEN_AUCTION_IN
    bars = [
        BarInput(ts=1, session_min=0, open=5200, high=5202, low=5198, close=5199,
                 pd_high=5210, pd_low=5190),
        BarInput(ts=2, session_min=5, open=5199, high=5201, low=5197, close=5200,
                 pd_high=5210, pd_low=5190),
    ]
    # Net CVD ≈ 0 (balanced)
    ot, d, c, shadow = detect_opening_type_cvd(
        bars, footprint_deltas=[10, -10],
    )
    assert ot == OpeningType.OPEN_AUCTION_IN  # CVD is now live
    assert shadow["shadow_label"] == "AUCTION"
    assert shadow["cvd_is_live"] is True
    assert shadow["cvd_net_ratio"] < 0.15


def test_flag_on_rejection_live(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.day_type.detector import detect_opening_type_cvd
    # Price goes DOWN overall but CVD net is positive → divergence
    bars = [
        BarInput(ts=1, session_min=0, open=5200, high=5210, low=5200, close=5210),
        BarInput(ts=2, session_min=5, open=5210, high=5210, low=5200, close=5202),
        BarInput(ts=3, session_min=10, open=5202, high=5202, low=5195, close=5195),
    ]
    # CVD flips sign AND net positive while price is negative → divergence
    ot, d, c, shadow = detect_opening_type_cvd(
        bars, footprint_deltas=[200, 150, -80, -50],
    )
    assert ot == OpeningType.OPEN_REJECTION_REVERSE  # CVD is now live
    assert shadow["cvd_sign_flip"] is True
    assert shadow["cvd_divergence"] is True
    assert shadow["shadow_label"] == "REJECTION_REVERSE"
    assert shadow["cvd_is_live"] is True


# ---------- Flag ON but no deltas: fallback ----------

def test_flag_on_no_deltas_empty_shadow(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.day_type.detector import detect_opening_type_cvd
    ot, d, c, shadow = detect_opening_type_cvd(_drive_bars(), footprint_deltas=None)
    assert ot == OpeningType.OPEN_DRIVE
    assert shadow == {}


# ---------- Gap classification ----------

def test_gap_atr_classification():
    from backend.v9.systems.day_type.detector import classify_gap_atr
    # With daily ATR
    assert classify_gap_atr(2.0, atr_daily=20.0) == "TINY"    # 0.1
    assert classify_gap_atr(8.0, atr_daily=20.0) == "SMALL"   # 0.4
    assert classify_gap_atr(15.0, atr_daily=20.0) == "MEDIUM"  # 0.75
    assert classify_gap_atr(25.0, atr_daily=20.0) == "LARGE"   # 1.25


def test_gap_atr_fallback():
    from backend.v9.systems.day_type.detector import classify_gap_atr
    # No ATR → absolute fallback
    assert classify_gap_atr(2.0, atr_daily=None) == "TINY"
    assert classify_gap_atr(5.0, atr_daily=None) == "SMALL"
    assert classify_gap_atr(10.0, atr_daily=None) == "MEDIUM"
    assert classify_gap_atr(15.0, atr_daily=None) == "LARGE"


def test_gap_atr_with_bar_context(monkeypatch):
    """Gap tier appears in shadow dict when bars have pd_close."""
    _set_flag(monkeypatch, True)
    from backend.v9.systems.day_type.detector import detect_opening_type_cvd
    bars = [
        BarInput(ts=1, session_min=0, open=5210, high=5215, low=5210, close=5215,
                 pd_close=5200),
        BarInput(ts=2, session_min=5, open=5215, high=5220, low=5215, close=5220,
                 pd_close=5200),
    ]
    ot, d, c, shadow = detect_opening_type_cvd(
        bars, footprint_deltas=[100, 200], atr_daily=20.0,
    )
    assert shadow["gap_size"] == 10.0
    assert shadow["gap_tier"] == "MEDIUM"  # 10/20 = 0.5 (at boundary → MEDIUM)
