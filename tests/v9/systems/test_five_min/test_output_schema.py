"""Tests for T1Setup output schema (Pkg 3c · contract split fields)."""
from datetime import datetime, timezone
from backend.v9.systems.five_min.output_schema import T1Setup


def test_t1setup_accepts_contract_split_percentages():
    setup = T1Setup(
        pattern_name="REACTIVE_LONG",
        direction="LONG",
        entry_price=4500, stop_price=4495,
        t1_price=4510, t2_price=4520,
        confidence=75, bar_index=10,
        fired_at=datetime.now(timezone.utc),
        t1_pct=0.25, t2_pct=0.50, t3_pct=0.25,
    )
    assert setup.t1_pct == 0.25
    assert setup.t2_pct == 0.50
    assert setup.t3_pct == 0.25


def test_t1setup_defaults_split_to_zero():
    setup = T1Setup(
        pattern_name="REACTIVE_LONG",
        direction="LONG",
        entry_price=4500, stop_price=4495,
        t1_price=4510, t2_price=4520,
        confidence=75, bar_index=10,
        fired_at=datetime.now(timezone.utc),
    )
    assert setup.t1_pct == 0.0
    assert setup.t2_pct == 0.0
    assert setup.t3_pct == 0.0
