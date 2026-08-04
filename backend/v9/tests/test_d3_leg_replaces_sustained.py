"""D3 — LEG_REPLACES_SUSTAINED_V1 tests (2026-08-04).

Four test cases from this week:
1. 07-31 19:15-20:20: UP leg active, dir_sustained=DOWN → leg overrides → LONG passes
2. 07-29 afternoon: no leg, dir_sustained=UP → cont_trend blocks SHORT (correct)
3. 07-30 evening: leg=UP, setup=SHORT → against leg → still blocked
4. No leg, no sustained → NEUTRAL → blocks CONT (correct)
"""
import pytest


def _should_pass_cont_trend(set_dir, sustained, leg_dir, flag_on):
    """Pure logic: does the setup pass cont_trend_filter?

    set_dir: "UP"/"DOWN" (mapped from LONG/SHORT)
    sustained: "UP"/"DOWN"/"NEUTRAL" (from dir_sustained or leg override)
    """
    effective_sustained = sustained
    if flag_on and leg_dir in ("UP", "DOWN"):
        effective_sustained = leg_dir
    return effective_sustained == set_dir


def test_case1_leg_overrides_stale_sustained():
    """07-31: UP leg active, dir_sustained=DOWN → leg wins → LONG passes."""
    assert _should_pass_cont_trend("UP", "DOWN", "UP", flag_on=True)


def test_case1_without_flag_blocked():
    """Same case but flag OFF → dir_sustained=DOWN blocks LONG."""
    assert not _should_pass_cont_trend("UP", "DOWN", "UP", flag_on=False)


def test_case2_no_leg_sustained_blocks():
    """07-29: no leg, sustained=UP → SHORT blocked (correct)."""
    assert not _should_pass_cont_trend("DOWN", "UP", None, flag_on=True)


def test_case3_against_leg_blocked():
    """07-30: leg=UP, setup=SHORT → still blocked (against the leg)."""
    assert not _should_pass_cont_trend("DOWN", "NEUTRAL", "UP", flag_on=True)


def test_case4_no_leg_no_sustained_blocked():
    """No leg, sustained=NEUTRAL → blocks CONT."""
    assert not _should_pass_cont_trend("UP", "NEUTRAL", None, flag_on=True)
