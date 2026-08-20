"""T-62 — a LADDER's P&L is the sum of its OWN fills, not one exit price.

Trade **#749** (2026-08-19) was the first live TREND_STEP ladder: LONG 4 @ 7737.5.
`trade_fills_journal.jsonl` records four exit fills that sum to **+$1.25**:

    T1   order 10406  1 @ 7740.75   +3.25 pt   +$16.25   (the T0 scale-out)
    T3   order 10412  1 @ 7742.25   +4.75 pt   +$23.75
    STOP order 10410  1 @ 7734.75   -2.75 pt   -$13.75
    STOP order 10416  1 @ 7732.50   -5.00 pt   -$25.00
                                    ------------------
                                    +0.25 pt   **+$1.25**

The books said `pnl_usd = -51.25`. A **$52.50 error on one trade**, and the same
class as 2026-08-14 (books -$135 vs broker +$120). Two independent roots, both
visible in `v9_trade_management_log` for trade 749:

  1. `T0_HIT {"ts": "..."}` — **no price**. With BE_AFTER_REAL_T1_V1 + 4
     contracts + a T0 target, the DLL's "T1" is remapped to "T0"; the T0 branch
     stores no fill price and sets no `*_hit_ts`, so the contract that really
     banked +3.25 pt was booked at the stop instead. **-$41.25.**
  2. `PNL_CORRECTION {"old_pnl": -17.5, "new_pnl": -51.25}` — the ladder stopped
     out in TWO pieces at TWO prices, but `exit_price` is one column. The second
     stop (7732.50) arrived on an already-CLOSED trade and re-priced the first
     one (7734.75) through `update_closed_trade_pnl`. **-$11.25.**

Note this is NOT the T-53 bug (contract→ladder-group mapping, commit 7ed455bb):
that fix was already in the running code when #749 was booked.
"""
import types
from datetime import datetime, timezone

import pytest

from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.trade_manager.state_machine import (
    TradeStateMachine, TradeState,
)

MES = 5.0
ENTRY = 7737.5

#: exactly the lines in trade_fills_journal.jsonl for entry order 10414
JOURNAL_749 = [
    ("T1", 10406, 7740.75, 1),
    ("T3", 10412, 7742.25, 1),
    ("STOP", 10410, 7734.75, 1),
    ("STOP", 10416, 7732.50, 1),
]
SIERRA_TRUTH_749 = round(
    sum((px - ENTRY) * qty for _, _, px, qty in JOURNAL_749) * MES, 2)


def _ts(sec):
    return datetime(2026, 8, 19, 19, 32, sec, tzinfo=timezone.utc)


def _trade_749(**over):
    """#749 as the gateway created it (pre-exit)."""
    t = types.SimpleNamespace(
        id=749, direction="LONG", mode="live", entry_price=ENTRY, stop=7732.5,
        t1=7742.25, t2=7742.25, t3=7746.25, t4=None,
        t1_hit_ts=None, t2_hit_ts=None, t3_hit_ts=None, t4_hit_ts=None,
        stop_hit_ts=None, exit_ts=None, exit_price=None, exit_reason=None,
        state="FILLED", pnl_usd=None, pnl_r=None, outcome=None,
        cross_context=[],
        quality={"contracts": 4, "has_t0": True, "t0_target_pts": 3.0,
                 "initial_stop": 7732.5, "sierra_order_id": 10414,
                 "c1_target_id": 10406, "c1_stop_id": 10407,
                 "c2_target_id": 10409, "c2_stop_id": 10410,
                 "c3_target_id": 10412, "c3_stop_id": 10413,
                 "c4_target_id": 10415, "c4_stop_id": 10416},
    )
    for k, v in over.items():
        setattr(t, k, v)
    return t


def _mgr(trade, state=TradeState.FILLED):
    """Real state machine + real P&L math; only DB/emitter/IO are stubbed."""
    from unittest.mock import MagicMock
    m = TradeManager.__new__(TradeManager)
    machine = TradeStateMachine(state)
    m._machines = {trade.id: machine}
    m._db = MagicMock()
    m._emitter = MagicMock()
    m._log_management = MagicMock()
    m._append_snapshot = MagicMock()
    m._apply_smart_be_after_t1 = MagicMock()
    m._get_trade = lambda tid: trade
    m._get_machine = lambda t: machine
    return m, machine


