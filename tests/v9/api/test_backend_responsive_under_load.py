"""P30 — Critical GET endpoints must stay responsive (<2s).

Regression for backend hang when a single uvicorn worker saturates under polling load.
Mitigation in production: `--workers 2`. This test guards the lightweight read path.
"""

import time

from fastapi.testclient import TestClient

from backend.v9.app import app

client = TestClient(app)

_CRITICAL_GETS = (
    "/api/v9/cockpit/heartbeat",
    "/api/v9/chart/bars5min?limit=10",
    "/api/v9/tpo/current",
    "/api/v9/cumulative_delta/current",
)


def test_critical_gets_respond_under_2s():
    for path in _CRITICAL_GETS:
        start = time.monotonic()
        resp = client.get(path)
        elapsed = time.monotonic() - start
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"
        assert elapsed < 2.0, f"{path} took {elapsed:.2f}s (budget 2s)"
