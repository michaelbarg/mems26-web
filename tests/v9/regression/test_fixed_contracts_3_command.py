"""GAP-1 regression: FIXED_CONTRACTS_3 must reach the ACTUAL Sierra command qty.

The flag was dead-wired (2026-07-01): it only patched compute_v2_sizing (S4 path),
while the S2 emit used get_quality_tier_v2 (tier-based 2/3) and the Sierra command read
setup["contracts"]. Live evidence: MEDIUM/LOW fires emitted contracts=2 (18:20 BULL_FLAG,
19:55 REACTIVE). These tests lock the fix at command_from_setup — the single choke point
all fire paths converge on before Sierra (both S2 and S4, demo + live).
"""
import pytest

from backend.v9.services import sierra_command as sc


def _capture(monkeypatch):
    captured = {}

    def _fake_write(payload):
        captured.clear()
        captured.update(payload)
        return payload

    monkeypatch.setattr(sc, "_write_command", _fake_write)
    return captured


def _setup(contracts):
    return {
        "direction": "LONG",
        "entry_price": 7500.0,
        "stop": 7495.0,
        "t1": 7505.0,
        "contracts": contracts,
    }


def test_flag_on_forces_3_from_tier_2(monkeypatch):
    """The bug: a MEDIUM/LOW tier setup carries contracts=2 → must become 3."""
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    cap = _capture(monkeypatch)
    sc.command_from_setup(_setup(2), trade_id="T-A", account="SIM", mode="demo")
    assert cap["contracts"] == 3


def test_flag_on_keeps_3(monkeypatch):
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    cap = _capture(monkeypatch)
    sc.command_from_setup(_setup(3), trade_id="T-B", account="SIM", mode="demo")
    assert cap["contracts"] == 3


def test_flag_off_preserves_tier(monkeypatch):
    """Anti-tautological: with the flag OFF the tier count (2) must survive unchanged."""
    monkeypatch.delenv("FIXED_CONTRACTS_3", raising=False)
    cap = _capture(monkeypatch)
    sc.command_from_setup(_setup(2), trade_id="T-C", account="SIM", mode="demo")
    assert cap["contracts"] == 2
