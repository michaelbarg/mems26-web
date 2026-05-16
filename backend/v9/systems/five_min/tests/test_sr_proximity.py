"""Tests for sr_proximity gate (Reactive S/R check)."""
from backend.v9.systems.five_min.sr_proximity import check_proximity


def test_long_near_pdl():
    levels = {'pdh': 5270.0, 'pdl': 5240.0, 'vah': 5260.0, 'val': 5245.0, 'ibh': None, 'ibl': 5242.0}
    is_near, name = check_proximity(5240.5, 'LONG', levels=levels, tolerance_ticks=5)
    assert is_near is True
    assert name == 'PDL'


def test_long_far_from_support():
    levels = {'pdh': 5270.0, 'pdl': 5240.0, 'vah': 5260.0, 'val': 5245.0, 'ibh': None, 'ibl': 5242.0}
    is_near, name = check_proximity(5255.0, 'LONG', levels=levels, tolerance_ticks=5)
    assert is_near is False
    assert name is None


def test_short_near_vah():
    levels = {'pdh': 5270.0, 'pdl': 5240.0, 'vah': 5260.0, 'val': 5245.0, 'ibh': 5265.0, 'ibl': None}
    is_near, name = check_proximity(5260.5, 'SHORT', levels=levels, tolerance_ticks=5)
    assert is_near is True
    assert name == 'VAH'


def test_levels_missing():
    is_near, name = check_proximity(5250.0, 'LONG', levels=None)
    assert is_near is False
    assert name is None
