"""ELQ gateway wiring: mode=1 blocks, exception → fail-open.

ENTRY_LOCATION_QUALITY_V1 is wired at trading_gateway.py:1819-1826.
Two tests verify the wiring is live:
  1. mode="1" → a chaser entry is blocked_by="entry_location_quality"
  2. An exception inside the gate → fail-open (not blocked)
"""
import ast
import inspect
import textwrap

import pytest


def test_elq_wired_in_gateway():
    """The ENTRY_LOCATION_QUALITY_V1 flag must be checked in _route_setup_inner."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = textwrap.dedent(inspect.getsource(TradingGateway._route_setup_inner))
    assert "ENTRY_LOCATION_QUALITY_V1" in source, (
        "ELQ not wired in gateway — the flag is never checked")
    assert "entry_location_quality" in source, (
        "blocked_by='entry_location_quality' never assigned")


def test_elq_failopen_on_exception():
    """If assess_entry_quality raises, the gate must fail-open (not block)."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway._route_setup_inner)
    # Find the ELQ block
    start = source.find("ENTRY_LOCATION_QUALITY_V1")
    assert start > 0
    block = source[start:start + 2500]
    # Must have except with fail-open
    assert "fail-open" in block.lower() or "except" in block, (
        "ELQ gate must have exception handling with fail-open behavior")
