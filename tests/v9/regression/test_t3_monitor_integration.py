"""End-to-end regression: T3 flows producer -> consumer without a phantom leg.

This is the integration counterpart to test_s2_gateway_t3_passthrough.py.
That test proves the *producer* (`build_s2_gateway_setup`) passes the resolved
T3. This one closes the loop on the *consumer*: the real
`ActiveTradeMonitor.update` (`monitor.py:104`) which is where a `0.0` T3 became
a phantom (unreachable) target on the C3 leg.

We drive a synthetic Trend-day setup (fixed T3) and a trail-day setup (None)
through the SAME production helper the fire site uses, map the setup onto a
trade exactly as the gateway persists it, and feed it to the REAL monitor —
no Sierra, no DB, no clock. Deterministic.

Litmus (anti-tautological):
- if the producer reverts to `"t3": 0.0`, the trail-day trade carries 0.0,
  `monitor.py:104` (`t3 is not None`) appends a phantom ("T3", 0.0) target,
  and `test_trail_day_emits_no_phantom_t3` goes RED.
- if the consumer stops managing a real T3, `test_trend_day_t3_is_managed` RED.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

from backend.v9.systems.five_min.output_schema import T1Setup
from backend.v9.systems.five_min.five_min_system import build_s2_gateway_setup
from backend.v9.services.active_trade_manager.monitor import ActiveTradeMonitor
from backend.v9.services.active_trade_manager.alerts import AlertEmitter
from backend.v9.services.trade_manager.state_machine import TradeState


def _setup(t3_price):
    """A SHORT reversal setup; entry 7444, stop 7457 (R=13), T1 7431, T2 7411.5."""
    return T1Setup(
        pattern_name="DOUBLE_TOP_AA_SHORT",
        direction="SHORT",
        entry_price=7444.0,
        stop_price=7457.0,
        t1_price=7431.0,
        t2_price=7411.5,
        t3_price=t3_price,
        confidence=75,
        bar_index=10,
        fired_at=datetime(2026, 6, 5, tzinfo=timezone.utc),
        sizing_contracts=3,
    )


def _trade_from_setup(setup_dict, trade_id=1):
    """Map a gateway setup onto a FILLED trade exactly as the gateway persists
    it — t3 carried through verbatim (this is the contract under test)."""
    return SimpleNamespace(
        id=trade_id,
        state=TradeState.FILLED.value,
        direction=setup_dict["direction"],
        entry_price=setup_dict["entry_price"],
        stop=setup_dict["stop"],
        t1=setup_dict["t1"],
        t2=setup_dict["t2"],
        t3=setup_dict["t3"],
        t1_hit_ts=None,
        t2_hit_ts=None,
        t3_hit_ts=None,
    )


class _FakeTradeManager:
    """Minimal stand-in: the monitor only calls get_active_trades()."""

    def __init__(self, trades):
        self._trades = trades

    def get_active_trades(self):
        return self._trades


def _monitor_with(trade):
    # AlertEmitter with no redis client => publish is a no-op; emit_* still
    # returns the alert payload, which is what update() collects.
    monitor = ActiveTradeMonitor(_FakeTradeManager([trade]), AlertEmitter(redis_client=None))
    return monitor


# Price placed 3 pts from the fixed T3 (7392): inside the 25% proximity band
# for T3 (|7392-7444|=52 -> 3/52=0.058), but OUTSIDE it for T1/T2/stop, so a
# clean single-signal assertion.
_PRICE_NEAR_T3 = 7395.0
_TS = 1_749_000_000.0


def test_producer_passes_t3():
    """Sanity: the fixed-T3 day reaches the setup, the trail day is None."""
    assert build_s2_gateway_setup(_setup(7392.0), info={})["t3"] == 7392.0
    assert build_s2_gateway_setup(_setup(None), info={})["t3"] is None


def test_trend_day_t3_is_managed():
    """Fixed-T3 (Trend) day: the real monitor manages T3 as a live target."""
    setup = build_s2_gateway_setup(_setup(7392.0), info={})
    trade = _trade_from_setup(setup)
    alerts = _monitor_with(trade).update(current_price=_PRICE_NEAR_T3, ts=_TS)
    # Exactly one proximity alert at this price, and it is about T3.
    assert len(alerts) == 1, alerts
    assert "T3" in str(alerts[0]), alerts[0]


def test_trail_day_emits_no_phantom_t3():
    """Trail/no-T3 day: T3 is None -> monitor never appends a T3 target.

    With the old `0.0` sentinel this trade would carry t3=0.0, `t3 is not None`
    at monitor.py:104 would be True, and a phantom ("T3", 0.0) leg would enter
    management. None makes the monitor skip it correctly.
    """
    setup = build_s2_gateway_setup(_setup(None), info={})
    trade = _trade_from_setup(setup)
    assert trade.t3 is None  # contract: trail carries None, never 0.0
    alerts = _monitor_with(trade).update(current_price=_PRICE_NEAR_T3, ts=_TS)
    assert alerts == []  # no phantom T3 (and nothing else is in proximity here)


def test_phantom_would_resurrect_if_t3_were_zero():
    """Guard documenting WHY None matters: a 0.0 T3 is NOT skipped by the
    `is not None` check, so the monitor would treat 0.0 as a managed target."""
    trade = _trade_from_setup(build_s2_gateway_setup(_setup(None), info={}))
    trade.t3 = 0.0  # simulate the pre-fix sentinel
    # Drive price toward 0 so a 0.0 target would be 'approaching' — proving the
    # phantom is reachable in the monitor's logic when t3 is 0.0 not None.
    alerts = _monitor_with(trade).update(current_price=1.0, ts=_TS)
    assert any("T3" in str(a) for a in alerts), "0.0 T3 should behave as a phantom target"
