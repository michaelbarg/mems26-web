"""Tests for FootprintSystem."""
import pytest
from types import SimpleNamespace

from backend.v9.systems.footprint.detectors import detect_cluster, detect_empty_zones, analyze_context


class FakeGateway:
    def __init__(self):
        self.calls = []

    def route_setup(self, setup, system_id):
        self.calls.append((setup, system_id))
        return {"shadow": "s3-shadow-1", "demo": None, "live": None, "blocked_by": None}


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


def _ready_system(tmp_path):
    from backend.v9.systems.footprint.footprint_system import FootprintSystem

    sys = FootprintSystem(db_path=str(tmp_path / "missing.db"))
    sys._cumulative_delta = 120
    sys._last_dominance = "BUYER_DOMINATE"
    sys._last_initiative_type = "INITIATIVE_UP"
    return sys


def _long_signal():
    return {
        "signal": "stacked_imbalance",
        "direction": "LONG",
        "level": 100.0,
        "strength": 0.75,
        "evidence": {"stack_count": 4},
    }


def _long_bar():
    return {
        "bar_id": "s3-test-bar",
        "open": 99.5,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
        "tick_size": 0.25,
    }


def test_s3_valid_fire_routes_through_gateway_after_pre_fire(tmp_path):
    sys = _ready_system(tmp_path)
    gw = FakeGateway()
    sys.set_gateway(gw)

    sys._fire(_long_signal(), _long_bar(), SimpleNamespace(bar_id="s3-test-bar", session="RTH"))

    assert len(gw.calls) == 1
    setup, system_id = gw.calls[0]
    assert system_id == 3
    assert setup["firing_system"] == 3
    assert setup["direction"] == "LONG"
    assert setup["metadata"]["source"] == "footprint_auto_fire"

    last_fire = sys.get_current()["last_fire"]
    assert last_fire["pre_fire"]["valid"] is True
    assert last_fire["routed"] is True
    assert last_fire["blocked_by"] is None
    assert last_fire["route_reason"] == "routed_to_trading_gateway"
    assert last_fire["gateway"]["shadow"] == "s3-shadow-1"
    assert last_fire["gateway"]["demo"] is None
    assert last_fire["gateway"]["live"] is None


def test_s3_pre_fire_block_does_not_route(monkeypatch, tmp_path):
    from backend.v9.systems.footprint import footprint_system as footprint_module

    sys = _ready_system(tmp_path)
    gw = FakeGateway()
    sys.set_gateway(gw)

    monkeypatch.setattr(
        footprint_module,
        "validate_fire",
        lambda _req: SimpleNamespace(
            valid=False,
            fail_reason="LONG: stop must be < entry",
            dict=lambda: {"valid": False, "fail_reason": "LONG: stop must be < entry"},
        ),
    )

    sys._fire(_long_signal(), _long_bar(), SimpleNamespace(bar_id="s3-test-bar", session="RTH"))

    assert gw.calls == []
    last_fire = sys.get_current()["last_fire"]
    assert last_fire["routed"] is False
    assert last_fire["blocked_by"] == "pre_fire_validator"
    assert last_fire["route_reason"] == "LONG: stop must be < entry"


def test_s3_gateway_injection_does_not_enable_demo_or_live():
    from backend.v9.gateway.trading_gateway import TradingGateway
    from backend.v9.systems.footprint.footprint_system import FootprintSystem

    gw = TradingGateway()
    sys = FootprintSystem()
    sys.set_gateway(gw)

    assert gw._demo_enabled_systems == set()
    assert gw._live_enabled_systems == set()


# ── Pkg 2bc · forces_history tests ───────────────────────────────


def test_forces_history_starts_empty():
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    sys = FootprintSystem()
    assert sys._forces_history == []


def test_forces_history_capped_at_7():
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    sys = FootprintSystem()
    # Simulate 10 entries via direct append
    for i in range(10):
        sys._forces_history.append({"ts": i, "ask_vol": 100 + i, "bid_vol": 50 + i})
        if len(sys._forces_history) > sys._FORCES_HISTORY_CAP:
            sys._forces_history = sys._forces_history[-sys._FORCES_HISTORY_CAP:]
    assert len(sys._forces_history) == 7
    assert sys._forces_history[0]["ts"] == 3  # oldest = bar 4 (0-indexed)


def test_forces_history_exposed_via_current_state():
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    sys = FootprintSystem()
    sys._forces_history = [{"ts": 1, "ask_vol": 100, "bid_vol": 50}]
    sys.current_state["forces_history"] = list(sys._forces_history)
    assert sys.current_state["forces_history"] == [{"ts": 1, "ask_vol": 100, "bid_vol": 50}]
