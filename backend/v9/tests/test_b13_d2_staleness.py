"""B-13 D2 regression: staleness guard rejects old/off-market bars.

if reverted → RED because _is_stale_bar returns None for stale bars,
allowing them through to DB write + _route_bar dispatch to S2.
"""

import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# bars module imports auth which requires BRIDGE_TOKEN at import time
if not os.getenv("BRIDGE_TOKEN"):
    os.environ["BRIDGE_TOKEN"] = "test-token-for-isolation"

from backend.v9.api.v9 import bars


class TestStalenessGuard:
    """B-13 D2: _is_stale_bar rejects old and off-market bars."""

    def test_stale_ts_rejected(self):
        """Bar from 30 days ago is rejected (staleness check)."""
        old_ts = datetime.now(timezone.utc) - timedelta(days=30)
        result = bars._is_stale_bar(old_ts, 7500.0)
        assert result is not None, "Stale bar (30d old) must be rejected"
        assert "stale_ts" in result

    def test_recent_ts_accepted(self):
        """Bar from 5 minutes ago is accepted."""
        recent_ts = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = bars._is_stale_bar(recent_ts, 7500.0)
        assert result is None, "Recent bar should pass staleness check"

    def test_off_market_price_rejected(self):
        """Bar with price 220pts below latest known is rejected."""
        bars._latest_known_price = 7580.0
        try:
            recent_ts = datetime.now(timezone.utc) - timedelta(minutes=1)
            result = bars._is_stale_bar(recent_ts, 7341.0)  # 239pts deviation
            assert result is not None, "Off-market bar must be rejected"
            assert "off_market" in result
        finally:
            bars._latest_known_price = None

    def test_within_band_accepted(self):
        """Bar with price 10pts from latest is accepted."""
        bars._latest_known_price = 7580.0
        try:
            recent_ts = datetime.now(timezone.utc) - timedelta(minutes=1)
            result = bars._is_stale_bar(recent_ts, 7570.0)  # 10pts deviation
            assert result is None, "Within-band bar should pass"
        finally:
            bars._latest_known_price = None

    def test_may6_phantom_bar_rejected(self):
        """Exact B-13 regression: May 6 bar (7341.00) with ts from 2026-05-06."""
        may6_ts = datetime(2026, 5, 6, 13, 30, tzinfo=timezone.utc)  # ~30 days old
        result = bars._is_stale_bar(may6_ts, 7341.0)
        assert result is not None, "May-6 phantom bar MUST be rejected"
        assert "stale_ts" in result

    def test_no_latest_price_skips_band_check(self):
        """When no latest price is known, only staleness check runs."""
        bars._latest_known_price = None
        recent_ts = datetime.now(timezone.utc) - timedelta(minutes=1)
        result = bars._is_stale_bar(recent_ts, 7341.0)
        assert result is None, "No latest price → skip band check, pass on ts alone"
