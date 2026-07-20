"""End-to-end stop-anchor V2 tests — per-pattern: bar → anchor → stop → sizing → T1.

Each test verifies the full V2 pipeline from YAML config through to final
trade parameters (stop, contracts, T1). Flag must be ON for V2 path.
"""
import os
from unittest.mock import patch

from backend.v9.config_loader import load_stop_anchors
from backend.v9.systems.stop_anchors import resolver as SA
from backend.v9.systems.stop_anchors.sizing import compute_v2_sizing
from backend.v9.systems.woodies.atr_stop import compute_stop_v2, PatternGroup

MES_TICK = 0.25


def _make_dict_bars(n, base_price=7400.0, spread=2.0, step=0.25):
    """Create dict-style bars (for resolver)."""
    return [
        {"h": base_price + spread + i * step,
         "l": base_price - spread + i * step,
         "c": base_price + i * step}
        for i in range(n)
    ]


def _cfg():
    cfg = load_stop_anchors()
    assert cfg is not None
    return cfg


# ═══════════════════════════════════════════════════════════════════════════
# S4 CONT
# ═══════════════════════════════════════════════════════════════════════════

def test_e2e_zlr():
    """ZLR: cluster_low(4) → structural stop → V2 → sizing → T1."""
    cfg = _cfg()
    bars = _make_dict_bars(20)
    a = cfg["anchors"]["ZLR"]
    assert a["type"] == "cluster_low"
    assert a["window"] == 4

    # Resolve anchor from last 4 bars
    window_bars = bars[-4:]
    struct = SA.resolve_anchor_from_window(window_bars, "LONG",
                                           cfg["principles"]["anchor_offset_ticks"])
    # Structural = min low of last 4 - 3 ticks
    expected_anchor = min(b["l"] for b in window_bars) - 3 * MES_TICK
    assert abs(struct - expected_anchor) < 0.01

    entry = bars[-1]["c"]
    v2 = compute_stop_v2("LONG", entry, struct, PatternGroup.CONT_TIGHT, atr_14=10.0)
    assert v2.stop_price <= entry  # stop below entry
    assert v2.risk_ticks >= 4     # at least floor

    sz = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="LONG",
        pattern_key="ZLR", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg)
    assert sz is not None
    assert sz.contracts >= 1
    assert sz.t1_price > entry


def test_e2e_tlb():
    """TLB: since_trendline_peak(8) → structural → sizing."""
    cfg = _cfg()
    bars = _make_dict_bars(20)
    a = cfg["anchors"]["TLB"]
    assert a["type"] == "since_trendline_peak"

    struct = SA.resolve_anchor_from_window(bars[-8:], "SHORT",
                                           cfg["principles"]["anchor_offset_ticks"])
    entry = bars[-1]["c"]
    v2 = compute_stop_v2("SHORT", entry, struct, PatternGroup.CONT_TIGHT, atr_14=10.0)
    assert v2.stop_price >= entry

    sz = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="SHORT",
        pattern_key="TLB", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg)
    assert sz is not None
    assert sz.t1_price < entry


def test_e2e_tt():
    """TT: zl_excursion(9) → structural → sizing."""
    cfg = _cfg()
    bars = _make_dict_bars(20)
    a = cfg["anchors"]["TT"]
    assert a["type"] == "zl_excursion"

    struct = SA.resolve_anchor_from_window(bars[-9:], "LONG",
                                           cfg["principles"]["anchor_offset_ticks"])
    entry = bars[-1]["c"]
    v2 = compute_stop_v2("LONG", entry, struct, PatternGroup.CONT_TIGHT, atr_14=10.0)
    assert v2.stop_price <= entry

    sz = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="LONG",
        pattern_key="TT", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg)
    assert sz is not None


def test_e2e_gb100():
    """GB100: cluster_low(6) → structural → sizing."""
    cfg = _cfg()
    bars = _make_dict_bars(20)
    a = cfg["anchors"]["GB100"]
    assert a["type"] == "cluster_low"
    assert a["window"] == 6

    struct = SA.resolve_anchor_from_window(bars[-6:], "LONG",
                                           cfg["principles"]["anchor_offset_ticks"])
    entry = bars[-1]["c"]
    v2 = compute_stop_v2("LONG", entry, struct, PatternGroup.CONT_MED, atr_14=10.0)
    assert v2.stop_price <= entry

    sz = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="LONG",
        pattern_key="GB100", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg)
    assert sz is not None


