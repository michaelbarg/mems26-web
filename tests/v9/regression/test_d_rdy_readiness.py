"""D-RDY: Readiness verdict from BuildStatusAggregator.

Calls PRODUCTION _compute_readiness with real SystemStatus objects.
Asserts on the consumer (readiness.verdict), not on internal logic.

if reverted → RED because removing _compute_readiness or returning
  always-READY → the assert on verdict != "READY" fails.
"""

import pytest
from backend.v9.systems.build_status.types import (
    SystemStatus, GlobalGate, LiveInput, Interpretation, RTBSession,
    Readiness, ReadinessCheck,
)
from backend.v9.systems.build_status.aggregator import _compute_readiness


def _bridge_with_gates(all_fresh=True):
    """Bridge system with global_gates."""
    gates = [
        GlobalGate(key="woodies_5min", spec="< 90s", present=all_fresh, live="5s", required="< 90s"),
        GlobalGate(key="footprint", spec="< 90s", present=all_fresh, live="3s", required="< 90s"),
        GlobalGate(key="5min_bars", spec="< 360s", present=all_fresh, live="10s", required="< 360s"),
    ]
    return SystemStatus(id="bridge", name="Bridge", running=True, hydrated=True, global_gates=gates)


def _woodies_with_trend(trend="BLUE"):
    return SystemStatus(
        id="woodies", name="S4 Woodies", running=True, hydrated=True,
        live_inputs=[LiveInput(field="trend_state", value=trend)],
    )


def _day_type_with(day_type="Normal_Center"):
    return SystemStatus(
        id="day_type", name="S1 Day Type", running=True, hydrated=True,
        interpretations=[Interpretation(key="day_type", value=day_type)],
    )


def test_all_healthy_in_rth_is_ready():
    """D-RDY: All checks pass during RTH → READY."""
    systems = [_bridge_with_gates(True), _woodies_with_trend("BLUE"), _day_type_with("Normal_Center")]
    rtb = RTBSession(in_session=True, minutes_to_close=120)
    result = _compute_readiness(systems, rtb)
    assert result.verdict == "READY", f"Expected READY, got {result.verdict}: {result.reason}"


def test_dead_bridge_in_rth_is_blocked():
    """D-RDY: Dead bridge stream during RTH → BLOCKED.

    if reverted → RED because without readiness logic, verdict defaults to BLOCKED
      from the Readiness() default, OR if always-READY, this assert fails.
    """
    systems = [_bridge_with_gates(False), _woodies_with_trend("BLUE"), _day_type_with("Normal_Center")]
    rtb = RTBSession(in_session=True, minutes_to_close=120)
    result = _compute_readiness(systems, rtb)
    assert result.verdict == "BLOCKED", f"Expected BLOCKED, got {result.verdict}"
    assert any(c.key == "bridge_streams_fresh" and not c.passed for c in result.checks)


def test_dead_bridge_outside_rth_not_blocked():
    """D-RDY: Dead bridge outside RTH → not BLOCKED (info severity)."""
    systems = [_bridge_with_gates(False), _woodies_with_trend("BLUE"), _day_type_with("Normal_Center")]
    rtb = RTBSession(in_session=False, minutes_to_open=60)
    result = _compute_readiness(systems, rtb)
    assert result.verdict != "BLOCKED", f"Outside RTH, dead bridge should not BLOCK. Got {result.verdict}"


def test_gray_trend_is_degraded():
    """D-RDY: trend_state=GRAY → DEGRADED (not READY).

    if reverted → RED because removing the trend check makes verdict READY.
    """
    systems = [_bridge_with_gates(True), _woodies_with_trend("GRAY"), _day_type_with("Normal_Center")]
    rtb = RTBSession(in_session=True, minutes_to_close=120)
    result = _compute_readiness(systems, rtb)
    assert result.verdict == "DEGRADED", f"Expected DEGRADED for GRAY trend. Got {result.verdict}"
    assert any(c.key == "s4_trend_not_stuck_gray" and not c.passed for c in result.checks)


def test_unknown_day_type_is_degraded():
    """D-RDY: day_type=UNKNOWN → DEGRADED."""
    systems = [_bridge_with_gates(True), _woodies_with_trend("BLUE"), _day_type_with("UNKNOWN")]
    rtb = RTBSession(in_session=True, minutes_to_close=120)
    result = _compute_readiness(systems, rtb)
    assert result.verdict == "DEGRADED", f"Expected DEGRADED for UNKNOWN day_type. Got {result.verdict}"
    assert any(c.key == "s1_day_type_classified" and not c.passed for c in result.checks)
