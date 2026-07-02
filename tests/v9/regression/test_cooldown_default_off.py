"""Standing decision (Michael 2026-07-02): 2-stop cooldown BLOCK is default-OFF.

The cooldown was a ζ.A4 spec-era mechanism never ratified by Michael; it was
inert until I-57 fixed stop-counting, then blocked trading for the first time.
Ruling: counting stays (observability), the BLOCK is flag-gated
COOLDOWN_2STOP_V1 (default OFF) + Michael sign-off to enable.

Anti-tautological: drives the real CooldownManager after 2 real stop closes.
Fails on pre-ruling code (which blocked with the flag unset).
"""
import os

import pytest

from backend.v9.gateway.cooldown import CooldownManager


@pytest.fixture(autouse=True)
def _clean_flag(monkeypatch):
    monkeypatch.delenv("COOLDOWN_2STOP_V1", raising=False)


def test_two_stops_do_not_block_by_default():
    cm = CooldownManager()
    cm.on_trade_close("STOP")
    cm.on_trade_close("STOP")
    assert cm.consecutive_stops == 2, "counting must stay live (observability)"
    assert cm.is_blocked() is False, "block must be OFF by default (Michael 2026-07-02)"
    assert cm.get_state()["cooldown_active"] is False


def test_flag_on_restores_blocking(monkeypatch):
    monkeypatch.setenv("COOLDOWN_2STOP_V1", "1")
    cm = CooldownManager()
    cm.on_trade_close("STOP")
    cm.on_trade_close("STOP")
    assert cm.is_blocked() is True, "with the flag ON the original behavior returns"


def test_win_still_resets_counter():
    cm = CooldownManager()
    cm.on_trade_close("STOP")
    cm.on_trade_close("WIN")
    assert cm.consecutive_stops == 0
