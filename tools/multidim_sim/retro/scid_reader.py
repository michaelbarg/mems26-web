"""
Sierra Chart .scid binary tick file reader.

SCID format (version 1):
  Header: 56 bytes ('SCID' magic + header_size + record_size + version)
  Records: 40 bytes each
    int64   timestamp (microseconds since 1899-12-30 00:00:00 UTC)
    float32 open  (may contain sentinel -1.99e38 on tick data)
    float32 high
    float32 low
    float32 close
    uint32  num_trades
    uint32  total_volume
    uint32  bid_volume
    uint32  ask_volume
"""

import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, List

# Sierra Chart epoch
SC_EPOCH = datetime(1899, 12, 30, tzinfo=timezone.utc)
HEADER_SIZE = 56
RECORD_SIZE = 40
RECORD_FMT = '<qffffIIII'
INVALID_FLOAT_THRESHOLD = -1e30  # Sierra sentinel for missing Open


def _unix_to_sc_microsec(unix_ts: float) -> int:
    """Convert Unix epoch seconds to SC microseconds since 1899-12-30."""
    dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
    delta = dt - SC_EPOCH
    return int(delta.total_seconds() * 1_000_000)


def _sc_microsec_to_datetime(us: int) -> datetime:
    """Convert SC microseconds to Python datetime (UTC)."""
    return SC_EPOCH + timedelta(microseconds=us)


class ScidReader:
    """Read Sierra Chart .scid tick files with efficient binary search."""

    def __init__(self, scid_path: Path):
        self.path = Path(scid_path)
        if not self.path.exists():
            raise FileNotFoundError(f"{self.path} not found")
        self._file_size = self.path.stat().st_size
        self._n_records = (self._file_size - HEADER_SIZE) // RECORD_SIZE

    @property
    def n_records(self) -> int:
        return self._n_records

    def _read_record_ts(self, f, record_idx: int) -> int:
        """Read just the timestamp of a specific record by index."""
        f.seek(HEADER_SIZE + record_idx * RECORD_SIZE)
        buf = f.read(8)
        if len(buf) < 8:
            return 0
        return struct.unpack('<q', buf)[0]

    def _binary_search_start(self, f, target_us: int) -> int:
        """Binary search for the first record with ts >= target_us."""
        lo, hi = 0, self._n_records - 1
        result = self._n_records  # past end if nothing found

        while lo <= hi:
            mid = (lo + hi) // 2
            ts = self._read_record_ts(f, mid)
            if ts >= target_us:
                result = mid
                hi = mid - 1
            else:
                lo = mid + 1

        return result

    def read_ticks(self, start_dt: datetime, end_dt: datetime) -> Iterator[dict]:
        """
        Yield ticks between start_dt and end_dt.
        Uses binary search to find start position efficiently.
        """
        # Ensure timezone-aware
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        start_us = int((start_dt - SC_EPOCH).total_seconds() * 1_000_000)
        end_us = int((end_dt - SC_EPOCH).total_seconds() * 1_000_000)

        with open(self.path, 'rb') as f:
            # Binary search for start position
            start_idx = self._binary_search_start(f, start_us)
            f.seek(HEADER_SIZE + start_idx * RECORD_SIZE)

            for _ in range(start_idx, self._n_records):
                buf = f.read(RECORD_SIZE)
                if len(buf) < RECORD_SIZE:
                    break

                ts_us, o, h, l, c, nt, tv, bv, av = struct.unpack(RECORD_FMT, buf)

                if ts_us > end_us:
                    break

                # Skip garbage records
                if h < INVALID_FLOAT_THRESHOLD or l < INVALID_FLOAT_THRESHOLD:
                    continue

                # Sierra stores MES prices × 100 (integer cents)
                yield {
                    'ts': _sc_microsec_to_datetime(ts_us),
                    'high': float(h) / 100.0,
                    'low': float(l) / 100.0,
                    'close': float(c) / 100.0,
                    'volume': int(tv),
                }

    def read_ticks_after(self, start_unix_ts: float,
                         max_minutes: int = 60) -> List[dict]:
        """
        Read ticks starting from a Unix epoch timestamp, for max_minutes.
        Convenience wrapper for setup processing.
        """
        start_dt = datetime.fromtimestamp(start_unix_ts, tz=timezone.utc)
        end_dt = start_dt + timedelta(minutes=max_minutes)
        return list(self.read_ticks(start_dt, end_dt))


def get_default_scid_path() -> Path:
    """Return path to active MES contract .scid file."""
    base = Path("/Users/michael/SierraChart2/Data")
    for contract in ["MESM26_FUT_CME.scid", "MESU26_FUT_CME.scid",
                     "MESH26_FUT_CME.scid"]:
        p = base / contract
        if p.exists():
            return p
    raise FileNotFoundError("No MES .scid file found in Sierra Data folder")
