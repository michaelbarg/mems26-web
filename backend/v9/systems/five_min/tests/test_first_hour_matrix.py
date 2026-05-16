"""Tests for First Hour Matrix (Tree V3.3 §Stage C)."""
from backend.v9.systems.five_min.first_hour_matrix import lookup_matrix


def test_open_drive_long_full_size():
    mod, ts = lookup_matrix("OPEN_DRIVE", "LONG")
    assert mod == 1.0
    assert ts is None


def test_open_drive_short_skip():
    mod, ts = lookup_matrix("OPEN_DRIVE", "SHORT")
    assert mod == 0.0  # skip counter-drive


def test_open_auction_in_conservative():
    mod, ts = lookup_matrix("OPEN_AUCTION_IN", "LONG")
    assert mod == 0.5
    assert ts == 30


def test_unknown_opening_type_default():
    mod, ts = lookup_matrix(None, "LONG")
    assert mod == 0.5
    assert ts == 45


def test_open_test_drive_short_aligned():
    mod, ts = lookup_matrix("OPEN_TEST_DRIVE", "SHORT")
    assert mod == 1.0  # aligned with reversal
