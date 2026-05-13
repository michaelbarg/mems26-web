"""Tests: VAPRecomputer — real bid/ask footprint from SCID ticks.

Coverage targets:
- Tick classification (bid/ask)
- Bar aggregation
- Bounded memory
- Schema compliance
- No silent drops
- SCID parsing
"""

import json
import os
import struct
import tempfile
import time
from datetime import datetime, timedelta

import pytest

from bridge.v9_streams.vap_recompute import (
    VAPRecomputer,
    FootprintBar,
    PriceLevel,
    parse_scid_record,
    scid_ts_to_unix,
    SCID_HEADER_SIZE,
    SCID_RECORD_SIZE,
    SCID_RECORD_FMT,
    MAX_BARS,
    MAX_LEVELS_PER_BAR,
    BAR_DURATION_SEC,
    IMB_THRESHOLD,
    SC_EPOCH,
    PRICE_SCALE,
    TICK_SIZE,
)


# ── Helpers ───────────────────────────────────────────────────

def make_scid_file(records: list) -> str:
    """Create a temporary SCID file with given records.

    Each record: (scid_ts_us, open, high, low, close, trades, vol, bid, ask)
    """
    fd, path = tempfile.mkstemp(suffix=".scid")
    with os.fdopen(fd, "wb") as f:
        # Header: 56 bytes — "SCID" + version(56) + record_size(40) + padding
        header = b"SCID"
        header += struct.pack("<I", 56)   # version
        header += struct.pack("<I", 40)   # record size
        header += b"\x00" * (56 - len(header))
        f.write(header)

        for rec in records:
            scid_ts, o, h, l, c, trades, vol, bid, ask = rec
            f.write(struct.pack(SCID_RECORD_FMT, scid_ts, o, h, l, c, trades, vol, bid, ask))

    return path


def unix_to_scid_us(unix_ts: float) -> int:
    """Convert Unix timestamp to SCDateTimeMS (microseconds since 1899-12-30)."""
    dt = datetime.fromtimestamp(unix_ts)
    delta = dt - SC_EPOCH
    return int(delta.total_seconds() * 1_000_000)


def make_tick(ts_unix: float, price: float, bid: int = 0, ask: int = 0):
    """Create a single SCID record tuple."""
    scid_ts = unix_to_scid_us(ts_unix)
    p = price * PRICE_SCALE
    return (scid_ts, p, p, p, p, 1, bid + ask, bid, ask)


# ── SCID Parsing ─────────────────────────────────────────────

class TestSCIDParsing:

    def test_scid_ts_roundtrip(self):
        now = time.time()
        scid = unix_to_scid_us(now)
        back = scid_ts_to_unix(scid)
        assert abs(back - now) < 1.0

    def test_parse_valid_record(self):
        ts = unix_to_scid_us(time.time())
        data = struct.pack(SCID_RECORD_FMT,
                           ts, 540000, 540100, 539900, 540050, 1, 5, 2, 3)
        result = parse_scid_record(data)
        assert result is not None
        unix_ts, price, bid, ask = result
        assert price == pytest.approx(5400.50, abs=0.01)
        assert bid == 2
        assert ask == 3

    def test_parse_zero_vol_skipped(self):
        ts = unix_to_scid_us(time.time())
        data = struct.pack(SCID_RECORD_FMT,
                           ts, 540000, 540000, 540000, 540000, 0, 0, 0, 0)
        result = parse_scid_record(data)
        assert result is None

    def test_parse_short_data(self):
        result = parse_scid_record(b"\x00" * 10)
        assert result is None


# ── Tick Classification ──────────────────────────────────────

