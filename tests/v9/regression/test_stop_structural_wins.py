"""#1 P0: structural stop always wins — Dalton alignment.

Case #420: REACTIVE_SHORT entry 7508.75, structure high 7527.5.
Old behavior: stop at 7514 (bar high, inside structure) → caught in 8s.
New behavior: stop at 7527.5 + 6T = 7529.0 (above structure).

Tests the full pipeline:
  1. resolve_stop with wide structure → accepts (not rejects)
  2. resolve_stop without flag → rejects (legacy)
  3. R:R is correct with structural stop
"""
import os
import pytest

from backend.v9.systems.stop_anchors.stop_resolver import resolve_stop


# ── #420 fixture ──

ENTRY = 7508.75
STRUCT_HIGH = 7527.5  # max(b1.h, b2.h, b3.h) — supply zone ceiling
ATR = 10.0  # typical ATR


def test_widen_to_structure_accepts_wide_stop(monkeypatch):
    """STOP_WIDEN_TO_STRUCTURE_V1=1: structure 7527.5 + 6T = 7529.0 accepted."""
    monkeypatch.setenv("STOP_WIDEN_TO_STRUCTURE_V1", "1")
    result = resolve_stop(
        direction="SHORT",
        entry_price=ENTRY,
        rungs=[STRUCT_HIGH],  # one rung: the structural high
        rung_names=["swing_high"],
        atr_5m=ATR,
        family="REV",
        offset_ticks=6,
    )
    # Stop should be ABOVE structure: 7527.5 + 6*0.25 = 7529.0
    assert result.stop_price == 7529.0, f"Expected 7529.0, got {result.stop_price}"
    assert not result.rejected, "Structure should NOT be rejected"
    # Risk: 7529.0 - 7508.75 = 20.25pt
    assert abs(result.risk_points - 20.25) < 0.01
    # Above ATR cap (1.5 * 10 = 15) but accepted because structural wins
    assert result.risk_points > result.cap_pts


def test_legacy_rejects_wide_stop(monkeypatch):
    """Without flag: structure wider than cap → rejected."""
    monkeypatch.delenv("STOP_WIDEN_TO_STRUCTURE_V1", raising=False)
    result = resolve_stop(
        direction="SHORT",
        entry_price=ENTRY,
        rungs=[STRUCT_HIGH],
        rung_names=["swing_high"],
        atr_5m=ATR,
        family="REV",
        offset_ticks=6,
    )
    assert result.rejected, "Without flag, wide structure should be rejected"


def test_rr_correct_with_structural_stop(monkeypatch):
    """With structural stop, R:R is realistic (not inflated by narrow stop)."""
    monkeypatch.setenv("STOP_WIDEN_TO_STRUCTURE_V1", "1")
    result = resolve_stop(
        direction="SHORT",
        entry_price=ENTRY,
        rungs=[STRUCT_HIGH],
        rung_names=["swing_high"],
        atr_5m=ATR,
        family="REV",
        offset_ticks=6,
    )
    # T1 target: entry - 4pt = 7504.75 (typical for SHORT)
    t1_target = ENTRY - 4.0
    reward = abs(ENTRY - t1_target)
    risk = result.risk_points
    rr = reward / risk if risk > 0 else 0
    # R:R = 4 / 20.25 = ~0.20 — this is the REAL R:R
    # With the old narrow stop (risk ~5pt), R:R was artificially 0.80
    assert rr < 0.3, f"R:R should be low with wide structural stop, got {rr:.2f}"


def test_narrow_structure_within_band(monkeypatch):
    """Structure within [floor, cap] → accepted regardless of flag."""
    monkeypatch.setenv("STOP_WIDEN_TO_STRUCTURE_V1", "1")
    # Narrow structure: only 3pt above entry
    result = resolve_stop(
        direction="SHORT",
        entry_price=7500.0,
        rungs=[7508.0],  # 8pt above entry
        rung_names=["swing_high"],
        atr_5m=ATR,
        family="REV",
        offset_ticks=6,
    )
    # 7508 + 1.5 = 7509.5, dist = 9.5pt. Cap = 15pt. In band.
    assert not result.rejected
    assert result.in_band


def test_long_mirror(monkeypatch):
    """LONG: structural floor below entry, stop below structure."""
    monkeypatch.setenv("STOP_WIDEN_TO_STRUCTURE_V1", "1")
    result = resolve_stop(
        direction="LONG",
        entry_price=7500.0,
        rungs=[7478.0],  # structural low 22pt below
        rung_names=["swing_low"],
        atr_5m=ATR,
        family="REV",
        offset_ticks=6,
    )
    # 7478 - 1.5 = 7476.5, dist = 23.5pt > cap 15pt → accepted with widen
    assert result.stop_price == 7476.5
    assert not result.rejected
