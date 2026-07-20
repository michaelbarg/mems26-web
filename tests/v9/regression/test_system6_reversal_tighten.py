"""T16 — SYSTEM6_REVERSAL_TIGHTEN_V1: on CVD reversal after T1, tighten stop + target.

Michael ruling 2026-07-20: default OFF. Conservative: CVD-flip + >=2 adverse
closes after T1. NOT op=EXIT. Anti-tautological:
  1. reversal → MODIFY_STOP (tighten to BE) + MODIFY_TARGET (50% closer)
  2. no reversal → byte-identical (no new issues)
  3. flag OFF → byte-identical regardless of cvd_reversal
  4. reversal pre-T1 → no action (T1 required)
"""
import os
import pytest
from unittest.mock import patch

from backend.v9.systems.system6_supervisor import diagnose_trade


def _base_trade(direction="LONG"):
    return {
        "direction": direction,
        "entry_price": 7500.0,
        "stop": 7490.0,
        "t1": 7510.0,
        "t2": 7520.0,
        "t3": 7530.0,
        "contracts": 3,
    }


# ── Test 1: reversal after T1 → tighten stop + target ────────────────────────

def test_reversal_after_t1_tightens(monkeypatch):
    """CVD reversal + T1 hit + flag ON → MODIFY_STOP to BE + MODIFY_TARGET closer."""
    monkeypatch.setenv("SYSTEM6_REVERSAL_TIGHTEN_V1", "1")
    report = diagnose_trade(
        trade=_base_trade("LONG"), atr=10.0, t1_hit=True,
        cvd_reversal=True,
    )
    codes = [i.code for i in report.issues]
    assert "reversal_tighten_stop" in codes
    assert "reversal_tighten_target" in codes

    stop_iss = next(i for i in report.issues if i.code == "reversal_tighten_stop")
    assert stop_iss.correction["op"] == "MODIFY_STOP"
    assert stop_iss.correction["price"] == 7500.0  # BE = entry

    tgt_iss = next(i for i in report.issues if i.code == "reversal_tighten_target")
    assert tgt_iss.correction["op"] == "MODIFY_TARGET"
    # t2=7520, entry=7500, 50% of 20 = 10 → new target = 7510
    assert tgt_iss.correction["price"] == 7510.0


def test_reversal_short_trade(monkeypatch):
    """SHORT trade + reversal → stop tightens to entry, target closer (below)."""
    monkeypatch.setenv("SYSTEM6_REVERSAL_TIGHTEN_V1", "1")
    trade = _base_trade("SHORT")
    trade.update({"stop": 7510.0, "t1": 7490.0, "t2": 7480.0, "t3": 7470.0})
    report = diagnose_trade(
        trade=trade, atr=10.0, t1_hit=True,
        cvd_reversal=True,
    )
    stop_iss = next(i for i in report.issues if i.code == "reversal_tighten_stop")
    assert stop_iss.correction["price"] == 7500.0  # BE

    tgt_iss = next(i for i in report.issues if i.code == "reversal_tighten_target")
    # t2=7480, entry=7500, dist=20, 50%=10 → new = 7500 - 10 = 7490
    assert tgt_iss.correction["price"] == 7490.0


# ── Test 2: no reversal → byte-identical ──────────────────────────────────────

def test_no_reversal_no_issues(monkeypatch):
    """No CVD reversal → no reversal_tighten issues (even with flag ON)."""
    monkeypatch.setenv("SYSTEM6_REVERSAL_TIGHTEN_V1", "1")
    report = diagnose_trade(
        trade=_base_trade(), atr=10.0, t1_hit=True,
        cvd_reversal=False,
    )
    codes = [i.code for i in report.issues]
    assert "reversal_tighten_stop" not in codes
    assert "reversal_tighten_target" not in codes


# ── Test 3: flag OFF → byte-identical regardless ─────────────────────────────

def test_flag_off_no_tighten(monkeypatch):
    """Flag OFF + reversal → no reversal_tighten issues."""
    monkeypatch.delenv("SYSTEM6_REVERSAL_TIGHTEN_V1", raising=False)
    report = diagnose_trade(
        trade=_base_trade(), atr=10.0, t1_hit=True,
        cvd_reversal=True,
    )
    codes = [i.code for i in report.issues]
    assert "reversal_tighten_stop" not in codes
    assert "reversal_tighten_target" not in codes


# ── Test 4: reversal pre-T1 → no action ──────────────────────────────────────

def test_reversal_pre_t1_no_action(monkeypatch):
    """CVD reversal but T1 not yet hit → no tighten (too early to declare reversal)."""
    monkeypatch.setenv("SYSTEM6_REVERSAL_TIGHTEN_V1", "1")
    report = diagnose_trade(
        trade=_base_trade(), atr=10.0, t1_hit=False,
        cvd_reversal=True,
    )
    codes = [i.code for i in report.issues]
    assert "reversal_tighten_stop" not in codes
    assert "reversal_tighten_target" not in codes


# ── Test 5: picks first open target (skips t2 if absent) ─────────────────────

def test_picks_next_open_target(monkeypatch):
    """If t2 is None (already hit), picks t3 as the target to tighten."""
    monkeypatch.setenv("SYSTEM6_REVERSAL_TIGHTEN_V1", "1")
    trade = _base_trade()
    trade["t2"] = None  # already hit
    report = diagnose_trade(
        trade=trade, atr=10.0, t1_hit=True,
        cvd_reversal=True,
    )
    tgt_iss = next(i for i in report.issues if i.code == "reversal_tighten_target")
    # t3=7530, entry=7500, 50% of 30 = 15 → new = 7515
    assert tgt_iss.correction["price"] == 7515.0
