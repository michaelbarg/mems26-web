"""T-160: close_trade without exit_price → UNPRICED (no phantom P&L).

The phantom_reconcile path closes trades that Sierra declared flat, but
without an exit_price. The old code fell through to target-based P&L
calculation, crediting phantom wins ($406.25 across 11 trades).

PNL_REQUIRES_EXIT_PRICE_V1: a close without exit_price on demo/live
sets pnl_usd=NULL and pnl_status='UNPRICED'. Rule 1.
"""
import os
import types
from unittest.mock import patch, MagicMock

import pytest


def _mk_trade(tid=900, direction="SHORT", entry_price=7750.0, stop=7765.0,
              mode="live", state="FILLED", t1_hit_ts=None):
    t = types.SimpleNamespace()
    t.id = tid
    t.mode = mode
    t.state = state
    t.direction = direction
    t.entry_price = entry_price
    t.stop = stop
    t.exit_price = None
    t.exit_ts = None
    t.exit_reason = None
    t.outcome = None
    t.pnl_usd = None
    t.pnl_r = None
    t.t1 = 7740.0
    t.t2 = 7730.0
    t.t3 = 7720.0
    t.t1_hit_ts = t1_hit_ts
    t.t2_hit_ts = None
    t.t3_hit_ts = None
    t.quality = {"contracts": 3}
    t.cross_context = []
    return t


class TestT160:
    """PNL_REQUIRES_EXIT_PRICE_V1: unpriced closes."""

    def test_phantom_close_without_exit_price_is_unpriced(self):
        """Flag ON + no exit_price → pnl_usd=None, outcome=UNPRICED."""
        from backend.v9.services.trade_manager.manager import TradeManager

        trade = _mk_trade()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = trade
        db.flush = MagicMock()

        tm = TradeManager(db=db)
        # Pre-create the state machine
        from backend.v9.services.trade_manager.state_machine import (
            TradeStateMachine, TradeState)
        tm._machines[trade.id] = TradeStateMachine(TradeState.FILLED)

        with patch.dict(os.environ, {"PNL_REQUIRES_EXIT_PRICE_V1": "1"}):
            tm.close_trade(trade.id, reason="phantom_reconcile")

        assert trade.pnl_usd is None, \
            f"pnl should be NULL, got {trade.pnl_usd}"
        assert trade.outcome == "UNPRICED", \
            f"outcome should be UNPRICED, got {trade.outcome}"
        q = trade.quality if isinstance(trade.quality, dict) else {}
        assert q.get("pnl_status") == "UNPRICED"

    def test_close_with_exit_price_has_pnl(self):
        """Flag ON + exit_price provided → normal P&L calculation."""
        from backend.v9.services.trade_manager.manager import TradeManager

        trade = _mk_trade()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = trade
        db.flush = MagicMock()

        tm = TradeManager(db=db)
        from backend.v9.services.trade_manager.state_machine import (
            TradeStateMachine, TradeState)
        tm._machines[trade.id] = TradeStateMachine(TradeState.FILLED)

        with patch.dict(os.environ, {"PNL_REQUIRES_EXIT_PRICE_V1": "1"}):
            tm.close_trade(trade.id, reason="STOP_HIT", exit_price=7760.0)

        assert trade.pnl_usd is not None, "With exit_price, pnl should be calculated"
        assert trade.exit_price == 7760.0

    def test_flag_off_preserves_legacy_behavior(self):
        """Flag OFF → phantom close still calculates P&L (legacy)."""
        from backend.v9.services.trade_manager.manager import TradeManager

        trade = _mk_trade(t1_hit_ts="2026-08-28T18:00:00")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = trade
        db.flush = MagicMock()

        tm = TradeManager(db=db)
        from backend.v9.services.trade_manager.state_machine import (
            TradeStateMachine, TradeState)
        tm._machines[trade.id] = TradeStateMachine(TradeState.FILLED)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PNL_REQUIRES_EXIT_PRICE_V1", None)
            tm.close_trade(trade.id, reason="phantom_reconcile")

        # Legacy: pnl IS calculated (the bug, but preserved when flag OFF)
        assert trade.pnl_usd is not None, "Flag OFF → legacy P&L (phantom wins)"

    def test_shadow_trades_exempt(self):
        """Shadow trades are exempt — they never have Sierra fills."""
        from backend.v9.services.trade_manager.manager import TradeManager

        trade = _mk_trade(mode="shadow")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = trade
        db.flush = MagicMock()

        tm = TradeManager(db=db)
        from backend.v9.services.trade_manager.state_machine import (
            TradeStateMachine, TradeState)
        tm._machines[trade.id] = TradeStateMachine(TradeState.FILLED)

        with patch.dict(os.environ, {"PNL_REQUIRES_EXIT_PRICE_V1": "1"}):
            tm.close_trade(trade.id, reason="bar_close")

        # Shadow exempt: pnl calculated normally
        assert trade.pnl_usd is not None, "Shadow trades exempt from T-160"
