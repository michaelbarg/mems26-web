"""T-41 CVD feed: timestamp normalization + window resilience.

Michael 28.08: "the volume+candles confluence cannot exist" because a single
missing CVD bar in the 20-bar window returns None for the entire reading.
28 rows vs 38 bars → 27% gap rate.

Root causes:
  (a) DLL writes timestamps at :59 (end-of-bar tick) instead of :00 (bar start),
      misaligning with the 5-min bar grid → holes in the WHERE range query.
  (b) len(cums) < window → return None is all-or-nothing; a single missing bar
      kills the entire CVD reading.

Fixes:
  (a) Normalize CVD timestamps to the 5-minute grid (:00/:05/:10/...).
  (b) Allow partial coverage (90% threshold) with coverage tag.
"""
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest


class TestTimestampNormalization:
    """CVD timestamps must snap to the 5-minute bar grid."""

    def test_second_59_snaps_to_next_5min(self):
        """16:04:59 → 16:05:00 (the 5-min bar it belongs to)."""
        from backend.v9.services.history_loader import _normalize_cvd_ts
        result = _normalize_cvd_ts("2026-08-28 16:04:59.000000")
        assert "16:05:00" in result, f"Expected 16:05:00, got {result}"

    def test_second_00_stays(self):
        """16:05:00 → 16:05:00 (already on grid)."""
        from backend.v9.services.history_loader import _normalize_cvd_ts
        result = _normalize_cvd_ts("2026-08-28 16:05:00.000000")
        assert "16:05:00" in result, f"Expected 16:05:00, got {result}"

    def test_second_01_snaps_forward(self):
        """16:03:01 → 16:05:00 (next 5-min boundary)."""
        from backend.v9.services.history_loader import _normalize_cvd_ts
        result = _normalize_cvd_ts("2026-08-28 16:03:01.000000")
        assert "16:05:00" in result, f"Expected 16:05:00, got {result}"

    def test_second_59_at_exact_boundary(self):
        """16:09:59 → 16:10:00."""
        from backend.v9.services.history_loader import _normalize_cvd_ts
        result = _normalize_cvd_ts("2026-08-28 16:09:59.000000")
        assert "16:10:00" in result, f"Expected 16:10:00, got {result}"

    def test_second_30_midbar(self):
        """16:07:30 → 16:10:00 (round up to next 5-min)."""
        from backend.v9.services.history_loader import _normalize_cvd_ts
        result = _normalize_cvd_ts("2026-08-28 16:07:30.000000")
        assert "16:10:00" in result, f"Expected 16:10:00, got {result}"


class TestWindowResilience:
    """CVD window should tolerate partial coverage instead of returning None."""

    def test_full_coverage_returns_data(self):
        """20/20 rows → returns CVD data with coverage=1.0."""
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        # We'll test _cvd_window by mocking the DB read
        cums = list(range(20))  # 20 cumulative values
        rows = [{"cumulative": float(c)} for c in cums]
        bars = [{"ts": f"2026-08-28T16:{i*5:02d}:00"} for i in range(20)]

        with patch("backend.v9.db.read.read_all", return_value=rows):
            sys = FiveMinSystem.__new__(FiveMinSystem)
            result = sys._compute_setup_cvd(bars, window=20)

        assert result is not None, "Full coverage should return data"
        assert result["coverage"] == 1.0, f"Coverage should be 1.0, got {result['coverage']}"

    def test_19_of_20_returns_data_with_tag(self):
        """19/20 rows (95%) → returns CVD data with coverage=0.95."""
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        cums = list(range(19))  # 19 values out of 20 needed
        rows = [{"cumulative": float(c)} for c in cums]
        bars = [{"ts": f"2026-08-28T16:{i*5:02d}:00"} for i in range(20)]

        with patch("backend.v9.db.read.read_all", return_value=rows):
            sys = FiveMinSystem.__new__(FiveMinSystem)
            result = sys._compute_setup_cvd(bars, window=20)

        assert result is not None, "19/20 (95%) should return data, not None"
        assert result["coverage"] == 0.95, f"Coverage should be 0.95, got {result['coverage']}"

    def test_17_of_20_returns_none(self):
        """17/20 rows (85%) → below 90% threshold → returns None."""
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        cums = list(range(17))
        rows = [{"cumulative": float(c)} for c in cums]
        bars = [{"ts": f"2026-08-28T16:{i*5:02d}:00"} for i in range(20)]

        with patch("backend.v9.db.read.read_all", return_value=rows):
            sys = FiveMinSystem.__new__(FiveMinSystem)
            result = sys._compute_setup_cvd(bars, window=20)

        assert result is None, "17/20 (85%) should return None (below 90% threshold)"

    def test_28_08_scenario_with_fix(self):
        """28.08 had 28 rows for 38 bars (73.7%) → still None (below threshold).
        But after timestamp fix, most holes should be filled → acceptance test
        is 0 holes in last 20 bars."""
        # This test documents that 28/38 = 73.7% is still below threshold
        coverage = 28 / 38
        assert coverage < 0.9, "28/38 is below 90% — the fix needs timestamp normalization"
