"""Regression: S2 must pass the resolved T3 price to the gateway, not 0.0.

Root bug (pre-fix): five_min_system built the gateway setup with a hardcoded
`"t3": 0.0`, dropping the T3 price computed from targets_table. Downstream,
active_trade_manager.monitor treats `t3 is not None` as a live target, so a
0.0 T3 becomes a phantom (unreachable) target on the C3 leg instead of being
managed as trail/no-T3.

These tests call the REAL production helper `build_s2_gateway_setup` (the same
one five_min_system uses at the fire site) — not a copy of its logic.

Litmus (anti-tautological):
- if `build_s2_gateway_setup` reverts to `"t3": 0.0` → test_fixed_t3_passes_through RED.
- if it coerces None→0.0 → test_trail_day_is_none RED.
"""

from datetime import datetime, timezone

from backend.v9.systems.five_min.output_schema import T1Setup
from backend.v9.systems.five_min.five_min_system import build_s2_gateway_setup


def _setup(t3_price):
    """A SHORT reversal setup; entry 7444, stop 7457 (R=13)."""
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
        sizing_contracts=2,
    )


def test_fixed_t3_passes_through():
    """Fixed-T3 day (e.g. Trend_Normal 4R): the price reaches the gateway."""
    setup = build_s2_gateway_setup(_setup(t3_price=7392.0), info={})
    assert setup["t3"] == 7392.0  # NOT 0.0


def test_trail_day_is_none():
    """Trail/no-T3 day (Variation/Normal): T3 is None, never coerced to 0.0."""
    setup = build_s2_gateway_setup(_setup(t3_price=None), info={})
    assert setup["t3"] is None
    assert setup["t3"] != 0.0


def test_t1_t2_and_metadata_intact():
    """Sanity: the rest of the bracket mapping is unchanged."""
    setup = build_s2_gateway_setup(_setup(t3_price=7392.0), info={"variant": "A_VSA"})
    assert setup["t1"] == 7431.0
    assert setup["t2"] == 7411.5
    assert setup["stop"] == 7457.0
    assert setup["metadata"]["variant"] == "A_VSA"
    assert setup["metadata"]["sizing"] == 2
