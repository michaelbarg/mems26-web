"""The staircase must reach the tape the way the replay measured it.

Two live-path defects, both found on 18.08 by comparing the replayed model
against what actually shipped:

1. ONE STAIRCASE, FOUR ENTRIES. `_trend_step_on_bar` deduped on the bar
   timestamp only. That stops a double evaluation of the same bar — it does
   nothing about the same step still qualifying on the next bar, and the next.
   14.08: four entries on one staircase, -$555.

2. THE STOP WAS 2.3x THE MODEL. The setup shipped `stop=None` on purpose and
   let F3's session-median ladder size it (~7.0pt). The replayed edge was
   measured on a pause-relative stop of 2.5-3.0pt. At 7.0pt the T1 R:R is
   0.32 — the replayed +$2,801.25 was not merely missed, it was unreachable
   by construction.
"""
import pytest


def _bars_with_a_surviving_step():
    """A down-staircase that keeps qualifying for three consecutive bars."""
    bars, px = [], 7800.0
    for t in range(6):
        px -= 2.0
        bars.append({"o": px + 1, "h": px + 1.5, "l": px - 0.5, "c": px,
                     "v": 900, "lsma": px + 2 - 0.3 * t, "hhmm": "10:%02d" % (t * 5)})
    for t in range(3):
        bars.append({"o": px, "h": px + 2.0, "l": px - 0.25, "c": px + 0.5,
                     "v": 500, "lsma": px + 0.5 - 0.3 * (6 + t),
                     "hhmm": "10:%02d" % (30 + t * 5)})
    return bars


class TestOneStaircaseIsOneEvent:
    def test_the_step_carries_a_stable_identity(self):
        from backend.v9.systems.trend_step.detector import detect_trend_step
        bars = _bars_with_a_surviving_step()
        ids = {detect_trend_step(bars, i)["step_id"]
               for i in range(6, len(bars)) if detect_trend_step(bars, i)}
        assert len(ids) == 1, (
            "the same staircase produced %d identities — dedup cannot work" % len(ids))

    def test_the_identity_reaches_the_setup(self):
        import inspect
        from backend.v9.systems.trend_step import detector
        src = inspect.getsource(detector.build_setup)
        assert '"step_id"' in src

    def test_main_dedups_on_the_step_not_only_the_bar(self):
        import inspect, backend.main as m
        src = inspect.getsource(m)
        i = src.index("_trend_step_on_bar")
        window = src[i:i + 4000]
        assert 'step_id' in window, (
            "backend.main must dedup on the step identity; deduping on bar_ts "
            "alone let one staircase fire on every bar it survived")

    def test_a_different_step_is_not_suppressed(self):
        """The dedup must not swallow a genuinely new staircase."""
        from backend.v9.systems.trend_step.detector import detect_trend_step
        a = detect_trend_step(_bars_with_a_surviving_step(), 6)
        bars = _bars_with_a_surviving_step()
        for b in bars:                      # same shape, 20pt lower on the tape
            for k in ("o", "h", "l", "c", "lsma"):
                if b[k] is not None:
                    b[k] -= 20.0
        b2 = detect_trend_step(bars, 6)
        assert a and b2 and a["step_id"] != b2["step_id"]


class TestTheStopIsTheModelledStop:
    def test_the_setup_no_longer_ships_without_a_stop(self):
        from backend.v9.systems.trend_step.detector import detect_trend_step
        d = detect_trend_step(_bars_with_a_surviving_step(), 7)
        assert d and d["stop"] is not None

    def test_the_risk_matches_the_replayed_model(self):
        """pause extreme + 10% of the impulse, clamped [2.5, 9.0]."""
        from backend.v9.systems.trend_step.detector import detect_trend_step
        d = detect_trend_step(_bars_with_a_surviving_step(), 7)
        imp, pause_ext, entry = d["impulse_pts"], d["pause_extreme"], d["entry_price"]
        want = min(max(pause_ext + max(0.5, 0.10 * imp) - entry, 2.5), 9.0)
        assert d["risk_pts"] == pytest.approx(want, abs=0.26)

    def test_the_stop_is_nothing_like_the_session_median_stop(self):
        """F3 gave ~7.0pt on this tape; the model gives 2.5-3.0."""
        from backend.v9.systems.trend_step.detector import detect_trend_step
        d = detect_trend_step(_bars_with_a_surviving_step(), 7)
        assert d["risk_pts"] <= 4.0

    def test_t1_clears_the_rr_gate_it_has_to_pass(self):
        from backend.v9.systems.trend_step.detector import detect_trend_step
        d = detect_trend_step(_bars_with_a_surviving_step(), 7)
        rr = abs(d["t1"] - d["entry_price"]) / d["risk_pts"]
        assert rr >= 1.0, "T1 R:R %.2f — the 0.32 defect is still here" % rr

    def test_the_ladder_is_strictly_increasing(self):
        from backend.v9.systems.trend_step.detector import detect_trend_step
        d = detect_trend_step(_bars_with_a_surviving_step(), 7)
        e = d["entry_price"]
        assert abs(d["t1"] - e) < abs(d["t2"] - e) < abs(d["t3"] - e)
        for t in (d["t1"], d["t2"], d["t3"]):
            assert (t < e) == (d["direction"] == "SHORT")


class TestArbitrationIsRecorded:
    def test_f3_leaves_a_native_ladder_alone(self):
        import inspect
        from backend.v9.gateway import trading_gateway as g
        src = inspect.getsource(g)
        assert "_STEP_NATIVE_STOP_SOURCES" in src
        assert "TREND_STEP_LEG" in src

    def test_every_override_names_both_writers(self):
        """T-07: the resolver lost 15 of 15 and left no trace."""
        import inspect
        from backend.v9.gateway import trading_gateway as g
        src = inspect.getsource(g)
        assert "STOP ARBITRATION" in src
        i = src.index("STOP ARBITRATION")
        assert src.count("STOP ARBITRATION") >= 2, (
            "both outcomes — kept and overridden — must be logged")
