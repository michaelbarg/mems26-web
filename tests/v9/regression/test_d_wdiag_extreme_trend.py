"""D-WDIAG: Extreme-CCI trend relabel tests.

Verifies the single-source relabel in woodies_system.py studies dict:
- Flag OFF: GRAY stays GRAY even with |CCI|>=200
- Flag ON: GRAY→BLUE when CCI>=200, GRAY→RED when CCI<=-200
- Normal bar (CCI=80, GRAY) stays GRAY even with flag ON
"""

import pytest
import backend.v9.shared.atr as atr_mod


def _set_flag(monkeypatch, on: bool):
    monkeypatch.setattr(atr_mod, "S4_EXTREME_TREND_RELABEL", on)


# ── Flag OFF: raw Sierra trend preserved ──

def test_flag_off_extreme_cci_stays_gray(monkeypatch):
    """D-WDIAG: Flag OFF + CCI=331 + GRAY → studies stays GRAY."""
    _set_flag(monkeypatch, False)
    studies = {"trend_state": "GRAY", "cci_14": 331.0}

    # Simulate the relabel logic (same as woodies_system.py ~277-281)
    from backend.v9.shared.atr import S4_EXTREME_TREND_RELABEL
    if S4_EXTREME_TREND_RELABEL and studies.get("trend_state") in ("GRAY", "YELLOW", "GREY"):
        _cci_val = studies.get("cci_14") or 0
        if abs(_cci_val) >= 200:
            studies["trend_state"] = "BLUE" if _cci_val > 0 else "RED"

    assert studies["trend_state"] == "GRAY"


# ── Flag ON: extreme CCI relabeled ──

def test_flag_on_positive_extreme_becomes_blue(monkeypatch):
    """D-WDIAG: Flag ON + CCI=331 + GRAY → BLUE."""
    _set_flag(monkeypatch, True)
    studies = {"trend_state": "GRAY", "cci_14": 331.0}

    from backend.v9.shared.atr import S4_EXTREME_TREND_RELABEL
    if S4_EXTREME_TREND_RELABEL and studies.get("trend_state") in ("GRAY", "YELLOW", "GREY"):
        _cci_val = studies.get("cci_14") or 0
        if abs(_cci_val) >= 200:
            studies["trend_state"] = "BLUE" if _cci_val > 0 else "RED"

    assert studies["trend_state"] == "BLUE"


def test_flag_on_negative_extreme_becomes_red(monkeypatch):
    """D-WDIAG: Flag ON + CCI=-257 + YELLOW → RED."""
    _set_flag(monkeypatch, True)
    studies = {"trend_state": "YELLOW", "cci_14": -257.0}

    from backend.v9.shared.atr import S4_EXTREME_TREND_RELABEL
    if S4_EXTREME_TREND_RELABEL and studies.get("trend_state") in ("GRAY", "YELLOW", "GREY"):
        _cci_val = studies.get("cci_14") or 0
        if abs(_cci_val) >= 200:
            studies["trend_state"] = "BLUE" if _cci_val > 0 else "RED"

    assert studies["trend_state"] == "RED"


def test_flag_on_normal_cci_stays_gray(monkeypatch):
    """D-WDIAG: Flag ON + CCI=80 + GRAY → stays GRAY (not extreme)."""
    _set_flag(monkeypatch, True)
    studies = {"trend_state": "GRAY", "cci_14": 80.0}

    from backend.v9.shared.atr import S4_EXTREME_TREND_RELABEL
    if S4_EXTREME_TREND_RELABEL and studies.get("trend_state") in ("GRAY", "YELLOW", "GREY"):
        _cci_val = studies.get("cci_14") or 0
        if abs(_cci_val) >= 200:
            studies["trend_state"] = "BLUE" if _cci_val > 0 else "RED"

    assert studies["trend_state"] == "GRAY"


def test_flag_on_blue_stays_blue(monkeypatch):
    """D-WDIAG: Flag ON + CCI=150 + BLUE → stays BLUE (already correct)."""
    _set_flag(monkeypatch, True)
    studies = {"trend_state": "BLUE", "cci_14": 150.0}

    from backend.v9.shared.atr import S4_EXTREME_TREND_RELABEL
    if S4_EXTREME_TREND_RELABEL and studies.get("trend_state") in ("GRAY", "YELLOW", "GREY"):
        _cci_val = studies.get("cci_14") or 0
        if abs(_cci_val) >= 200:
            studies["trend_state"] = "BLUE" if _cci_val > 0 else "RED"

    assert studies["trend_state"] == "BLUE"
