"""Confirm-tol floor: max(frac×ATR, min_pts) — Michael ruling 2026-07-10."""


def test_floor_applies_when_atr_tiny():
    """With ATR=3pt and frac=0.10, raw tol=0.3pt but floor=0.5pt wins."""
    frac = 0.10
    atr = 3.0
    min_pts = 0.5
    tol = max(frac * atr, min_pts)
    assert tol == 0.5


def test_floor_inactive_when_atr_normal():
    """With ATR=7pt and frac=0.10, raw tol=0.7pt > floor=0.5pt."""
    frac = 0.10
    atr = 7.0
    min_pts = 0.5
    tol = max(frac * atr, min_pts)
    assert tol == pytest.approx(0.7)


def test_floor_at_zero_when_no_env():
    """With min_pts=0 (env not set), pure frac×ATR behavior."""
    frac = 0.10
    atr = 5.0
    min_pts = 0.0
    tol = max(frac * atr, min_pts)
    assert tol == pytest.approx(0.5)


import pytest
