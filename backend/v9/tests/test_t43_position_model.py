"""T-43 Position model — stops from avg_price + contract validation + slot release.

Michael 28.08 19:30: "Sierra manages one averaged position; the TM thinks there
are two separate trades (5 contracts vs 3). The stops sit ABOVE the average —
a loss while the position is in profit."

Three properties:
  (a) Two live same-direction trades → stops computed from sierra.avg_price.
  (b) T1 partial → slot stays occupied → second entry at 19:01 is blocked.
  (c) Contract mismatch → entries blocked until resolved.

Test data from the live incident: #851 SHORT 3 @7750, #853 SHORT 2 @7736.
Sierra avg_price=7740.83, position_qty=-3 (after T1 hits).
"""
import json
import os
import time
import types
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── fakes ───────────────────────────────────────────────────────────────────

def _mk_trade(direction="SHORT", contracts=3, mode="live", tid=851,
              state="PARTIAL", entry_price=7750.0, stop=7745.50,
              t1_hit_ts=None):
    """V9Trade stand-in matching the 28.08 incident."""
    t = types.SimpleNamespace()
    t.id = tid
    t.mode = mode
    t.state = state
    t.direction = direction
    t.entry_price = entry_price
    t.stop = stop
    t.quality = {"contracts": contracts}
    t.t1_hit_ts = t1_hit_ts
    t.t2_hit_ts = None
    t.t3_hit_ts = None
    t.t4_hit_ts = None
    t.cross_context = []
    return t


def _write_sierra_state(tmp, qty, avg_price, working_orders=0):
    """Write a fresh sierra_state.json to tmp."""
    state = {
        "ts": int(time.time()),
        "position_qty": qty,
        "avg_price": avg_price,
        "working_orders": working_orders,
        "orders": [],
    }
    p = Path(tmp) / "sierra_state.json"
    p.write_text(json.dumps(state))
    return p


# ── T-43a: position reference price uses avg_price ─────────────────────────

class TestPositionReferencePrice:
    """When >1 same-direction trade is live, stop reference = sierra.avg_price."""

    def test_single_trade_uses_entry_price(self):
        """One trade → reference = trade.entry_price (no averaging)."""
        from backend.v9.services.trade_manager.manager import _position_reference_price

        trade = _mk_trade(entry_price=7750.0)
        # Mock DB session returning only this one trade
        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        query.all.return_value = [trade]

        ref = _position_reference_price(trade, db)
        assert ref == 7750.0, f"Single trade should use entry_price, got {ref}"

    def test_two_trades_uses_sierra_avg(self):
        """Two same-direction trades → reference = sierra.avg_price."""
        from backend.v9.services.trade_manager.manager import _position_reference_price

        trade1 = _mk_trade(tid=851, entry_price=7750.0, contracts=3)
        trade2 = _mk_trade(tid=853, entry_price=7736.0, contracts=2)

        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        query.all.return_value = [trade1, trade2]

        with patch("backend.v9.services.sierra_position_reconciler._sierra_state_avg_price",
                   return_value=7740.83):
            ref = _position_reference_price(trade1, db)
        assert abs(ref - 7740.83) < 0.01, \
            f"Two trades should use sierra avg_price=7740.83, got {ref}"

    def test_two_trades_sierra_stale_uses_weighted_avg(self):
        """Two trades, sierra stale → weighted average of TM entries."""
        from backend.v9.services.trade_manager.manager import _position_reference_price

        trade1 = _mk_trade(tid=851, entry_price=7750.0, contracts=3)
        trade2 = _mk_trade(tid=853, entry_price=7736.0, contracts=2)

        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        query.all.return_value = [trade1, trade2]

        with patch("backend.v9.services.sierra_position_reconciler._sierra_state_avg_price",
                   return_value=None):
            ref = _position_reference_price(trade1, db)
        # Weighted: (7750*3 + 7736*2) / 5 = (23250 + 15472) / 5 = 7744.40
        expected = (7750.0 * 3 + 7736.0 * 2) / 5
        assert abs(ref - expected) < 0.01, \
            f"Should use weighted avg={expected:.2f}, got {ref}"

    def test_stops_from_avg_not_entry(self):
        """28.08 replay: with avg_price=7740.83, BE stops must be BELOW avg
        (for SHORT), not above it (the bug: stops at 7745.50 from entry 7750)."""
        from backend.v9.services.trade_manager.manager import _position_reference_price

        trade = _mk_trade(tid=851, entry_price=7750.0, contracts=3,
                          direction="SHORT")

        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query
        # Two trades on same side
        trade2 = _mk_trade(tid=853, entry_price=7736.0, contracts=2,
                           direction="SHORT")
        query.all.return_value = [trade, trade2]

        with patch("backend.v9.services.sierra_position_reconciler._sierra_state_avg_price",
                   return_value=7740.83):
            ref = _position_reference_price(trade, db)

        # BE for SHORT = ref - tick = 7740.83 - 0.25 = 7740.58
        # This is BELOW avg_price — correct (trade is in profit)
        # The old bug had BE at 7750 + tick = 7745.50 — ABOVE avg
        assert ref < 7745.0, \
            (f"Reference price {ref} must be below the broken stops (7745.50). "
             f"The position avg is 7740.83 — stops must be computed from there.")


