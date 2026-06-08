"""S2 relative-threshold tests — verify expansion + POC gates scale with avg bar range.

Expansion gate: bar_range must be 1.3×–2.5× the average range of recent bars.
POC tolerance: 0.2× average range. Both adapt to market conditions.
Other ATR-relative thresholds (floor_ticks, proximity, pole_height) unchanged.
"""

import backend.v9.shared.atr as atr_mod


def _set_flag(monkeypatch, on: bool):
    monkeypatch.setattr(atr_mod, "S2_ATR_RELATIVE", on)
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


def _make_bars(n=14, avg_range=3.0):
    """Make n bars with a specific average range (h-l)."""
    return [{"h": 7400 + avg_range, "l": 7400.0, "c": 7400 + avg_range / 2, "o": 7400.0}
            for _ in range(n)]


# ---------- Expansion: avg_range-relative (Michael 2026-06-08) ----------

def test_expansion_scales_with_avg_range():
    """Expansion gate uses 1.3×–2.5× average bar range."""
    from backend.v9.systems.five_min.five_min_system import get_expansion_range
    bars = _make_bars(14, avg_range=3.0)
    lo, hi = get_expansion_range(bars)
    assert abs(lo - 3.9) < 0.01   # 1.3 × 3.0
    assert abs(hi - 7.5) < 0.01   # 2.5 × 3.0


def test_expansion_adapts_to_volatile_day():
    """On a volatile day (avg_range=12), expansion gate widens proportionally."""
    from backend.v9.systems.five_min.five_min_system import get_expansion_range
    bars = _make_bars(14, avg_range=12.0)
    lo, hi = get_expansion_range(bars)
    assert abs(lo - 15.6) < 0.01  # 1.3 × 12.0
    assert abs(hi - 30.0) < 0.01  # 2.5 × 12.0


def test_expansion_no_bars_uses_fallback():
    """No bars → fallback to default avg range (3.0pt)."""
    from backend.v9.systems.five_min.five_min_system import get_expansion_range
    lo, hi = get_expansion_range(None)
    assert abs(lo - 3.9) < 0.01   # 1.3 × 3.0
    assert abs(hi - 7.5) < 0.01   # 2.5 × 3.0


def test_poc_return_scales_with_avg_range():
    """POC tolerance = 0.2 × average bar range."""
    from backend.v9.systems.five_min.five_min_system import get_poc_return_tolerance
    bars = _make_bars(14, avg_range=3.0)
    assert abs(get_poc_return_tolerance(bars) - 0.6) < 0.01  # 0.2 × 3.0


def test_poc_return_no_bars_fallback():
    from backend.v9.systems.five_min.five_min_system import get_poc_return_tolerance
    assert abs(get_poc_return_tolerance(None) - 0.6) < 0.01  # 0.2 × 3.0 default


# ---------- Other ATR-relative thresholds (unchanged) ----------

def test_flag_off_floor_ticks(monkeypatch):
    _set_flag(monkeypatch, False)
    from backend.v9.systems.five_min.adaptive_stop import get_floor_ticks
    assert get_floor_ticks(atr_5m=2.0) == 4


def test_flag_on_proximity(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.quality_tier import get_proximity_pt
    assert get_proximity_pt(atr_5m=1.0) == 1.25


def test_flag_on_sr_proximity_ticks(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.sr_proximity import get_proximity_ticks
    result = get_proximity_ticks(atr_5m=1.0, tick_size=0.25)
    assert result == 5


def test_flag_on_floor_ticks_with_backstop(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.adaptive_stop import get_floor_ticks
    assert get_floor_ticks(atr_5m=0.3) >= 4  # backstop
    assert get_floor_ticks(atr_5m=2.0) == 14  # round(1.75 × 2.0 / 0.25)


def test_flag_on_pole_height(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.patterns.flags import get_pole_min_height_ticks
    assert get_pole_min_height_ticks(atr_5m=1.0) == 22


def test_flag_on_head_ext_proportional(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.patterns.head_shoulders import get_head_min_ext_ticks
    assert get_head_min_ext_ticks(pattern_height=4.0) == 2


def test_flag_on_trough_tolerance(monkeypatch):
    _set_flag(monkeypatch, True)
    from backend.v9.systems.five_min.patterns.double_bt import get_trough_tolerance
    assert get_trough_tolerance(atr_5m=1.0) == 0.75
