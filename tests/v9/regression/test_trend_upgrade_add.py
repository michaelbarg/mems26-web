"""TREND_UPGRADE_ADD_V1 — mutation contract (built 28.08 night, DEFAULT OFF).

Ruling (מייקל 27.08 19:55 §12 + doctrine ~19:10): when the PUBLISHED label
upgrades into Trend_* while a live position rides WITH the direction — child
+2 (param 1/2) through the SCALE_IN mechanism (own bracket, child stop at
parent BE). Enabling requires cowork+Michael — these tests pin that OFF is
inert and that the pure decision flips ONLY on the ruled facts.
"""
from __future__ import annotations

import inspect

import pytest

from backend.v9.services.trade_manager.scale_in import trend_upgrade_add


def _dec(**kw):
    base = dict(label_now="Trend_Normal", label_prev="Variation",
                position_direction="LONG", dir_bias="UP",
                already_added=False, add_contracts=2)
    base.update(kw)
    return trend_upgrade_add(**base)


# ─────────────────────────── the edge fires ──────────────────────────────────

def test_upgrade_edge_with_direction_adds():
    d = _dec()
    assert d is not None and d["add_contracts"] == 2
    assert "Variation→Trend_Normal" in d["reason"]


def test_short_with_down_bias_adds():
    d = _dec(label_now="Trend_DD", position_direction="SHORT", dir_bias="DOWN")
    assert d is not None


@pytest.mark.parametrize("n,expect", [(1, 1), (2, 2), (5, 2), (0, 1)])
def test_add_param_clamped_to_ruled_1_or_2(n, expect):
    d = _dec(add_contracts=n)
    assert d is not None and d["add_contracts"] == expect


# ─────────────────────────── the edge does NOT fire ──────────────────────────

def test_already_trend_is_not_an_edge():
    assert _dec(label_prev="Trend_DD") is None


@pytest.mark.parametrize("prev", [None, "", "UNKNOWN", "FORMING", "None"])
def test_first_label_or_unknown_prev_is_not_an_upgrade(prev):
    """A restart / first label of the day must never trigger an add."""
    assert _dec(label_prev=prev) is None


def test_downgrade_never_adds():
    assert _dec(label_now="Variation", label_prev="Trend_Normal") is None


def test_counter_trend_position_never_adds():
    assert _dec(position_direction="SHORT", dir_bias="UP") is None
    assert _dec(position_direction="LONG", dir_bias="DOWN") is None


@pytest.mark.parametrize("bias", [None, "", "NEUTRAL", "SIDEWAYS"])
def test_undetermined_bias_is_not_an_add_signal(bias):
    """Absence of knowledge is not an add signal (binary doctrine)."""
    assert _dec(dir_bias=bias) is None


def test_undetermined_position_direction_never_adds():
    assert _dec(position_direction=None) is None


def test_once_per_position():
    assert _dec(already_added=True) is None


# ─────────────────────── OFF-is-inert + wiring contract ──────────────────────

def test_flag_default_off_and_guards_present():
    from backend.v9.services.trade_manager import bar_level_detector as bld
    src = inspect.getsource(bld.BarLevelDetector._maybe_trend_upgrade_add)
    assert 'getenv("TREND_UPGRADE_ADD_V1", "0")' in src, "default must be OFF"
    # ruled safety rails, in order: sierra sanity → ceiling 6 → margin precheck
    # → parent marked BEFORE the command is built
    i_acct = src.index("_sierra_state_qty")
    i_ceil = src.index("> 6")
    i_mp = src.index("SCALE_IN_MARGIN_PRECHECK_V1")
    i_mark = src.index('q2["trend_upgrade_added"] = True')
    i_cmd = src.index("command_from_setup")
    assert i_acct < i_ceil < i_mp < i_mark < i_cmd
    assert "stop = float(trade.entry_price)" in src, "child stop must be parent BE"


def test_hook_is_failsafe_wrapped():
    from backend.v9.services.trade_manager import bar_level_detector as bld
    src = inspect.getsource(bld)
    at = src.index("_maybe_trend_upgrade_add(trade, bar_high, bar_low)")
    ctx = src[at - 300:at]
    assert "try:" in ctx, "the hook must never be able to break bar processing"


def test_ruled_flags_row_exists():
    import os
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    txt = open(os.path.join(root, "config", "RULED_FLAGS.yaml"),
               encoding="utf-8").read()
    line = [l for l in txt.splitlines() if "TREND_UPGRADE_ADD_V1" in l]
    assert line, "built flag with no RULED_FLAGS row will silently drift"
    assert 'expected: "unset_or_0"' in line[0]
