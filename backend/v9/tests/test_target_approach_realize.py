"""Tests for S6_TARGET_APPROACH_REALIZE_V1 — discretionary target realization.

Key invariants:
1. Only fires when flag ON
2. Requires proximity (≤1pt) + K bars + rejection signature
3. Never triggers on a filled target
4. CCI reversal and delta flip are independent rejection sources
"""

import os
import pytest
from unittest.mock import patch

from backend.v9.systems.target_approach_realize import (
    should_realize, ApproachState, APPROACH_DIST_PTS,
)


def _trade(direction="LONG", entry=7600.0, t1=7606.0, t2=7612.0, t3=7620.0,
           t1_hit=False, t2_hit=False):
    return {
        "direction": direction,
        "entry_price": entry,
        "t1": t1, "t2": t2, "t3": t3,
        "t1_hit_ts": "2026-08-05T14:00:00" if t1_hit else None,
        "t2_hit_ts": "2026-08-05T15:00:00" if t2_hit else None,
    }


class TestFlagGating:
    def test_off_by_default(self):
        """Flag OFF → never triggers."""
        os.environ.pop("S6_TARGET_APPROACH_REALIZE_V1", None)
        ok, _, _ = should_realize(
            trade=_trade(), bar_high=7605.5, bar_low=7603.0, bar_close=7604.0,
        )
        assert not ok

    def test_on_when_flag_set(self, monkeypatch):
        """Flag ON → can trigger."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        # First bar near T1 — not enough bars yet
        ok, _, state = should_realize(
            trade=_trade(), bar_high=7605.5, bar_low=7603.0, bar_close=7604.0,
        )
        assert not ok
        assert state.bars_near == 1


class TestProximityDetection:
    def test_long_near_t1(self, monkeypatch):
        """LONG: bar_high within 1pt of T1 counts as near."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        ok, _, state = should_realize(
            trade=_trade(t1=7606.0),
            bar_high=7605.5, bar_low=7603.0, bar_close=7604.0,
        )
        assert state.bars_near == 1

    def test_short_near_t1(self, monkeypatch):
        """SHORT: bar_low within 1pt of T1 counts as near."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        ok, _, state = should_realize(
            trade=_trade(direction="SHORT", entry=7600.0, t1=7594.0),
            bar_high=7597.0, bar_low=7594.5, bar_close=7596.0,
        )
        assert state.bars_near == 1

    def test_not_near_no_count(self, monkeypatch):
        """Price far from target → no approach count."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        ok, _, state = should_realize(
            trade=_trade(t1=7606.0),
            bar_high=7603.0, bar_low=7600.0, bar_close=7602.0,
        )
        assert state.bars_near == 0


class TestRejectionAndTrigger:
    def test_close_away_triggers(self, monkeypatch):
        """2 bars near + close away from target → trigger."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        trade = _trade(t1=7606.0)

        # Bar 1: near T1
        _, _, state = should_realize(
            trade=trade, bar_high=7605.5, bar_low=7604.0, bar_close=7605.0,
            approach_state=None,
        )
        # Bar 2: near T1 + close away
        ok, reason, state = should_realize(
            trade=trade, bar_high=7605.5, bar_low=7603.0, bar_close=7603.0,
            approach_state=state,
        )
        assert ok, "Should trigger on close_away after 2 bars near"
        assert "close_away" in reason

    def test_cci_reversal_triggers(self, monkeypatch):
        """2 bars near + CCI sign change → trigger."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        trade = _trade(t1=7606.0)

        _, _, state = should_realize(
            trade=trade, bar_high=7605.5, bar_low=7604.0, bar_close=7605.2,
            cci_current=80.0, cci_previous=90.0,
        )
        ok, reason, state = should_realize(
            trade=trade, bar_high=7605.8, bar_low=7604.5, bar_close=7605.5,
            approach_state=state,
            cci_current=-10.0, cci_previous=80.0,
        )
        assert ok
        assert "cci_reversal" in reason

    def test_delta_flip_triggers(self, monkeypatch):
        """2 bars near + delta direction flip → trigger."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        trade = _trade(t1=7606.0)

        _, _, state = should_realize(
            trade=trade, bar_high=7605.5, bar_low=7604.0, bar_close=7605.2,
            delta_direction="UP", delta_direction_prev="UP",
        )
        ok, reason, state = should_realize(
            trade=trade, bar_high=7605.8, bar_low=7603.0, bar_close=7604.0,
            approach_state=state,
            delta_direction="DOWN", delta_direction_prev="UP",
        )
        assert ok
        assert "delta_flip" in reason

    def test_no_rejection_no_trigger(self, monkeypatch):
        """2 bars near but NO rejection signature → no trigger."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        trade = _trade(t1=7606.0)

        _, _, state = should_realize(
            trade=trade, bar_high=7605.5, bar_low=7604.5, bar_close=7605.3,
        )
        # Bar 2: near but close still near target (no rejection)
        ok, _, state = should_realize(
            trade=trade, bar_high=7605.8, bar_low=7605.0, bar_close=7605.5,
            approach_state=state,
        )
        assert not ok, "No rejection → should NOT trigger"


class TestTargetSelection:
    def test_pending_t1_before_hit(self, monkeypatch):
        """Before T1 hit, approach checks T1."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        _, _, state = should_realize(
            trade=_trade(t1=7606.0, t1_hit=False),
            bar_high=7605.5, bar_low=7604.0, bar_close=7604.0,
        )
        assert state.target_field == "t1"

    def test_pending_t2_after_t1_hit(self, monkeypatch):
        """After T1 hit, approach checks T2."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        _, _, state = should_realize(
            trade=_trade(t2=7612.0, t1_hit=True),
            bar_high=7611.5, bar_low=7610.0, bar_close=7610.0,
        )
        assert state.target_field == "t2"

    def test_pending_t3_after_t2_hit(self, monkeypatch):
        """After T2 hit, approach checks T3."""
        monkeypatch.setenv("S6_TARGET_APPROACH_REALIZE_V1", "1")
        _, _, state = should_realize(
            trade=_trade(t3=7620.0, t1_hit=True, t2_hit=True),
            bar_high=7619.5, bar_low=7618.0, bar_close=7618.0,
        )
        assert state.target_field == "t3"
