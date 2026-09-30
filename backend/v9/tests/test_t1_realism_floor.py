"""T-518 (30.09) — T1_REALISM_FLOOR_R_V1: the realism ceiling may not cut T1 below r×R. Pure tests."""
import os
import pytest
from backend.v9.systems.structural_targets import apply_t1_realism_floor, t1_realism_floor_r


def test_off_is_identity(monkeypatch):
    monkeypatch.delenv("T1_REALISM_FLOOR_R_V1", raising=False)
    assert t1_realism_floor_r() == 0.0
    assert apply_t1_realism_floor("LONG", 7793.25, 7782.5, 7810.0, 7795.75) == 7795.75


def test_long_floor_lifts_capped_t1_to_one_r():
    # 21.09 #2029: entry 7793.25, stop 7782.5 (R=10.75), structural t1 7810, realism cut it to 7795.75 (2.5 pts)
    t1 = apply_t1_realism_floor("LONG", 7793.25, 7782.5, 7810.0, 7795.75, r=1.0)
    assert t1 == 7804.0          # entry + 10.75, tick-aligned


def test_short_floor_symmetric():
    t1 = apply_t1_realism_floor("SHORT", 7700.0, 7708.0, 7680.0, 7698.0, r=1.5)
    assert t1 == 7688.0          # entry − 12


def test_never_beyond_structural_t1():
    # structural t1 is only 0.8R away: the floor cannot push past it (tighten-only stays tighten-only)
    t1 = apply_t1_realism_floor("LONG", 7800.0, 7790.0, 7806.0, 7801.0, r=1.5)
    assert t1 == 7806.0


def test_capped_already_beyond_floor_unchanged():
    t1 = apply_t1_realism_floor("LONG", 7800.0, 7790.0, 7830.0, 7822.0, r=1.0)
    assert t1 == 7822.0


def test_no_stop_or_bad_r_is_identity():
    assert apply_t1_realism_floor("LONG", 7800.0, None, 7830.0, 7801.0, r=1.0) == 7801.0
    assert apply_t1_realism_floor("LONG", 7800.0, 7800.0, 7830.0, 7801.0, r=1.0) == 7801.0
    assert apply_t1_realism_floor("LONG", 7800.0, 7790.0, 7830.0, 7801.0, r=0) == 7801.0


def test_env_value_read(monkeypatch):
    monkeypatch.setenv("T1_REALISM_FLOOR_R_V1", "1.5")
    assert t1_realism_floor_r() == 1.5
    assert apply_t1_realism_floor("LONG", 7800.0, 7790.0, 7830.0, 7801.0) == 7815.0
