"""Regression: double-bottom/top trough tolerance is ATR-relative when the
S2_ATR_RELATIVE flag is ON (I-17, Michael-approved 2026-06-05).

Guards the wiring added in a607d11: _trough_width_bars / _peak_width_bars use
get_trough_tolerance(atr_5m) instead of a hardcoded TICK_SIZE*2.
"""

import backend.v9.systems.five_min.patterns.double_bt as double_bt
from backend.v9.systems.five_min.patterns.double_bt import (
    get_trough_tolerance,
    TICK_SIZE,
    _TROUGH_TOL_ATR_K,
)


def _set_flag(monkeypatch, on: bool):
    # get_trough_tolerance reads the flag from the double_bt module namespace.
    monkeypatch.setattr(double_bt, "S2_ATR_RELATIVE", on)


# ---------- Flag ON: ATR-relative ----------

def test_flag_on_relative_tolerance(monkeypatch):
    _set_flag(monkeypatch, True)
    # 0.75 × ATR
    assert get_trough_tolerance(atr_5m=2.0) == _TROUGH_TOL_ATR_K * 2.0
    assert get_trough_tolerance(atr_5m=4.0) == _TROUGH_TOL_ATR_K * 4.0


def test_flag_on_no_atr_falls_back(monkeypatch):
    """Honest fallback: no ATR available → fixed 2-tick tolerance, never synth."""
    _set_flag(monkeypatch, True)
    assert get_trough_tolerance(atr_5m=None) == TICK_SIZE * 2


# ---------- Flag OFF: fixed (kill-switch) ----------

def test_flag_off_fixed_tolerance(monkeypatch):
    _set_flag(monkeypatch, False)
    assert get_trough_tolerance(atr_5m=2.0) == TICK_SIZE * 2
    assert get_trough_tolerance(atr_5m=None) == TICK_SIZE * 2
