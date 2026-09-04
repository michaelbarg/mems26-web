"""T-252 regression — one thesis per forming bar, and a timer that can settle cost.

Root, read in the code (not inferred from the log):
`five_min_system.py:1774` does `self._bar_buffer[-1] = bar`, REPLACING the
in-progress 5-min bar, and `api/v9/bars.py:197` publishes a "5min" event on
every bridge push. So `_delta_dbl_on_bar` re-ran every 2-5 seconds against the
same forming bar and, while the pattern condition held, emitted a fresh setup
each time.

Measured on 2026-09-04: 129 `S2_DELTA_DBL_LONG` shadow trades in 11 distinct
minutes; #1014..#1037 is 24 of them inside 69 seconds with identical
stop/T1/T2/T3. Deduping the whole shadow book by (pattern, direction, 5-min
bar) takes it from 167 trades / +$1,509.15 to 42 trades / **-$2,060.75** — the
sign of the day flips, in the flattering direction. Nothing that quotes a raw
shadow count is usable until this is fixed.

The gateway's existing DEDUP_FIRE_GUARD cannot catch it: it keys on entry price
+-0.5pt inside 30s, and this burst walked a 1.00pt range over 69 seconds.
"""
import pytest

from backend.v9.systems.five_min.patterns.delta_dbl import (
    is_new_thesis, reset_theses, thesis_key,
)


def _setup(direction="LONG", trig="2026-09-04T15:40:00", t1="2026-09-04T15:10:00",
           t2="2026-09-04T15:25:00", entry=7721.0):
    return {
        "pattern": "S2_DELTA_DBL_%s" % direction,
        "direction": direction,
        "entry_price": entry,
        "metadata": {"trigger_bar_ts": trig, "t1_bar_ts": t1, "t2_bar_ts": t2},
    }


@pytest.fixture(autouse=True)
def _clean():
    reset_theses()
    yield
    reset_theses()


def test_same_thesis_emits_once_however_often_the_bar_is_republished():
    """The real shape of #1014..#1037: same bar, entry walking with the tick."""
    entries = [7721.0, 7721.0, 7721.0, 7721.25, 7721.5, 7721.5, 7721.5,
               7721.75, 7721.75, 7721.75, 7722.0, 7721.5]
    emitted = [e for e in entries if is_new_thesis(_setup(entry=e))]
    assert len(emitted) == 1, "24 re-evaluations of one forming bar = ONE thesis"
    assert emitted[0] == 7721.0


def test_entry_price_keying_is_why_the_old_guard_leaked():
    """DEDUP_FIRE_GUARD's key (+-0.5pt) splits this single thesis in two."""
    lo, hi = 7721.0, 7722.0
    assert abs(hi - lo) > 0.5          # outside the gateway guard's tolerance
    assert thesis_key(_setup(entry=lo)) == thesis_key(_setup(entry=hi))


def test_next_bar_is_a_new_thesis():
    assert is_new_thesis(_setup(trig="2026-09-04T15:40:00")) is True
    assert is_new_thesis(_setup(trig="2026-09-04T15:40:00")) is False
    assert is_new_thesis(_setup(trig="2026-09-04T15:45:00")) is True


def test_both_directions_are_independent_theses():
    assert is_new_thesis(_setup("LONG")) is True
    assert is_new_thesis(_setup("SHORT")) is True
    assert is_new_thesis(_setup("LONG")) is False


def test_a_different_double_on_the_same_trigger_bar_is_a_different_thesis():
    """The swing bars are part of the identity, not just the trigger."""
    assert is_new_thesis(_setup(t1="2026-09-04T15:10:00")) is True
    assert is_new_thesis(_setup(t1="2026-09-04T14:55:00")) is True


def test_fails_open_when_the_bar_carries_no_timestamp():
    """Rule 1: an unknown must not be laundered into a silent drop."""
    s = _setup()
    s["metadata"]["trigger_bar_ts"] = None
    assert is_new_thesis(s) is True
    assert is_new_thesis(s) is True
    assert is_new_thesis(None) is True


def test_memory_is_bounded():
    for i in range(500):
        is_new_thesis(_setup(trig="2026-09-04T%02d:%02d:00" % (i // 60, i % 60)))
    from backend.v9.systems.five_min.patterns import delta_dbl
    assert len(delta_dbl._SEEN_THESES) <= delta_dbl._SEEN_CAP


def test_detector_stamps_the_bar_timestamps_it_used():
    """Indices slide as the buffer rolls; only timestamps identify a thesis."""
    from backend.v9.systems.five_min.patterns import delta_dbl
    bars = [{"ts": "2026-09-04T%02d:%02d:00" % (14 + i // 12, (i % 12) * 5),
             "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "v": 10}
            for i in range(12)]
    # a double bottom: two equal lows, then a delta-driven breakout close
    bars[2]["l"] = 90.0
    bars[8]["l"] = 90.0
    bars[11].update({"c": 102.0, "o": 100.0, "h": 102.0})
    bars[10]["h"] = 101.0
    deltas = [0.0] * 11 + [500.0]
    s = delta_dbl.detect_delta_dbl(bars, "Normal", 4.0, deltas)
    if s is None:
        pytest.skip("fixture does not satisfy the pattern's geometry")
    md = s["metadata"]
    assert md["trigger_bar_ts"] == bars[-1]["ts"]
    assert md["t1_bar_ts"] == bars[md["t1_bar"]]["ts"]
    assert md["t2_bar_ts"] == bars[md["t2_bar"]]["ts"]


# ------------------------------------------------------- the in-code timer

def test_bar_level_detector_reports_cost_split_by_mode():
    """The log cannot settle the cost question; get_stats() can.

    BarRouter prints a handler's time only above 100ms (a truncated
    distribution — the mean of what was printed is not the mean) and reports
    ONE number for shadow and live together. That is why 19:00 and 20:00, both
    with 70 open trades, differed 2x while 22:00 with 47 open was cheaper than
    21:00 with 22: the log was never measuring what the question asked.
    """
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    d = BarLevelDetector.__new__(BarLevelDetector)
    d._bars_processed = 3
    d._mode_secs = {"shadow": 0.020, "live": 0.004}
    d._mode_trades = {"shadow": 40, "live": 2}
    d._loop_ms_total, d._loop_ms_max, d._loop_bars = 72.0, 40.0, 3
    d._open_by_mode = {"shadow": 40, "live": 2}
    st = d.get_stats()
    assert st["us_per_trade"]["shadow"] == 500.0     # 20ms / 40 visits
    assert st["us_per_trade"]["live"] == 2000.0      # 4ms / 2 visits
    assert st["loop_ms_mean"] == 24.0
    assert st["open_by_mode"] == {"shadow": 40, "live": 2}


def test_timer_reports_none_rather_than_zero_before_any_bar():
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    d = BarLevelDetector.__new__(BarLevelDetector)
    d._bars_processed = 0
    d._mode_secs = {"shadow": 0.0, "live": 0.0}
    d._mode_trades = {"shadow": 0, "live": 0}
    d._loop_ms_total = d._loop_ms_max = 0.0
    d._loop_bars = 0
    d._open_by_mode = {"shadow": 0, "live": 0}
    st = d.get_stats()
    assert st["us_per_trade"] == {"shadow": None, "live": None}
    assert st["loop_ms_mean"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
