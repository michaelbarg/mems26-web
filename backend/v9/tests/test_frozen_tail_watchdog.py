"""Tests for frozen-tail watchdog — detect + alert, no false positives."""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.v9.services.frozen_tail_watchdog import (
    check_once, _read_bars_tip, _state, FrozenTailState,
    STALE_THRESHOLD, LIVE_PRICE_FRESH, get_frozen_tail_state,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset watchdog state before each test."""
    _state.status = "idle"
    _state.last_check_ts = 0.0
    _state.bars_tip_ts = None
    _state.bars_tip_iso = None
    _state.file_mtime = 0.0
    _state.live_price_age = -1.0
    _state.frozen_since = None
    _state.alert_count = 0
    _state.last_alert_ts = 0.0
    yield


@pytest.fixture
def fake_export(tmp_path):
    """Create a temporary export directory with 5min.json and live_price.json."""
    fivemin = tmp_path / "5min.json"
    liveprice = tmp_path / "live_price.json"
    return tmp_path, fivemin, liveprice


def _write_5min(path: Path, bar_ts: float):
    """Write a minimal 5min.json with a single bar at given timestamp."""
    data = {"bars": [{"ts": bar_ts, "o": 100, "h": 101, "l": 99, "c": 100.5, "v": 1000}]}
    path.write_text(json.dumps(data))


def _write_liveprice(path: Path, price: float = 5500.0):
    """Write a minimal live_price.json."""
    data = {"price": price, "ts": time.time()}
    path.write_text(json.dumps(data))


# ── _read_bars_tip tests ──

def test_read_bars_tip_unix_ts(tmp_path):
    p = tmp_path / "5min.json"
    ts = 1717500000.0
    _write_5min(p, ts)
    assert _read_bars_tip(p) == ts


def test_read_bars_tip_iso_string(tmp_path):
    p = tmp_path / "5min.json"
    data = {"bars": [{"ts": "2026-06-04T10:00:00+00:00"}]}
    p.write_text(json.dumps(data))
    result = _read_bars_tip(p)
    assert result is not None
    assert abs(result - 1780570800.0) < 86400  # rough check — within a day


def test_read_bars_tip_missing_file(tmp_path):
    p = tmp_path / "nonexistent.json"
    assert _read_bars_tip(p) is None


def test_read_bars_tip_empty_bars(tmp_path):
    p = tmp_path / "5min.json"
    p.write_text(json.dumps({"bars": []}))
    assert _read_bars_tip(p) is None


# ── check_once tests ──

@patch("backend.v9.services.frozen_tail_watchdog._is_rth_now", return_value=True)
@patch("backend.v9.services.frozen_tail_watchdog._weekday_now", return_value=2)  # Wednesday
@patch("backend.v9.services.frozen_tail_watchdog._pg_max_ts", return_value=None)
@patch("backend.v9.services.frozen_tail_watchdog._send_alert")
def test_frozen_tail_detected(mock_alert, mock_pg, mock_wd, mock_rth, fake_export):
    """Synthetic frozen-tail: mtime fresh, bars stale, live_price alive."""
    tmp_path, fivemin, liveprice = fake_export

    # Write 5min.json with bar stuck 20 minutes ago
    stale_ts = time.time() - STALE_THRESHOLD - 300  # 10min + 5min ago
    _write_5min(fivemin, stale_ts)
    # Touch to make mtime fresh (file is being written)
    fivemin.touch()

    # Write fresh live_price.json
    _write_liveprice(liveprice)

    with patch("backend.v9.services.frozen_tail_watchdog.EXPORT_DIR", str(tmp_path)):
        status = check_once()

    assert status == "frozen_tail"
    assert _state.status == "frozen_tail"
    assert _state.frozen_since is not None
    assert _state.alert_count == 1
    mock_alert.assert_called_once()
    # Verify alert message contains key info
    msg = mock_alert.call_args[0][0]
    assert "frozen-tail" in msg.lower()
    assert "Reload Study" in msg


@patch("backend.v9.services.frozen_tail_watchdog._is_rth_now", return_value=True)
@patch("backend.v9.services.frozen_tail_watchdog._weekday_now", return_value=2)
@patch("backend.v9.services.frozen_tail_watchdog._pg_max_ts", return_value=None)
@patch("backend.v9.services.frozen_tail_watchdog._send_alert")
def test_healthy_feed_no_alert(mock_alert, mock_pg, mock_wd, mock_rth, fake_export):
    """Healthy feed: mtime fresh, bars fresh, live_price fresh → no alert."""
    tmp_path, fivemin, liveprice = fake_export

    # Write 5min.json with fresh bar (just now)
    _write_5min(fivemin, time.time() - 10)  # 10 seconds ago = fresh
    _write_liveprice(liveprice)

    with patch("backend.v9.services.frozen_tail_watchdog.EXPORT_DIR", str(tmp_path)):
        status = check_once()

    assert status == "ok"
    assert _state.status == "ok"
    assert _state.frozen_since is None
    assert _state.alert_count == 0
    mock_alert.assert_not_called()


@patch("backend.v9.services.frozen_tail_watchdog._is_rth_now", return_value=True)
@patch("backend.v9.services.frozen_tail_watchdog._weekday_now", return_value=2)
@patch("backend.v9.services.frozen_tail_watchdog._pg_max_ts", return_value=None)
@patch("backend.v9.services.frozen_tail_watchdog._send_alert")
def test_feed_down_not_frozen_tail(mock_alert, mock_pg, mock_wd, mock_rth, fake_export):
    """Feed down: both files stale → feed_down, NOT frozen-tail."""
    tmp_path, fivemin, liveprice = fake_export

    # Write files but make them old
    stale_ts = time.time() - STALE_THRESHOLD - 300
    _write_5min(fivemin, stale_ts)
    _write_liveprice(liveprice)

    # Make both files old (mtime in the past)
    old_time = time.time() - 120  # 2 minutes ago — past CHECK_INTERVAL*2
    os.utime(fivemin, (old_time, old_time))
    os.utime(liveprice, (old_time, old_time))

    with patch("backend.v9.services.frozen_tail_watchdog.EXPORT_DIR", str(tmp_path)):
        status = check_once()

    assert status == "feed_down"
    assert _state.status == "feed_down"
    assert _state.alert_count == 0
    mock_alert.assert_not_called()


@patch("backend.v9.services.frozen_tail_watchdog._is_rth_now", return_value=False)
@patch("backend.v9.services.frozen_tail_watchdog._weekday_now", return_value=2)
def test_outside_rth_idle(mock_wd, mock_rth, fake_export):
    """Outside RTH → idle, no checks."""
    tmp_path, fivemin, liveprice = fake_export
    _write_5min(fivemin, time.time() - 9999)
    _write_liveprice(liveprice)

    with patch("backend.v9.services.frozen_tail_watchdog.EXPORT_DIR", str(tmp_path)):
        status = check_once()

    assert status == "idle"


@patch("backend.v9.services.frozen_tail_watchdog._is_rth_now", return_value=True)
@patch("backend.v9.services.frozen_tail_watchdog._weekday_now", return_value=5)  # Saturday
def test_weekend_idle(mock_wd, mock_rth, fake_export):
    """Weekend → idle regardless of RTH."""
    tmp_path, fivemin, liveprice = fake_export
    _write_5min(fivemin, time.time() - 9999)
    _write_liveprice(liveprice)

    with patch("backend.v9.services.frozen_tail_watchdog.EXPORT_DIR", str(tmp_path)):
        status = check_once()

    assert status == "idle"


@patch("backend.v9.services.frozen_tail_watchdog._is_rth_now", return_value=True)
@patch("backend.v9.services.frozen_tail_watchdog._weekday_now", return_value=2)
@patch("backend.v9.services.frozen_tail_watchdog._pg_max_ts", return_value=None)
@patch("backend.v9.services.frozen_tail_watchdog._send_alert")
def test_rate_limiting(mock_alert, mock_pg, mock_wd, mock_rth, fake_export):
    """Second check within REALERT_INTERVAL should NOT re-alert."""
    tmp_path, fivemin, liveprice = fake_export
    stale_ts = time.time() - STALE_THRESHOLD - 300
    _write_5min(fivemin, stale_ts)
    _write_liveprice(liveprice)

    with patch("backend.v9.services.frozen_tail_watchdog.EXPORT_DIR", str(tmp_path)):
        check_once()  # first → alert
        fivemin.touch()  # refresh mtime for next check
        check_once()  # second → rate-limited, no alert

    assert mock_alert.call_count == 1
    assert _state.alert_count == 1


@patch("backend.v9.services.frozen_tail_watchdog._is_rth_now", return_value=True)
@patch("backend.v9.services.frozen_tail_watchdog._weekday_now", return_value=2)
@patch("backend.v9.services.frozen_tail_watchdog._pg_max_ts")
@patch("backend.v9.services.frozen_tail_watchdog._send_alert")
def test_pg_cross_check_stale(mock_alert, mock_pg, mock_wd, mock_rth, fake_export):
    """PG MAX(ts) stale also triggers frozen-tail (even if file bar tip looks OK)."""
    tmp_path, fivemin, liveprice = fake_export

    # File bars look fresh-ish (within threshold)
    _write_5min(fivemin, time.time() - 60)
    _write_liveprice(liveprice)

    # But PG is stale
    mock_pg.return_value = time.time() - STALE_THRESHOLD - 300

    with patch("backend.v9.services.frozen_tail_watchdog.EXPORT_DIR", str(tmp_path)):
        status = check_once()

    assert status == "frozen_tail"
    assert _state.alert_count == 1


def test_get_state_dict():
    """get_frozen_tail_state returns a dict with expected keys."""
    result = get_frozen_tail_state()
    assert isinstance(result, dict)
    assert "status" in result
    assert "bars_tip_ts" in result
    assert "alert_count" in result
    assert "live_price_age" in result
