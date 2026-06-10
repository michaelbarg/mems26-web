"""A7 regression: T2=None must not crash pre_fire_validator.

if reverted → RED: FireRequest(t2_price=None) → Pydantic ValidationError
(t2_price: float = Field(gt=0) rejects None).
"""
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire


def test_t2_none_passes_validator():
    """T2=None (CCI-cross deferred) → validator runs without crash."""
    req = FireRequest(
        system_id="T2_WOODIES", direction="SHORT",
        entry_price=7400.0, stop_price=7410.0,
        t1_price=7393.0, t2_price=None,
        time_stop_minutes=90, confidence=65,
    )
    # GATE: must not crash
    resp = validate_fire(req)
    assert resp is not None
    # With valid T1 (7pt reward on 10pt risk = R:R=0.7 < 1.0 → fails R:R, not crash)
    # That's fine — the point is it doesn't TypeError on T2=None


def test_t2_none_with_good_rr_passes():
    """T2=None + R:R≥1 → valid=True (ready to route)."""
    req = FireRequest(
        system_id="T2_WOODIES", direction="SHORT",
        entry_price=7400.0, stop_price=7405.0,  # 5pt risk
        t1_price=7393.0,  # 7pt reward → R:R=1.4
        t2_price=None,
        time_stop_minutes=90, confidence=65,
    )
    resp = validate_fire(req)
    assert resp.valid is True, f"Should pass: {resp.fail_reason}"


def test_t2_present_still_works():
    """T2 as float still validates normally (no regression)."""
    req = FireRequest(
        system_id="T2_WOODIES", direction="SHORT",
        entry_price=7400.0, stop_price=7405.0,
        t1_price=7395.0, t2_price=7390.0,
        time_stop_minutes=90, confidence=65,
    )
    resp = validate_fire(req)
    assert resp.valid is True
