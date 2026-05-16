"""Tests for setup_emitter (Path A: full Layer 3 + validator)."""
from backend.v9.systems.five_min.setup_emitter import emit_t1_setup


def test_emit_valid_long():
    setup = emit_t1_setup(
        'REACTIVE_LONG', 'LONG',
        entry_price=5250.0, stop_price=5248.0,
        t1_price=5252.0, t2_price=5254.0,
        bar_index=100,
        day_type="Variation",
        tpo_data={"poc": 5250.0, "vah": 5260.0, "val": 5240.0},
    )
    assert setup is not None
    assert setup.direction == 'LONG'
    assert setup.provisional is False
    assert setup.quality_tier == 'HIGH'  # at POC
    assert setup.sizing_contracts == 3


def test_emit_reduces_low_quality_without_rejecting():
    setup = emit_t1_setup(
        'REACTIVE_LONG', 'LONG',
        entry_price=5280.0, stop_price=5278.0,  # outside value area
        t1_price=5282.0, t2_price=5284.0,
        bar_index=100,
        tpo_data={"poc": 5250.0, "vah": 5260.0, "val": 5240.0},
    )
    assert setup is not None
    assert setup.quality_tier == 'LOW'
    assert setup.sizing_contracts == 1


def test_emit_rejects_invalid_rr():
    setup = emit_t1_setup(
        'INITIATIVE_SHORT', 'SHORT',
        entry_price=5250.0, stop_price=5252.0,
        t1_price=5249.5, t2_price=5249.0,  # R:R < 1.0 (risk=2, reward=0.5)
        bar_index=50,
        tpo_data={"poc": 5250.0, "vah": 5260.0, "val": 5240.0},
    )
    assert setup is None  # pre_fire_validator rejects


def test_emit_uses_day_type_time_stop():
    setup = emit_t1_setup(
        'REACTIVE_SHORT', 'SHORT',
        entry_price=5260.0, stop_price=5262.0,
        t1_price=5258.0, t2_price=5256.0,
        bar_index=80,
        day_type="Nontrend",
        tpo_data={"poc": 5260.0, "vah": 5265.0, "val": 5255.0},
    )
    assert setup is not None
    assert setup.time_stop_minutes == 20  # Nontrend = 20min
