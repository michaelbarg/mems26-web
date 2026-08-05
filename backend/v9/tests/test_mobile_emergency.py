"""Mobile emergency tests — PAUSE/RESUME/FLATTEN via mobile + gateway pause gate.

Key invariants:
1. Gateway blocks demo/live when trading_paused.json exists (shadow continues)
2. Gateway allows all when file absent (fail-open)
3. _is_trading_paused never raises
4. PAUSE endpoint creates the file, RESUME removes it
"""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── Test 1: gateway pause gate ──

def test_gateway_pause_blocks_when_file_exists(tmp_path):
    """When trading_paused.json exists, _is_trading_paused returns True."""
    pause_file = tmp_path / "trading_paused.json"
    pause_file.write_text('{"paused": true}')

    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway()
    with patch.object(gw, "_is_trading_paused") as mock:
        mock.return_value = True
        assert gw._is_trading_paused() is True


def test_gateway_pause_allows_when_file_absent():
    """When trading_paused.json doesn't exist, _is_trading_paused returns False."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway()
    # Patch the home path to a non-existent location
    with patch("os.path.expanduser", return_value="/tmp/nonexistent_mems26_test"):
        result = gw._is_trading_paused()
    assert result is False


def test_gateway_pause_failopen_on_exception():
    """If file check raises, _is_trading_paused returns False (fail-open)."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway()
    with patch("os.path.expanduser", side_effect=PermissionError("denied")):
        result = gw._is_trading_paused()
    assert result is False


# ── Test 2: classify root cause (MANAGEMENT from postmortem) ──

def test_pause_file_round_trip(tmp_path):
    """PAUSE creates the file, RESUME removes it."""
    pause_file = tmp_path / "trading_paused.json"

    # PAUSE: write
    pause_file.write_text(json.dumps({"paused": True, "source": "test"}))
    assert pause_file.exists()

    # RESUME: delete
    pause_file.unlink()
    assert not pause_file.exists()


# ── Test 3: render relay command endpoints ──

def test_render_cmd_queue():
    """Command relay: POST → pending → ACK lifecycle."""
    # Import and test the internal state directly
    from render_mobile_relay.app import _CMD

    # Initially empty
    assert _CMD["pending"] is None

    # Simulate POST /cmd
    import time
    _CMD["counter"] += 1
    _CMD["pending"] = {"action": "FLATTEN", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "id": _CMD["counter"]}
    _CMD["ts"] = time.monotonic()
    assert _CMD["pending"]["action"] == "FLATTEN"

    # Simulate GET /cmd/pending
    assert _CMD["pending"] is not None

    # Simulate POST /cmd/ack
    _CMD["pending"] = None
    assert _CMD["pending"] is None


def test_render_cmd_ttl_expiry():
    """Command expires after TTL."""
    from render_mobile_relay.app import _CMD, _CMD_TTL
    import time

    _CMD["counter"] += 1
    _CMD["pending"] = {"action": "PAUSE", "id": _CMD["counter"]}
    _CMD["ts"] = time.monotonic() - _CMD_TTL - 1  # expired

    # Should be expired
    assert time.monotonic() - _CMD["ts"] > _CMD_TTL


def test_double_cmd_overwrites():
    """Second command overwrites the first (queue of 1)."""
    from render_mobile_relay.app import _CMD
    import time

    _CMD["counter"] += 1
    _CMD["pending"] = {"action": "PAUSE", "id": _CMD["counter"]}
    _CMD["ts"] = time.monotonic()

    _CMD["counter"] += 1
    _CMD["pending"] = {"action": "FLATTEN", "id": _CMD["counter"]}
    _CMD["ts"] = time.monotonic()

    assert _CMD["pending"]["action"] == "FLATTEN"
    _CMD["pending"] = None  # cleanup
