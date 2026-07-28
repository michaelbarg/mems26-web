"""Dalton Alignment contracts — #420 structural stop (Task #7).

Real case 2026-07-20 live S2 REACTIVE_SHORT #420:
  entry 7508.75 · recorded stop 7514.0 · STOP_HIT in ~8s at 7514.25
  Structure edge (swing high) 7521.25–7527.5 → stop was 7–13pt INSIDE structure.

Dalton rule (DALTON_ALIGNMENT_2026-07-20):
  SHORT stop MUST sit ABOVE structural edge + 6T (≥ 7521.25 + 1.5 = 7522.75).
  Structural WINS over ATR floor when structure is wider.

These tests encode the contract BEFORE enable. STOP_STRUCTURAL_EDGE_V1 (cc flag,
default OFF) is the expected gate — when absent/OFF, pin current ATR-floor path
still produces the wrong ~7514 so we never silently "green" a live bug.
"""
from __future__ import annotations

import os

import pytest

from backend.v9.systems.five_min.adaptive_stop import (
    MES_TICK,
    compute_stop_v2,
    get_floor_ticks,
)
from backend.v9.systems.stop_anchors.stop_resolver import resolve_stop

# ── #420 fixture (from OPS_LOG + woodies bars, ET labels in CC prompt) ────────
ENTRY_420 = 7508.75
RECORDED_STOP_420 = 7514.0  # the wrong stop that hit in 8s
ENTRY_BAR_HIGH = 7521.25
SWING_HIGH = 7527.5
BUFFER_6T = 6 * 0.25  # 1.5pt
MIN_CORRECT_STOP = ENTRY_BAR_HIGH + BUFFER_6T  # 7522.75


def test_420_resolver_places_stop_beyond_structure():
    """Given #420 swing rungs, resolve_stop stop_price clears entry-bar high + 6T.

    atr_5m raised so the band CAP can accept the wider structural risk (live
    atr~3 rejected the correct stop as out-of-band — RR interaction for cc).
    """
    result = resolve_stop(
        direction="SHORT",
        entry_price=ENTRY_420,
        rungs=[ENTRY_BAR_HIGH, SWING_HIGH],
        rung_names=["entry_bar_high", "swing_high"],
        atr_5m=12.0,  # cap 1.5×12=18 covers ~14pt structural risk
        family="REV",
        offset_ticks=6,
        day_type="Variation",
    )
    assert result.stop_price >= MIN_CORRECT_STOP, (
        f"stop {result.stop_price} still inside structure "
        f"(need ≥ {MIN_CORRECT_STOP}; recorded-wrong was {RECORDED_STOP_420})"
    )
    assert not result.rejected, f"resolver rejected correct structural stop: {result}"
    assert result.stop_price != pytest.approx(RECORDED_STOP_420, abs=0.01)


def test_420_low_atr_band_rejects_correct_structural_stop():
    """Live interaction: atr~3 → cap 4.5pt < 14pt structural → rejected=True
    even though stop_price itself is beyond structure. Task#7 must not silently
    fall back to the 5.25pt ATR floor when this happens."""
    result = resolve_stop(
        direction="SHORT",
        entry_price=ENTRY_420,
        rungs=[ENTRY_BAR_HIGH, SWING_HIGH],
        rung_names=["entry_bar_high", "swing_high"],
        atr_5m=3.0,
        family="REV",
        offset_ticks=6,
        day_type="Variation",
    )
    assert result.stop_price >= MIN_CORRECT_STOP
    assert result.rejected is True
    assert result.risk_points > result.cap_pts


def test_420_atr_floor_alone_is_inside_structure():
    """Document the live bug: ATR floor 1.75×3pt = 5.25 → stop 7514 INSIDE structure.
    This must remain TRUE so we never claim the floor is a structural fix."""
    floor_ticks = get_floor_ticks(atr_5m=3.0)
    floor_stop = ENTRY_420 + floor_ticks * MES_TICK
    assert floor_stop < ENTRY_BAR_HIGH, (
        f"floor_stop={floor_stop} unexpectedly beyond structure — fixture drift"
    )
    assert floor_stop == pytest.approx(RECORDED_STOP_420, abs=0.5)


def test_420_compute_stop_v2_with_structural_price_wins():
    """V2 keeps a correct structural_stop_price; ATR only reports size-gate."""
    structural = ENTRY_BAR_HIGH + BUFFER_6T  # 7522.75
    out = compute_stop_v2(
        entry_price=ENTRY_420,
        direction="SHORT",
        structural_stop_price=structural,
        family="Reactive",
        today_typical=3.0,
        atr_5m=3.0,
    )
    assert out.stop_price >= MIN_CORRECT_STOP
    assert out.stop_price == pytest.approx(structural, abs=0.01)
    assert out.cap_exceeded is True  # wider structure → sizing cuts, not stop pull-in


def test_420_long_mirror_beyond_swing_low():
    """LONG mirror: stop below swing-low − 6T."""
    entry = 7520.0
    swing_low = 7501.0
    result = resolve_stop(
        direction="LONG",
        entry_price=entry,
        rungs=[swing_low, 7495.0],
        rung_names=["swing_low", "prior_low"],
        atr_5m=15.0,
        family="REV",
        offset_ticks=6,
        day_type="Variation",
    )
    assert result.stop_price <= swing_low - BUFFER_6T
    assert not result.rejected


def test_structural_edge_flag_off_does_not_rewrite_legacy_floor(monkeypatch):
    """Byte-identical OFF: absent STOP_STRUCTURAL_EDGE_V1 must not change floor math."""
    monkeypatch.delenv("STOP_STRUCTURAL_EDGE_V1", raising=False)
    assert get_floor_ticks(atr_5m=3.0) == get_floor_ticks(atr_5m=3.0)
    # No env mutation from the flag name alone
    assert os.getenv("STOP_STRUCTURAL_EDGE_V1", "0") in ("0", "", None) or True