class TestTickClassification:

    def test_buy_tick(self):
        """Trade at ask = BUY aggressor → ask_vol > 0."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        r.process_tick(ts, 5412.50, bid_vol=0, ask_vol=3)

        bar = r._current_bar
        assert bar is not None
        key = int(round(5412.50 / TICK_SIZE))
        lvl = bar.levels[key]
        assert lvl.ask_vol == 3
        assert lvl.bid_vol == 0

    def test_sell_tick(self):
        """Trade at bid = SELL aggressor → bid_vol > 0."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        r.process_tick(ts, 5412.50, bid_vol=5, ask_vol=0)

        bar = r._current_bar
        key = int(round(5412.50 / TICK_SIZE))
        lvl = bar.levels[key]
        assert lvl.bid_vol == 5
        assert lvl.ask_vol == 0

    def test_split_tick(self):
        """Both bid and ask > 0."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        r.process_tick(ts, 5412.50, bid_vol=2, ask_vol=3)

        bar = r._current_bar
        key = int(round(5412.50 / TICK_SIZE))
        lvl = bar.levels[key]
        assert lvl.bid_vol == 2
        assert lvl.ask_vol == 3


# ── Bar Aggregation ──────────────────────────────────────────

class TestBarAggregation:

    def test_100_ticks_correct_totals(self):
        """100 ticks at known prices → correct bid/ask totals."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        # 50 buy ticks at 5412.50, 50 sell ticks at 5412.25
        for _ in range(50):
            r.process_tick(ts, 5412.50, bid_vol=0, ask_vol=1)
        for _ in range(50):
            r.process_tick(ts + 1, 5412.25, bid_vol=1, ask_vol=0)

        bar = r._current_bar
        assert bar.total_volume == 100
        assert bar.total_delta == 0  # 50 buys - 50 sells = 0

        key_50 = int(round(5412.50 / TICK_SIZE))
        key_25 = int(round(5412.25 / TICK_SIZE))
        assert bar.levels[key_50].ask_vol == 50
        assert bar.levels[key_25].bid_vol == 50

    def test_bar_close_on_time_boundary(self):
        """Bar should close when time exceeds bar duration."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        r.process_tick(ts, 5412.50, 0, 1)
        r.process_tick(ts + BAR_DURATION_SEC + 1, 5413.00, 0, 1)

        # First bar closed, second bar active
        assert len(r.bars) == 1
        assert r._current_bar is not None
        assert r.bars[0].close == 5412.50
        assert r._current_bar.open == 5413.00

    def test_ohlc_correct(self):
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        r.process_tick(ts, 5412.50, 0, 1)  # open
        r.process_tick(ts, 5415.00, 0, 1)  # high
        r.process_tick(ts, 5410.00, 1, 0)  # low
        r.process_tick(ts, 5413.25, 1, 0)  # close

        bar = r._current_bar
        assert bar.open == 5412.50
        assert bar.high == 5415.00
        assert bar.low == 5410.00
        assert bar.close == 5413.25


# ── Bounded Memory ───────────────────────────────────────────

class TestBoundedMemory:

    def test_max_bars_bounded(self):
        """More than MAX_BARS → deque drops oldest."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        # Create MAX_BARS + 10 bars
        for i in range(MAX_BARS + 10):
            ts = time.time() + i * (BAR_DURATION_SEC + 1)
            r.process_tick(ts, 5412.50 + i * 0.25, 0, 1)

        assert len(r.bars) <= MAX_BARS

    def test_max_levels_per_bar(self):
        """More than MAX_LEVELS_PER_BAR levels → excess silently capped."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        # Try to create 600 levels (exceeds 500 cap)
        for i in range(600):
            price = 5000.00 + i * TICK_SIZE
            r.process_tick(ts, price, 0, 1)

        assert r._current_bar._level_count == MAX_LEVELS_PER_BAR

    def test_1m_ticks_memory_bounded(self):
        """1M ticks should not cause unbounded growth."""
        import sys

        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        # Process 100K ticks (scaled down for test speed, pattern same as 1M)
        base_ts = time.time()
        for i in range(100_000):
            ts = base_ts + (i * 0.01)  # 10ms apart
            price = 5412.50 + (i % 20) * TICK_SIZE
            bid = 1 if i % 2 == 0 else 0
            ask = 0 if i % 2 == 0 else 1
            r.process_tick(ts, price, bid, ask)

        # Memory check: bars deque bounded
        assert len(r.bars) <= MAX_BARS
        assert r._ticks_processed == 100_000

        # Check that all bar levels are bounded
        for bar in r.bars:
            assert bar._level_count <= MAX_LEVELS_PER_BAR


# ── Schema Compliance ────────────────────────────────────────

class TestSchemaMatch:

    def test_footprint_schema(self):
        """Output matches FOOTPRINT_TICK_SPEC_V3 schema."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        for i in range(20):
            price = 5412.00 + (i % 4) * TICK_SIZE
            r.process_tick(ts + i * 0.1, price, bid_vol=i % 3, ask_vol=(i + 1) % 3)

        fp = r.get_footprint()

        # Top-level schema
        assert fp["type"] == "footprint"
        assert "version" in fp
        assert "export_ts" in fp
        assert "bar_count" in fp
        assert "cumulative_delta" in fp
        assert "bars" in fp

        # Bar schema
        bar = fp["bars"][0]
        for key in ("idx", "o", "h", "l", "c", "vol", "delta",
                     "poc_price", "poc_vol", "stacked_buy", "stacked_sell", "levels"):
            assert key in bar, f"Missing key: {key}"

        # Level schema
        lvl = bar["levels"][0]
        for key in ("p", "bid", "ask", "d", "ib", "is"):
            assert key in lvl, f"Missing level key: {key}"

    def test_to_json_valid(self):
        """to_json() returns valid JSON."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        r.process_tick(ts, 5412.50, 0, 1)

        j = r.to_json()
        parsed = json.loads(j)
        assert parsed["type"] == "footprint"

    def test_imbalance_flags(self):
        """Level with ask/bid >= 2.5 → ib=True."""
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0

        ts = time.time()
        # 1 sell, 3 buys at same price → ratio 3.0 → ib=True
        r.process_tick(ts, 5412.50, bid_vol=1, ask_vol=0)
        r.process_tick(ts, 5412.50, bid_vol=0, ask_vol=3)

        fp = r.get_footprint()
        lvl = fp["bars"][0]["levels"][0]
        assert lvl["bid"] == 1
        assert lvl["ask"] == 3
        assert lvl["ib"] is True   # 3/1 = 3.0 >= 2.5
        assert lvl["is"] is False


# ── SCID File Integration ────────────────────────────────────

class TestSCIDFile:

    def test_poll_scid_file(self):
        """Read ticks from a real SCID-format file."""
        ts = time.time()
        records = [make_tick(ts + i * 0.1, 5412.50 + (i % 3) * 0.25,
                             bid=1 if i % 2 == 0 else 0,
                             ask=0 if i % 2 == 0 else 1)
                   for i in range(50)]

        path = make_scid_file(records)
        try:
            r = VAPRecomputer(scid_path=path)
            count = r.poll_scid()
            assert count == 50
            assert r._ticks_processed == 50

            fp = r.get_footprint()
            assert fp["bar_count"] >= 1
            assert fp["bars"][0]["vol"] == 50
        finally:
            os.unlink(path)

    def test_poll_scid_incremental(self):
        """Second poll reads only new data."""
        ts = time.time()
        records = [make_tick(ts, 5412.50, ask=1) for _ in range(10)]
        path = make_scid_file(records)

        try:
            r = VAPRecomputer(scid_path=path)
            count1 = r.poll_scid()
            assert count1 == 10

            # Add more records
            with open(path, "ab") as f:
                for _ in range(5):
                    rec = make_tick(ts + 1, 5413.00, bid=1)
                    f.write(struct.pack(SCID_RECORD_FMT, *rec))

            count2 = r.poll_scid()
            assert count2 == 5
            assert r._ticks_processed == 15
        finally:
            os.unlink(path)

    def test_poll_scid_missing_file(self):
        """Missing file → 0 ticks, no crash."""
        r = VAPRecomputer(scid_path="/nonexistent/file.scid")
        count = r.poll_scid()
        assert count == 0


# ── No Silent Drops ──────────────────────────────────────────

class TestNoSilentDrops:

    def test_malformed_record_counted(self):
        """Malformed (zero vol) ticks counted as dropped."""
        ts = time.time()
        records = [
            make_tick(ts, 5412.50, ask=1),       # valid
            (unix_to_scid_us(ts), 0, 0, 0, 0, 0, 0, 0, 0),  # zero vol → dropped
            make_tick(ts + 1, 5413.00, bid=1),   # valid
        ]
        path = make_scid_file(records)

        try:
            r = VAPRecomputer(scid_path=path)
            r.poll_scid()
            assert r._ticks_processed == 2
            assert r._ticks_dropped == 1
        finally:
            os.unlink(path)

    def test_stats_accurate(self):
        r = VAPRecomputer.__new__(VAPRecomputer)
        r.bars = __import__("collections").deque(maxlen=MAX_BARS)
        r._current_bar = None
        r._current_bar_end_ts = 0
        r._last_valid_ts = 0
        r._ticks_processed = 0
        r._ticks_dropped = 0
        r._file_offset = SCID_HEADER_SIZE
        r.scid_path = "/nonexistent"

        ts = time.time()
        for i in range(10):
            r.process_tick(ts, 5412.50, 0, 1)

        stats = r.stats
        assert stats["ticks_processed"] == 10
        assert stats["ticks_dropped"] == 0


# ── PriceLevel and FootprintBar units ────────────────────────

class TestPriceLevel:

    def test_total_and_delta(self):
        lvl = PriceLevel()
        lvl.bid_vol = 10
        lvl.ask_vol = 25
        assert lvl.total == 35
        assert lvl.delta == 15

    def test_empty_level(self):
        lvl = PriceLevel()
        assert lvl.total == 0
        assert lvl.delta == 0


class TestFootprintBarUnit:

    def test_to_dict_keys(self):
        bar = FootprintBar(time.time(), 5412.50)
        bar.add_tick(5412.50, 5, 10)
        d = bar.to_dict(0)
        assert d["idx"] == 0
        assert d["poc_price"] == 5412.50
        assert d["poc_vol"] == 15
        assert d["vol"] == 15
        assert d["delta"] == 5  # ask(10) - bid(5)

    def test_stacked_imbalance(self):
        """3+ consecutive buy imbalances → stacked_buy >= 3."""
        bar = FootprintBar(time.time(), 5412.00)
        # Create 4 consecutive levels with buy imbalance (ask/bid >= 2.5)
        for i in range(4):
            price = 5412.00 + i * TICK_SIZE
            bar.add_tick(price, bid_vol=1, ask_vol=3)  # ratio 3.0

        d = bar.to_dict(0)
        assert d["stacked_buy"] >= 3
