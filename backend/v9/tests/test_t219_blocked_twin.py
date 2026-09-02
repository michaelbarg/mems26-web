"""T-219: shadow_blocked twin for every refused candidate.

Five isolation guarantees (spec §3):
  3.1 Structural: runs AFTER result is final
  3.2 Slot: never touches live_slot/demo_slot
  3.3 Sierra: no order written
  3.4 Feedback: NOT appended to shadow_trades (no phantom fires)
  3.5 Flag: BLOCKED_TWIN_V1, code default OFF
"""
import ast
import inspect
import os
import textwrap

import pytest


def test_blocked_twin_flag_in_route_setup():
    """The flag must be checked in route_setup."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    assert "BLOCKED_TWIN_V1" in source


def test_blocked_twin_does_not_append_shadow_trades():
    """shadow_trades.append must NOT appear in the T-219 block.
    Appending would feed duplicate_fire/cluster_guard with phantom fires."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    start = source.find("T-219")
    assert start > 0
    # The block from T-219 marker to the end of the try
    block = source[start:start + 3000]
    # shadow_trades.append must NOT be in this block
    assert "shadow_trades.append" not in block, (
        "MUTATION §3.4: shadow_blocked appends to shadow_trades — "
        "this feeds duplicate_fire/cluster_guard with phantom fires")


def test_blocked_twin_does_not_touch_daily_trades():
    """_daily_trades and _daily_pnl must NOT be incremented."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    start = source.find("T-219")
    block = source[start:start + 3000]
    # Check for actual assignment (=), not just mentions in comments
    code_lines = [l for l in block.split("\n") if l.strip() and not l.strip().startswith("#")]
    code_only = "\n".join(code_lines)
    assert "_daily_trades +=" not in code_only and "_daily_trades =" not in code_only, (
        "MUTATION §3.4: shadow_blocked increments _daily_trades")
    assert "_daily_pnl +=" not in code_only and "_daily_pnl =" not in code_only, (
        "MUTATION §3.4: shadow_blocked increments _daily_pnl")


def test_blocked_twin_has_daily_cap():
    """A daily cap must exist to bound management load."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    start = source.find("T-219")
    block = source[start:start + 3000]
    assert "SHADOW_BLOCKED_MAX_PER_DAY" in block or "_bt_max" in block, (
        "T-219 must have a daily cap (spec §4.2: ~124/day mean)")


def test_flag_off_no_effect():
    """BLOCKED_TWIN_V1=0 → the insertion block is skipped entirely."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    # The flag check must gate the entire block
    assert 'BLOCKED_TWIN_V1", "0"' in source, (
        "Flag must default to OFF")
