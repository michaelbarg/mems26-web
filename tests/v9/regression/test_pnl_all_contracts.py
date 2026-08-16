"""T3 — P&L must count EVERY contract, not the first three.

Measured 2026-08-14 (S6 audit): `contract_exits` was always a 3-element list and
`[:n_contracts]` truncated instead of extending, so every 4-contract trade
booked only 3 legs — **25% of the P&L missing on 102 closed trades**. #682's
real loss was $83.75; the books said $75.00. RISK_HALT_V1 counts realized loss,
so it tripped late. At Michael's new 6-contract size the same bug hides 50%.
"""
import types

import pytest

from backend.v9.services.trade_manager import manager as mgr_mod

MES = 5.0  # $ per point per contract


def _tm():
    m = mgr_mod.TradeManager.__new__(mgr_mod.TradeManager)
    return m


def _trade(*, contracts, direction="SHORT", entry=7800.0, stop=7805.0,
           t1=7796.0, t2=7792.0, t3=7788.0, t4=7784.0,
           exit_reason="STOP_HIT", exit_price=7805.0,
           t1_hit=None, t2_hit=None, t3_hit=None, t4_hit=None):
    return types.SimpleNamespace(
        id=1, direction=direction, entry_price=entry, stop=stop,
        t1=t1, t2=t2, t3=t3, t4=t4,
        t1_hit_ts=t1_hit, t2_hit_ts=t2_hit, t3_hit_ts=t3_hit, t4_hit_ts=t4_hit,
        contracts=contracts, exit_reason=exit_reason, exit_price=exit_price,
        state="CLOSED", pnl_usd=None, pnl_r=None,
        quality={"contracts": contracts},
    )


def _compute(tm, trade):
    tm._compute_pnl(trade) if hasattr(tm, "_compute_pnl") else None
    return trade.pnl_usd


@pytest.fixture
def tm(monkeypatch):
    m = _tm()
    # isolate from DB/session helpers
    monkeypatch.setattr(m, "_initial_stop", lambda t: t.stop, raising=False)
    return m


def _call(m, trade):
    """Find and run the P&L routine regardless of its private name."""
    for name in ("_compute_pnl", "_finalize_pnl", "_calculate_pnl", "_update_pnl"):
        fn = getattr(m, name, None)
        if callable(fn):
            fn(trade)
            return trade.pnl_usd
    pytest.skip("P&L routine not found under the expected names")


class TestAllContractsCounted:
    def test_four_contract_stop_out_books_four_legs(self, tm):
        """SHORT 4 @7800, all stopped at 7805 → 4 × −5pt × $5 = −$100."""
        t = _trade(contracts=4)
        pnl = _call(tm, t)
        assert pnl == pytest.approx(-100.0), (
            f"expected 4 legs (−$100), got {pnl} — a 3-leg truncation gives −$75")

    def test_six_contract_stop_out_books_six_legs(self, tm):
        """Michael's new size. 6 × −5pt × $5 = −$150."""
        t = _trade(contracts=6)
        pnl = _call(tm, t)
        assert pnl == pytest.approx(-150.0), (
            f"expected 6 legs (−$150), got {pnl} — truncation would give −$75")

    def test_two_contract_trade_still_books_two(self, tm):
        """L7 (2026-07-08) must not regress: a 2c trade has 2 legs, not 3."""
        t = _trade(contracts=2)
        pnl = _call(tm, t)
        assert pnl == pytest.approx(-50.0)

    def test_partial_targets_are_credited_per_contract(self, tm):
        """C1 reached T1 (+4pt), the rest stopped (−5pt each), 4 contracts."""
        t = _trade(contracts=4, t1_hit="2026-08-14T17:00:00")
        pnl = _call(tm, t)
        expected = (4.0 * MES) + 3 * (-5.0 * MES)
        assert pnl == pytest.approx(expected), f"expected {expected}, got {pnl}"

    def test_long_direction_sign(self, tm):
        t = _trade(contracts=4, direction="LONG", entry=7800.0, stop=7795.0,
                   t1=7804.0, t2=7808.0, t3=7812.0, t4=7816.0,
                   exit_price=7795.0)
        pnl = _call(tm, t)
        assert pnl == pytest.approx(-100.0)


class TestPartialTargetWinnersBookEveryLeg:
    """Regression for a bug my own T3 fix introduced and the L7 suite caught:
    forcing the LAST leg to the exit fill overwrote a contract that had banked
    its target. A 2-contract T1+T2 winner booked $20 instead of $60.

    The old code's `c3 = exit_p` was unconditional only because `[:n]` threw
    that leg away for n < 3. The rule it encoded is "a contract that did not
    reach its target exits at the fill" — per leg, not per position.
    """

    def test_two_contract_t1_t2_winner_books_both_targets(self, tm):
        t = _trade(direction="LONG", entry=7500.0, stop=7496.0,
                   t1=7504.0, t2=7508.0, t3=7512.0, t4=None,
                   contracts=2, t1_hit=1, t2_hit=1,
                   exit_reason="T2_HIT", exit_price=None)
        pnl = _call(tm, t)
        assert pnl == pytest.approx(60.0), (
            f"got {pnl}: c1@T1 (+4pt=$20) + c2@T2 (+8pt=$40) = $60")

    def test_a_contract_that_missed_its_target_still_exits_at_the_fill(self, tm):
        t = _trade(direction="LONG", entry=7500.0, stop=7496.0,
                   t1=7504.0, t2=7508.0, t3=7512.0, t4=None,
                   contracts=3, t1_hit=1, t2_hit=None,
                   exit_reason="MANUAL", exit_price=7502.0)
        pnl = _call(tm, t)
        # c1@T1 (+4=$20), c2 and c3 at the 7502 fill (+2=$10 each) = $40
        assert pnl == pytest.approx(40.0), pnl
