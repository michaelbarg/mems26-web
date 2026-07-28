"""Dalton Alignment — Variation-down SHORT: T2/T3 must be structural (POC/VAL).

Real day 2026-07-20: Variation-down, VAH≈7527.5. Correct fade SHORT near VAH
should take profits DOWN toward POC (T2) and VAL (T3) — not arbitrary 2×/3× pts.

Contract (FULL_AUDIT / CURSOR_FULL_GATE_TARGET_AUDIT):
  structural_targets._resolve_variation REV SHORT → C2=POC, C3=VAL
  pattern_t1_points must NOT be the sole source of T2/T3 (gateway stomp is a
  known bug — this test pins the STRUCTURAL contract before enable of a fix).

Flag DAYTYPE_TARGETS_STRUCTURAL must be ON for resolve_structural_targets.
"""
from __future__ import annotations

import pytest

from backend.v9.systems.structural_targets import resolve_structural_targets

# Live-day-ish levels (VAH from Dalton handoff; IB/VAL/POC synthetic but consistent)
TPO = {
    "ib_high": 7520.0,
    "ib_low": 7480.0,  # width 40
    "poc": 7505.0,
    "vah": 7527.5,
    "val": 7490.0,
}
ENTRY_NEAR_VAH = 7527.0  # SHORT at ceiling
STOP_ABOVE = 7535.0      # beyond structure (correct stop — not #420's)


@pytest.fixture(autouse=True)
def _structural_on(monkeypatch):
    monkeypatch.setenv("DAYTYPE_TARGETS_STRUCTURAL", "1")


def test_variation_rev_short_t2_poc_t3_val():
    """REACTIVE (REV) Variation SHORT: C2=POC, C3=VAL below entry."""
    r = resolve_structural_targets(
        day_type="Variation",
        direction="SHORT",
        entry_price=ENTRY_NEAR_VAH,
        stop_price=STOP_ABOVE,
        tpo_ctx=TPO,
        pattern_family="REV",
    )
    assert r is not None, "structural resolver returned None"
    t2 = r.get("t2_price") or r.get("c2") or r.get("c2_price")
    t3 = r.get("t3_price") or r.get("c3") or r.get("c3_price")
    # _build_result keys — inspect if needed
    if t2 is None:
        t2 = r.get("targets", {}).get("t2") if isinstance(r.get("targets"), dict) else None
    assert t2 == pytest.approx(TPO["poc"], abs=0.01), f"T2 want POC; got {r}"
    assert t3 == pytest.approx(TPO["val"], abs=0.01), f"T3 want VAL; got {r}"
    assert t2 < ENTRY_NEAR_VAH and t3 < t2


def test_variation_cont_short_t3_is_val_not_vah():
    """CONT SHORT Variation: runner C3 = VAL (day direction), never VAH."""
    r = resolve_structural_targets(
        day_type="Variation",
        direction="SHORT",
        entry_price=ENTRY_NEAR_VAH,
        stop_price=STOP_ABOVE,
        tpo_ctx=TPO,
        pattern_family="CONT",
    )
    assert r is not None
    t3 = r.get("t3_price") or r.get("c3") or r.get("c3_price")
    assert t3 == pytest.approx(TPO["val"], abs=0.01), f"got {r}"
    assert t3 != TPO["vah"]
    assert t3 < ENTRY_NEAR_VAH


def test_variation_short_ladder_monotonic_down():
    r = resolve_structural_targets(
        day_type="Variation",
        direction="SHORT",
        entry_price=ENTRY_NEAR_VAH,
        stop_price=STOP_ABOVE,
        tpo_ctx=TPO,
        pattern_family="REV",
    )
    assert r is not None
    t1 = r.get("t1_price") or r.get("c1") or r.get("c1_price")
    t2 = r.get("t2_price") or r.get("c2") or r.get("c2_price")
    t3 = r.get("t3_price") or r.get("c3") or r.get("c3_price")
    assert t1 < ENTRY_NEAR_VAH
    assert t2 < t1 or t2 == pytest.approx(t1, abs=0.5)  # allow equal after caps
    assert t3 <= t2 + 0.01


def test_structural_flag_off_returns_none(monkeypatch):
    monkeypatch.setenv("DAYTYPE_TARGETS_STRUCTURAL", "0")
    r = resolve_structural_targets(
        day_type="Variation",
        direction="SHORT",
        entry_price=ENTRY_NEAR_VAH,
        stop_price=STOP_ABOVE,
        tpo_ctx=TPO,
        pattern_family="REV",
    )
    assert r is None


def test_pattern_t1_multiples_are_not_val():
    """Document the live stomp: 2×/3× of 9pt from VAH entry ≠ VAL/POC.
    Pure math — gateway must not leave T2/T3 as only this after structural."""
    pts = 9.0
    entry = ENTRY_NEAR_VAH
    t2_pts = entry - 2 * pts  # 7509
    t3_pts = entry - 3 * pts  # 7500
    assert t2_pts != pytest.approx(TPO["poc"], abs=0.5)
    assert t3_pts != pytest.approx(TPO["val"], abs=0.5)
