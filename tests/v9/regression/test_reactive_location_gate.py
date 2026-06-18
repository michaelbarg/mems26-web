"""Reactive Location Gate — anti-tautological tests with RED-on-revert.

REACTIVE_LONG entry>POC → block (buying at ceiling).
REACTIVE_SHORT entry<POC → block (selling at floor).
Non-REACTIVE / poc=None → allow (fail-open).
"""

import os
import pytest


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setenv("REACTIVE_LOCATION_GATE", "1")


class TestReactiveLocationGate:

    def _decide(self, pattern, direction, entry, poc):
        from backend.v9.systems.reactive_location_gate import decide
        return decide(pattern, direction, entry, poc)

    # ── BLOCKED ──

    def test_long_above_poc_blocked(self):
        """REACTIVE_LONG at 7430 when POC=7415 → block (upper half)."""
        allow, reason = self._decide("REACTIVE_LONG", "LONG", 7430.0, 7415.0)
        assert not allow, f"Must block LONG above POC, got allow=True reason={reason}"
        assert "wrong side" in reason

    def test_short_below_poc_blocked(self):
        """REACTIVE_SHORT at 7400 when POC=7415 → block (lower half)."""
        allow, reason = self._decide("REACTIVE_SHORT", "SHORT", 7400.0, 7415.0)
        assert not allow, f"Must block SHORT below POC, got allow=True reason={reason}"

    # ── ALLOWED (correct side) ──

    def test_long_below_poc_allowed(self):
        """REACTIVE_LONG at 7400 when POC=7415 → allow (lower half, correct)."""
        allow, _ = self._decide("REACTIVE_LONG", "LONG", 7400.0, 7415.0)
        assert allow

    def test_short_above_poc_allowed(self):
        """REACTIVE_SHORT at 7430 when POC=7415 → allow (upper half, correct)."""
        allow, _ = self._decide("REACTIVE_SHORT", "SHORT", 7430.0, 7415.0)
        assert allow

    def test_long_at_poc_allowed(self):
        """Entry == POC → allow (not strictly above)."""
        allow, _ = self._decide("REACTIVE_LONG", "LONG", 7415.0, 7415.0)
        assert allow

    # ── FAIL-OPEN ──

    def test_non_reactive_allowed(self):
        allow, _ = self._decide("TLB", "LONG", 7430.0, 7415.0)
        assert allow

    def test_hfe_not_targeted(self):
        allow, _ = self._decide("HFE", "SHORT", 7400.0, 7415.0)
        assert allow

    def test_poc_none_fail_open(self):
        allow, reason = self._decide("REACTIVE_LONG", "LONG", 7430.0, None)
        assert allow
        assert "fail-open" in reason

    def test_flag_off(self, monkeypatch):
        monkeypatch.setenv("REACTIVE_LOCATION_GATE", "0")
        allow, reason = self._decide("REACTIVE_LONG", "LONG", 7430.0, 7415.0)
        assert allow
        assert "gate OFF" in reason
