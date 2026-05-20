"""GW-02: cluster_guard.record_attempt only after pre-trade gates pass."""
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


def test_record_attempt_not_counted_when_cooldown_blocks():
    gw = TradingGateway()
    gw.cooldown.cooldown_until = datetime.utcnow() + timedelta(minutes=30)
    gw.cooldown.consecutive_stops = 2

    result = gw.route_setup(_setup(), system_id=4)

    assert result["blocked_by"] == "cooldown"
    assert result["shadow"] is None
    assert gw.cluster_guard.get_state()["recent_attempts"] == 0


def test_record_attempt_counted_when_gates_pass(monkeypatch):
    gw = TradingGateway()
    monkeypatch.setattr(gw, "_get_chop_state", lambda: "FOUND")

    result = gw.route_setup(_setup(), system_id=4)

    assert result.get("blocked_by") is None
    assert result["shadow"] is not None
    assert gw.cluster_guard.get_state()["recent_attempts"] == 1
