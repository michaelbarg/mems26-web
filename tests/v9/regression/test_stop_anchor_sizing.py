"""V2 sizing pipeline tests — contracts, T1, mode classification."""
from backend.v9.systems.stop_anchors.sizing import compute_v2_sizing
from backend.v9.config_loader import load_stop_anchors


def _load_cfg():
    cfg = load_stop_anchors()
    assert cfg is not None, "stop_anchors.yaml must be loadable"
    return cfg


def test_sizing_basic_long():
    cfg = _load_cfg()
    r = compute_v2_sizing(
        entry_price=7400.0, stop_price=7390.0, direction="LONG",
        pattern_key="ZLR", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg,
    )
    assert r is not None
    assert r.contracts >= 1
    assert r.risk_points == 10.0  # |7400 - 7390|
    assert r.t1_price > 7400.0   # T1 above entry for LONG
    assert r.mode == "strategic"  # trend day + with-trend


def test_sizing_counter_trend_tactical():
    cfg = _load_cfg()
    r = compute_v2_sizing(
        entry_price=7400.0, stop_price=7390.0, direction="SHORT",
        pattern_key="VEGAS", day_type="Trend_Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=False,  # counter-trend
        value_area_full_traverse=None, cfg=cfg, reversal=True,
    )
    assert r is not None
    assert r.mode == "tactical"
    assert r.mode_cap == 2  # tactical cap


def test_sizing_high_risk_reduces_contracts():
    cfg = _load_cfg()
    # 20 point risk → ladder says 2 contracts
    r = compute_v2_sizing(
        entry_price=7400.0, stop_price=7380.0, direction="LONG",
        pattern_key="ZLR", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg,
    )
    assert r is not None
    assert r.risk_points == 20.0
    assert r.ladder_contracts == 2  # 15-25pt band → 2


def test_sizing_skip_verdict():
    """Auth SKIP → returns None (no trade)."""
    cfg = _load_cfg()
    # Use a fake auth matrix with SKIP verdict
    fake_auth = {("ZLR", "Normal"): ("SKIP", 0, 0, 0)}
    r = compute_v2_sizing(
        entry_price=7400.0, stop_price=7390.0, direction="LONG",
        pattern_key="ZLR", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg, auth_matrix=fake_auth,
    )
    assert r is None


def test_t1_floor_enforced():
    """T1 must be at least 3 points from entry (commission floor)."""
    cfg = _load_cfg()
    # Tiny risk (1 pt) → T1 floor kicks in at 3 pts
    r = compute_v2_sizing(
        entry_price=7400.0, stop_price=7399.0, direction="LONG",
        pattern_key="Reactive", day_type="Normal", confidence_tier="medium",
        day_has_direction=False, trade_with_trend=None,
        value_area_full_traverse=True, cfg=cfg,
    )
    assert r is not None
    assert r.t1_price >= 7403.0  # at least 3 pts above entry


def test_reversal_multiplier_applied():
    """REV patterns get 0.8× T1 multiplier (more conservative)."""
    cfg = _load_cfg()
    common = dict(
        entry_price=7400.0, stop_price=7390.0, direction="LONG",
        day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg,
    )
    r_cont = compute_v2_sizing(pattern_key="ZLR", reversal=False, **common)
    r_rev = compute_v2_sizing(pattern_key="VEGAS", reversal=True, **common)
    assert r_cont is not None and r_rev is not None
    # Reversal T1 should be closer to entry (more conservative)
    assert r_rev.t1_price < r_cont.t1_price


def test_hfe_ladder_shift():
    """HFE has t1_ladder_shift=-1 in YAML (more conservative T1)."""
    cfg = _load_cfg()
    # Verify the YAML has the shift
    assert cfg["anchors"]["HFE"].get("t1_ladder_shift") == -1
    r = compute_v2_sizing(
        entry_price=7400.0, stop_price=7395.0, direction="LONG",
        pattern_key="HFE", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg, reversal=True,
    )
    assert r is not None
    assert r.t1_price > 7400.0  # still above entry
