"""F3 — STEP_SCALED_LADDER_V1 tests (2026-08-12).

Step-scaled stop+target ladder: stop = max(4, 0.6×median_step),
targets = 0.5/1.0/1.5 × median_step.
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


# ── compute_median_session_step ────────────────────────────────────────────

class TestMedianStep:
    def test_ascending_session_long(self):
        """LONG: highs advance 100→103→105→109→112 → steps 3,2,4,3 → median 3."""
        bars = [_bar(100, 98), _bar(103, 100), _bar(105, 102),
                _bar(109, 104), _bar(112, 108)]
        m = compute_median_session_step(bars, "LONG")
        assert m == 3.0

    def test_descending_session_short(self):
        """SHORT: lows descend 100→97→94→91→88 → steps 3,3,3,3 → median 3."""
        bars = [_bar(102, 100), _bar(99, 97), _bar(96, 94),
                _bar(93, 91), _bar(90, 88)]
        m = compute_median_session_step(bars, "SHORT")
        assert m == 3.0

    def test_flat_session_returns_none(self):
        """No advances → no steps → None."""
        bars = [_bar(100, 98)] * 10
        m = compute_median_session_step(bars, "LONG")
        assert m is None

    def test_too_few_bars_returns_none(self):
        bars = [_bar(100, 98), _bar(102, 99)]
        m = compute_median_session_step(bars, "LONG")
        assert m is None

    def test_less_than_3_steps_returns_none(self):
        """Only 2 steps (need >= 3) → None."""
        bars = [_bar(100, 98), _bar(103, 100), _bar(106, 102),
                _bar(105, 101), _bar(104, 100)]  # only 2 advances
        m = compute_median_session_step(bars, "LONG")
        assert m is None

    def test_realistic_mes_steps(self):
        """Realistic MES trend: steps ~3-5pt."""
        bars = [
            _bar(7770, 7766), _bar(7774, 7769), _bar(7777, 7773),
            _bar(7781, 7776), _bar(7783, 7779), _bar(7787, 7782),
            _bar(7790, 7785), _bar(7794, 7789), _bar(7797, 7793),
            _bar(7801, 7796),
        ]
        m = compute_median_session_step(bars, "LONG")
        assert m is not None
        assert 2.5 <= m <= 5.0


# ── build_step_ladder ──────────────────────────────────────────────────────

class TestBuildLadder:
    def test_long_ladder(self):
        """LONG: entry 7790, median 6pt → stop 7786.5, t1=+3, t2=+6, t3=+9."""
        bars = [_bar(7770+i*6, 7770+i*6-3) for i in range(8)]
        ladder = build_step_ladder(7790.0, "LONG", bars)
        assert ladder is not None
        assert ladder["stop"] < 7790.0  # below entry
        assert ladder["t1"] > 7790.0
        assert ladder["t2"] > ladder["t1"]
        assert ladder["t3"] > ladder["t2"]

    def test_short_ladder(self):
        """SHORT: targets below entry, stop above."""
        bars = [_bar(7800-i*5, 7800-i*5-3) for i in range(8)]
        ladder = build_step_ladder(7780.0, "SHORT", bars)
        assert ladder is not None
        assert ladder["stop"] > 7780.0
        assert ladder["t1"] < 7780.0
        assert ladder["t2"] < ladder["t1"]
        assert ladder["t3"] < ladder["t2"]

    def test_stop_floor(self):
        """Stop distance must be >= STEP_STOP_FLOOR (4pt)."""
        # Tiny steps → floor kicks in
        bars = [_bar(7770+i*2, 7770+i*2-1) for i in range(8)]
        ladder = build_step_ladder(7790.0, "LONG", bars)
        if ladder is not None:
            assert abs(7790.0 - ladder["stop"]) >= STEP_STOP_FLOOR

    def test_returns_none_on_flat(self):
        """Flat session → None (no median step)."""
        bars = [_bar(7790, 7788)] * 10
        ladder = build_step_ladder(7790.0, "LONG", bars)
        assert ladder is None

    def test_tick_grid_alignment(self):
        """All prices must be on the 0.25 tick grid."""
        bars = [_bar(7770+i*5, 7770+i*5-2) for i in range(8)]
        ladder = build_step_ladder(7790.0, "LONG", bars)
        if ladder is not None:
            for key in ("stop", "t1", "t2", "t3"):
                assert (ladder[key] * 4) == int(ladder[key] * 4), \
                    f"{key}={ladder[key]} not on tick grid"


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

    def test_flag_default_off(self):
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert 'STEP_SCALED_LADDER_V1", "0"' in src

    def test_ladder_after_structural_targets(self):
        """Step ladder must run AFTER structural targets (overrides them)."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        struct_pos = src.index("DAYTYPE_TARGETS_STRUCTURAL")
        ladder_pos = src.index("STEP_SCALED_LADDER_V1")
        assert ladder_pos > struct_pos
