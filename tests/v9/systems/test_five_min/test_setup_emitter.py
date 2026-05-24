"""Tests for setup_emitter (Pkg 3c · contract split population)."""
from backend.v9.systems.five_min.setup_emitter import emit_t1_setup


def test_setup_emitter_populates_contract_split_for_reactive_long():
    setup = emit_t1_setup(
        pattern_name="REACTIVE_LONG",
        direction="LONG",
        entry_price=4500, stop_price=4495,
        t1_price=4510, t2_price=4520,
        bar_index=10,
        day_type="Trend_Normal",
    )
    assert setup is not None
    assert (setup.t1_pct, setup.t2_pct, setup.t3_pct) == (0.25, 0.50, 0.25)
