"""VAP Recompute — Real bid/ask footprint from Sierra SCID tick data.

Reads raw ticks from SCID file, computes REAL bid/ask per price level.
Replaces DLL's degraded proportional distribution (MaintainVolumeAtPriceData=0).

Memory-bounded: deque(maxlen=30) bars, max 500 levels per bar.
"""

import json
import logging
import os
import struct
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────

SCID_HEADER_SIZE = 56
SCID_RECORD_SIZE = 40
SCID_RECORD_FMT = "<q4f4I"  # int64 + 4 floats + 4 uint32

SC_EPOCH = datetime(1899, 12, 30)
PRICE_SCALE = 100.0       # SCID stores price * 100
TICK_SIZE = 0.25           # MES tick size in points
IMB_THRESHOLD = 2.5        # 250% ratio for imbalance detection

MAX_BARS = 30              # Maximum bars to retain
MAX_LEVELS_PER_BAR = 500   # Safety cap per bar
BAR_DURATION_SEC = 180     # 3-minute bars (matching Sierra chart)
READ_BATCH_SIZE = 4096     # Records per read batch
SESSION_GAP_SEC = 300      # 5 min gap = new session


# ── Data structures ───────────────────────────────────────────

class PriceLevel:
    """Volume at a single price level."""
    __slots__ = ("bid_vol", "ask_vol")

    def __init__(self):
        self.bid_vol = 0
        self.ask_vol = 0

    @property
    def total(self) -> int:
        return self.bid_vol + self.ask_vol

    @property
    def delta(self) -> int:
        return self.ask_vol - self.bid_vol


class FootprintBar:
    """Aggregated footprint for one 3-minute bar."""
    __slots__ = (
        "bar_start_ts", "open", "high", "low", "close",
        "total_volume", "total_delta", "levels", "_level_count",
    )

    def __init__(self, ts: float, price: float):
        self.bar_start_ts = ts
        self.open = price
        self.high = price
        self.low = price
        self.close = price
        self.total_volume = 0
        self.total_delta = 0
        self.levels: Dict[int, PriceLevel] = {}  # key = price * 4 (tick index)
        self._level_count = 0

    def add_tick(self, price: float, bid_vol: int, ask_vol: int):
        """Add a tick to this bar. Bounded by MAX_LEVELS_PER_BAR."""
        if price > self.high:
            self.high = price
        if price < self.low:
            self.low = price
        self.close = price

        vol = bid_vol + ask_vol
        self.total_volume += vol
        self.total_delta += (ask_vol - bid_vol)

        tick_key = int(round(price / TICK_SIZE))
        if tick_key not in self.levels:
            if self._level_count >= MAX_LEVELS_PER_BAR:
                return  # bounded — skip excess levels
            self.levels[tick_key] = PriceLevel()
            self._level_count += 1

        lvl = self.levels[tick_key]
        lvl.bid_vol += bid_vol
        lvl.ask_vol += ask_vol

    def to_dict(self, idx: int) -> dict:
        """Convert to spec-compliant JSON dict."""
        # Find POC
        poc_key = 0
        poc_vol = 0
        for key, lvl in self.levels.items():
            if lvl.total > poc_vol:
                poc_vol = lvl.total
                poc_key = key

        poc_price = poc_key * TICK_SIZE

        # Stacked imbalance detection
        sorted_keys = sorted(self.levels.keys())
        max_buy_stack = 0
        max_sell_stack = 0
        cur_buy = 0
        cur_sell = 0

        for key in sorted_keys:
            lvl = self.levels[key]
            is_buy_imb = lvl.bid_vol > 0 and lvl.ask_vol / lvl.bid_vol >= IMB_THRESHOLD
            is_sell_imb = lvl.ask_vol > 0 and lvl.bid_vol / lvl.ask_vol >= IMB_THRESHOLD

            if is_buy_imb:
                cur_buy += 1
                cur_sell = 0
                if cur_buy > max_buy_stack:
                    max_buy_stack = cur_buy
            elif is_sell_imb:
                cur_sell += 1
                cur_buy = 0
                if cur_sell > max_sell_stack:
                    max_sell_stack = cur_sell
            else:
                cur_buy = 0
                cur_sell = 0

        # Build levels array
        levels_out = []
        for key in sorted_keys:
            lvl = self.levels[key]
            price = key * TICK_SIZE
            is_buy_imb = lvl.bid_vol > 0 and lvl.ask_vol / lvl.bid_vol >= IMB_THRESHOLD
            is_sell_imb = lvl.ask_vol > 0 and lvl.bid_vol / lvl.ask_vol >= IMB_THRESHOLD
            levels_out.append({
                "p": round(price, 2),
                "bid": lvl.bid_vol,
                "ask": lvl.ask_vol,
                "d": lvl.delta,
                "ib": is_buy_imb,
                "is": is_sell_imb,
            })

        return {
            "idx": idx,
            "o": round(self.open, 2),
            "h": round(self.high, 2),
            "l": round(self.low, 2),
            "c": round(self.close, 2),
            "vol": self.total_volume,
            "delta": self.total_delta,
            "poc_price": round(poc_price, 2),
            "poc_vol": poc_vol,
            "stacked_buy": max_buy_stack,
            "stacked_sell": max_sell_stack,
            "levels": levels_out,
        }


# ── SCID Reader ───────────────────────────────────────────────

def scid_ts_to_unix(scid_us: int) -> float:
    """Convert SCDateTimeMS (microseconds since 1899-12-30) to Unix timestamp."""
    days = scid_us / (86400 * 1_000_000)
    dt = SC_EPOCH + timedelta(days=days)
    return dt.timestamp()


