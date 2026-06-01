"""S1-daytype relative mode tests — flag ON produces ATR-scaled IB width + staged confidence."""

import backend.v9.shared.atr as atr_mod
from backend.v9.systems.day_type.schemas import IBWidth


def _set_flags(monkeypatch, ib_atr: bool = False, staging: bool = False):
    monkeypatch.setattr(atr_mod, "S1_IB_WIDTH_ATR", ib_atr)
    monkeypatch.setattr(atr_mod, "S1_DAYTYPE_STAGING", staging)
    import backend.v9.systems.day_type.detector as det
    monkeypatch.setattr(det, "S1_IB_WIDTH_ATR", ib_atr)
    monkeypatch.setattr(det, "S1_DAYTYPE_STAGING", staging)


# ============ IB Width ATR ============

# ---------- Always ratio (Michael 2026-06-01) ----------

def test_ib_width_flag_off(monkeypatch):
    """Even with flag OFF, classification is now always by IB/ATR ratio."""
    _set_flags(monkeypatch, ib_atr=False)
    from backend.v9.systems.day_type.detector import classify_ib_width_atr
    # IB/ATR ratio: 10/20=0.5→MEDIUM, 20/20=1.0→WIDE, 30/20=1.5→EXTREME
    assert classify_ib_width_atr(10.0, atr_daily=20.0) == IBWidth.MEDIUM   # 0.5 = boundary
    assert classify_ib_width_atr(20.0, atr_daily=20.0) == IBWidth.WIDE     # 1.0
    assert classify_ib_width_atr(30.0, atr_daily=20.0) == IBWidth.EXTREME  # 1.5


# ---------- Flag ON: ATR-relative ----------

def test_ib_width_flag_on_narrow(monkeypatch):
    _set_flags(monkeypatch, ib_atr=True)
    from backend.v9.systems.day_type.detector import classify_ib_width_atr
    assert classify_ib_width_atr(8.0, atr_daily=20.0) == IBWidth.NARROW  # 0.4

def test_ib_width_flag_on_medium(monkeypatch):
    _set_flags(monkeypatch, ib_atr=True)
    from backend.v9.systems.day_type.detector import classify_ib_width_atr
    assert classify_ib_width_atr(15.0, atr_daily=20.0) == IBWidth.MEDIUM  # 0.75

def test_ib_width_flag_on_wide(monkeypatch):
    _set_flags(monkeypatch, ib_atr=True)
    from backend.v9.systems.day_type.detector import classify_ib_width_atr
    assert classify_ib_width_atr(25.0, atr_daily=20.0) == IBWidth.WIDE  # 1.25

def test_ib_width_flag_on_extreme(monkeypatch):
    _set_flags(monkeypatch, ib_atr=True)
    from backend.v9.systems.day_type.detector import classify_ib_width_atr
    assert classify_ib_width_atr(35.0, atr_daily=20.0) == IBWidth.EXTREME  # 1.75

def test_ib_width_flag_on_no_atr_fallback(monkeypatch):
    _set_flags(monkeypatch, ib_atr=True)
    from backend.v9.systems.day_type.detector import classify_ib_width_atr
    # No ATR → uses default MES ATR (20pt)
    # 10/20=0.5→MEDIUM, 20/20=1.0→WIDE
    assert classify_ib_width_atr(10.0, atr_daily=None) == IBWidth.MEDIUM
    assert classify_ib_width_atr(20.0, atr_daily=None) == IBWidth.WIDE


# ============ Staged Confidence ============

# ---------- Flag OFF: unchanged ----------

def test_conf_staging_flag_off(monkeypatch):
    _set_flags(monkeypatch, staging=False)
    from backend.v9.systems.day_type.detector import cap_confidence_staged
    assert cap_confidence_staged(0.85, session_min=20) == 0.85  # unchanged


# ---------- Flag ON: capped before IB lock ----------

def test_conf_staging_flag_on_early(monkeypatch):
    _set_flags(monkeypatch, staging=True)
    from backend.v9.systems.day_type.detector import cap_confidence_staged
    assert cap_confidence_staged(0.85, session_min=20) == 0.60  # capped

def test_conf_staging_flag_on_post_ib(monkeypatch):
    _set_flags(monkeypatch, staging=True)
    from backend.v9.systems.day_type.detector import cap_confidence_staged
    assert cap_confidence_staged(0.85, session_min=65) == 0.85  # full


# ============ C-Period Re-eval ============

def test_c_period_flag_off(monkeypatch):
    _set_flags(monkeypatch, staging=False)
    from backend.v9.systems.day_type.detector import check_c_period_reeval
    assert check_c_period_reeval(70, 0.10) is None

def test_c_period_hold(monkeypatch):
    _set_flags(monkeypatch, staging=True)
    from backend.v9.systems.day_type.detector import check_c_period_reeval
    assert check_c_period_reeval(70, 0.10) == "HOLD"  # <25% retrace

def test_c_period_rediagnose(monkeypatch):
    _set_flags(monkeypatch, staging=True)
    from backend.v9.systems.day_type.detector import check_c_period_reeval
    assert check_c_period_reeval(70, 0.55) == "RE_DIAGNOSE"  # ≥50% retrace

def test_c_period_outside_window(monkeypatch):
    _set_flags(monkeypatch, staging=True)
    from backend.v9.systems.day_type.detector import check_c_period_reeval
    assert check_c_period_reeval(95, 0.10) is None  # after C-period


# ============ EXTREME in Decision Matrix ============

def test_extreme_in_decision_matrix():
    from backend.v9.systems.day_type.decision_matrix import DECISION_MATRIX
    from backend.v9.systems.day_type.schemas import OpeningType
    # All opening types should have an EXTREME entry
    for ot in [OpeningType.OPEN_DRIVE, OpeningType.OPEN_TEST_DRIVE,
               OpeningType.OPEN_REJECTION_REVERSE, OpeningType.OPEN_AUCTION_IN,
               OpeningType.OPEN_AUCTION_OUT, OpeningType.INDETERMINATE]:
        key = (ot, IBWidth.EXTREME)
        assert key in DECISION_MATRIX, f"Missing EXTREME for {ot}"
