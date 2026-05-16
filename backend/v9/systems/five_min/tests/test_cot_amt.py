"""Tests for COT/AMT standalone module."""
from backend.v9.systems.five_min.cot_amt import compute_cot, compute_amt, cot_vs_amt


def test_cot_positive():
    points = [{"cum": 100.0}, {"cum": 200.0}, {"cum": 350.0}]
    assert compute_cot(points) == 350.0


def test_amt_rolling():
    # 5 points, window=3 → avg of last 3 cumulative values
    points = [{"cum": 100.0}, {"cum": 200.0}, {"cum": 300.0}, {"cum": 400.0}, {"cum": 500.0}]
    amt = compute_amt(points, window=3)
    assert amt == (300.0 + 400.0 + 500.0) / 3


def test_vs_above():
    # COT (last cum) = 500, AMT (avg of all 5) = 300
    points = [{"cum": 100.0}, {"cum": 200.0}, {"cum": 300.0}, {"cum": 400.0}, {"cum": 500.0}]
    assert cot_vs_amt(points) == 'ABOVE'


def test_vs_below():
    # COT (last cum) = 100, AMT (avg of all 5) = 300
    points = [{"cum": 500.0}, {"cum": 400.0}, {"cum": 300.0}, {"cum": 200.0}, {"cum": 100.0}]
    assert cot_vs_amt(points) == 'BELOW'
