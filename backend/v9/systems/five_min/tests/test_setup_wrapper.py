"""Tests for setup_wrapper (graceful degradation)."""
from backend.v9.systems.five_min.setup_wrapper import build_t1setup, ClusterInfo, EmptyZone
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire


def _bars_long():
    return [
        {"o": 5250, "h": 5250, "l": 5247, "c": 5247.5, "v": 1000},  # Bar -3
        {"o": 5248, "h": 5248, "l": 5247, "c": 5247.75, "v": 80},   # Bar -2
        {"o": 5247.25, "h": 5249, "l": 5247.25, "c": 5248.75, "v": 800},  # Bar -1
        {"o": 5248.5, "h": 5250, "l": 5248.5, "c": 5249.75, "v": 700},   # Bar 0
    ]


def test_wrapper_with_cluster():
    cluster: ClusterInfo = {"top": 5250.0, "bottom": 5248.0, "yellow_poc": 5249.0}
    empty: EmptyZone = {"top": 5248.0, "bottom": 5246.5}
    setup = build_t1setup(
        'REACTIVE_LONG', 'LONG', _bars_long(), bar_index=100,
        cluster=cluster, empty_zone=empty, day_type="Normal",
    )
    assert setup.provisional is False
    assert setup.entry_price == 5249.0
    assert setup.stop_price == 5246.5


def test_wrapper_without_cluster():
    setup = build_t1setup('REACTIVE_LONG', 'LONG', _bars_long(), bar_index=100)
    assert setup.provisional is True
    assert "no Layer 3 cluster" in setup.provisional_reason
    assert setup.entry_price == 5249.75  # bar_0 close


def test_wrapper_long_pricing():
    setup = build_t1setup('REACTIVE_LONG', 'LONG', _bars_long(), bar_index=100)
    assert setup.stop_price < setup.entry_price
    assert setup.t1_price > setup.entry_price
    assert setup.t2_price > setup.t1_price


def test_wrapper_short_pricing():
    bars = [
        {"o": 5247, "h": 5250, "l": 5247, "c": 5249.5, "v": 1000},
        {"o": 5249, "h": 5249, "l": 5248, "c": 5248.25, "v": 90},
        {"o": 5249, "h": 5249, "l": 5247, "c": 5247.5, "v": 800},
        {"o": 5248, "h": 5248, "l": 5246, "c": 5246.5, "v": 700},
    ]
    setup = build_t1setup('REACTIVE_SHORT', 'SHORT', bars, bar_index=100)
    assert setup.stop_price > setup.entry_price
    assert setup.t1_price < setup.entry_price
    assert setup.t2_price < setup.t1_price


def test_wrapper_emits_valid_t1setup():
    setup = build_t1setup('INITIATIVE_LONG', 'LONG', _bars_long(), bar_index=50)
    # Should pass pre_fire_validator
    req = FireRequest(
        system_id=setup.system_id,
        direction=setup.direction,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        t1_price=setup.t1_price,
        t2_price=setup.t2_price,
        time_stop_minutes=setup.time_stop_minutes,
        confidence=setup.confidence,
    )
    resp = validate_fire(req)
    assert resp.valid is True
