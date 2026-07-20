"""S2 stop floor min-backstop = 32 ticks (8pt) — Michael 2026-07-20 live fix.

Trade #420 (S2 REACTIVE_SHORT) got a 5.25pt stop = 1.75×ATR5m when ATR5m dipped
to ~3pt at fire, and a normal pullback stopped it out ("too close"). The absolute
backstop was raised 4→32 ticks so no S2 stop is ever tighter than 8pt regardless of
a low 5-min ATR reading (still capped above by per-pattern max_risk_points).

The binding path was get_floor_ticks() = max(round(1.75*ATR5m/tick), backstop).
The real knob lives in config/stop_params.yaml s2_adaptive.floor_ticks_min_backstop
(loaded by _try_load_yaml_stop at import) — the code default is a fallback.
"""
import yaml

import backend.v9.systems.five_min.adaptive_stop as a


def test_config_floor_backstop_is_32():
    c = yaml.safe_load(open("config/stop_params.yaml"))
    assert c["s2_adaptive"]["floor_ticks_min_backstop"] == 32


def test_loaded_backstop_is_32():
    assert a.FLOOR_TICKS_MIN_BACKSTOP == 32


def test_low_atr5m_floors_at_8pt_not_tighter():
    # ATR5m ~3pt would give 1.75*3/0.25 = 21 ticks (5.25pt, the #420 stop);
    # the 32-tick backstop must now win → 8.0pt.
    assert a.get_floor_ticks(3.0) == 32          # 8.0 pt (was 21 / 5.25 pt)
    assert a.get_floor_ticks(1.0) == 32          # very low ATR → still 8pt
    assert a.get_floor_ticks(3.0) * a.MES_TICK == 8.0


def test_high_atr5m_atr_relative_still_dominates():
    # When ATR5m is large the 1.75×ATR floor exceeds the backstop and governs.
    assert a.get_floor_ticks(8.0) >= 32
    assert a.get_floor_ticks(8.0) == max(round(a._FLOOR_ATR_K * 8.0 / a.MES_TICK), 32)
