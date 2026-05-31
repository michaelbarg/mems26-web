"""S2 Golden Regression — flag OFF must reproduce original absolute thresholds.

When S2_ATR_RELATIVE is OFF (default), every threshold used in detection
must equal the golden snapshot values. This test catches accidental
regressions where a relative-mode code path leaks into the default path.
"""

import json
from pathlib import Path

GOLDEN = Path(__file__).parent / "golden" / "s2_constants.json"


def _load_golden():
    with GOLDEN.open() as f:
        return json.load(f)


# ---------- five_min_system.py constants ----------

def test_five_min_expansion_thresholds():
    from backend.v9.systems.five_min.five_min_system import (
        EXPANSION_MIN_PT, EXPANSION_MAX_PT, POC_RETURN_TOLERANCE_PT,
        DROP_THRESHOLD_PCT, LOOKBACK_MAX_VOL_RATIO, BELLY_DOMINANCE_RATIO,
        MIN_BARS_REQUIRED, LOOKBACK_BARS,
    )
    g = _load_golden()["five_min_system"]
    assert EXPANSION_MIN_PT == g["EXPANSION_MIN_PT"]
    assert EXPANSION_MAX_PT == g["EXPANSION_MAX_PT"]
    assert POC_RETURN_TOLERANCE_PT == g["POC_RETURN_TOLERANCE_PT"]
    assert DROP_THRESHOLD_PCT == g["DROP_THRESHOLD_PCT"]
    assert LOOKBACK_MAX_VOL_RATIO == g["LOOKBACK_MAX_VOL_RATIO"]
    assert BELLY_DOMINANCE_RATIO == g["BELLY_DOMINANCE_RATIO"]
    assert MIN_BARS_REQUIRED == g["MIN_BARS_REQUIRED"]
    assert LOOKBACK_BARS == g["LOOKBACK_BARS"]


# ---------- quality_tier.py ----------

def test_quality_tier_proximity():
    from backend.v9.systems.five_min.quality_tier import PROXIMITY_PT
    g = _load_golden()["quality_tier"]
    assert PROXIMITY_PT == g["PROXIMITY_PT"]


# ---------- sr_proximity.py ----------

def test_sr_proximity_ticks():
    from backend.v9.systems.five_min.sr_proximity import DEFAULT_PROXIMITY_TICKS
    g = _load_golden()["sr_proximity"]
    assert DEFAULT_PROXIMITY_TICKS == g["DEFAULT_PROXIMITY_TICKS"]


# ---------- adaptive_stop.py ----------

def test_adaptive_stop_floor():
    from backend.v9.systems.five_min.adaptive_stop import FLOOR_TICKS, MES_TICK
    g = _load_golden()["adaptive_stop"]
    assert FLOOR_TICKS == g["FLOOR_TICKS"]
    assert MES_TICK == g["MES_TICK"]


# ---------- patterns/flags.py ----------

def test_flag_pattern_thresholds():
    from backend.v9.systems.five_min.patterns.flags import (
        POLE_MIN_HEIGHT_TICKS, FLAG_MAX_RETRACE_PCT, POLE_DIRECTIONAL_PCT,
        POLE_MIN_BARS, POLE_MAX_BARS, FLAG_MIN_BARS, FLAG_MAX_BARS,
    )
    g = _load_golden()["patterns_flags"]
    assert POLE_MIN_HEIGHT_TICKS == g["POLE_MIN_HEIGHT_TICKS"]
    assert FLAG_MAX_RETRACE_PCT == g["FLAG_MAX_RETRACE_PCT"]
    assert POLE_DIRECTIONAL_PCT == g["POLE_DIRECTIONAL_PCT"]
    assert POLE_MIN_BARS == g["POLE_MIN_BARS"]
    assert POLE_MAX_BARS == g["POLE_MAX_BARS"]
    assert FLAG_MIN_BARS == g["FLAG_MIN_BARS"]
    assert FLAG_MAX_BARS == g["FLAG_MAX_BARS"]


# ---------- patterns/head_shoulders.py ----------

def test_head_shoulders_thresholds():
    from backend.v9.systems.five_min.patterns.head_shoulders import (
        HEAD_MIN_EXT_TICKS, SHOULDER_SYM_PCT,
    )
    g = _load_golden()["patterns_head_shoulders"]
    assert HEAD_MIN_EXT_TICKS == g["HEAD_MIN_EXT_TICKS"]
    assert SHOULDER_SYM_PCT == g["SHOULDER_SYM_PCT"]


# ---------- patterns/double_bt.py ----------

def test_double_bt_thresholds():
    from backend.v9.systems.five_min.patterns.double_bt import (
        TROUGH_SYM_PCT, NECKLINE_MIN_RISE_PCT, TICK_SIZE,
    )
    g = _load_golden()["patterns_double_bt"]
    assert TROUGH_SYM_PCT == g["TROUGH_SYM_PCT"]
    assert NECKLINE_MIN_RISE_PCT == g["NECKLINE_MIN_RISE_PCT"]
    # Trough tolerance = TICK_SIZE * 2 (line 87 of double_bt.py)
    assert TICK_SIZE * 2 == g["TROUGH_TOLERANCE_TICKS"] * 0.25


# ---------- Functional regression: compute_stop with absolute floor ----------

def test_compute_stop_golden_long():
    """compute_stop with known inputs must produce deterministic output."""
    from backend.v9.systems.five_min.adaptive_stop import compute_stop
    result = compute_stop(
        entry_price=5250.0,
        direction="LONG",
        structural_anchor=5247.0,
        family="Reactive",
        today_typical=1.5,
    )
    # Floor = 5250 - 4*0.25 = 5249.0
    # Structural = 5247 - 0.25 = 5246.75
    # ATR cap = 5250 - 1.0*1.5 = 5248.5
    # Candidate = max(5246.75, 5248.5) = 5248.5
    # Final = min(5248.5, 5249.0) = 5248.5
    assert result.stop_price == 5248.5
    assert result.binding_layer == "B"


def test_compute_stop_golden_short():
    from backend.v9.systems.five_min.adaptive_stop import compute_stop
    result = compute_stop(
        entry_price=5250.0,
        direction="SHORT",
        structural_anchor=5253.0,
        family="OFA",
        today_typical=1.5,
    )
    # Floor = 5250 + 4*0.25 = 5251.0
    # Structural = 5253 + 0.25 = 5253.25
    # ATR cap = 5250 + 1.5*1.5 = 5252.25
    # Candidate = min(5253.25, 5252.25) = 5252.25
    # Final = max(5252.25, 5251.0) = 5252.25
    assert result.stop_price == 5252.25
    assert result.binding_layer == "B"
