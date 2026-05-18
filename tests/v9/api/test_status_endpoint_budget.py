import time

from backend.v9.api.v9 import status


def test_bridge_status_respects_redis_budget(monkeypatch):
    def slow_redis_cmd(_args, timeout=status.STATUS_REDIS_TIMEOUT_S):
        time.sleep(0.05)
        return None

    monkeypatch.setattr(status, "STATUS_BRIDGE_BUDGET_S", 0.12)
    monkeypatch.setattr(status, "_redis_cmd", slow_redis_cmd)

    started = time.monotonic()
    result = status._check_bridge()
    elapsed = time.monotonic() - started

    assert elapsed < 0.25
    assert result["partial"] is True
    assert result["streams_checked"] < result["streams_total"]


def test_status_endpoint_returns_when_one_check_is_slow(monkeypatch):
    def slow_bridge():
        time.sleep(0.5)
        return {"running": True}

    monkeypatch.setattr(status, "STATUS_ENDPOINT_BUDGET_S", 0.1)
    monkeypatch.setattr(status, "_check_session", lambda: {"current": "TEST"})
    monkeypatch.setattr(status, "_check_sierra", lambda: {"status": "active"})
    monkeypatch.setattr(status, "_check_bridge", slow_bridge)
    monkeypatch.setattr(status, "_check_event_bus", lambda: {"reachable": True})
    monkeypatch.setattr(status, "_check_ws", lambda: {"clients": 0})
    monkeypatch.setattr(status, "_check_frontend", lambda: {"reachable": True})
    monkeypatch.setattr(status, "_check_audit", lambda: {"running": False})
    monkeypatch.setattr(status, "_check_day_type", lambda: {"running": True})
    monkeypatch.setattr(status, "_check_hydration", lambda: {"bar_ingestion": {}})
    monkeypatch.setattr(status, "_check_bar_router", lambda: {"available": False})
    monkeypatch.setattr(status, "_check_historical_replay", lambda: {"available": True})

    started = time.monotonic()
    result = status.system_status()
    elapsed = time.monotonic() - started

    assert elapsed < 0.25
    assert result["bridge"] == {"available": False, "status": "timeout"}
    assert result["session"] == {"current": "TEST"}
