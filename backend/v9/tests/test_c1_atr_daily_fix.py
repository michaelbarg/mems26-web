"""C1 — ATR ×13 bug fix (2026-08-11).

Bug: _last_atr_daily was the mean of 5-min bar ranges (~5-7pt for MES),
not the real daily ATR (~80-100pt). This made IB/ATR ratio ~always EXTREME.

Example from 2026-08-10:
  IB = 20.25pt, _last_atr_daily (buggy) = 5.2pt → ratio = 3.89 → EXTREME
  IB = 20.25pt, real daily ATR = 84pt → ratio = 0.24 → NARROW

Fix: compute_daily_atr() queries 14-session true ranges from DB.
Flag: ATR_DAILY_FIX_V1 (default OFF).
"""
import pytest

from backend.v9.systems.day_type.detector import (
    classify_ib_width_atr,
    compute_daily_atr,
    _DEFAULT_ATR_MES,
)
from backend.v9.systems.day_type.schemas import IBWidth


# ── classify_ib_width_atr with correct ATR ─────────────────────────────────

class TestClassifyIBWidthATR:
    """Verify classifications with the correct daily ATR scale."""

    def test_narrow_with_real_atr(self):
        """IB 20.25 / ATR 84 = 0.24 → NARROW."""
        result = classify_ib_width_atr(20.25, atr_daily=84.0)
        assert result == IBWidth.NARROW

    def test_medium_with_real_atr(self):
        """IB 50 / ATR 84 = 0.60 → MEDIUM."""
        result = classify_ib_width_atr(50.0, atr_daily=84.0)
        assert result == IBWidth.MEDIUM

    def test_wide_with_real_atr(self):
        """IB 100 / ATR 84 = 1.19 → WIDE."""
        result = classify_ib_width_atr(100.0, atr_daily=84.0)
        assert result == IBWidth.WIDE

    def test_extreme_with_real_atr(self):
        """IB 150 / ATR 84 = 1.79 → EXTREME."""
        result = classify_ib_width_atr(150.0, atr_daily=84.0)
        assert result == IBWidth.EXTREME

    def test_buggy_atr_gives_wrong_result(self):
        """BUG DEMO: IB 20.25 / ATR 5.2 (5-min avg) = 3.89 → EXTREME (wrong!)."""
        result = classify_ib_width_atr(20.25, atr_daily=5.2)
        assert result == IBWidth.EXTREME  # This is the bug!

    def test_none_atr_uses_default(self):
        """When atr_daily=None, uses _DEFAULT_ATR_MES (20) as fallback."""
        result = classify_ib_width_atr(9.0, atr_daily=None)
        # 9/20 = 0.45 → NARROW
        assert result == IBWidth.NARROW

    def test_zero_atr_uses_default(self):
        """When atr_daily=0, uses _DEFAULT_ATR_MES (20)."""
        result = classify_ib_width_atr(9.0, atr_daily=0.0)
        # 9/20 = 0.45 → NARROW
        assert result == IBWidth.NARROW

    def test_case_20260810_with_fix(self):
        """2026-08-10 exact numbers with real ATR → NARROW (not EXTREME)."""
        # IB was 20.25pt, real daily ATR ~84pt
        result = classify_ib_width_atr(20.25, atr_daily=84.25)
        assert result == IBWidth.NARROW


# ── compute_daily_atr ──────────────────────────────────────────────────────