# ── T-43b: contract mismatch blocks entries (behind POSITION_MISMATCH_BLOCK_V1) ──

class TestContractMismatchBlock:
    """Σ TM.contracts ≠ |position_qty| → entries blocked (when flag ON)."""

    def test_mismatch_sets_block_when_enabled(self):
        """reconcile_position on mismatch with flag ON → blocks entry."""
        from backend.v9.services import sierra_position_reconciler as spr

        spr._position_mismatch_block = False
        spr._phantom_flat_streak = 0

        trade = _mk_trade(contracts=3, direction="SHORT")
        tm = MagicMock()
        tm.get_active_trades.return_value = [trade]

        with patch.object(spr, "_sierra_state_qty", return_value=-5), \
             patch.object(spr, "_sierra_position_qty", return_value=None), \
             patch.object(spr, "_unprotected_contracts", return_value=None), \
             patch.dict(os.environ, {"POSITION_MISMATCH_BLOCK_V1": "1"}):
            ok, msg = spr.reconcile_position(tm)
            assert not ok, f"Should detect divergence, msg={msg}"
            # Check inside the patch.dict context (env var still set)
            assert spr.position_mismatch_blocks_entry(), \
                "Mismatch with flag ON should block entries"

    def test_mismatch_does_not_block_when_flag_off(self):
        """Default OFF: mismatch detected but entry not blocked."""
        from backend.v9.services import sierra_position_reconciler as spr

        spr._position_mismatch_block = False
        spr._phantom_flat_streak = 0

        trade = _mk_trade(contracts=3, direction="SHORT")
        tm = MagicMock()
        tm.get_active_trades.return_value = [trade]

        with patch.object(spr, "_sierra_state_qty", return_value=-5), \
             patch.object(spr, "_sierra_position_qty", return_value=None), \
             patch.object(spr, "_unprotected_contracts", return_value=None), \
             patch.dict(os.environ, {}, clear=False):
            # Ensure flag is OFF
            os.environ.pop("POSITION_MISMATCH_BLOCK_V1", None)
            ok, msg = spr.reconcile_position(tm)

        assert not ok, f"Should detect divergence, msg={msg}"
        assert not spr.position_mismatch_blocks_entry(), \
            "Mismatch with flag OFF must NOT block entries (cowork gate)"

    def test_match_clears_block(self):
        """When count matches again → block cleared."""
        from backend.v9.services import sierra_position_reconciler as spr

        spr._position_mismatch_block = True

        trade = _mk_trade(contracts=3, direction="SHORT")
        tm = MagicMock()
        tm.get_active_trades.return_value = [trade]

        with patch.object(spr, "_sierra_state_qty", return_value=-3), \
             patch.object(spr, "_sierra_position_qty", return_value=None), \
             patch.object(spr, "_unprotected_contracts", return_value=None):
            ok, msg = spr.reconcile_position(tm)

        assert ok, f"Should match, msg={msg}"
        assert not spr._position_mismatch_block, \
            "Match should clear the mismatch flag"

    def test_early_return_no_sierra_clears_block(self):
        """No sierra data → can't prove mismatch → block cleared."""
        from backend.v9.services import sierra_position_reconciler as spr

        spr._position_mismatch_block = True

        tm = MagicMock()
        with patch.object(spr, "_sierra_state_qty", return_value=None), \
             patch.object(spr, "_sierra_position_qty", return_value=None):
            ok, msg = spr.reconcile_position(tm)

        assert not spr._position_mismatch_block, \
            "No sierra data → block must be cleared (T-43b cleanup)"


