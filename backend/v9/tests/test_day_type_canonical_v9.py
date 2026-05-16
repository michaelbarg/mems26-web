"""Prompt 20b — Prove /api/v9/day_type/current serves V9 canonical source.

Tests verify:
  1. V9 wins over stale V1 when both could classify
  2. Stale V1 does NOT become source of truth
  3. Response contains backward-compatible fields
  4. No SHADOW/DEMO/LIVE activation
"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from unittest.mock import patch, MagicMock
import importlib


def _get_current_handler():
    """Import the get_current function fresh."""
    import backend.v9.systems.day_type.api as api_module
    importlib.reload(api_module)
    return api_module.get_current


def test_v9_wins_over_v1_when_classified():
    """When V9 /v9/current returns classified=True, /current uses V9 data."""
    get_current = _get_current_handler()

    v9_response = MagicMock()
    v9_response.json.return_value = {
        "classified": True,
        "data": {
            "day_type": "Variation",
            "probability": 0.38,
            "ib_h": 7467.5,
            "ib_l": 7449.5,
            "ib_width_class": "MEDIUM",
            "opening_type": "OPEN_REJECTION_REVERSE",
        },
    }
    v9_response.status_code = 200

    with patch("requests.get", return_value=v9_response):
        result = get_current()

    assert result["day_type"] == "Variation", f"Expected Variation from V9, got {result['day_type']}"
    assert result["classified"] is True
    assert result["source"] == "v9"
    assert result["confidence"] == 38  # 0.38 * 100


def test_v1_stale_does_not_become_canonical():
    """When V9 has no classification, V1 result is demoted (not canonical)."""
    get_current = _get_current_handler()

    # V9 returns not classified
    v9_response = MagicMock()
    v9_response.json.return_value = {"classified": False, "data": None}

    # Mock _get_state_machine_classification to return None
    with patch("requests.get", return_value=v9_response), \
         patch("backend.v9.systems.day_type.api._get_state_machine_classification", return_value=None), \
         patch("backend.v9.systems.day_type.api._classify_v1_from_tpo", return_value={
             "day_type": "Nontrend", "confidence": 55, "classified": True,
             "ib_h": 7472.5, "ib_l": 7172.5, "ib_range": 300.0,
         }):
        result = get_current()

    # V1 result should be DEMOTED — classified=False
    assert result["classified"] is False, "V1 stale should NOT be canonical"
    assert result.get("source") == "v1_demoted"
    assert "V9 has not classified" in result.get("reason", "")


def test_pre_ib_returns_pending():
    """Pre-IB state returns PENDING (not stale classification)."""
    get_current = _get_current_handler()

    v9_response = MagicMock()
    v9_response.json.return_value = {"classified": False, "data": None}

    with patch("requests.get", return_value=v9_response), \
         patch("backend.v9.systems.day_type.api._get_state_machine_classification", return_value=None), \
         patch("backend.v9.systems.day_type.api._classify_v1_from_tpo", return_value={
             "day_type": "PENDING", "confidence": 0, "classified": False,
             "stage": "PRE_IB", "reason": "Awaiting IB lock @ 10:30 ET",
         }):
        result = get_current()

    assert result["day_type"] == "PENDING"
    assert result["classified"] is False


def test_response_has_backward_compatible_fields():
    """V9 response includes fields consumers expect."""
    get_current = _get_current_handler()

    v9_response = MagicMock()
    v9_response.json.return_value = {
        "classified": True,
        "data": {
            "day_type": "Trend_Normal",
            "probability": 0.70,
            "ib_h": 7480.0,
            "ib_l": 7465.0,
            "ib_width_class": "MEDIUM",
            "opening_type": "OPEN_DRIVE",
        },
    }

    with patch("requests.get", return_value=v9_response):
        result = get_current()

    # Must have these fields for backward compat
    assert "day_type" in result
    assert "confidence" in result
    assert "classified" in result
    assert "ib_h" in result
    assert "ib_l" in result


def test_no_shadow_demo_live_in_response():
    """Response never contains mode activation fields."""
    get_current = _get_current_handler()

    v9_response = MagicMock()
    v9_response.json.return_value = {
        "classified": True,
        "data": {"day_type": "Normal", "probability": 0.5},
    }

    with patch("requests.get", return_value=v9_response):
        result = get_current()

    assert "shadow" not in result
    assert "demo" not in result
    assert "live" not in result
    assert "mode" not in result