class TestComputeDailyATR:
    """Test the daily ATR computation function."""

    def test_function_exists(self):
        """compute_daily_atr must be importable."""
        assert callable(compute_daily_atr)

    def test_returns_none_on_error(self):
        """Should return None when DB is unavailable (not raise)."""
        from unittest.mock import patch
        with patch("backend.v9.db.read.read_all", side_effect=Exception("no db")):
            result = compute_daily_atr(14)
            assert result is None

    def test_returns_none_on_empty(self):
        """Should return None when no rows returned."""
        from unittest.mock import patch
        with patch("backend.v9.db.read.read_all", return_value=[]):
            result = compute_daily_atr(14)
            assert result is None

    def test_returns_none_on_too_few_sessions(self):
        """Should return None with < 3 sessions."""
        from unittest.mock import patch
        rows = [{"day_high": 7800, "day_low": 7700, "session_date": "2026-08-10"}]
        with patch("backend.v9.db.read.read_all", return_value=rows):
            result = compute_daily_atr(14)
            assert result is None

    def test_computes_average_range(self):
        """Should compute mean(high-low) across sessions."""
        from unittest.mock import patch
        rows = [
            {"day_high": 7800, "day_low": 7720, "session_date": "2026-08-10"},  # 80
            {"day_high": 7850, "day_low": 7760, "session_date": "2026-08-09"},  # 90
            {"day_high": 7700, "day_low": 7630, "session_date": "2026-08-08"},  # 70
        ]
        with patch("backend.v9.db.read.read_all", return_value=rows):
            result = compute_daily_atr(14)
            assert result == pytest.approx(80.0)  # (80+90+70)/3

    def test_realistic_mes_atr(self):
        """Realistic MES daily ranges should give ATR in 60-120pt range."""
        from unittest.mock import patch
        rows = [
            {"day_high": 7800, "day_low": 7710, "session_date": f"2026-08-{10-i:02d}"}
            for i in range(14)
        ]  # all 90pt range
        with patch("backend.v9.db.read.read_all", return_value=rows):
            result = compute_daily_atr(14)
            assert result == 90.0


# ── State machine integration ─────────────────────────────────────────────

class TestStateMachineATRFix:
    """Verify the flag gates the fix correctly."""

    def test_flag_off_uses_old_behavior(self, monkeypatch):
        """ATR_DAILY_FIX_V1=0 → _last_atr_daily = mean of 5-min bar ranges."""
        monkeypatch.setenv("ATR_DAILY_FIX_V1", "0")
        from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
        from backend.v9.systems.day_type.schemas import BarInput
        m = DayTypeStateMachine()
        # Feed 5 bars with range ~5pt each
        for i in range(5):
            m.process_bar(BarInput(ts=1000+i*300, session_min=i*5,
                                   open=7780, high=7785, low=7780, close=7783))
        # _last_atr_daily should be ~5 (the 5-min bar range average)
        assert m._last_atr_daily is not None
        assert m._last_atr_daily < 10  # 5-min scale, not daily scale

    def test_flag_on_seeds_daily_atr(self, monkeypatch):
        """ATR_DAILY_FIX_V1=1 → _last_atr_daily seeded from compute_daily_atr."""
        monkeypatch.setenv("ATR_DAILY_FIX_V1", "1")
        from unittest.mock import patch
        from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
        from backend.v9.systems.day_type.schemas import BarInput

        m = DayTypeStateMachine()
        with patch("backend.v9.systems.day_type.detector.compute_daily_atr", return_value=85.0):
            m.process_bar(BarInput(ts=1000, session_min=5,
                                   open=7780, high=7785, low=7780, close=7783))
        assert m._last_atr_daily == 85.0
        assert m._atr_daily_seeded is True

    def test_flag_on_none_atr_falls_back(self, monkeypatch):
        """ATR_DAILY_FIX_V1=1 but compute returns None → falls back to 5-min avg."""
        monkeypatch.setenv("ATR_DAILY_FIX_V1", "1")
        from unittest.mock import patch
        from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
        from backend.v9.systems.day_type.schemas import BarInput

        m = DayTypeStateMachine()
        with patch("backend.v9.systems.day_type.detector.compute_daily_atr", return_value=None):
            for i in range(5):
                m.process_bar(BarInput(ts=1000+i*300, session_min=i*5,
                                       open=7780, high=7785, low=7780, close=7783))
        # Should fall back to 5-min avg
        assert m._last_atr_daily is not None
        assert m._last_atr_daily < 10
        assert m._atr_daily_seeded is False
