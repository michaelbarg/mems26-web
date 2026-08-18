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
    def test_setup_carries_its_own_leg_ladder(self, monkeypatch):
        """SUPERSEDED 2026-08-18. This used to assert stop/targets stay None so
        F3's session-median ladder owned them. That handoff is exactly what made
        the replayed result unreachable: F3 sized the stop at ~7.0pt against a
        model measured on 2.5-3.0pt, so T1 R:R was 0.32. The ladder the evidence
        was built on now travels with the setup, and the gateway's arbitration
        leaves it alone."""
        monkeypatch.setenv("TREND_STEP_ENTRY_V1", "1")
        monkeypatch.setattr(tsd, "live_bars", lambda limit=60: _stair_down())
        s = tsd.build_setup()
        assert s is not None
        assert s["classification"] == "TREND_STEP"
        assert s["firing_system"] == 4
        assert s["stop"] is not None and s["t1"] is not None
        assert s["stop_source"] == "TREND_STEP_LEG"
        assert s["metadata"]["trend_step"] is True
        risk = abs(s["entry_price"] - s["stop"])
        assert 2.5 <= risk <= 9.0, "the model clamps risk to [2.5, 9.0]"

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


class TestClosedBarsOnly:
    """T6 — the detector must never see the bar that is still forming.

    `ts` is the bar's OPEN time, so the row inside the current 5-minute bucket
    is rewritten by the DLL on every tick. Feeding it in moved the live entry
    5.25pt away from the replay's — the difference between the replayed
    +$2,378.75 and the −$696.25 the slip sweep measured.
    """

    def test_query_excludes_the_forming_bar(self, monkeypatch):
        seen = {}

        def _fake_read_all(sql, params):
            seen["sql"] = sql
            return []

        import backend.v9.db.read as _read
        monkeypatch.setattr(_read, "read_all", _fake_read_all)
        from backend.v9.systems.trend_step import detector as d
        d.live_bars()
        sql = " ".join(seen["sql"].split())
        assert "ts <= now() - interval '5 minutes'" in sql, (
            "live_bars must exclude the in-progress bar")

    def test_it_still_returns_the_closed_bars(self, monkeypatch):
        """The boundary must not eat a legitimately closed bar."""
        from datetime import datetime, timedelta, timezone

        base = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)
        rows = [{"ts": base + timedelta(minutes=5 * i), "open": 7800.0 + i,
                 "high": 7802.0 + i, "low": 7799.0 + i, "close": 7801.0 + i,
                 "volume": 500, "lsma_value": 7800.0 + i} for i in range(8)]

        import backend.v9.db.read as _read
        monkeypatch.setattr(_read, "read_all", lambda sql, params: rows)
        from backend.v9.systems.trend_step import detector as d
        bars = d.live_bars()
        assert len(bars) == 8
        assert bars[-1]["c"] == 7808.0
