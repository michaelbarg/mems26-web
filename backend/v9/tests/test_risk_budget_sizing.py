"""RISK_BUDGET_SIZING_V1: risk-based contract sizing (Michael 01.09).

"אפשר לעשות חוזים יחסי? כדי שהסטופ יהיה במיקום נכון."

n = floor(BUDGET / (risk_pts × $5))
n < MIN → REJECT (not n=MIN — quality gate, not floor)
contracts = min(n, ruled)
"""
import os
from unittest.mock import patch

import pytest
from backend.v9.services.sierra_command import _effective_contracts_raw


def _setup(risk_pts=None, entry=7750.0, stop=7740.0, sizing=None):
    s = {
        "entry_price": entry,
        "stop": stop,
        "metadata": {},
    }
    if risk_pts is not None:
        s["risk_pts"] = risk_pts
    if sizing is not None:
        s["metadata"]["sizing_contracts"] = sizing
    return s


class TestRiskBudget:
    """Core sizing: n = floor(BUDGET / (risk × $5)), min=3."""

    def test_small_risk_gets_5_contracts(self):
        """risk=4.0 → 150/(4×5)=7.5 → floor=7 → min(7,5)=5."""
        with patch.dict(os.environ, {
            "RISK_BUDGET_SIZING_V1": "1",
            "RISK_BUDGET_USD": "150",
            "RISK_MIN_CONTRACTS": "3",
            "FIXED_CONTRACTS_5": "1",
        }):
            n = _effective_contracts_raw(_setup(risk_pts=4.0))
        assert n == 5, f"risk=4.0 should give 5 (ruled cap), got {n}"

    def test_medium_risk_gets_4(self):
        """risk=7.0 → 150/(7×5)=4.28 → floor=4."""
        with patch.dict(os.environ, {
            "RISK_BUDGET_SIZING_V1": "1",
            "RISK_BUDGET_USD": "150",
            "RISK_MIN_CONTRACTS": "3",
            "FIXED_CONTRACTS_5": "1",
        }):
            n = _effective_contracts_raw(_setup(risk_pts=7.0))
        assert n == 4, f"risk=7.0 should give 4, got {n}"

    def test_max_risk_gets_3(self):
        """risk=10.0 → 150/(10×5)=3.0 → floor=3."""
        with patch.dict(os.environ, {
            "RISK_BUDGET_SIZING_V1": "1",
            "RISK_BUDGET_USD": "150",
            "RISK_MIN_CONTRACTS": "3",
            "FIXED_CONTRACTS_5": "1",
        }):
            n = _effective_contracts_raw(_setup(risk_pts=10.0))
        assert n == 3, f"risk=10.0 should give 3, got {n}"

    def test_too_wide_rejected(self):
        """risk=10.1 → 150/(10.1×5)=2.97 → floor=2 < min=3 → REJECT."""
        with patch.dict(os.environ, {
            "RISK_BUDGET_SIZING_V1": "1",
            "RISK_BUDGET_USD": "150",
            "RISK_MIN_CONTRACTS": "3",
            "FIXED_CONTRACTS_5": "1",
        }):
            n = _effective_contracts_raw(_setup(risk_pts=10.1))
        assert n == 0, f"risk=10.1 should be rejected (0), got {n}"

    def test_11pt_rejected(self):
        """risk=11.0 → rejected, not 1-contract."""
        with patch.dict(os.environ, {
            "RISK_BUDGET_SIZING_V1": "1",
            "RISK_BUDGET_USD": "150",
            "RISK_MIN_CONTRACTS": "3",
            "FIXED_CONTRACTS_5": "1",
        }):
            n = _effective_contracts_raw(_setup(risk_pts=11.0))
        assert n == 0, f"risk=11 should be rejected, got {n}"

    def test_floor_not_round(self):
        """raw=2.99 → floor=2 < min=3 → rejected. NOT rounded to 3."""
        with patch.dict(os.environ, {
            "RISK_BUDGET_SIZING_V1": "1",
            "RISK_BUDGET_USD": "150",
            "RISK_MIN_CONTRACTS": "3",
            "FIXED_CONTRACTS_5": "1",
        }):
            # risk that gives raw=2.99: 150/(x×5)=2.99 → x=10.033
            n = _effective_contracts_raw(_setup(risk_pts=10.04))
        assert n == 0, f"raw=2.98 should reject (floor, not round), got {n}"


class TestFlagOff:
    """Flag OFF → byte-identical to old behavior."""

    def test_flag_off_uses_ruled(self):
        with patch.dict(os.environ, {"FIXED_CONTRACTS_5": "1"}, clear=False):
            os.environ.pop("RISK_BUDGET_SIZING_V1", None)
            n = _effective_contracts_raw(_setup(risk_pts=25.0))
        assert n == 5, f"Flag OFF should use ruled=5, got {n}"


class TestNeverExceedsRuled:
    """contracts ≤ ruled_contracts() always."""

    def test_tiny_risk_capped_by_ruled(self):
        """risk=1.0 → 150/(1×5)=30 → min(30,5)=5."""
        with patch.dict(os.environ, {
            "RISK_BUDGET_SIZING_V1": "1",
            "RISK_BUDGET_USD": "150",
            "RISK_MIN_CONTRACTS": "3",
            "FIXED_CONTRACTS_5": "1",
        }):
            n = _effective_contracts_raw(_setup(risk_pts=1.0))
        assert n == 5, f"Should be capped at ruled=5, got {n}"


class TestMutation:
    """Removing the risk budget check must fail this test."""

    def test_mutation_wide_stop_not_rejected_without_fix(self):
        """If the fix is removed, risk=11 would give 5 (ruled) not 0."""
        with patch.dict(os.environ, {
            "RISK_BUDGET_SIZING_V1": "1",
            "RISK_BUDGET_USD": "150",
            "RISK_MIN_CONTRACTS": "3",
            "FIXED_CONTRACTS_5": "1",
        }):
            n = _effective_contracts_raw(_setup(risk_pts=11.0))
        # If mutation removed the budget check, n would be 5 (ruled)
        assert n != 5, "MUTATION: wide stop should be rejected, not given ruled count"
