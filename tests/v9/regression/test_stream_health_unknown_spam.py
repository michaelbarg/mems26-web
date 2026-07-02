"""StreamHealth log-spam fix (cleanup audit §B1, 2026-07-02).

Live problem: the bridge pushes continuous twins (cvd_continuous /
bars_5min_continuous) that StreamHealth doesn't track → thousands of
"unknown stream" WARNINGs per day drowned real alerts (bit the night
audit twice on 2026-07-02). Fix: known-untracked = silent ack; truly
unknown = rate-limited (first + every 1000th). Fails on pre-fix code.
"""
import logging

from backend.v9.services.stream_health.health import StreamHealthService


def _warnings(caplog):
    return [r for r in caplog.records
            if r.levelno == logging.WARNING and "unknown stream" in r.getMessage()]


def test_continuous_twins_are_silent(caplog):
    svc = StreamHealthService()
    with caplog.at_level(logging.WARNING):
        for _ in range(50):
            svc.record_push("cvd_continuous")
            svc.record_push("bars_5min_continuous")
    assert _warnings(caplog) == [], "continuous twins must not spam the log (pre-fix code warns 100x here)"


def test_truly_unknown_is_rate_limited_not_silent(caplog):
    """A genuinely unknown stream must stay LOUD (no-silent-failures) but
    bounded: 2500 pushes → warnings at #1, #1000, #2000 only."""
    svc = StreamHealthService()
    with caplog.at_level(logging.WARNING):
        for _ in range(2500):
            svc.record_push("mystery_stream")
    w = _warnings(caplog)
    assert len(w) == 3, f"expected 3 rate-limited warnings, got {len(w)}"
    assert "seen 1000 times" in w[1].getMessage()


def test_canonical_stream_still_recorded():
    svc = StreamHealthService()
    svc.record_push("live_price")
    svc.record_push("live_price")
    assert svc._streams["live_price"].push_count == 2
