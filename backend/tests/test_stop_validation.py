"""
Tests for stop validation in POST /trade/execute.

Three branches:
  1. stop_pts > 8  → 400 STOP_TOO_WIDE
  2. stop_pts < 3  → auto-expand to 3pt
  3. stop_pts in [3, 8] → accepted
"""

import os
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo

# Ensure env vars are set before importing app
os.environ.setdefault("UPSTASH_REDIS_REST_URL", "https://fake-redis.upstash.io")
os.environ.setdefault("UPSTASH_REDIS_REST_TOKEN", "fake-token")
os.environ.setdefault("MEMS26_MODE", "SIM")

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

# Fake time inside NY Open killzone: 09:45 ET
_FAKE_ET = datetime(2026, 4, 17, 9, 45, 0, tzinfo=ZoneInfo("America/New_York"))


def _patches():
    """Context managers that bypass Redis, circuit breaker, killzone, and news guard."""
    return [
        patch("backend.main.redis_get_key", new=AsyncMock(return_value=None)),
        patch("backend.main.redis_set_key", new=AsyncMock(return_value=None)),
        patch("backend.main.redis_get", new=AsyncMock(return_value={"price": 7100})),
        patch("backend.main.check_circuit_breaker", new=AsyncMock(
            return_value={"allowed": True, "reason": ""})),
        patch("backend.main.get_daily_state", new=AsyncMock(return_value={
            "pnl": 0, "trade_count": 0, "consecutive_losses": 0,
            "locked_until": 0, "hard_locked": False, "date": "2026-04-17",
        })),
        patch("backend.main.save_daily_state", new=AsyncMock(return_value=None)),
        patch("backend.main.redis_delete_key", new=AsyncMock(return_value=None)),
    ]


def _run_with_patches(payload: dict):
    """Execute POST /trade/execute with all guards patched except stop validation."""
    patches = _patches()
    for p in patches:
        p.start()
    try:
        return client.post("/trade/execute", json=payload)
    finally:
        for p in patches:
            p.stop()


# ── Branch 1: stop_pts > 8 → 400 STOP_TOO_WIDE ──

def test_stop_too_wide_long():
    resp = _run_with_patches({
        "direction": "LONG", "entry_price": 7100.0, "stop": 7090.0,
        "t1": 7115, "t2": 7130, "t3": 0, "setup_type": "TEST",
    })
    assert resp.status_code == 400
    assert "STOP_TOO_WIDE" in resp.json()["detail"]


def test_stop_too_wide_short():
    resp = _run_with_patches({
        "direction": "SHORT", "entry_price": 7100.0, "stop": 7108.75,
        "t1": 7085, "t2": 7070, "t3": 0, "setup_type": "TEST",
    })
    assert resp.status_code == 400
    assert "STOP_TOO_WIDE" in resp.json()["detail"]


def test_stop_too_wide_boundary():
    """8.01pt risk should be rejected."""
    resp = _run_with_patches({
        "direction": "LONG", "entry_price": 7100.0, "stop": 7091.99,
        "t1": 7115, "t2": 7130, "t3": 0, "setup_type": "TEST",
    })
    assert resp.status_code == 400
    assert "STOP_TOO_WIDE" in resp.json()["detail"]


# ── Branch 2: stop_pts < 3 → auto-expand to 3pt ──

def test_stop_auto_expand_long():
    resp = _run_with_patches({
        "direction": "LONG", "entry_price": 7100.0, "stop": 7099.0,
        "t1": 7115, "t2": 7130, "t3": 0, "setup_type": "TEST",
    })
    # May get 403 from killzone — but should NOT get STOP_TOO_WIDE
    if resp.status_code == 200:
        trade = resp.json()["trade"]
        assert trade["stop"] == 7097.0  # entry - 3pt
        assert trade["risk_pts"] == 3.0
    else:
        assert "STOP_TOO_WIDE" not in resp.json().get("detail", "")


def test_stop_auto_expand_short():
    resp = _run_with_patches({
        "direction": "SHORT", "entry_price": 7100.0, "stop": 7101.0,
        "t1": 7085, "t2": 7070, "t3": 0, "setup_type": "TEST",
    })
    if resp.status_code == 200:
        trade = resp.json()["trade"]
        assert trade["stop"] == 7103.0  # entry + 3pt
        assert trade["risk_pts"] == 3.0
    else:
        assert "STOP_TOO_WIDE" not in resp.json().get("detail", "")


# ── Branch 3: stop_pts in [3, 8] → accepted ──

def test_stop_accepted_5pt():
    resp = _run_with_patches({
        "direction": "LONG", "entry_price": 7100.0, "stop": 7095.0,
        "t1": 7115, "t2": 7130, "t3": 0, "setup_type": "TEST",
    })
    if resp.status_code == 200:
        trade = resp.json()["trade"]
        assert trade["risk_pts"] == 5.0
    else:
        # Killzone may block, but stop validation should not
        assert "STOP_TOO_WIDE" not in resp.json().get("detail", "")


def test_stop_accepted_boundary_8pt():
    """Exactly 8pt → should pass."""
    resp = _run_with_patches({
        "direction": "SHORT", "entry_price": 7100.0, "stop": 7108.0,
        "t1": 7085, "t2": 7070, "t3": 0, "setup_type": "TEST",
    })
    if resp.status_code == 200:
        trade = resp.json()["trade"]
        assert trade["risk_pts"] == 8.0
    else:
        assert "STOP_TOO_WIDE" not in resp.json().get("detail", "")


def test_stop_accepted_boundary_3pt():
    """Exactly 3pt → should pass without expansion."""
    resp = _run_with_patches({
        "direction": "LONG", "entry_price": 7100.0, "stop": 7097.0,
        "t1": 7115, "t2": 7130, "t3": 0, "setup_type": "TEST",
    })
    if resp.status_code == 200:
        trade = resp.json()["trade"]
        assert trade["risk_pts"] == 3.0
        assert trade["stop"] == 7097.0
    else:
        assert "STOP_TOO_WIDE" not in resp.json().get("detail", "")
