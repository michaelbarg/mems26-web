"""Trend Direction Gate — anti-tautological tests with RED-on-revert.

Verifies: HFE/REACTIVE_LONG/ZLR-SHORT blocked counter-trend;
ZLR-LONG@RED passes (target-side preserved); fail-open on GRAY/None.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def _enable_gate(monkeypatch):
    monkeypatch.setenv("TREND_DIRECTION_GATE", "1")


class TestTrendGateDecide:
    """Unit tests for decide() — the actual code path."""

    def _decide(self, pattern, direction, trend_state):
        # Force config reload each time
        import backend.v9.systems.trend_direction_gate as mod
        mod._cfg_cache = None
        return mod.decide(pattern, direction, trend_state)

    # ── BLOCKED (counter-trend targeted patterns) ──

    def test_hfe_long_red_blocked(self):
        allow, reason = self._decide("HFE", "LONG", "RED")
        assert not allow, f"HFE LONG@RED must be blocked, got allow=True reason={reason}"
        assert "counter-trend" in reason

    def test_hfe_short_blue_blocked(self):
        allow, reason = self._decide("HFE", "SHORT", "BLUE")
        assert not allow

    def test_reactive_long_red_blocked(self):
        allow, reason = self._decide("REACTIVE_LONG", "LONG", "RED")
        assert not allow

    def test_zlr_short_blue_blocked(self):
        allow, reason = self._decide("ZLR", "SHORT", "BLUE")
        assert not allow

    # ── ALLOWED (with-trend or not-targeted) ──

    def test_zlr_long_red_allowed(self):
        """CRITICAL: ZLR-LONG is profitable, must NOT be blocked even counter-trend."""
        allow, reason = self._decide("ZLR", "LONG", "RED")
        assert allow, f"ZLR LONG@RED must pass (not targeted), got blocked: {reason}"

    def test_hfe_long_blue_with_trend(self):
        allow, _ = self._decide("HFE", "LONG", "BLUE")
        assert allow, "HFE LONG@BLUE is with-trend, must pass"

    def test_reactive_short_blue_not_targeted(self):
        allow, _ = self._decide("REACTIVE_SHORT", "SHORT", "BLUE")
        assert allow, "REACTIVE_SHORT not in config, must pass"

    def test_tlb_any_not_targeted(self):
        allow, _ = self._decide("TLB", "LONG", "RED")
        assert allow, "TLB not in config, must pass"

    # ── FAIL-OPEN ──

    def test_gray_fail_open(self):
        allow, _ = self._decide("HFE", "LONG", "GRAY")
        assert allow

    def test_yellow_fail_open(self):
        allow, _ = self._decide("HFE", "LONG", "YELLOW")
        assert allow

    def test_none_fail_open(self):
        allow, _ = self._decide("HFE", "LONG", None)
        assert allow

    # ── FLAG OFF ──

    def test_flag_off_allows_all(self, monkeypatch):
        monkeypatch.setenv("TREND_DIRECTION_GATE", "0")
        allow, reason = self._decide("HFE", "LONG", "RED")
        assert allow
        assert "gate OFF" in reason
