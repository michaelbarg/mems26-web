"""SCALE_IN_V1 — reinforce a winner (Michael ruling 2026-08-13). Pure-function tests.

The decision is ADDITIVE: it can only fire on an already-open, T1-banked, with-trend
trade whose direction keeps going. It never gates/blocks an entry.
"""
from __future__ import annotations

from backend.v9.services.trade_manager.scale_in import (
    should_scale_in, ScaleInCfg, ScaleInDecision,
)

CFG = ScaleInCfg(min_profit_pts=6.0, add_contracts=2, max_total_contracts=8)


def test_fires_on_winning_with_trend_short():
    """SHORT past entry by ≥6pt, T1 banked, down-trend, not yet scaled → reinforce."""
    d = should_scale_in(direction="SHORT", entry_price=7460.0, t1_hit=True,
                        already_scaled=False, n_contracts_open=2,
                        bar_high=7455.0, bar_low=7450.0, dir_bias="DOWN", cfg=CFG)
    assert isinstance(d, ScaleInDecision)
    assert d.add_contracts == 2 and d.direction == "SHORT"
    assert d.stop == 7460.0  # add-on stop = parent entry (BE)


def test_fires_on_winning_with_trend_long():
    d = should_scale_in(direction="LONG", entry_price=7400.0, t1_hit=True,
                        already_scaled=False, n_contracts_open=2,
                        bar_high=7410.0, bar_low=7405.0, dir_bias="UP", cfg=CFG)
    assert d is not None and d.stop == 7400.0


def test_no_fire_before_t1():
    """Never add before the entry proved itself (T1 not banked)."""
    d = should_scale_in(direction="SHORT", entry_price=7460.0, t1_hit=False,
                        already_scaled=False, n_contracts_open=2,
                        bar_high=7455.0, bar_low=7450.0, dir_bias="DOWN", cfg=CFG)
    assert d is None


def test_no_fire_once_scaled():
    """Once per parent."""
    d = should_scale_in(direction="SHORT", entry_price=7460.0, t1_hit=True,
                        already_scaled=True, n_contracts_open=2,
                        bar_high=7455.0, bar_low=7450.0, dir_bias="DOWN", cfg=CFG)
    assert d is None


def test_no_fire_counter_trend():
    """Never reinforce against the day trend (SHORT while bias is UP)."""
    d = should_scale_in(direction="SHORT", entry_price=7460.0, t1_hit=True,
                        already_scaled=False, n_contracts_open=2,
                        bar_high=7455.0, bar_low=7450.0, dir_bias="UP", cfg=CFG)
    assert d is None


def test_no_fire_insufficient_profit():
    """Price hasn't run far enough past entry (proof the move has legs)."""
    d = should_scale_in(direction="SHORT", entry_price=7460.0, t1_hit=True,
                        already_scaled=False, n_contracts_open=2,
                        bar_high=7459.0, bar_low=7457.0, dir_bias="DOWN", cfg=CFG)
    assert d is None  # only 3pt past entry < 6


def test_no_fire_over_cap():
    """Parent + add-on must not exceed max_total_contracts."""
    d = should_scale_in(direction="SHORT", entry_price=7460.0, t1_hit=True,
                        already_scaled=False, n_contracts_open=7,
                        bar_high=7450.0, bar_low=7448.0, dir_bias="DOWN", cfg=CFG)
    assert d is None  # 7 + 2 > 8


def test_no_fire_nothing_open():
    d = should_scale_in(direction="SHORT", entry_price=7460.0, t1_hit=True,
                        already_scaled=False, n_contracts_open=0,
                        bar_high=7450.0, bar_low=7448.0, dir_bias="DOWN", cfg=CFG)
    assert d is None


def test_unknown_dir_bias_allowed_when_profit_ok():
    """dir_bias unknown → with-trend check is skipped (fail-open on the trend side),
    but profit + T1 still required."""
    d = should_scale_in(direction="SHORT", entry_price=7460.0, t1_hit=True,
                        already_scaled=False, n_contracts_open=2,
                        bar_high=7453.0, bar_low=7450.0, dir_bias=None, cfg=CFG)
    assert d is not None
