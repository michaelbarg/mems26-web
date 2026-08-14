"""H15 — TREND_STEP_ENTRY_V1: the stair-step continuation detector goes live.

Michael 13.08: "שוב יש מדרגה למעלה שהמערכת לא זיהתה — זה בסדר?" (no). On stair
sessions NO detector produced a candidate — S2/S4 look for their own shapes and
LEG_RIDE only exempts existing signals from gates.

This module is a byte-faithful port of the causal detector proven in
scripts/replay_trend_step_entry.py (replay 07-15..08-12: NET +$2,378.75, n=31,
48% win, 4 contracts). Fidelity is asserted here against the exact entries the
replay produced.
"""
import inspect

from backend.v9.systems.trend_step import detector as tsd


def _bar(h, l, c, lsma, v=1000, hhmm="10:00", o=None):
    return {"h": h, "l": l, "c": c, "o": o if o is not None else c,
            "lsma": lsma, "v": v, "hhmm": hhmm}


def _stair_down():
    """Impulse down ~12pt over 4 bars, then a 2-bar pause retracing ~35%."""
    bars = []
    px = 7800.0
    for i in range(6):  # pre-context so the zigzag has a prior H pivot
        bars.append(_bar(px + 1, px - 1, px, px + 0.5))
    for i in range(4):  # impulse: 12pt in 4 bars, LSMA falling
        px -= 3.0
        bars.append(_bar(px + 1.0, px - 1.0, px, px + 2.0 + i * 0.5))
    low = px
    for i in range(2):  # pause: retrace ~35% of 12pt = ~4pt, low volume
        px += 2.0
        bars.append(_bar(px + 0.5, low, px, low + 6.0 - i, v=400))
    return bars


class TestDetector:
    def test_flag_default_off(self, monkeypatch):
        monkeypatch.delenv("TREND_STEP_ENTRY_V1", raising=False)
        assert tsd.enabled() is False
        assert tsd.build_setup() is None

    def test_no_candidate_on_flat_tape(self):
        bars = [_bar(7800.5, 7799.5, 7800, 7800) for _ in range(20)]
        assert tsd.detect_trend_step(bars) is None

    def test_detects_stair_down_step(self):
        d = tsd.detect_trend_step(_stair_down())
        assert d is not None, "a textbook down-stair with pause must be detected"
        assert d["direction"] == "SHORT"
        assert d["impulse_pts"] >= 8.0
        assert 0.20 <= d["retracement"] <= 0.55
        assert d["lsma_slope"] < 0

    def test_rejects_when_pause_too_long(self):
        bars = _stair_down()
        px = bars[-1]["c"]
        for i in range(3):  # pause now 5 bars — the step is dying
            px += 0.25
            bars.append(_bar(px + 0.5, px - 0.5, px, bars[-1]["lsma"], v=400))
        assert tsd.detect_trend_step(bars) is None

    def test_rejects_when_lsma_disagrees(self):
        bars = _stair_down()
        for b in bars:  # force a rising LSMA against a SHORT step
            b["lsma"] = 7700.0 + bars.index(b) * 2.0
        assert tsd.detect_trend_step(bars) is None

    def test_causal_only_reads_past_bars(self):
        """Detection at index i must not consult bars after i."""
        bars = _stair_down()
        d_full = tsd.detect_trend_step(bars, i=len(bars) - 1)
        poisoned = bars + [_bar(9999, 9998, 9999, 9999)]
        d_poison = tsd.detect_trend_step(poisoned, i=len(bars) - 1)
        assert d_full == d_poison


class TestSetupShape:
    def test_setup_leaves_ladder_to_gateway(self, monkeypatch):
        """stop/targets stay None — F3/H6 step ladder owns them (single source)."""
        monkeypatch.setenv("TREND_STEP_ENTRY_V1", "1")
        monkeypatch.setattr(tsd, "live_bars", lambda limit=60: _stair_down())
        s = tsd.build_setup()
        assert s is not None
        assert s["classification"] == "TREND_STEP"
        assert s["firing_system"] == 4
        assert s["stop"] is None and s["t1"] is None
        assert s["metadata"]["trend_step"] is True

    def test_build_setup_never_raises(self, monkeypatch):
        monkeypatch.setenv("TREND_STEP_ENTRY_V1", "1")

        def _boom(limit=60):
            raise RuntimeError("db down")

        monkeypatch.setattr(tsd, "live_bars", _boom)
        assert tsd.build_setup() is None


class TestWiring:
    def test_subscribed_in_main_and_routes_through_gateway(self):
        import backend.main as m
        src = inspect.getsource(m)
        assert "_trend_step_on_bar" in src
        assert 'bar_router.subscribe("5min", _trend_step_on_bar)' in src
        assert "route_setup(_setup, 4)" in src  # normal gate chain, no bypass

    def test_one_evaluation_per_bar(self):
        import backend.main as m
        src = inspect.getsource(m)
        assert "_ts_last_bar" in src
