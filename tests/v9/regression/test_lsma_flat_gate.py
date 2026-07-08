"""Anti-tautological tests for LSMA_FLAT_GATE_V1 (Michael 2026-07-08).

"No fires while the Woodies LSMA (the cyan dotted line) is too horizontal —
no clear trend angle." lsma_slope_pts_per_bar measures the LSMA's OWN slope
(points/bar); the gateway blocks when |slope| < LSMA_FLAT_MIN_SLOPE_PTS.

if reverted -> RED because:
- test_flat_lsma_is_zero_slope / test_rising_half_point_per_bar pin the magnitude;
- test_most_recent_first_sign pins the DESC-ordering sign convention (a naive
  oldest-first read flips the sign);
- test_flat_passes_dir_sustained_but_fails_flat_gate proves the NEW metric is
  not already covered by CONT_TREND_FILTER's side-of-LSMA check (the gap that
  motivated the gate);
- honesty tests pin None (never 0.0) when data is missing (Rule 1).
"""
import os

from backend.v9.systems.direction_context_live import (
    lsma_slope_pts_per_bar,
    sustained_lsma_side,
)


def _rows(lsma_desc, close_off=1.0):
    """rows MOST-RECENT FIRST (ORDER BY ts DESC); close = lsma + close_off."""
    return [{"close": v + close_off, "lsma_value": v} for v in lsma_desc]


# ── slope magnitude ──────────────────────────────────────────────────────────
def test_flat_lsma_is_zero_slope():
    assert lsma_slope_pts_per_bar(_rows([7500.0, 7500.0, 7500.0, 7500.0]), 4) == 0.0


def test_rising_half_point_per_bar():
    # newest 7501.5 ... oldest 7500.0 over 4 bars = 3 intervals -> +0.5 pts/bar
    assert lsma_slope_pts_per_bar(_rows([7501.5, 7501.0, 7500.5, 7500.0]), 4) == 0.5


def test_falling_slope_negative():
    assert lsma_slope_pts_per_bar(_rows([7499.0, 7500.0, 7501.0]), 3) == -1.0


def test_most_recent_first_sign():
    # DESC rows: newest=7502 > oldest=7500 -> RISING (+1.0). An oldest-first
    # implementation returns -1.0 -> RED.
    assert lsma_slope_pts_per_bar(_rows([7502.0, 7501.0, 7500.0]), 3) == 1.0


def test_lookback_k_uses_only_newest_k():
    # k=3 must ignore the old crash bar (index 3): slope from [7501,7500.5,7500]=+0.5
    rows = _rows([7501.0, 7500.5, 7500.0, 7400.0])
    assert lsma_slope_pts_per_bar(rows, 3) == 0.5


# ── honesty (Rule 1): missing data -> None, never a synthesized 0.0 ─────────
def test_empty_and_none_rows_are_none():
    assert lsma_slope_pts_per_bar([], 4) is None
    assert lsma_slope_pts_per_bar(None, 4) is None


def test_single_value_is_none():
    assert lsma_slope_pts_per_bar(_rows([7500.0]), 4) is None


def test_null_lsma_values_skipped():
    rows = [{"close": 1.0, "lsma_value": None}, {"close": 1.0, "lsma_value": None}]
    assert lsma_slope_pts_per_bar(rows, 4) is None


# ── the motivating gap: flat LSMA passes the SIDE filter, fails the FLAT gate ─
def test_flat_passes_dir_sustained_but_fails_flat_gate():
    """Price hugging ABOVE a dead-flat LSMA: dir_sustained=UP (CONT_TREND_FILTER
    passes) yet slope=0.0 < any positive threshold -> only the NEW gate blocks.
    Removing the new metric makes this scenario unfiltered again -> RED."""
    rows = _rows([7500.0, 7500.0, 7500.0], close_off=1.0)
    assert sustained_lsma_side(rows, 3) == "UP"          # side filter: sustained
    slope = lsma_slope_pts_per_bar(rows, 3)
    assert slope == 0.0                                   # but the line is flat
    thr = float(os.getenv("LSMA_FLAT_MIN_SLOPE_PTS", "0.25") or "0.25")
    assert abs(slope) < thr                               # -> gate blocks when ON


# ── default wiring: flag unset ⇒ gate inert (byte-identical behavior) ────────
def test_flag_default_off():
    assert os.getenv("LSMA_FLAT_GATE_V1", "0").lower() not in ("1", "true", "yes"), (
        "LSMA_FLAT_GATE_V1 must default OFF — enabling is a trading-risk-surface "
        "change requiring Michael's explicit sign-off")


# ── scope semantics reuse the unified CONT/REV family map ────────────────────
def test_scope_cont_would_exempt_reversals():
    from backend.v9.systems.daytype_position_gate import _pattern_family
    assert _pattern_family("ZLR") == "CONT"       # filtered under scope=CONT
    assert _pattern_family("HTLB") == "REV"       # exempt under scope=CONT