# ═══════════════════════════════════════════════════════════════════════════
# S4 REV
# ═══════════════════════════════════════════════════════════════════════════

def test_e2e_vegas():
    """VEGAS: swing_extreme → apply_offset → V2 → sizing (reversal ×0.8)."""
    cfg = _cfg()
    a = cfg["anchors"]["VEGAS"]
    assert a["type"] == "swing_extreme"

    swing_high = 7410.0  # the price extreme
    struct = SA.apply_offset(swing_high, "SHORT",
                             cfg["principles"]["anchor_offset_ticks"])
    entry = 7400.0
    v2 = compute_stop_v2("SHORT", entry, struct, PatternGroup.REV, atr_14=10.0)
    assert v2.stop_price >= entry

    sz = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="SHORT",
        pattern_key="VEGAS", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=False,
        value_area_full_traverse=None, cfg=cfg, reversal=True)
    assert sz is not None
    assert sz.t1_price < entry  # T1 below entry for SHORT


def test_e2e_ghost():
    """GHOST: shoulder → apply_offset → sizing with t1_measure_cap."""
    cfg = _cfg()
    a = cfg["anchors"]["GHOST"]
    assert a["type"] == "shoulder"
    assert a.get("t1_measure_cap") == 0.5

    shoulder_high = 7408.0
    struct = SA.apply_offset(shoulder_high, "SHORT",
                             cfg["principles"]["anchor_offset_ticks"])
    entry = 7400.0
    v2 = compute_stop_v2("SHORT", entry, struct, PatternGroup.REV, atr_14=10.0)

    sz = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="SHORT",
        pattern_key="GHOST", day_type="Normal", confidence_tier="medium",
        day_has_direction=False, trade_with_trend=None,
        value_area_full_traverse=True, cfg=cfg, reversal=True)
    assert sz is not None


def test_e2e_famir():
    """FAMIR: failed_bar → apply_offset → sizing."""
    cfg = _cfg()
    a = cfg["anchors"]["FAMIR"]
    assert a["type"] == "failed_bar"

    failed_low = 7392.0
    struct = SA.apply_offset(failed_low, "LONG",
                             cfg["principles"]["anchor_offset_ticks"])
    entry = 7400.0
    v2 = compute_stop_v2("LONG", entry, struct, PatternGroup.REV, atr_14=10.0)

    sz = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="LONG",
        pattern_key="FAMIR", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg, reversal=True)
    assert sz is not None


def test_e2e_htlb():
    """HTLB: consolidation_extreme from window → sizing."""
    cfg = _cfg()
    a = cfg["anchors"]["HTLB"]
    assert a["type"] == "consolidation_extreme"

    bars = _make_dict_bars(15)
    struct = SA.resolve_anchor_from_window(bars[-15:], "LONG",
                                           cfg["principles"]["anchor_offset_ticks"])
    entry = bars[-1]["c"]
    v2 = compute_stop_v2("LONG", entry, struct, PatternGroup.CONT_MED, atr_14=10.0)

    sz = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="LONG",
        pattern_key="HTLB", day_type="Normal", confidence_tier="medium",
        day_has_direction=False, trade_with_trend=None,
        value_area_full_traverse=False, cfg=cfg, reversal=True)
    assert sz is not None
    assert sz.mode == "tactical"  # value_day + not full traverse