def _replay_749(mgr, trade, *, with_qty=True):
    """Feed the four journal fills through the real event path, in order."""
    q = (lambda n: n) if with_qty else (lambda n: None)
    # 1. DLL "T1" @7740.75 → remapped to T0 (the scale-out with no column)
    mgr.on_target_hit(trade.id, "T1", fill_ts=_ts(36), fill_price=7740.75,
                      fill_qty=q(1), order_id=10406)
    # 2. DLL "T3" @7742.25 → remapped to T2
    mgr.on_target_hit(trade.id, "T3", fill_ts=_ts(9), fill_price=7742.25,
                      fill_qty=q(1), order_id=10412)
    # 3. first stop leg closes the trade
    mgr.on_stop_hit(trade.id, fill_ts=_ts(58), fill_price=7734.75,
                    fill_qty=q(1), order_id=10410)
    # 4. the fourth contract's stop lands on an already-CLOSED trade
    mgr.update_closed_trade_pnl(trade.id, 7732.50, exit_reason="STOP_FILL",
                                fill_qty=q(1), order_id=10416, kind="STOP")


class TestTrade749:
    def test_journal_sums_to_one_twentyfive(self):
        """Guard the fixture itself: these four fills ARE +$1.25."""
        assert SIERRA_TRUTH_749 == pytest.approx(1.25)

    def test_749_books_the_sierra_truth(self, monkeypatch):
        """The whole point of F2: books == broker on the ladder trade."""
        monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
        monkeypatch.setenv("ZLR_MGMT_V1", "0")
        trade = _trade_749()
        mgr, _ = _mgr(trade)

        _replay_749(mgr, trade)

        assert trade.pnl_usd == pytest.approx(SIERRA_TRUTH_749), (
            f"#749 booked {trade.pnl_usd}, Sierra's four fills say "
            f"{SIERRA_TRUTH_749}. The books lie about a LIVE ladder trade.")
        assert trade.pnl_usd == pytest.approx(1.25)
        assert trade.outcome == "WIN"

    def test_749_books_every_leg_exactly_once(self, monkeypatch):
        """Four fills, four legs, four contracts — no leg lost, none doubled."""
        monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
        trade = _trade_749()
        mgr, _ = _mgr(trade)
        _replay_749(mgr, trade)

        legs = trade.quality["exit_fills"]
        assert sum(int(f["qty"]) for f in legs) == 4, (
            f"ladder has 4 contracts, ledger covers {legs}")
        assert sorted(f["price"] for f in legs) == [
            7732.50, 7734.75, 7740.75, 7742.25]

    def test_the_t0_scaleout_is_not_thrown_away(self, monkeypatch):
        """Root 1 in isolation: the T0 leg is worth +$16.25, not -$25.00."""
        monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
        trade = _trade_749()
        mgr, _ = _mgr(trade)

        mgr.on_target_hit(trade.id, "T1", fill_ts=_ts(36), fill_price=7740.75,
                          fill_qty=1, order_id=10406)

        assert trade.t1_hit_ts is None, "T0 must not claim to be T1 (T17 remap)"
        assert trade.pnl_usd == pytest.approx(16.25), (
            "the T0 scale-out banked 1 @ 7740.75 = +$16.25; booking it at the "
            "trade's exit fill is what cost #749 $41.25")

    def test_two_stop_fills_keep_their_own_prices(self, monkeypatch):
        """Root 2 in isolation: the later stop must not re-price the earlier."""
        monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
        trade = _trade_749()
        mgr, _ = _mgr(trade)

        mgr.on_stop_hit(trade.id, fill_ts=_ts(58), fill_price=7734.75,
                        fill_qty=1, order_id=10410)
        after_first = trade.pnl_usd
        mgr.update_closed_trade_pnl(trade.id, 7732.50, exit_reason="STOP_FILL",
                                    fill_qty=1, order_id=10416, kind="STOP")

        # 1 leg @7734.75 (-2.75) + 3 remaining @7734.75 → -$55.00 …
        assert after_first == pytest.approx(-55.0)
        # … then the 4th contract takes its own -5.00 instead of re-pricing all:
        # 2×(-2.75) + 1×(-5.00) + 1 remaining @7732.50 = -3×2.75… spelled out:
        expected = ((7734.75 - ENTRY) * 1 + (7732.50 - ENTRY) * 1
                    + (7732.50 - ENTRY) * 2) * MES
        assert trade.pnl_usd == pytest.approx(expected)
        assert trade.pnl_usd > -100.0

    def test_a_replayed_fill_is_never_booked_twice(self, monkeypatch):
        """trade_fills.json is re-read on every mtime bump."""
        monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
        trade = _trade_749()
        mgr, _ = _mgr(trade)
        _replay_749(mgr, trade)
        once = trade.pnl_usd

        mgr.update_closed_trade_pnl(trade.id, 7732.50, exit_reason="STOP_FILL",
                                    fill_qty=1, order_id=10416, kind="STOP")

        assert len(trade.quality["exit_fills"]) == 4
        assert trade.pnl_usd == pytest.approx(once)