# ── T-43c: slot freed only at position_qty==0 ─────────────────────────────
# These tests call the ACTUAL on_trade_close method on a real TradingGateway
# instance, not a logic duplicate.

class TestSlotRelease:
    """live_slot freed only when position_qty==0 AND zero protective orders."""

    def _make_gateway_instance(self):
        """Create a minimal TradingGateway with live_slot set, mocking
        only the parts that don't exist without a running backend."""
        from backend.v9.gateway.trading_gateway import TradingGateway

        # Patch the __init__ to avoid needing a real registry
        with patch.object(TradingGateway, '__init__', lambda self: None):
            gw = TradingGateway()
        gw.live_slot = {"trade_id": "851"}
        gw.demo_slot = None
        gw._daily_trades = 0
        gw._daily_pnl = 0.0
        gw._consecutive_losses = 0
        gw.cooldown = MagicMock()
        gw.ssv = MagicMock()
        gw._close_notified = set()
        gw.shadow_trades = []
        return gw

    def test_slot_retained_when_position_nonzero(self):
        """T1 partial: Sierra still holds -3 → on_trade_close keeps slot."""
        gw = self._make_gateway_instance()
        assert gw.live_slot is not None, "Pre: slot must be occupied"

        with patch("backend.v9.services.sierra_position_reconciler._sierra_state_qty",
                   return_value=-3), \
             patch("backend.v9.services.sierra_position_reconciler._sierra_state_working",
                   return_value=4), \
             patch("backend.v9.services.ntfy_notify.on_close", return_value=None):
            gw.on_trade_close({
                "trade_id": 851, "mode": "live",
                "pnl_usd": 58.75, "outcome": "T1_HIT",
                "direction": "SHORT",
            })

        assert gw.live_slot is not None, \
            "Slot must stay occupied when Sierra position_qty=-3 (T1 partial)"

    def test_slot_freed_when_position_zero(self):
        """Full close: Sierra position_qty=0 → on_trade_close frees slot."""
        gw = self._make_gateway_instance()

        with patch("backend.v9.services.sierra_position_reconciler._sierra_state_qty",
                   return_value=0), \
             patch("backend.v9.services.sierra_position_reconciler._sierra_state_working",
                   return_value=0), \
             patch("backend.v9.services.ntfy_notify.on_close", return_value=None):
            gw.on_trade_close({
                "trade_id": 851, "mode": "live",
                "pnl_usd": 200.0, "outcome": "T3_HIT",
                "direction": "SHORT",
            })

        assert gw.live_slot is None, \
            "Slot must be freed when Sierra position_qty=0 + working=0"

    def test_cancelled_always_frees_slot(self):
        """CANCELLED always frees immediately — no sierra check."""
        gw = self._make_gateway_instance()

        # Don't mock sierra — CANCELLED must bypass it entirely
        with patch("backend.v9.services.ntfy_notify.on_close", return_value=None):
            gw.on_trade_close({
                "trade_id": 851, "mode": "live",
                "pnl_usd": 0.0, "outcome": "CANCELLED",
                "direction": "SHORT",
            })

        assert gw.live_slot is None, \
            "CANCELLED must always free the slot (no position exists)"
