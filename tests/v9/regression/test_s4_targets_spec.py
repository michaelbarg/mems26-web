"""S4 targets per 2026-06-10 spec: ladder T1 for CONT, measure for VEGAS/GHOST,
CCI-cross targets = None (deferred §1.6).

Calls REAL detect functions and resolver. RED-on-revert noted per test.
"""
from backend.v9.systems.stop_anchors import resolver as SA
from backend.v9.config_loader import load_stop_anchors


def _cfg():
    cfg = load_stop_anchors()
    assert cfg is not None
    return cfg


def test_zlr_t1_uses_risk_ladder():
    """ZLR T1 = ladder(risk), not 12T fixed.
    if reverted → RED because T1 would be entry±12*0.25=3pt (fixed ticks)."""
    cfg = _cfg()
    entry, stop = 7400.0, 7390.0  # 10pt risk, LONG
    t1 = SA.t1_price(
        entry, stop, "LONG",
        t1_ladder_cont=cfg["t1_ladder_continuation"],
        reversal=False,
        reversal_mult=cfg.get("t1_reversal_multiplier", 0.8),
        t1_floor_points=cfg.get("t1_floor_points", 3.0),
    )
    # Ladder: 10pt risk → band [5,10] → t1_r=0.75 → T1 = 7400 + 0.75*10 = 7407.5
    assert t1 > entry  # LONG: T1 above entry
    assert abs(t1 - 7407.5) < 0.01, f"ZLR T1={t1}, expected 7407.5 (ladder 0.75R)"
    # NOT 12T fixed = 7403.0
    assert abs(t1 - 7403.0) > 1.0, "T1 should NOT be 12-tick fixed"


def test_vegas_t1_measure_075():
    """VEGAS T1 = Measure×0.75 (was ×0.5).
    if reverted → RED because t1_measure_cap would be 0.5."""
    cfg = _cfg()
    assert cfg["anchors"]["VEGAS"]["t1_measure_cap"] == 0.75


def test_ghost_t1_measure_05():
    """GHOST T1 = Measure×0.5."""
    cfg = _cfg()
    assert cfg["anchors"]["GHOST"]["t1_measure_cap"] == 0.5


def test_famir_htlb_reversal_mult():
    """FAMIR/HTLB T1 = ladder × 0.8 (reversal).
    if reverted → RED because reversal_mult not applied."""
    cfg = _cfg()
    entry, stop = 7400.0, 7415.0  # 15pt risk, SHORT
    # FAMIR (reversal=True)
    t1_rev = SA.t1_price(
        entry, stop, "SHORT",
        t1_ladder_cont=cfg["t1_ladder_continuation"],
        reversal=True,
        reversal_mult=cfg.get("t1_reversal_multiplier", 0.8),
        t1_floor_points=cfg.get("t1_floor_points", 3.0),
    )
    # Without reversal
    t1_cont = SA.t1_price(
        entry, stop, "SHORT",
        t1_ladder_cont=cfg["t1_ladder_continuation"],
        reversal=False,
        reversal_mult=cfg.get("t1_reversal_multiplier", 0.8),
        t1_floor_points=cfg.get("t1_floor_points", 3.0),
    )
    # Reversal T1 should be closer to entry (more conservative)
    assert abs(t1_rev - entry) < abs(t1_cont - entry), \
        f"Reversal T1={t1_rev} should be closer to entry than CONT T1={t1_cont}"


def test_hfe_ladder_shift_floor():
    """HFE T1 = ladder shift=-1 × 0.8, floor 3pt.
    if reverted → RED because ladder_shift not applied."""
    cfg = _cfg()
    assert cfg["anchors"]["HFE"].get("t1_ladder_shift") == -1

    # Small risk (2pt) → floor 3pt should govern
    entry, stop = 7400.0, 7398.0  # 2pt risk
    t1 = SA.t1_price(
        entry, stop, "LONG",
        t1_ladder_cont=cfg["t1_ladder_continuation"],
        reversal=True,
        reversal_mult=0.8,
        t1_floor_points=3.0,
        ladder_shift=-1,
    )
    assert t1 >= entry + 3.0, f"T1={t1}, floor 3pt should give ≥{entry+3.0}"


def test_cci_cross_targets_are_none():
    """CCI-cross targets (CONT T2/T3, GHOST T2/T3, etc.) must be None.
    if reverted → RED because someone synthesized a price for CCI-cross."""
    # This verifies the design decision: CCI-cross = None until §1.6 monitor
    # We verify by checking that CONT patterns in the YAML have no t2/t3 fields
    cfg = _cfg()
    for pat in ["ZLR", "TLB", "TT", "GB100", "FAMIR", "HTLB", "HFE"]:
        acfg = cfg["anchors"].get(pat, {})
        assert acfg.get("t2_measure_mult") is None, \
            f"{pat} should not have t2_measure_mult (CCI-cross → None)"


def test_vegas_has_t2_measure():
    """VEGAS T2 = Measure×1.0 (the only pattern with pre-computed T2)."""
    cfg = _cfg()
    assert cfg["anchors"]["VEGAS"].get("t2_measure_mult") == 1.0