class TestPreFixBehaviourIsReproduced:
    """revert→RED, and proof the legacy path is untouched.

    Without per-leg fills the math must still be exactly what shipped before
    T-62 — that is what keeps every other P&L suite green.
    """

    def test_the_persisted_749_row_still_computes_minus_5125(self):
        """The DB row exactly as it was written on 2026-08-19."""
        trade = _trade_749(
            t2_hit_ts=datetime(2026, 8, 19, 19, 33, 9, tzinfo=timezone.utc),
            exit_price=7732.5, exit_reason="STOP_FILL", state="CLOSED")
        mgr, _ = _mgr(trade, state=TradeState.CLOSED)

        mgr._calculate_pnl(trade)

        assert trade.pnl_usd == pytest.approx(-51.25), (
            "this is the number the live books held for #749 — if the legacy "
            "path drifts, every historical row silently changes meaning")

    def test_no_fill_qty_falls_back_to_the_single_exit_price(self, monkeypatch):
        """A caller with no per-leg quantity (bar_level_detector, shadow) is
        byte-identical to pre-T-62: everything left exits at the fill."""
        monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "0")
        trade = _trade_749()
        mgr, _ = _mgr(trade)

        mgr.on_stop_hit(trade.id, fill_ts=_ts(58), fill_price=7734.75)

        assert "exit_fills" not in trade.quality
        assert trade.pnl_usd == pytest.approx((7734.75 - ENTRY) * 4 * MES)


class TestSixContractLadder:
    """Michael's ruled 1/2/2/1 (`contract_size.LADDER[6]` = T0/T1/T2/T3).

    At six the T1 and T2 levels each hold TWO contracts, so a leg's quantity
    can never be assumed to be 1.
    """

    def _six(self):
        return _trade_749(quality={"contracts": 6, "initial_stop": 7732.5,
                                   "has_t0": True, "t0_target_pts": 3.0})

    def test_sierra_quantity_is_used_verbatim(self, monkeypatch):
        monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
        trade = self._six()
        mgr, _ = _mgr(trade)

        # DLL "T2" → logical T1, the level that holds 2 contracts at six
        mgr.on_target_hit(trade.id, "T2", fill_ts=_ts(1), fill_price=7742.25,
                          fill_qty=2, order_id=10409)

        assert trade.pnl_usd == pytest.approx((7742.25 - ENTRY) * 2 * MES)

    def test_missing_quantity_uses_the_ladder_weight_not_one(self, monkeypatch):
        """Rule 1: when Sierra omits `contracts`, fall back to the table the
        DLL brackets with — never a blind 1, which under-books a six-ladder."""
        monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
        trade = self._six()
        mgr, _ = _mgr(trade)

        mgr.on_target_hit(trade.id, "T2", fill_ts=_ts(1), fill_price=7742.25,
                          order_id=10409)  # no fill_qty

        assert trade.quality["exit_fills"][0]["qty"] == 2, (
            "logical T1 is ladder group 1 = 2 contracts at six")

    def test_the_t0_group_is_one_contract(self, monkeypatch):
        monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
        trade = self._six()
        mgr, _ = _mgr(trade)

        mgr.on_target_hit(trade.id, "T1", fill_ts=_ts(1), fill_price=7740.75,
                          order_id=10406)  # DLL "T1" → T0

        assert trade.quality["exit_fills"][0]["qty"] == 1
        assert trade.quality["exit_fills"][0]["column"] is None, (
            "T0 owns no t*/t*_hit_ts column — that hole is why #749 lost it")
