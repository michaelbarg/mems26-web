"""P4/A — MARKET_CONTEXT_V1: System 0 context unifier (2026-07-29).

Tests:
1. Flag OFF → all UNKNOWN (byte-identical, zero behavior change)
2. Flag ON → composes sources into unified context
3. Escalation-only: fields only strengthen, never degrade
4. Balance state derived from opening type
5. Day bias priority: expansion > dir_bias > seed
"""
import os
import types
from unittest.mock import patch

import pytest

from backend.v9.services.market_context import (
    MarketContext, get_market_context, reset_context, _escalate,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_context()
    yield
    reset_context()


# ── Test 1: flag OFF → skeleton ──────────────────────────────────────────────

def test_flag_off_returns_unknown(monkeypatch):
    monkeypatch.delenv("MARKET_CONTEXT_V1", raising=False)
    ctx = get_market_context()
    assert ctx.balance_state == "UNKNOWN"
    assert ctx.opening_type == "UNKNOWN"
    assert ctx.day_bias == "NONE"
    assert ctx.day_type == "UNKNOWN"


# ── Test 2: flag ON → composes ───────────────────────────────────────────────

def test_flag_on_composes_day_type(monkeypatch):
    monkeypatch.setenv("MARKET_CONTEXT_V1", "1")
    with patch("backend.v9.services.trade_context.get_live_day_type", return_value="Variation"), \
         patch("backend.v9.services.trade_context.get_live_dir_bias", return_value="UP"), \
         patch("backend.v9.services.trade_context.get_live_expansion", return_value=None), \
         patch("backend.v9.services.trade_context.get_opening_type_seed", return_value="UP"):
        ctx = get_market_context()
    assert ctx.day_type == "Variation"
    assert ctx.day_bias == "UP"


# ── Test 3: escalation-only ──────────────────────────────────────────────────

def test_escalate_only_strengthens():
    seq = ("UNKNOWN", "in_value_accepted", "out_value_in_range", "out_of_range")
    assert _escalate("UNKNOWN", "out_value_in_range", seq) == "out_value_in_range"
    assert _escalate("out_value_in_range", "UNKNOWN", seq) == "out_value_in_range"  # no degrade
    assert _escalate("out_value_in_range", "out_of_range", seq) == "out_of_range"


# ── Test 4: balance from opening type ────────────────────────────────────────

def test_drive_sets_out_of_range(monkeypatch):
    monkeypatch.setenv("MARKET_CONTEXT_V1", "1")
    app_state = types.SimpleNamespace(
        opening_type_result={"opening_type": "OPEN_DRIVE", "direction": "DOWN", "confidence": 0.85},
    )
    app = types.SimpleNamespace(state=app_state)
    with patch("backend.v9.services.trade_context.get_live_day_type", return_value=None), \
         patch("backend.v9.services.trade_context.get_live_dir_bias", return_value=None), \
         patch("backend.v9.services.trade_context.get_live_expansion", return_value=None), \
         patch("backend.v9.services.trade_context.get_opening_type_seed", return_value=None), \
         patch("backend.main.app", app):
        ctx = get_market_context()
    assert ctx.opening_type == "OPEN_DRIVE"
    assert ctx.balance_state == "out_of_range"
    assert ctx.balance_conviction == "high"


def test_auction_in_sets_in_value(monkeypatch):
    monkeypatch.setenv("MARKET_CONTEXT_V1", "1")
    app = types.SimpleNamespace(state=types.SimpleNamespace(
        opening_type_result={"opening_type": "OPEN_AUCTION_IN", "direction": "NEUTRAL", "confidence": 0.4},
    ))
    with patch("backend.v9.services.trade_context.get_live_day_type", return_value=None), \
         patch("backend.v9.services.trade_context.get_live_dir_bias", return_value=None), \
         patch("backend.v9.services.trade_context.get_live_expansion", return_value=None), \
         patch("backend.v9.services.trade_context.get_opening_type_seed", return_value=None), \
         patch("backend.main.app", app):
        ctx = get_market_context()
    assert ctx.balance_state == "in_value_accepted"
    assert ctx.balance_conviction == "low"


# ── Test 5: day bias priority ────────────────────────────────────────────────

def test_expansion_overrides_dir_bias(monkeypatch):
    monkeypatch.setenv("MARKET_CONTEXT_V1", "1")
    with patch("backend.v9.services.trade_context.get_live_day_type", return_value=None), \
         patch("backend.v9.services.trade_context.get_live_dir_bias", return_value="DOWN"), \
         patch("backend.v9.services.trade_context.get_live_expansion", return_value={"dir": "UP", "ref": "IB"}), \
         patch("backend.v9.services.trade_context.get_opening_type_seed", return_value=None):
        ctx = get_market_context()
    assert ctx.day_bias == "UP"  # expansion wins over dir_bias
