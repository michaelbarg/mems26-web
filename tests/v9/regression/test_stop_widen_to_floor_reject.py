"""Ruling 2026-07-19 (Michael): widen-to-floor on StopResolver REJECT.

When STOP_RESOLVER_V1 rejects (no structural rung in band) it keeps the ORIGINAL
detector stop and the trade still fires. If that kept stop is narrower than the
dynamic ATR floor (but > 0, above the 2pt degenerate guard) it can die on noise
(#372 class). This ruling widens it OUT to the floor distance — widen-only, never
past the cap, no synthetic price (a minimum RISK DISTANCE).

Flag STOP_WIDEN_TO_FLOOR_ON_REJECT_V1 default OFF (Sunday sim-verified before
live). These tests exercise the pure arithmetic of the widen so it can be pinned
without standing up the whole gateway.
"""
import pytest


def _widen(entry, orig_stop, direction, floor_pts):
    """Mirror of the gateway branch: returns the widened stop, or the original
    if no widen applies. Pure — the gateway wraps this exact math."""
    orig_risk = abs(entry - orig_stop)
    if not (0 < orig_risk < floor_pts):
        return orig_stop
    sign = -1.0 if direction == "LONG" else 1.0
    tick = 0.25
    return round(round((entry + sign * floor_pts) / tick) * tick, 2)


def test_long_narrow_stop_widened_to_floor():
    # entry 7500, detector stop 7498.5 (1.5pt), floor 3.5pt → widen to 7496.5
    out = _widen(7500.0, 7498.5, "LONG", 3.5)
    assert out == 7496.5
    assert 7500.0 - out == pytest.approx(3.5)


def test_short_narrow_stop_widened_to_floor():
    # entry 7500, detector stop 7501.5 (1.5pt), floor 3.5 → widen to 7503.5
    out = _widen(7500.0, 7501.5, "SHORT", 3.5)
    assert out == 7503.5
    assert out - 7500.0 == pytest.approx(3.5)


def test_stop_already_at_or_beyond_floor_untouched():
    # 5pt original with a 3.5pt floor → no widen (never tightens)
    assert _widen(7500.0, 7495.0, "LONG", 3.5) == 7495.0


def test_widen_is_protective_side_only():
    # LONG widened stop must be BELOW entry; SHORT ABOVE
    assert _widen(7500.0, 7499.0, "LONG", 4.0) < 7500.0
    assert _widen(7500.0, 7501.0, "SHORT", 4.0) > 7500.0


def test_degenerate_zero_risk_not_widened():
    # risk == 0 (stop == entry) is the degenerate case the 2pt guard owns —
    # widen-to-floor must NOT act on it (guard: 0 < risk < floor)
    assert _widen(7500.0, 7500.0, "LONG", 3.5) == 7500.0


def test_result_on_tick_grid():
    out = _widen(7500.0, 7499.3, "LONG", 3.3)  # floor 3.3 → 7496.7 snaps to grid
    assert round(out / 0.25) * 0.25 == pytest.approx(out)


def test_flag_default_off_in_code():
    """The gateway branch is gated on STOP_WIDEN_TO_FLOOR_ON_REJECT_V1 defaulting
    to '0' — pin that the source keeps the default OFF (Sunday-sim gate)."""
    import inspect
    import backend.v9.gateway.trading_gateway as tg
    src = inspect.getsource(tg)
    assert 'STOP_WIDEN_TO_FLOOR_ON_REJECT_V1", "0"' in src, \
        "flag must default OFF in code"
