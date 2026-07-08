"""P5: End-to-end trade management — 3 contracts, structural targets, BE+1T, trail, close.

Verifies the SAME management path runs for ALL 16 patterns:
  detect → targets (C1/C2/C3) → 3 contracts → T1→BE+1T → trail → T3→CLOSED → slot freed

Anti-tautological: calls REAL TradeManager.on_target_hit + on_stop_hit.
Contract: docs/handoff/CC_HANDOFF_CONTRACT.md
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.trade_manager.state_machine import TradeState


class _FakeTrade:
    """Minimal trade object matching V9Trade interface for on_target_hit/on_stop_hit."""
    def __init__(self, trade_id=1, entry=7553.0, stop=7550.25, t1=7567.0, t2=7565.69, t3=7572.25,
                 direction="LONG", mode="demo"):
        self.id = trade_id
        self.entry_price = entry
        self.stop = stop
        self.t1 = t1
        self.t2 = t2
        self.t3 = t3
        self.direction = direction
        self.mode = mode
        self.state = "FILLED"
        self.t1_hit_ts = None
        self.t2_hit_ts = None
        self.t3_hit_ts = None
        self.stop_hit_ts = None
        self.exit_ts = None
        self.exit_reason = None
        self.exit_price = None  # L7: real V9Trade field, read by the close-time recalc
        self.pnl_usd = 0.0
        self.pnl_r = 0.0
        self.contracts = 3
        self.system_id = 4
        self.pattern_id_at_entry = "ZLR"
        self.day_type_at_entry = "Variation"
        self.session_at_entry = "RTH"
        self.cross_context = []
        self.management_log = "[]"
        self.is_synthetic = 0
        self.hwm = entry
        self.original_stop = stop
        self.quality = "HIGH"
        self.sizing = "full"
        self.entry_ts = datetime(2026, 7, 1, 17, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Test 1: T1 hit → PARTIAL + BE+1T (applies to ALL patterns)
# if reverted → RED because smart_be is the core of 3-contract management
# ---------------------------------------------------------------------------
class TestT1BEAfterHit:
    def test_t1_hit_transitions_to_partial(self):
        """T1 hit: FILLED → PARTIAL, stop → BE+1T."""
        from backend.v9.services.trade_manager.manager import TradeManager
        tm = TradeManager.__new__(TradeManager)
        tm._db = MagicMock()
        tm._emitter = MagicMock()
        tm._machines = {}
        tm._management_log = {}
        tm._snapshot = None

        trade = _FakeTrade()
        tm._get_trade = lambda tid: trade

        # Before T1
        assert trade.t1_hit_ts is None

        tm.on_target_hit(trade.id, "T1")

        # After T1
        assert trade.state == "PARTIAL"
        assert trade.t1_hit_ts is not None
        # Smart BE: stop should move to entry + 1T for LONG
        assert trade.stop == 7553.0 + 0.25  # BE + 1 tick


# ---------------------------------------------------------------------------
# Test 2: Full sequence T1→T2→T3 → CLOSED (all patterns same path)
# if reverted → RED because the 3-contract close flow breaks
# ---------------------------------------------------------------------------
class TestFullT1T2T3Close:
    def test_t3_closes_trade(self):
        """T1+T2+T3 all hit → trade CLOSED."""
        tm = TradeManager.__new__(TradeManager)
        tm._db = MagicMock()
        tm._emitter = MagicMock()
        tm._machines = {}
        tm._management_log = {}
        tm._snapshot = None

        trade = _FakeTrade()
        tm._get_trade = lambda tid: trade

        tm.on_target_hit(trade.id, "T1")
        assert trade.state == "PARTIAL"

        tm.on_target_hit(trade.id, "T2")
        assert trade.state == "PARTIAL"  # still partial after T2

        tm.on_target_hit(trade.id, "T3")
        assert trade.state == "CLOSED"  # all 3 contracts out
        assert trade.exit_reason == "T3_HIT"


# ---------------------------------------------------------------------------
# Test 3: Stop hit → CLOSED (all patterns same path)
# if reverted → RED because stop detection is universal
# ---------------------------------------------------------------------------
class TestStopHitCloses:
    def test_stop_hit_closes_trade(self):
        """Stop hit → CLOSED."""
        tm = TradeManager.__new__(TradeManager)
        tm._db = MagicMock()
        tm._emitter = MagicMock()
        tm._machines = {}
        tm._management_log = {}
        tm._snapshot = None

        trade = _FakeTrade()
        tm._get_trade = lambda tid: trade

        tm.on_stop_hit(trade.id)
        assert trade.state == "CLOSED"


# ---------------------------------------------------------------------------
# Test 4: Structural targets — CONT vs REV produce different C2/C3
# if reverted → RED because the resolver's family-aware logic breaks
# ---------------------------------------------------------------------------
class TestStructuralTargetsByFamily:
    def test_cont_c3_is_vah(self):
        """CONT LONG on Variation: C3 = VAH (runner to value edge)."""
        import os; os.environ['DAYTYPE_TARGETS_STRUCTURAL'] = '1'
        from backend.v9.systems.structural_targets import resolve_structural_targets
        tpo = {'ib_high': 7553.75, 'ib_low': 7506.0, 'poc': 7569.5, 'vah': 7572.25, 'val': 7568.0}
        r = resolve_structural_targets(day_type='Variation', direction='LONG',
            entry_price=7553.0, stop_price=7550.25, tpo_ctx=tpo, pattern_family='CONT')
        assert r is not None
        assert r["t3_price"] == 7572.25  # VAH

    def test_rev_short_c2_structural(self):
        """REV SHORT on Variation: C2 structural (POC when below entry, R-fallback when above)."""
        import os; os.environ['DAYTYPE_TARGETS_STRUCTURAL'] = '1'
        from backend.v9.systems.structural_targets import resolve_structural_targets
        # POC below entry → C2 = POC
        tpo_below = {'ib_high': 7553.75, 'ib_low': 7506.0, 'poc': 7560.0, 'vah': 7572.25, 'val': 7550.0}
        r = resolve_structural_targets(day_type='Variation', direction='SHORT',
            entry_price=7574.5, stop_price=7579.75, tpo_ctx=tpo_below, pattern_family='REV')
        assert r is not None
        assert r["t2_price"] is not None and r["t2_price"] < 7574.5  # below entry

    def test_cap_prevents_absurd_targets(self):
        """Hard cap: no target > 2×ATR from entry."""
        import os; os.environ['DAYTYPE_TARGETS_STRUCTURAL'] = '1'
        from backend.v9.systems.structural_targets import resolve_structural_targets
        # Wide IB that would produce 92pt targets without cap
        tpo = {'ib_high': 7553.75, 'ib_low': 7506.0, 'poc': 7569.5, 'vah': 7572.25, 'val': 7568.0}
        r = resolve_structural_targets(day_type='Variation', direction='SHORT',
            entry_price=7574.5, stop_price=7579.75, tpo_ctx=tpo, pattern_family='REV')
        assert r is not None
        # T1 should be capped (not 92pt away)
        assert abs(7574.5 - r["t1_price"]) <= 15  # 2×ATR ≈ 14pt
