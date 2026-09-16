"""T-368: System 6 stuck_trade → BE when T0 already filled.

Michael 16.09: "תבדוק למה מערכת 6 לא מתפקדת" — 70 stuck_trade ALERTs
with zero actions. When stuck + T0 filled + stop far from BE →
MODIFY_STOP to BE. Never widens, never FLATTEN, never op=EXIT.
"""

import os
import pytest
from unittest.mock import patch

from backend.v9.systems.system6_supervisor import (
    diagnose_trade, Issue, AUTO, ALERT,
)


def _base_trade(direction="LONG", entry=7700.0, stop=7690.0):
    return {
        "direction": direction,
        "entry_price": entry,
        "stop": stop,
        "contracts": 2,
    }


class TestS6StuckToBe:
    """T-368 stuck_trade → BE tests."""

    @patch.dict(os.environ, {"S6_STUCK_TO_BE_V1": "1"})
    def test_stuck_plus_t0_modifies_stop_to_be(self):
        """Stuck + T0 filled → MODIFY_STOP to BE."""
        trade = _base_trade("LONG", 7700.0, 7690.0)
        report = diagnose_trade(
            trade=trade, atr=5.0,
            bars_since_entry=15, progress_pts=1.0,
            t0_hit=True,
        )
        auto = [i for i in report.issues if i.code == "stuck_trade_to_be"]
        assert len(auto) == 1
        assert auto[0].action == AUTO
        assert auto[0].correction["op"] == "MODIFY_STOP"
        assert auto[0].correction["price"] == 7700.0  # BE = entry

    @patch.dict(os.environ, {"S6_STUCK_TO_BE_V1": "1"})
    def test_stuck_without_t0_no_action(self):
        """Stuck but T0 NOT filled → no AUTO action (only ALERT)."""
        trade = _base_trade("LONG", 7700.0, 7690.0)
        report = diagnose_trade(
            trade=trade, atr=5.0,
            bars_since_entry=15, progress_pts=1.0,
            t0_hit=False,
        )
        auto = [i for i in report.issues if i.code == "stuck_trade_to_be"]
        assert len(auto) == 0
        # The ALERT should still be there
        alerts = [i for i in report.issues if i.code == "stuck_trade"]
        assert len(alerts) == 1

    @patch.dict(os.environ, {"S6_STUCK_TO_BE_V1": "1"})
    def test_stop_already_at_be_no_action(self):
        """Stop already at BE → no action."""
        trade = _base_trade("LONG", 7700.0, 7700.0)  # stop == entry
        report = diagnose_trade(
            trade=trade, atr=5.0,
            bars_since_entry=15, progress_pts=1.0,
            t0_hit=True,
        )
        auto = [i for i in report.issues if i.code == "stuck_trade_to_be"]
        assert len(auto) == 0

    @patch.dict(os.environ, {"S6_STUCK_TO_BE_V1": "1"})
    def test_idempotent_second_call_no_action(self):
        """Second call on same trade → no duplicate action."""
        trade = _base_trade("LONG", 7700.0, 7690.0)
        # First call
        report1 = diagnose_trade(
            trade=trade, atr=5.0,
            bars_since_entry=15, progress_pts=1.0,
            t0_hit=True,
        )
        auto1 = [i for i in report1.issues if i.code == "stuck_trade_to_be"]
        assert len(auto1) == 1
        # Second call — _s6_stuck_be_done is set
        report2 = diagnose_trade(
            trade=trade, atr=5.0,
            bars_since_entry=15, progress_pts=1.0,
            t0_hit=True,
        )
        auto2 = [i for i in report2.issues if i.code == "stuck_trade_to_be"]
        assert len(auto2) == 0

    @patch.dict(os.environ, {"S6_STUCK_TO_BE_V1": "1"})
    def test_never_widen_short(self):
        """SHORT: stop below entry (already better than BE) → no widen."""
        trade = _base_trade("SHORT", 7700.0, 7695.0)  # stop closer than entry
        report = diagnose_trade(
            trade=trade, atr=5.0,
            bars_since_entry=15, progress_pts=1.0,
            t0_hit=True,
        )
        auto = [i for i in report.issues if i.code == "stuck_trade_to_be"]
        # stop is 7695 which is BELOW entry 7700 for SHORT → already better than BE
        assert len(auto) == 0

    @patch.dict(os.environ, {"S6_STUCK_TO_BE_V1": "1"})
    def test_short_stuck_moves_to_be(self):
        """SHORT: stop above entry (worse than BE) → MODIFY_STOP to BE."""
        trade = _base_trade("SHORT", 7700.0, 7710.0)  # stop above entry
        report = diagnose_trade(
            trade=trade, atr=5.0,
            bars_since_entry=15, progress_pts=1.0,
            t0_hit=True,
        )
        auto = [i for i in report.issues if i.code == "stuck_trade_to_be"]
        assert len(auto) == 1
        assert auto[0].correction["price"] == 7700.0  # BE = entry

    @patch.dict(os.environ, {"S6_STUCK_TO_BE_V1": "0"})
    def test_flag_off_no_action(self):
        """Flag off → no AUTO action even when all conditions met."""
        trade = _base_trade("LONG", 7700.0, 7690.0)
        report = diagnose_trade(
            trade=trade, atr=5.0,
            bars_since_entry=15, progress_pts=1.0,
            t0_hit=True,
        )
        auto = [i for i in report.issues if i.code == "stuck_trade_to_be"]
        assert len(auto) == 0

    def test_no_flatten_no_exit_in_code(self):
        """Mutation: the stuck_to_be code never emits FLATTEN or op=EXIT."""
        import inspect
        from backend.v9.systems import system6_supervisor
        source = inspect.getsource(system6_supervisor.diagnose_trade)
        # Find the stuck_trade_to_be block
        idx = source.find("stuck_trade_to_be")
        assert idx > 0
        block = source[idx:idx + 500]
        assert "FLATTEN" not in block
        assert "op=EXIT" not in block
        assert "EXIT" not in block.split("MODIFY_STOP")[0]  # no EXIT before MODIFY_STOP
