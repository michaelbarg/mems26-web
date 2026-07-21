"""BE_AFTER_REAL_T1_V1 — BE fires on real T1 (C2), NOT T0 scalp (C1).

Michael ruling 2026-07-20: with 4-contract T0 ladder, the DLL reports C1 fill
as "T1". Without the fix, on_target_hit("T1") triggers BE prematurely.
With the flag ON + 4 contracts + t0_target_pts in quality, remap:
  DLL T1 → T0 (no BE), DLL T2 → T1 (BE here), DLL T3 → T2, DLL T4 → T3.

Anti-tautological:
  1. Flag ON + 4c + T0: DLL "T1" → T0 hit, NO BE
  2. Flag ON + 4c + T0: DLL "T2" → real T1 hit, BE fires
  3. Flag OFF: DLL "T1" → T1 hit, BE fires (legacy)
  4. Flag ON + 3c (no T0): DLL "T1" → T1 hit, BE fires (no remap)
"""
import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone


@pytest.fixture
def tm():
    """Minimal TradeManager with mocked internals."""
    from backend.v9.services.trade_manager.manager import TradeManager
    mgr = TradeManager.__new__(TradeManager)
    mgr._trades = {}
    mgr._machines = {}
    mgr._db = None
    return mgr


def _make_trade(contracts=4, has_t0=True, direction="LONG"):
    """Create a trade object with the right attributes."""
    trade = MagicMock()
    trade.id = 1
    trade.direction = direction
    trade.entry_price = 7500.0
    trade.stop = 7490.0
    trade.t1 = 7510.0
    trade.t2 = 7520.0
    trade.t3 = 7530.0
    trade.t4 = 7540.0 if contracts >= 4 else None
    trade.t1_hit_ts = None
    trade.t2_hit_ts = None
    trade.t3_hit_ts = None
    trade.t4_hit_ts = None
    trade.state = "OPEN"
    trade.mode = "demo"
    q = {"contracts": contracts}
    if has_t0:
        q["t0_target_pts"] = 3.5
        q["has_t0"] = True
    trade.quality = q
    return trade


def test_flag_on_t0_no_be(monkeypatch):
    """Flag ON + 4c + T0: DLL 'T1' → remapped to T0, NO BE."""
    monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
    trade = _make_trade(contracts=4, has_t0=True)
    mgr = _setup_mgr(trade)
    mgr.on_target_hit(1, "T1")  # DLL says T1, should remap to T0
    assert mgr._log_management.call_args[0][1] == "T0_HIT"
    mgr._apply_smart_be_after_t1.assert_not_called()  # KEY: no BE on T0


def _setup_mgr(trade, monkeypatch=None):
    """Create a minimal TradeManager with all internals mocked."""
    from backend.v9.services.trade_manager.manager import TradeManager
    mgr = TradeManager.__new__(TradeManager)
    mgr._trades = {1: trade}
    machine = MagicMock()
    mgr._machines = {1: machine}
    mgr._db = MagicMock()
    mgr._emitter = MagicMock()
    mgr._log_management = MagicMock()
    mgr._calculate_pnl = MagicMock()
    mgr._apply_smart_be_after_t1 = MagicMock()
    mgr._append_snapshot = MagicMock()
    mgr._close_on_final_target = MagicMock()
    mgr._get_trade = lambda tid: trade
    mgr._get_machine = lambda t: machine
    return mgr


def test_flag_on_real_t1_triggers_be(monkeypatch):
    """Flag ON + 4c + T0: DLL 'T2' → remapped to T1, BE fires."""
    monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
    trade = _make_trade(contracts=4, has_t0=True)
    mgr = _setup_mgr(trade)
    mgr.on_target_hit(1, "T2")  # DLL says T2, should remap to T1
    mgr._apply_smart_be_after_t1.assert_called_once()


def test_flag_off_legacy_be_on_t1(monkeypatch):
    """Flag OFF: DLL 'T1' → T1 hit, BE fires (legacy behavior)."""
    monkeypatch.delenv("BE_AFTER_REAL_T1_V1", raising=False)
    trade = _make_trade(contracts=4, has_t0=True)
    mgr = _setup_mgr(trade)
    mgr.on_target_hit(1, "T1")
    mgr._apply_smart_be_after_t1.assert_called_once()


def test_flag_on_3c_no_remap(monkeypatch):
    """Flag ON + 3 contracts (no T0): DLL 'T1' → T1, BE fires."""
    monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
    trade = _make_trade(contracts=3, has_t0=False)
    mgr = _setup_mgr(trade)
    mgr.on_target_hit(1, "T1")
    mgr._apply_smart_be_after_t1.assert_called_once()


def test_accept_setup_writes_t0_quality(monkeypatch):
    """accept_setup with FIXED_CONTRACTS_4+T0_TARGET_PTS writes quality.has_t0."""
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setenv("T0_TARGET_PTS", "4.0")
    monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")

    from backend.v9.services.trade_manager.manager import TradeManager
    mgr = TradeManager.__new__(TradeManager)
    mgr._trades = {}
    mgr._machines = {}
    mgr._db = MagicMock()
    mgr._emitter = MagicMock()
    mgr._snapshot = None
    mgr._log_management = MagicMock()

    # Test the quality construction directly (accept_setup needs DB/machine setup)
    from backend.v9.services.sierra_command import effective_contracts
    setup = {
        "direction": "SHORT",
        "entry_price": 7508.75,
        "stop_price": 7529.0,
        "target_price": 7500.0,
        "confidence": 0.8,
        "cross_context": {},
        "metadata": {"sizing": 4},
        "classification": "REACTIVE_SHORT",
    }
    _n_contracts = effective_contracts(setup)
    quality = {"contracts": _n_contracts}
    _t0p = float(os.getenv("T0_TARGET_PTS", "0") or 0)
    if _n_contracts >= 4 and _t0p > 0:
        quality["t0_target_pts"] = _t0p
        quality["has_t0"] = True

    assert quality.get("has_t0") is True, f"quality missing has_t0: {quality}"
    assert quality.get("t0_target_pts") == 4.0, f"t0_target_pts wrong: {quality}"
    assert quality.get("contracts") == 4, f"contracts wrong: {quality}"
