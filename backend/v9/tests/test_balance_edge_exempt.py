"""Tests for balance-edge direction_context exemption."""

import pytest
from backend.v9.systems.balance_edge_exempt import should_exempt


class TestBalanceEdgeExempt:
    def test_flag_off_never_exempts(self, monkeypatch):
        monkeypatch.delenv("BALANCE_EDGE_EXEMPT_V1", raising=False)
        ok, _ = should_exempt(direction="SHORT", entry_price=7758.0,
                               regime="BALANCE", session_high=7760.0)
        assert not ok

    def test_short_at_session_high_exempts(self, monkeypatch):
        monkeypatch.setenv("BALANCE_EDGE_EXEMPT_V1", "1")
        ok, reason = should_exempt(direction="SHORT", entry_price=7758.0,
                                    regime="BALANCE", session_high=7760.0)
        assert ok
        assert "session high" in reason

    def test_long_at_session_low_exempts(self, monkeypatch):
        monkeypatch.setenv("BALANCE_EDGE_EXEMPT_V1", "1")
        ok, reason = should_exempt(direction="LONG", entry_price=7502.0,
                                    regime="BALANCE", session_low=7500.0)
        assert ok
        assert "session low" in reason

    def test_imbalance_regime_no_exempt(self, monkeypatch):
        monkeypatch.setenv("BALANCE_EDGE_EXEMPT_V1", "1")
        ok, _ = should_exempt(direction="SHORT", entry_price=7758.0,
                               regime="IMBALANCE", session_high=7760.0)
        assert not ok

    def test_far_from_edge_no_exempt(self, monkeypatch):
        monkeypatch.setenv("BALANCE_EDGE_EXEMPT_V1", "1")
        ok, _ = should_exempt(direction="SHORT", entry_price=7730.0,
                               regime="BALANCE", session_high=7760.0)
        assert not ok

    def test_excess_adds_confirmation(self, monkeypatch):
        monkeypatch.setenv("BALANCE_EDGE_EXEMPT_V1", "1")
        ok, reason = should_exempt(
            direction="SHORT", entry_price=7758.0,
            regime="BALANCE", session_high=7760.0,
            extremes={"high_quality": "EXCESS"},
        )
        assert ok
        assert "confirmed" in reason

    def test_balance7_vah_edge(self, monkeypatch):
        monkeypatch.setenv("BALANCE_EDGE_EXEMPT_V1", "1")
        ok, reason = should_exempt(
            direction="SHORT", entry_price=7478.0,
            regime="BALANCE",
            balance7={"range": [7400, 7500], "value": [7420, 7480]},
        )
        assert ok
        assert "VAH" in reason