def test_e2e_hfe():
    """HFE: extreme_bar + ladder_shift=-1 → more conservative T1."""
    cfg = _cfg()
    a = cfg["anchors"]["HFE"]
    assert a["type"] == "extreme_bar"
    assert a.get("t1_ladder_shift") == -1

    extreme_low = 7388.0
    struct = SA.apply_offset(extreme_low, "LONG",
                             cfg["principles"]["anchor_offset_ticks"])
    entry = 7400.0
    v2 = compute_stop_v2("LONG", entry, struct, PatternGroup.REV, atr_14=10.0)

    # Compare HFE T1 (shifted) vs VEGAS T1 (unshifted) at same risk
    sz_hfe = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="LONG",
        pattern_key="HFE", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg, reversal=True)
    sz_vegas = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="LONG",
        pattern_key="VEGAS", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg, reversal=True)
    assert sz_hfe is not None and sz_vegas is not None
    # HFE ladder_shift=-1 moves to a lower-risk band (higher R-multiple)
    # so T1 is different from VEGAS at the same risk. Verify shift takes effect.
    assert sz_hfe.t1_price != sz_vegas.t1_price


# ═══════════════════════════════════════════════════════════════════════════
# S2
# ═══════════════════════════════════════════════════════════════════════════

def test_e2e_reactive():
    """Reactive: support_zone(4) → window extreme → S2 V2 stop → sizing."""
    cfg = _cfg()
    a = cfg["anchors"]["Reactive"]
    assert a["type"] == "support_zone"
    assert a["window"] == 4

    bars = _make_dict_bars(20)
    struct = SA.resolve_anchor_from_window(bars[-4:], "LONG",
                                           cfg["principles"]["anchor_offset_ticks"])
    entry = bars[-1]["c"]
    from backend.v9.systems.five_min.adaptive_stop import compute_stop_v2 as s2_v2
    v2 = s2_v2(entry_price=entry, direction="LONG", structural_stop_price=struct,
               family="Reactive", today_typical=1.5)
    assert v2.stop_price <= entry

    sz = compute_v2_sizing(
        entry_price=entry, stop_price=v2.stop_price, direction="LONG",
        pattern_key="Reactive", day_type="Normal", confidence_tier="medium",
        day_has_direction=False, trade_with_trend=None,
        value_area_full_traverse=True, cfg=cfg)
    assert sz is not None


def test_e2e_ofa_initiative():
    """OFA_Initiative: breakout_bar(1) → single bar → tight stop."""
    cfg = _cfg()
    a = cfg["anchors"]["OFA_Initiative"]
    assert a["type"] == "breakout_bar"
    assert a["window"] == 1  # tight!

    bar = {"h": 7402.0, "l": 7398.0, "c": 7401.0}
    struct = SA.resolve_anchor_from_window([bar], "LONG",
                                           cfg["principles"]["anchor_offset_ticks"])
    # Should be bar low - 6 ticks (Michael 2026-07-20 ruling; was 3T)
    assert abs(struct - (7398.0 - 6 * MES_TICK)) < 0.01

    from backend.v9.systems.five_min.adaptive_stop import compute_stop_v2 as s2_v2
    v2 = s2_v2(entry_price=7401.0, direction="LONG", structural_stop_price=struct,
               family="OFA", today_typical=1.5)
    assert v2.stop_price <= 7401.0


def test_e2e_double_bt():
    """Double_BT: second_bottom_top (pattern-provided) → sizing."""
    cfg = _cfg()
    a = cfg["anchors"]["Double_BT"]
    assert a["type"] == "second_bottom_top"

    # Pattern provides structural_anchor = lower trough
    structural = 7392.0
    struct = SA.apply_offset(structural, "LONG",
                             cfg["principles"]["anchor_offset_ticks"])
    from backend.v9.systems.five_min.adaptive_stop import compute_stop_v2 as s2_v2
    v2 = s2_v2(entry_price=7400.0, direction="LONG", structural_stop_price=struct,
               family="Double_BT", today_typical=2.0)

    sz = compute_v2_sizing(
        entry_price=7400.0, stop_price=v2.stop_price, direction="LONG",
        pattern_key="Double_BT", day_type="Normal", confidence_tier="high",
        day_has_direction=False, trade_with_trend=None,
        value_area_full_traverse=True, cfg=cfg, reversal=True)
    assert sz is not None


