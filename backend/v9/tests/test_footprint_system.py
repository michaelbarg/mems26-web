"""Tests for FootprintSystem."""
import pytest
from backend.v9.systems.footprint.detectors import detect_cluster, detect_empty_zones, analyze_context


def test_cluster_detected_strong_poc():
    fp = {100.0: {"bid_vol": 70, "ask_vol": 30}, 101.0: {"bid_vol": 5, "ask_vol": 5}}
    r = detect_cluster(fp)
    assert r.has_cluster
    assert r.yellow_poc_pct > 30


def test_cluster_no_detection_uniform():
    fp = {p: {"bid_vol": 10, "ask_vol": 10} for p in [100, 101, 102, 103, 104, 105]}
    r = detect_cluster(fp)
    assert not r.has_cluster


def test_empty_zones_found():
    fp = {100: {"bid_vol": 50, "ask_vol": 50}, 101: {"bid_vol": 1, "ask_vol": 1}, 102: {"bid_vol": 1, "ask_vol": 1}}
    r = detect_empty_zones(fp)
    assert r.has_empty


def test_context_accumulation():
    bars = [{"high": 100.5, "low": 99.5, "close": 100, "open": 100} for _ in range(5)]
    r = analyze_context(bars, min_acc_bars=5, range_ticks=15)
    assert r.accumulation


def test_context_three_jumps_up():
    bars = [
        {"open": 100, "close": 101, "high": 101, "low": 100},
        {"open": 101, "close": 102, "high": 102, "low": 101},
        {"open": 102, "close": 103, "high": 103, "low": 102},
    ]
    r = analyze_context(bars)
    assert r.jumps_count == 3
    assert r.jumps_direction == "UP"


def test_footprint_system_hydrate():
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    sys = FootprintSystem()
    result = sys.hydrate()
    assert result.success


def test_footprint_extends_base():
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    from backend.v9.systems.base.trading_system import BaseV9TradingSystem
    assert issubclass(FootprintSystem, BaseV9TradingSystem)


def test_footprint_subscribes_tick_reversal():
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    sys = FootprintSystem()
    assert "tick_reversal_15" in sys.subscribed_bar_types()
