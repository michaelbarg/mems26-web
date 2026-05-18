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