def test_e2e_hns():
    """HnS: shoulder (pattern-provided) → sizing."""
    cfg = _cfg()
    a = cfg["anchors"]["HnS"]
    assert a["type"] == "shoulder"

    shoulder = 7394.0
    struct = SA.apply_offset(shoulder, "LONG",
                             cfg["principles"]["anchor_offset_ticks"])
    from backend.v9.systems.five_min.adaptive_stop import compute_stop_v2 as s2_v2
    v2 = s2_v2(entry_price=7400.0, direction="LONG", structural_stop_price=struct,
               family="HnS", today_typical=2.0)

    sz = compute_v2_sizing(
        entry_price=7400.0, stop_price=v2.stop_price, direction="LONG",
        pattern_key="HnS", day_type="Normal", confidence_tier="medium",
        day_has_direction=False, trade_with_trend=None,
        value_area_full_traverse=False, cfg=cfg, reversal=True)
    assert sz is not None
    assert sz.mode == "tactical"


def test_e2e_flag():
    """Flag: breakout_bar (Michael 2026-06-09, NOT flag_low/wick) → sizing."""
    cfg = _cfg()
    a = cfg["anchors"]["Flag"]
    assert a["type"] == "breakout_bar"

    breakout_low = 7396.0
    struct = SA.apply_offset(breakout_low, "LONG",
                             cfg["principles"]["anchor_offset_ticks"])
    from backend.v9.systems.five_min.adaptive_stop import compute_stop_v2 as s2_v2
    v2 = s2_v2(entry_price=7400.0, direction="LONG", structural_stop_price=struct,
               family="Flag", today_typical=1.5)

    sz = compute_v2_sizing(
        entry_price=7400.0, stop_price=v2.stop_price, direction="LONG",
        pattern_key="Flag", day_type="Trend_Normal", confidence_tier="high",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg)
    assert sz is not None
    assert sz.mode == "strategic"  # trend day + with-trend


# ═══════════════════════════════════════════════════════════════════════════
# Cross-cutting: YAML values reach final trade params
# ═══════════════════════════════════════════════════════════════════════════

def test_yaml_anchor_offset_reaches_stop():
    """Verify the anchor offset from YAML actually reaches the stop price.

    Michael 2026-07-20 ruling: buffer widened 3T→6T (protective — fewer false
    stop-outs). Read the offset from config so this test verifies the YAML value
    truly flows through, and won't silently rot if the value changes again.
    """
    cfg = _cfg()
    off = cfg["principles"]["anchor_offset_ticks"]
    assert off == 6  # Michael 2026-07-20 (was 3)

    # One bar, LONG: window extreme = bar low, offset pushes stop off*T further
    bar = {"h": 7402.0, "l": 7398.0, "c": 7401.0}
    struct = SA.resolve_anchor_from_window([bar], "LONG", off)
    assert struct == 7398.0 - off * MES_TICK

    # atr_14=30t: structural risk (6T offset → 18t here) sits above the 0.5×ATR
    # floor (15t) and below the ATR cap, so the structural anchor governs and the
    # YAML offset reaches the final stop unchanged. (atr_14=100 previously let the
    # EARLY_ATR_FLOOR bind and masked the offset.)
    v2 = compute_stop_v2("LONG", 7401.0, struct, PatternGroup.CONT_TIGHT, atr_14=30.0)
    assert v2.stop_price == struct  # structural wins (not floored, not capped)


def test_yaml_floor_ticks_enforced():
    """Floor 4T from YAML prevents stop inside the bar."""
    cfg = _cfg()
    assert cfg["principles"]["floor_ticks"] == 4

    # Entry and structural are 1 tick apart → floor must win
    v2 = compute_stop_v2("LONG", 7400.0, 7399.75, PatternGroup.CONT_TIGHT, atr_14=100.0)
    assert v2.floor_applied is True
    assert v2.risk_ticks == 4


def test_yaml_contract_ladder_matches():
    """Contract ladder in YAML: ≤15→3, 15-25→2, >25→1."""
    cfg = _cfg()
    ladder = cfg["contract_ladder"]
    assert SA.contracts_from_risk(10.0, ladder) == 3
    assert SA.contracts_from_risk(20.0, ladder) == 2
    assert SA.contracts_from_risk(30.0, ladder) == 1
