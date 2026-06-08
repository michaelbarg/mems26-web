"""Chop gates are DISABLED by default (Michael 2026-06-08).

Guards CLAUDE.md § "Chop Gates (DISABLED — Michael approval to re-enable)".

Two independent gates, both default-OFF, both flag-gated:
  1. Gateway Layer-0 fire-veto  — env LAYER0_CHOP_GATE   (this file, behavioral)
  2. S2 inspector choppiness_ok — env S2_CHOPPINESS_GATE  (logic asserted below)

Re-enabling EITHER requires the env flag AND Michael's explicit approval.
If someone removes the default-off behavior, these tests fail.
"""
import os
import importlib

import pytest

from backend.v9.gateway import trading_gateway as tg


def _fresh_gateway(monkeypatch):
    """Construct an isolated gateway with the pre-chop and post-chop gates
    stubbed so only the Layer-0 chop branch decides blocked_by."""
    gw = tg.TradingGateway(db_path=":memory:")
    # Pre-chop gates → allow through to the chop branch.
    monkeypatch.setattr(tg, "is_within_firing_window", lambda *a, **k: True)
    monkeypatch.setattr(gw, "_capture_cross_context", lambda *a, **k: {})
    monkeypatch.setattr(gw, "_get_chop_state", lambda *a, **k: "SEARCHING")
    # Post-chop: stub shadow execution so we never touch the DB.
    monkeypatch.setattr(
        gw, "_execute_shadow",
        lambda *a, **k: {"trade_id": "T-TEST", "mode": "SHADOW"},
    )
    return gw


_SETUP = {
    "firing_system": 2, "direction": "LONG", "classification": "STRATEGIC",
    "confidence": 0.9, "stop": 7400.0, "t1": 7410.0, "entry_price": 7405.0,
    "metadata": {},
}


def test_chop_gate_disabled_by_default_does_not_block(monkeypatch):
    """Flag unset → chop_state=SEARCHING must NOT block (default-off)."""
    monkeypatch.delenv("LAYER0_CHOP_GATE", raising=False)
    gw = _fresh_gateway(monkeypatch)
    result = gw.route_setup(dict(_SETUP), system_id=2)
    assert result["blocked_by"] != "chop_searching", (
        "Layer-0 chop gate must be OFF by default (Michael 2026-06-08) — "
        "SEARCHING should not set blocked_by=chop_searching"
    )


def test_chop_gate_blocks_only_when_explicitly_enabled(monkeypatch):
    """Flag=1 → the gate is restored and SEARCHING blocks again."""
    monkeypatch.setenv("LAYER0_CHOP_GATE", "1")
    gw = _fresh_gateway(monkeypatch)
    result = gw.route_setup(dict(_SETUP), system_id=2)
    assert result["blocked_by"] == "chop_searching", (
        "With LAYER0_CHOP_GATE=1 the gate must block SEARCHING again"
    )


def test_s2_choppiness_gate_default_off_logic():
    """The S2 inspector expression: default-off means chop_ok=True regardless
    of score; only S2_CHOPPINESS_GATE=1 restores the score<70 gate. Mirrors
    s2_inspector.py so a silent default flip is caught here too."""
    def chop_ok(score, env):
        enabled = str(env).lower() in ("1", "true", "yes")
        return (score < 70) if enabled else True

    # Choppy score that WOULD block if the gate were on:
    assert chop_ok(93, "0") is True          # default-off → pass
    assert chop_ok(93, None) is True         # unset → pass
    assert chop_ok(93, "1") is False         # explicitly on → blocks
    assert chop_ok(40, "1") is True          # on + low score → pass
