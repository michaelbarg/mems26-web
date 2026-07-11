"""CERT direction override — real 21:00 fixtures (07-09 incident).

Incident: 21:00-21:15, 5 ZLR LONG blocks because dir_sustained=DOWN even
though trend_state=BLUE×3 and lsma_slope=+0.36. CERT should lift DOWN→UP.

If reverted → RED because:
  - test_blue_cert_lifts_down_to_up: without CERT, dir_sustained stays DOWN
    even when all bars are BLUE with positive slope.
  - test_red_cert_drops_neutral_to_down: symmetric — without CERT, stays NEUTRAL.
"""
import os
from unittest.mock import patch, MagicMock


def _mock_srows_blue(k=3):
    """K bars: close < lsma (sustained=DOWN in sustained_lsma_side) but trend_state=BLUE."""
    return [
        {"close": 7612.0, "lsma_value": 7615.0, "trend_state": "BLUE"},
        {"close": 7611.0, "lsma_value": 7614.5, "trend_state": "BLUE"},
        {"close": 7610.5, "lsma_value": 7614.0, "trend_state": "BLUE"},
    ][:k]


def _mock_srows_red(k=3):
    """K bars: close > lsma (sustained=UP) but trend_state=RED."""
    return [
        {"close": 7618.0, "lsma_value": 7615.0, "trend_state": "RED"},
        {"close": 7619.0, "lsma_value": 7615.5, "trend_state": "RED"},
        {"close": 7619.5, "lsma_value": 7616.0, "trend_state": "RED"},
    ][:k]


def _mock_bars():
    """Minimal RTH bars for compute_direction."""
    return [{"open": 7610, "high": 7615, "low": 7608, "close": 7612,
             "volume": 1000, "ts": "2026-07-09T21:00:00"}]


def test_blue_cert_lifts_down_to_up(monkeypatch):
    """21:00 incident fixture: BLUE×3 + slope +0.36 → cert lifts DOWN→UP."""
    monkeypatch.setenv("CONT_TREND_STATE_CERT_V1", "1")
    monkeypatch.setenv("DIRECTION_LSMA_VETO", "1")
    monkeypatch.setenv("LSMA_SUSTAIN_BARS", "3")
    monkeypatch.setenv("LSMA_FLAT_LOOKBACK_BARS", "4")

    from backend.v9.systems import direction_context_live as dcl

    # Clear cache
    dcl._CACHE.clear()

    srows = _mock_srows_blue()
    slope_rows = [
        {"lsma_value": 7614.0},
        {"lsma_value": 7613.5},
        {"lsma_value": 7613.0},
        {"lsma_value": 7612.5},
    ]

    def mock_read_one(sql, params=None):
        if "v9_tpo_sessions" in sql:
            return {"ib_high": 7620, "ib_low": 7600, "poc_price": 7610}
        if "v9_day_type_state" in sql:
            return {"day_type": "Normal_Variation", "ts": "2026-07-09T21:00:00"}
        if "v9_bars_5min_woodies" in sql and "ORDER BY ts DESC LIMIT 1" in sql:
            return {"close": 7612.0, "lsma_value": 7615.0, "trend_state": "BLUE"}
        return None

    def mock_read_all(sql, params=None):
        if "trend_state" in sql and "LIMIT 3" in sql:
            return srows
        if "lsma_value" in sql and "LIMIT 4" in sql:
            return slope_rows
        return []

    def mock_fetch_bars(today):
        return _mock_bars(), "mock"

    with patch("backend.v9.db.read.read_one", side_effect=mock_read_one), \
         patch("backend.v9.db.read.read_all", side_effect=mock_read_all), \
         patch.object(dcl, "_fetch_live_bars", side_effect=mock_fetch_bars):
        result = dcl.current()

    assert result["dir_sustained"] == "UP", (
        f"CERT should lift DOWN→UP with BLUE×3 + positive slope, got {result['dir_sustained']}"
    )


