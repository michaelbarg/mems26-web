"""S2 ATR-relative mode tests — verify flag ON produces expected ATR-scaled values.

These tests monkeypatch S2_ATR_RELATIVE=True and verify that getter
functions return ATR-proportional thresholds, with proper fallback to
absolute values when ATR is None.
"""

import backend.v9.shared.atr as atr_mod


def _set_flag(monkeypatch, on: bool):
    monkeypatch.setattr(atr_mod, "S2_ATR_RELATIVE", on)
    # Also patch the imported copies in each module
    import backend.v9.systems.five_min.five_min_system as fms
    import backend.v9.systems.five_min.quality_tier as qt
    import backend.v9.systems.five_min.sr_proximity as sr
    import backend.v9.systems.five_min.adaptive_stop as ast_
    import backend.v9.systems.five_min.patterns.flags as fl
    import backend.v9.systems.five_min.patterns.head_shoulders as hs
    import backend.v9.systems.five_min.patterns.double_bt as dbt
    for mod in (fms, qt, sr, ast_, fl, hs, dbt):
        if hasattr(mod, "S2_ATR_RELATIVE"):
            monkeypatch.setattr(mod, "S2_ATR_RELATIVE", on)


# ---------- Flag OFF: absolute values ----------

def test_flag_off_expansion(monkeypatch):
    _set_flag(monkeypatch, False)
    from backend.v9.systems.five_min.five_min_system import get_expansion_range
    lo, hi = get_expansion_range(atr_5m=2.0)
    assert lo == 1.5
    assert hi == 1.75


def test_flag_off_poc_return(monkeypatch):
    _set_flag(monkeypatch, False)
    from backend.v9.systems.five_min.five_min_system import get_poc_return_tolerance
    assert get_poc_return_tolerance(atr_5m=2.0) == 0.5


def test_flag_off_proximity(monkeypatch):
    _set_flag(monkeypatch, False)
    from backend.v9.systems.five_min.quality_tier import get_proximity_pt
    assert get_proximity_pt(atr_5m=2.0) == 2.0


def test_flag_off_floor_ticks(monkeypatch):
    _set_flag(monkeypatch, False)
    from backend.v9.systems.five_min.adaptive_stop import get_floor_ticks
    assert get_floor_ticks(atr_5m=2.0) == 4


# ---------- Flag ON: ATR-scaled ----------

def test_flag_on_expansion(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.five_min_system import get_expansion_range
    lo, hi = get_expansion_range(atr_5m=1.0)
    assert lo == 1.5  # 1.5 × 1.0
    assert hi == 2.0  # 2.0 × 1.0


def test_flag_on_poc_return(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.five_min_system import get_poc_return_tolerance
    assert get_poc_return_tolerance(atr_5m=1.0) == 0.2  # 0.2 × 1.0


def test_flag_on_proximity(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.quality_tier import get_proximity_pt
    assert get_proximity_pt(atr_5m=1.0) == 1.25  # 1.25 × 1.0


def test_flag_on_sr_proximity_ticks(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.sr_proximity import get_proximity_ticks
    result = get_proximity_ticks(atr_5m=1.0, tick_size=0.25)
    assert result == 5  # round(1.25 × 1.0 / 0.25) = 5


def test_flag_on_floor_ticks_with_backstop(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.adaptive_stop import get_floor_ticks
    # Small ATR → backstop kicks in
    result = get_floor_ticks(atr_5m=0.3)
    assert result >= 4  # backstop = FLOOR_TICKS_MIN_BACKSTOP = 4
    # Large ATR → ATR-based
    result = get_floor_ticks(atr_5m=2.0)
    assert result == 14  # round(1.75 × 2.0 / 0.25) = 14


def test_flag_on_pole_height(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.patterns.flags import get_pole_min_height_ticks
    result = get_pole_min_height_ticks(atr_5m=1.0)
    assert result == 22  # round(5.5 × 1.0 / 0.25) = 22


def test_flag_on_head_ext_proportional(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.patterns.head_shoulders import get_head_min_ext_ticks
    result = get_head_min_ext_ticks(pattern_height=4.0)
    assert result == 2  # round(0.15 × 4.0 / 0.25) = 2.4 → 2


def test_flag_on_trough_tolerance(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.patterns.double_bt import get_trough_tolerance
    result = get_trough_tolerance(atr_5m=1.0)
    assert result == 0.75  # 0.75 × 1.0


# ---------- Flag ON but ATR is None: fallback to absolute ----------

def test_flag_on_atr_none_falls_back(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.five_min_system import get_expansion_range, get_poc_return_tolerance
    from backend.v9.systems.five_min.adaptive_stop import get_floor_ticks
    lo, hi = get_expansion_range(atr_5m=None)
    assert lo == 1.5 and hi == 1.75
    assert get_poc_return_tolerance(atr_5m=None) == 0.5
    assert get_floor_ticks(atr_5m=None) == 4
