"""D-088: SHADOW records when cluster_guard blocks DEMO/LIVE."""
from datetime import datetime, timedelta

from backend.v9.gateway.trading_gateway import TradingGateway


def _setup():
    return {
        "firing_system": 4,
        "direction": "LONG",
        "classification": "TLB_LONG",
        "confidence": 0.8,
        "entry_price": 5900.0,
        "stop": 5890.0,
        "t1": 5910.0,
        "t2": 5920.0,
        "t3": 0.0,
    }


def test_shadow_recorded_when_cluster_guard_active(monkeypatch):
    gw = TradingGateway()
    monkeypatch.setattr(gw, "_get_chop_state", lambda: "FOUND")
    gw.cluster_guard._blocked_until = datetime.utcnow() + timedelta(minutes=5)

    result = gw.route_setup(_setup(), system_id=4)

    assert result["shadow"] is not None
    assert result["blocked_by"] == "cluster_guard"
    assert result["demo"] is None
    assert result["live"] is None
    assert gw.cluster_guard.get_state()["recent_attempts"] == 0


def test_record_attempt_still_after_gates_when_not_cluster_blocked(monkeypatch):
    gw = TradingGateway()
    monkeypatch.setattr(gw, "_get_chop_state", lambda: "FOUND")

    result = gw.route_setup(_setup(), system_id=4)

    assert result["blocked_by"] is None
    assert result["shadow"] is not None
    assert gw.cluster_guard.get_state()["recent_attempts"] == 1
