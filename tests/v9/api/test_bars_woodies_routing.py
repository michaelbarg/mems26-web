"""Regression: post_woodies_5min routes current_bar (live) over history[-1] (frozen).

Pinning the AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28 §6 rank-2 fix.
"""
import os
from unittest.mock import patch

import pytest

# Ensure bridge token matches .env
_TOKEN = os.environ.get("BRIDGE_TOKEN") or "michael-mems26-2026"
os.environ["BRIDGE_TOKEN"] = _TOKEN
_AUTH = {"Authorization": f"Bearer {_TOKEN}"}


def _frozen_bar(ts, cci=49.70, swi=-78.17, tcci=-21.09):
    return {
        "ts": ts,
        "ohlc": {"o": 7570.0, "h": 7572.0, "l": 7569.0, "c": 7571.5, "vol": 1000},
        "cci_14": cci, "cci_6_tcci": tcci, "swi_value": swi, "czi_value": 54.0,
        "trend_state": "BLUE", "ema_34": 7559.8, "lsma_value": 7577.9,
        "predictor_next_cci": 50.0,
    }


def test_current_bar_overrides_frozen_history():
    """When current_bar present, _route_bar receives its LIVE study values."""
    from fastapi.testclient import TestClient
    from backend.main import app
    client = TestClient(app)

    history = [_frozen_bar(f"17{i:02d}00") for i in range(5, 20, 5)]
    live = {
        "ts": "1720000",
        "ohlc": {"o": 7573.0, "h": 7575.0, "l": 7572.0, "c": 7574.5, "vol": 1500},
        "cci_14": 47.21, "cci_6_tcci": -94.66, "swi_value": 12.34,
        "czi_value": 60.0, "trend_state": "BLUE", "ema_34": 7560.0,
        "lsma_value": 7578.0, "predictor_next_cci": 50.5,
    }
    payload = {"type": "woodies_5min", "history": history, "current_bar": live}

    with patch("backend.v9.api.v9.bars._route_bar") as mock_route:
        resp = client.post("/api/v9/bars/woodies_5min", json=payload,
                           headers=_AUTH)
        assert resp.status_code == 200, resp.text
        mock_route.assert_called_once()
        _, flat = mock_route.call_args[0]
        assert flat["cci_14"] == pytest.approx(47.21)
        assert flat["swi_value"] == pytest.approx(12.34)
        assert flat["cci_6_tcci"] == pytest.approx(-94.66)


def test_no_current_bar_falls_back_to_history():
    """Legacy: when current_bar absent, _route_bar gets history[-1]."""
    from fastapi.testclient import TestClient
    from backend.main import app
    client = TestClient(app)

    history = [_frozen_bar(f"17{i:02d}00", cci=42.0 + i) for i in range(5, 20, 5)]
    payload = {"type": "woodies_5min", "history": history}

    with patch("backend.v9.api.v9.bars._route_bar") as mock_route:
        resp = client.post("/api/v9/bars/woodies_5min", json=payload,
                           headers=_AUTH)
        assert resp.status_code == 200
        mock_route.assert_called_once()
        _, flat = mock_route.call_args[0]
        assert flat["cci_14"] == pytest.approx(57.0)