def test_red_cert_drops_to_down(monkeypatch):
    """Symmetric RED fixture: RED×3 + slope -0.36 → cert drops NEUTRAL/UP→DOWN."""
    monkeypatch.setenv("CONT_TREND_STATE_CERT_V1", "1")
    monkeypatch.setenv("DIRECTION_LSMA_VETO", "1")
    monkeypatch.setenv("LSMA_SUSTAIN_BARS", "3")
    monkeypatch.setenv("LSMA_FLAT_LOOKBACK_BARS", "4")

    from backend.v9.systems import direction_context_live as dcl

    dcl._CACHE.clear()

    srows = _mock_srows_red()
    slope_rows = [
        {"lsma_value": 7616.0},
        {"lsma_value": 7616.5},
        {"lsma_value": 7617.0},
        {"lsma_value": 7617.5},
    ]

    def mock_read_one(sql, params=None):
        if "v9_tpo_sessions" in sql:
            return {"ib_high": 7620, "ib_low": 7600, "poc_price": 7610}
        if "v9_day_type_state" in sql:
            return {"day_type": "Normal_Variation", "ts": "2026-07-09T21:00:00"}
        if "v9_bars_5min_woodies" in sql and "ORDER BY ts DESC LIMIT 1" in sql:
            return {"close": 7618.0, "lsma_value": 7615.0, "trend_state": "RED"}
        return None

    def mock_read_all(sql, params=None):
        if "trend_state" in sql and "LIMIT 3" in sql:
            return srows
        if "lsma_value" in sql and "LIMIT 4" in sql:
            return slope_rows
        return []

    def mock_fetch_bars(today):
        return _mock_bars(), "mock"

    with patch("backend.v9.db.read.read_one", side_effect=mock_read_one), \
         patch("backend.v9.db.read.read_all", side_effect=mock_read_all), \
         patch.object(dcl, "_fetch_live_bars", side_effect=mock_fetch_bars):
        result = dcl.current()

    assert result["dir_sustained"] == "DOWN", (
        f"CERT should drop UP→DOWN with RED×3 + negative slope, got {result['dir_sustained']}"
    )


def test_cert_off_stays_down(monkeypatch):
    """Without CERT flag, dir_sustained stays DOWN even with BLUE bars."""
    monkeypatch.delenv("CONT_TREND_STATE_CERT_V1", raising=False)
    monkeypatch.setenv("DIRECTION_LSMA_VETO", "1")
    monkeypatch.setenv("LSMA_SUSTAIN_BARS", "3")
    monkeypatch.setenv("LSMA_FLAT_LOOKBACK_BARS", "4")

    from backend.v9.systems import direction_context_live as dcl

    dcl._CACHE.clear()

    srows = _mock_srows_blue()
    slope_rows = [
        {"lsma_value": 7614.0},
        {"lsma_value": 7613.5},
        {"lsma_value": 7613.0},
        {"lsma_value": 7612.5},
    ]

    def mock_read_one(sql, params=None):
        if "v9_tpo_sessions" in sql:
            return {"ib_high": 7620, "ib_low": 7600, "poc_price": 7610}
        if "v9_day_type_state" in sql:
            return {"day_type": "Normal_Variation", "ts": "2026-07-09T21:00:00"}
        if "v9_bars_5min_woodies" in sql and "ORDER BY ts DESC LIMIT 1" in sql:
            return {"close": 7612.0, "lsma_value": 7615.0, "trend_state": "BLUE"}
        return None

    def mock_read_all(sql, params=None):
        if "trend_state" in sql and "LIMIT 3" in sql:
            return srows
        if "lsma_value" in sql and "LIMIT 4" in sql:
            return slope_rows
        return []

    def mock_fetch_bars(today):
        return _mock_bars(), "mock"

    with patch("backend.v9.db.read.read_one", side_effect=mock_read_one), \
         patch("backend.v9.db.read.read_all", side_effect=mock_read_all), \
         patch.object(dcl, "_fetch_live_bars", side_effect=mock_fetch_bars):
        result = dcl.current()

    assert result["dir_sustained"] == "DOWN", (
        f"Without CERT flag, dir_sustained should stay DOWN, got {result['dir_sustained']}"
    )
