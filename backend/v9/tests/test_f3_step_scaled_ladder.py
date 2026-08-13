"""F3 — STEP_SCALED_LADDER_V1 tests (2026-08-12, realigned 2026-08-13).

H6 realignment (Michael "ליישר לפי רחב יותר"): the step is now the WIDE
measure — zigzag swing-leg amplitude (ZZ_REV=5.0, same construction as the
TREND_STEP_ENTRY §9 analysis that produced the replay-GO ~10.4pt medians) —
not the old extreme-advance increment (2-3pt) that made the ladder fail
rr_entry_gate by construction. T1 is structurally floored at min_rr×stop.
"""
import inspect
import pytest

from backend.v9.systems.five_min.step_scaled_ladder import (
    compute_median_session_step,
    build_step_ladder,
    STEP_STOP_FLOOR,
)


def _bar(h, l):
    return {"h": h, "l": l}


def _stair_down(legs, retrace=6.0, start=7800.0, leg_bars=4):
    """Synthetic stair-down tape: each leg drops `legs[i]` pts then retraces
    `retrace` pts (>= ZZ_REV=5 so the zigzag confirms each pivot)."""
    bars = []
    px = start
    for leg in legs:
        step = leg / leg_bars
        for _ in range(leg_bars):
            bars.append(_bar(px, px - step))
            px -= step
        # retrace up (confirms the L pivot)
        r = retrace / 2
        for _ in range(2):
            bars.append(_bar(px + r, px))
            px += r
        px -= 0.0
    return bars


# ── compute_median_session_step (wide zigzag-leg measure) ──────────────────

class TestMedianStep:
    def test_stair_down_short_measures_full_legs(self):
        """SHORT stair: down-legs of 12,10,14 (with 6pt retraces) → the step
        is the LEG amplitude (~10-14), not the per-bar increment (~3)."""
        bars = _stair_down([12.0, 10.0, 14.0])
        m = compute_median_session_step(bars, "SHORT")
        assert m is not None
        assert 9.0 <= m <= 15.0, f"expected wide leg median, got {m}"

    def test_stair_up_long(self):
        """LONG mirror: up-legs measured full-size."""
        bars = []
        px = 7700.0
        for leg in (11.0, 9.0, 13.0):
            step = leg / 4
            for _ in range(4):
                bars.append(_bar(px + step, px))
                px += step
            for _ in range(2):
                bars.append(_bar(px, px - 3.0))
                px -= 3.0
        m = compute_median_session_step(bars, "LONG")
        assert m is not None
        assert 8.0 <= m <= 14.0

    def test_flat_session_returns_none(self):
        """No 5pt reversal anywhere → no zigzag → None."""
        bars = [_bar(100, 98)] * 10
        assert compute_median_session_step(bars, "LONG") is None

    def test_too_few_bars_returns_none(self):
        bars = [_bar(100, 98), _bar(102, 99)]
        assert compute_median_session_step(bars, "LONG") is None

    def test_too_few_legs_returns_none(self):
        """One leg down + one retrace = <3 legs → None (fail-open)."""
        bars = _stair_down([12.0])
        assert compute_median_session_step(bars, "SHORT") is None

    def test_monotonic_grind_no_reversal_returns_none(self):
        """The OLD measure loved this tape (increments 2pt); the wide measure
        correctly refuses: a one-way grind with no >=5pt reversal has no
        completed legs yet."""
        bars = [_bar(7770 + i * 2, 7770 + i * 2 - 1) for i in range(12)]
        assert compute_median_session_step(bars, "LONG") is None


# ── build_step_ladder ──────────────────────────────────────────────────────

class TestBuildLadder:
    def test_short_ladder_geometry(self):
        bars = _stair_down([12.0, 10.0, 14.0])
        ladder = build_step_ladder(7740.0, "SHORT", bars)
        assert ladder is not None
        assert ladder["stop"] > 7740.0
        assert ladder["t1"] < 7740.0
        assert ladder["t2"] <= ladder["t1"]
        assert ladder["t3"] <= ladder["t2"]

    def test_stop_floor(self):
        bars = _stair_down([12.0, 10.0, 14.0])
        ladder = build_step_ladder(7740.0, "SHORT", bars, stop_floor=STEP_STOP_FLOOR)
        assert ladder is not None
        assert abs(ladder["stop"] - 7740.0) >= STEP_STOP_FLOOR

    def test_returns_none_on_flat(self):
        bars = [_bar(7790, 7788)] * 10
        assert build_step_ladder(7790.0, "LONG", bars) is None

    def test_tick_grid_alignment(self):
        bars = _stair_down([11.0, 9.5, 13.25])
        ladder = build_step_ladder(7740.25, "SHORT", bars)
        assert ladder is not None
        for key in ("stop", "t1", "t2", "t3"):
            assert (ladder[key] * 4) == int(ladder[key] * 4), \
                f"{key}={ladder[key]} not on tick grid"

    def test_min_rr_structural_floor_post_snap(self):
        """H6 core guarantee: with min_rr=1.0 the POST-SNAP T1 distance is
        >= the POST-SNAP stop distance — the ladder can never fail the very
        gate it was built for (incl. the 0.25-tick rounding edge)."""
        for entry in (7740.0, 7740.25, 7739.75):
            for legs in ([12.0, 10.0, 14.0], [9.0, 8.5, 7.5], [22.0, 18.0, 25.0]):
                bars = _stair_down(legs)
                ladder = build_step_ladder(entry, "SHORT", bars, min_rr=1.0)
                if ladder is None:
                    continue
                stop_d = abs(entry - ladder["stop"])
                t1_d = abs(entry - ladder["t1"])
                assert t1_d >= stop_d - 1e-9, \
                    f"RR floor broken: t1_d={t1_d} < stop_d={stop_d} (entry={entry}, legs={legs})"

    def test_min_rr_zero_keeps_native_t1(self):
        """min_rr=0 → T1 stays 0.5×median (native ladder RR ~0.83)."""
        bars = _stair_down([12.0, 12.0, 12.0])
        ladder = build_step_ladder(7740.0, "SHORT", bars, min_rr=0.0)
        assert ladder is not None
        t1_d = abs(7740.0 - ladder["t1"])
        assert t1_d <= 0.5 * ladder["median_step"] + 0.25


# ── Gateway wiring ─────────────────────────────────────────────────────────

class TestGatewayWiring:
    def test_flag_in_gateway(self):
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "STEP_SCALED_LADDER_V1" in src
        assert "build_step_ladder" in src

    def test_env_overrides_in_gateway(self):
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "STEP_STOP_FLOOR" in src
        assert "STEP_STOP_FRAC" in src
        assert "STEP_ZZ_REV" in src

    def test_flag_default_off(self):
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert 'STEP_SCALED_LADDER_V1", "0"' in src

    def test_ladder_after_structural_targets(self):
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        struct_pos = src.index("DAYTYPE_TARGETS_STRUCTURAL")
        ladder_pos = src.index("STEP_SCALED_LADDER_V1")
        assert ladder_pos > struct_pos

    def test_ladder_uses_effective_rr_min(self):
        """H6: the ladder must be built against the SAME rr_min the gate
        enforces (single source: _effective_rr_min)."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "min_rr=self._effective_rr_min()" in src
        assert hasattr(trading_gateway.TradingGateway, "_effective_rr_min")
