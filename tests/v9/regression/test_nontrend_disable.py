"""Anti-tautological regression tests for NONTREND_DISABLE_ALL.

Michael's rule: every pattern fires full on every day-type EXCEPT Nontrend where
ALL patterns are disabled. Tests call the REAL daytype_position_gate.decide().

if reverted → RED because: reverting the Nontrend branch to the old
(True, "Nontrend (playbook handles SKIP)") removes the block, so every
flag-ON + Nontrend assertion fails.
"""
import os
import pytest
from unittest.mock import patch

from backend.v9.systems.daytype_position_gate import decide

# Shared TPO context for position-gate calls
_TPO = {"poc": 7455.0, "ib_high": 7470.0, "ib_low": 7440.0,
        "session_high": 7480.0, "session_low": 7430.0}

# Both gates must be ON for the test to exercise the real path
_ENV_ON = {"DAYTYPE_POSITION_GATE": "1", "NONTREND_DISABLE_ALL": "1"}
_ENV_OFF = {"DAYTYPE_POSITION_GATE": "1", "NONTREND_DISABLE_ALL": "0"}


# ── Flag ON + Nontrend → blocks ALL fires ────────────────────────────────

@patch.dict(os.environ, _ENV_ON)
def test_nontrend_blocks_s2_reactive_long():
    ok, reason = decide(pattern="REACTIVE_LONG", direction="LONG",
                        day_type="Nontrend", entry_price=7450.0, tpo_ctx=_TPO)
    assert not ok, reason
    assert "Nontrend" in reason and "disabled" in reason


@patch.dict(os.environ, _ENV_ON)
def test_nontrend_blocks_s2_reactive_short():
    ok, reason = decide(pattern="REACTIVE_SHORT", direction="SHORT",
                        day_type="Nontrend", entry_price=7460.0, tpo_ctx=_TPO)
    assert not ok, reason


@patch.dict(os.environ, _ENV_ON)
def test_nontrend_blocks_s4_zlr_long():
    ok, reason = decide(pattern="ZLR", direction="LONG",
                        day_type="Nontrend", entry_price=7450.0, tpo_ctx=_TPO)
    assert not ok, reason


@patch.dict(os.environ, _ENV_ON)
def test_nontrend_blocks_s4_hfe_short():
    ok, reason = decide(pattern="HFE", direction="SHORT",
                        day_type="Nontrend", entry_price=7460.0, tpo_ctx=_TPO)
    assert not ok, reason


@patch.dict(os.environ, _ENV_ON)
def test_nontrend_blocks_s4_tlb_short():
    """TLB SHORT on Nontrend — the 06-22 #188/#190 case."""
    ok, reason = decide(pattern="TLB", direction="SHORT",
                        day_type="Nontrend", entry_price=7465.0, tpo_ctx=_TPO)
    assert not ok, reason


# ── Flag ON + non-Nontrend day-types → NOT blocked by this rule ──────────

@patch.dict(os.environ, _ENV_ON)
@pytest.mark.parametrize("dt", ["Normal", "Variation", "Trend_Normal", "Trend_DD",
                                 "Neutral_Center", "Neutral_Extreme"])
def test_non_nontrend_unaffected(dt):
    """Non-Nontrend day-types are not blocked by NONTREND_DISABLE_ALL.
    (They may still be gated by position rules, but NOT by this Nontrend block.)

    if reverted → RED because: this test doesn't break on revert (it passes either
    way for non-Nontrend). The anti-tautology is in the flag-off test below.
    """
    ok, reason = decide(pattern="REACTIVE_LONG", direction="LONG",
                        day_type=dt, entry_price=7435.0, tpo_ctx=_TPO)
    assert "Nontrend" not in reason or "disabled" not in reason


# ── Flag OFF → identical to today (anti-tautology) ───────────────────────

@patch.dict(os.environ, _ENV_OFF)
def test_flag_off_nontrend_allows():
    """With NONTREND_DISABLE_ALL=0, Nontrend behaves as before (defers/allows).

    if reverted → RED because: the flag-ON tests above would fail (they assert
    block on Nontrend), proving the flag gates the behavior.
    """
    ok, reason = decide(pattern="REACTIVE_LONG", direction="LONG",
                        day_type="Nontrend", entry_price=7450.0, tpo_ctx=_TPO)
    assert ok, "flag OFF must allow Nontrend fires (today's behavior)"
    assert "defer" in reason.lower() or "off" in reason.lower()


# ── 06-22 Nontrend backtest regression (the 5 fires) ────────────────────

@patch.dict(os.environ, _ENV_ON)
@pytest.mark.parametrize("pattern,direction", [
    ("TLB", "SHORT"),       # #188
    ("TLB", "SHORT"),       # #190
    ("HFE", "SHORT"),       # #191
    ("HFE", "SHORT"),       # #193
    ("HFE", "SHORT"),       # #194
])
def test_0622_nontrend_fires_blocked(pattern, direction):
    """All 5 Nontrend fires from 06-22 (≈ -$555) are blocked.

    if reverted → RED because: removing the Nontrend block makes these pass-through.
    """
    ok, reason = decide(pattern=pattern, direction=direction,
                        day_type="Nontrend", entry_price=7500.0, tpo_ctx=_TPO)
    assert not ok, f"{pattern} {direction} on Nontrend must be blocked: {reason}"
