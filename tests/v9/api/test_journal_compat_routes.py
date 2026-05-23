"""Journal compat — legacy /trades/log reads v9_trades."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_trades_log_returns_shadow_rows():
    resp = client.get("/trades/log?types=shadow&limit=5&min_score=0")
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    if rows:
        assert rows[0].get("is_shadow") is True
        assert "entry_ts" in rows[0] or "ts" in rows[0]


def test_shadow_today_summary():
    resp = client.get("/analytics/setups/today_summary?min_score=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_setups" in data
