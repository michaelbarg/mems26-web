"""F2 (2026-08-12) — the "5min" topic is SINGLE-fed by the Sierra path.

SYSTEM2_FULL_AUDIT_2026-08-11 §7: since fe86c3ee (2026-05-12) TWO publishers
wrote the BarRouter "5min" topic — bars.py:764 (Sierra, ts=str(datetime),
vol>100k guard) and bar_aggregator_5min.py (local tick aggregator,
ts=isoformat(), NO volume guard, cumulative volume 100-800× real).
FiveMinSystem deduped on the RAW ts string, so the same instant in the two
formats entered the S2 buffer TWICE from two different price series.

Regression contract:
  1. _canon_bar_ts collapses every representation of one instant to one key.
  2. process_bar: one real bar arriving in BOTH formats → ONE buffer entry,
     ONE bar count (fails on the pre-fix string compare).
  3. The aggregator does NOT publish to "5min" unless
     AGGREGATOR_5MIN_PUBLISH_V1=1 (default OFF — Sierra is the canonical
     source per docs/SOURCE_OF_TRUTH.md).
"""
import os
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.systems.five_min.five_min_system import (  # noqa: E402
    FiveMinMode, FiveMinSystem, _canon_bar_ts)
import backend.v9.services.bar_aggregator_5min as agg  # noqa: E402


# ── 1. canonical dedup key ───────────────────────────────────────────────────

def test_canon_ts_collapses_both_publisher_formats():
    sierra = "2026-08-11 16:20:00+00:00"        # str(datetime) — bars.py path
    aggreg = "2026-08-11T16:20:00+00:00"        # isoformat() — aggregator path
    zulu = "2026-08-11T16:20:00Z"
    dt = datetime(2026, 8, 11, 16, 20, tzinfo=timezone.utc)
    keys = {_canon_bar_ts(sierra), _canon_bar_ts(aggreg),
            _canon_bar_ts(zulu), _canon_bar_ts(dt),
            _canon_bar_ts(dt.timestamp())}
    assert len(keys) == 1, f"one instant must map to ONE dedup key: {keys}"


def test_canon_ts_distinct_bars_stay_distinct():
    a = _canon_bar_ts("2026-08-11 16:20:00+00:00")
    b = _canon_bar_ts("2026-08-11 16:25:00+00:00")
    assert a != b


def test_canon_ts_never_raises_on_garbage():
    assert _canon_bar_ts("") == ""
    assert _canon_bar_ts(None) == ""
    assert _canon_bar_ts("not-a-ts") == "not-a-ts"


# ── 2. one bar in two formats → ONE buffer entry ─────────────────────────────

def _bar(ts, vol):
    return {"ts": ts, "o": 7760.0, "h": 7762.0, "l": 7759.0, "c": 7761.0,
            "v": vol, "open": 7760.0, "high": 7762.0, "low": 7759.0,
            "close": 7761.0, "volume": vol}


def _run(coro):
    import asyncio
    return asyncio.new_event_loop().run_until_complete(coro)


def _pin_rth(monkeypatch):
    """Keep the system in DAY_TYPE_MODE regardless of wall-clock: process_bar
    itself flips DAY_TYPE→OVERNIGHT via is_after_firing_close(), and the
    OVERNIGHT branch appends without dedup (out of scope here — S2 cannot
    fire overnight). The audit's double-feed damage is on the RTH dedup path."""
    import backend.v9.gateway.session_gate as sg
    monkeypatch.setattr(sg, "is_after_firing_close", lambda *a, **k: False)


def test_same_instant_two_formats_one_buffer_entry(monkeypatch):
    _pin_rth(monkeypatch)
    s = FiveMinSystem()
    s._hydrated = True   # skip DB boot-hydration — buffer must start empty here
    s._bar_buffer = []   # _bar_buffer is CLASS-level (fms.py:1082) — isolate it
    s.mode = FiveMinMode.DAY_TYPE_MODE
    _run(s.process_bar(_bar("2026-08-11 16:20:00+00:00", 9_000)))    # Sierra form
    n_after_first = len(s._bar_buffer)
    count_after_first = s.buffer_size
    assert n_after_first == 1 and count_after_first >= 1
    _run(s.process_bar(_bar("2026-08-11T16:20:00+00:00", 700_000)))  # aggregator form
    assert len(s._bar_buffer) == n_after_first, (
        "the same instant in the aggregator's ISO-T format must NOT append a "
        "second buffer entry (pre-fix double-feed)")
    assert s.buffer_size == count_after_first, (
        "bar COUNT must not advance on a duplicate instant")


def test_new_instant_still_appends(monkeypatch):
    _pin_rth(monkeypatch)
    s = FiveMinSystem()
    s._hydrated = True   # skip DB boot-hydration — buffer must start empty here
    s._bar_buffer = []   # _bar_buffer is CLASS-level (fms.py:1082) — isolate it
    s.mode = FiveMinMode.DAY_TYPE_MODE
    _run(s.process_bar(_bar("2026-08-11 16:20:00+00:00", 9_000)))
    n1 = len(s._bar_buffer)
    _run(s.process_bar(_bar("2026-08-11 16:25:00+00:00", 8_000)))
    assert len(s._bar_buffer) == n1 + 1


# ── 3. aggregator publish is OFF by default ──────────────────────────────────

class _RouterRecorder:
    def __init__(self):
        self.published = []

    def publish_threadsafe(self, topic, payload):
        self.published.append((topic, payload))


def _closed_bar(vol=700_000):
    now = datetime(2026, 8, 11, 16, 20, tzinfo=timezone.utc)
    return agg.Bar5Min(start_ts=now, end_ts=now, open=7760.0, high=7762.0,
                       low=7759.0, close=7761.0, volume=vol, tick_count=42,
                       session="RTH")


def test_aggregator_does_not_publish_5min_by_default(monkeypatch):
    monkeypatch.delenv("AGGREGATOR_5MIN_PUBLISH_V1", raising=False)
    rec = _RouterRecorder()
    import backend.v9.api.v9.bars as bars_mod
    monkeypatch.setattr(bars_mod, "_bar_router", rec)
    agg._on_bar_close_default(_closed_bar())
    topics = [t for t, _ in rec.published]
    assert "5min" not in topics, (
        "the local tick aggregator must NOT publish to the canonical \"5min\" "
        f"topic by default (Sierra is the single source): {topics}")


def test_aggregator_publish_restorable_by_flag_only(monkeypatch):
    monkeypatch.setenv("AGGREGATOR_5MIN_PUBLISH_V1", "1")
    rec = _RouterRecorder()
    import backend.v9.api.v9.bars as bars_mod
    monkeypatch.setattr(bars_mod, "_bar_router", rec)
    agg._on_bar_close_default(_closed_bar())
    topics = [t for t, _ in rec.published]
    assert topics.count("5min") == 1, topics