def parse_scid_record(data: bytes) -> Optional[Tuple[float, float, int, int]]:
    """Parse a single SCID record. Returns (unix_ts, price, bid_vol, ask_vol) or None."""
    if len(data) < SCID_RECORD_SIZE:
        return None

    scid_ts, o, h, l, c, trades, vol, bid, ask = struct.unpack(SCID_RECORD_FMT, data)

    if vol == 0:
        return None  # padding record

    price = c / PRICE_SCALE
    unix_ts = scid_ts_to_unix(scid_ts) if scid_ts > 0 else 0.0

    return (unix_ts, price, bid, ask)


# ── Main Recomputer ───────────────────────────────────────────

class VAPRecomputer:
    """Reads SCID ticks, builds real bid/ask footprint bars.

    Memory-bounded: at most MAX_BARS bars in deque.
    """

    def __init__(self, scid_path: Optional[str] = None):
        self.scid_path = scid_path or os.path.expanduser(
            "~/SierraChart/Data/MESM26_FUT_CME.scid"
        )
        self.bars: deque = deque(maxlen=MAX_BARS)
        self._current_bar: Optional[FootprintBar] = None
        self._current_bar_end_ts: float = 0
        self._file_offset: int = SCID_HEADER_SIZE
        self._last_valid_ts: float = 0
        self._ticks_processed: int = 0
        self._ticks_dropped: int = 0

    def process_tick(self, ts: float, price: float, bid_vol: int, ask_vol: int):
        """Process a single tick. Creates/closes bars as needed."""
        if ts <= 0:
            ts = self._last_valid_ts
        else:
            self._last_valid_ts = ts

        # Session gap detection
        if (self._current_bar is not None and
                ts - self._current_bar.bar_start_ts > SESSION_GAP_SEC):
            self.close_bar()

        # Bar boundary
        if self._current_bar is None or ts >= self._current_bar_end_ts:
            if self._current_bar is not None:
                self.close_bar()
            self._current_bar = FootprintBar(ts, price)
            self._current_bar_end_ts = ts + BAR_DURATION_SEC

        self._current_bar.add_tick(price, bid_vol, ask_vol)
        self._ticks_processed += 1

    def close_bar(self):
        """Finalize current bar and add to history."""
        if self._current_bar is not None:
            self.bars.append(self._current_bar)
            self._current_bar = None

    def poll_scid(self) -> int:
        """Read new ticks from SCID file since last offset. Returns count."""
        if not os.path.exists(self.scid_path):
            logger.warning("SCID file not found: %s", self.scid_path)
            return 0

        file_size = os.path.getsize(self.scid_path)
        if self._file_offset >= file_size:
            return 0

        count = 0
        try:
            with open(self.scid_path, "rb") as f:
                f.seek(self._file_offset)

                while self._file_offset + SCID_RECORD_SIZE <= file_size:
                    batch_bytes = f.read(
                        min(READ_BATCH_SIZE * SCID_RECORD_SIZE,
                            file_size - self._file_offset)
                    )
                    if not batch_bytes:
                        break

                    for i in range(0, len(batch_bytes), SCID_RECORD_SIZE):
                        chunk = batch_bytes[i:i + SCID_RECORD_SIZE]
                        if len(chunk) < SCID_RECORD_SIZE:
                            break

                        parsed = parse_scid_record(chunk)
                        if parsed is None:
                            self._ticks_dropped += 1
                            self._file_offset += SCID_RECORD_SIZE
                            continue

                        ts, price, bid, ask = parsed
                        self.process_tick(ts, price, bid, ask)
                        self._file_offset += SCID_RECORD_SIZE
                        count += 1

        except OSError as e:
            logger.warning("SCID read error: %s", e)

        return count

    def get_footprint(self, num_bars: int = 30) -> dict:
        """Return spec-compliant footprint JSON dict."""
        # Include current building bar
        all_bars = list(self.bars)
        if self._current_bar is not None:
            all_bars.append(self._current_bar)

        # Limit to requested count
        bars_to_use = all_bars[-num_bars:]

        # Session cumulative delta
        cum_delta = sum(b.total_delta for b in bars_to_use)

        return {
            "type": "footprint",
            "version": "v9.2.1-python",
            "export_ts": int(time.time()),
            "bar_count": len(bars_to_use),
            "cumulative_delta": cum_delta,
            "bars": [b.to_dict(i) for i, b in enumerate(bars_to_use)],
        }

    def to_json(self, num_bars: int = 30) -> str:
        """Return spec-compliant footprint as JSON string."""
        return json.dumps(self.get_footprint(num_bars))

    @property
    def stats(self) -> dict:
        return {
            "ticks_processed": self._ticks_processed,
            "ticks_dropped": self._ticks_dropped,
            "bars_in_memory": len(self.bars),
            "current_bar_active": self._current_bar is not None,
            "file_offset": self._file_offset,
        }

    def seek_to_recent(self, lookback_seconds: int = 5400):
        """Seek SCID file to ~N seconds before now. Default: 90 minutes."""
        if not os.path.exists(self.scid_path):
            return

        file_size = os.path.getsize(self.scid_path)
        total_recs = (file_size - SCID_HEADER_SIZE) // SCID_RECORD_SIZE

        # Estimate: ~200 ticks/second average → lookback_seconds * 200 records
        est_records = lookback_seconds * 200
        start_rec = max(0, total_recs - est_records)
        self._file_offset = SCID_HEADER_SIZE + start_rec * SCID_RECORD_SIZE
