"""Read-only Sierra SCID validator for Replay Kernel session quality."""
from __future__ import annotations

import datetime as dt
import os
import struct
from pathlib import Path
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

from .types import ReplayBar, ReplaySession, SessionQuality


ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
SC_EPOCH = dt.datetime(1899, 12, 30)
HEADER_SIZE = 56
EXPECTED_RECORD_SIZE = 40
PRICE_DIVISOR = 100.0


class SCIDValidator:
    def __init__(self, path: str):
        self.path = Path(os.path.expanduser(path))
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        with self.path.open("rb") as handle:
            header = handle.read(HEADER_SIZE)
        if len(header) < HEADER_SIZE or header[:4] != b"SCID":
            raise ValueError(f"Invalid SCID header: {self.path}")
        self.header_size = struct.unpack("<I", header[4:8])[0]
        self.record_size = struct.unpack("<I", header[8:12])[0]
        if self.record_size != EXPECTED_RECORD_SIZE:
            raise ValueError(
                f"SCID record size {self.record_size}, "
                f"expected {EXPECTED_RECORD_SIZE}")
        self.record_count = (
            self.path.stat().st_size - self.header_size) // self.record_size

    def _timestamp_us(self, handle, index: int) -> int:
        handle.seek(self.header_size + index * self.record_size)
        raw = handle.read(8)
        if len(raw) != 8:
            return 0
        return struct.unpack("<q", raw)[0]

    def _find(self, handle, target_us: int) -> int:
        lo, hi = 0, self.record_count
        while lo < hi:
            mid = (lo + hi) // 2
            if self._timestamp_us(handle, mid) < target_us:
                lo = mid + 1
            else:
                hi = mid
        return lo

    @staticmethod
    def _scid_us(value: dt.datetime) -> int:
        if value.tzinfo is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return int((value - SC_EPOCH).total_seconds() * 1_000_000)

    def load_rth(self, session_date: dt.date) -> List[ReplayBar]:
        start_et = dt.datetime.combine(
            session_date, dt.time(9, 30), tzinfo=ET)
        end_et = dt.datetime.combine(
            session_date, dt.time(16, 0), tzinfo=ET)
        start_us = self._scid_us(start_et)
        end_us = self._scid_us(end_et)

        with self.path.open("rb") as handle:
            start_index = self._find(handle, start_us)
            end_index = self._find(handle, end_us)
            count = max(0, end_index - start_index)
            handle.seek(self.header_size + start_index * self.record_size)
            raw = handle.read(count * self.record_size)

        buckets: Dict[dt.datetime, Dict[str, float]] = {}
        for offset in range(count):
            row = struct.unpack_from(
                "<q4f4I", raw, offset * self.record_size)
            timestamp_us = row[0]
            close = float(row[4]) / PRICE_DIVISOR
            total_volume = int(row[6])
            bid_volume = int(row[7])
            ask_volume = int(row[8])
            if not 1000.0 <= close <= 50000.0:
                continue
            stamp = SC_EPOCH + dt.timedelta(microseconds=timestamp_us)
            bucket = stamp.replace(
                minute=(stamp.minute // 5) * 5,
                second=0,
                microsecond=0,
                tzinfo=UTC,
            )
            item = buckets.get(bucket)
            if item is None:
                buckets[bucket] = {
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "volume": total_volume,
                    "delta": ask_volume - bid_volume,
                }
            else:
                item["high"] = max(item["high"], close)
                item["low"] = min(item["low"], close)
                item["close"] = close
                item["volume"] += total_volume
                item["delta"] += ask_volume - bid_volume

        result: List[ReplayBar] = []
        cumulative = 0.0
        for timestamp in sorted(buckets):
            item = buckets[timestamp]
            cumulative += item["delta"]
            result.append(ReplayBar(
                ts=timestamp,
                open=item["open"],
                high=item["high"],
                low=item["low"],
                close=item["close"],
                volume=int(item["volume"]),
                delta=float(item["delta"]),
                cumulative_delta=cumulative,
            ))
        return result

    def validate(
        self,
        session: ReplaySession,
        *,
        price_tolerance: float = 0.01,
        volume_tolerance: int = 0,
    ) -> SessionQuality:
        truth = self.load_rth(session.session_date)
        quality = session.quality
        quality.metrics["scid_bars"] = len(truth)
        if len(truth) != quality.expected_bars:
            quality.add(
                "SCID_RTH_CARDINALITY",
                f"scid={len(truth)}, expected={quality.expected_bars}")

        db_by_ts = {bar.ts.replace(second=0, microsecond=0): bar
                    for bar in session.bars}
        truth_by_ts = {bar.ts.replace(second=0, microsecond=0): bar
                       for bar in truth}
        missing_db = sorted(set(truth_by_ts) - set(db_by_ts))
        extra_db = sorted(set(db_by_ts) - set(truth_by_ts))
        if missing_db or extra_db:
            quality.add(
                "SCID_TIMESTAMP_MISMATCH",
                f"missing_db={len(missing_db)}, extra_db={len(extra_db)}")

        ohlc_mismatches = 0
        volume_mismatches = 0
        cvd_overlap = 0
        delta_mismatches = 0
        cumulative_mismatches = 0
        close_matches = 0
        for timestamp in sorted(set(db_by_ts) & set(truth_by_ts)):
            db_bar = db_by_ts[timestamp]
            truth_bar = truth_by_ts[timestamp]
            price_diffs = (
                abs(db_bar.open - truth_bar.open),
                abs(db_bar.high - truth_bar.high),
                abs(db_bar.low - truth_bar.low),
                abs(db_bar.close - truth_bar.close),
            )
            if abs(db_bar.close - truth_bar.close) <= 0.5:
                close_matches += 1
            if max(price_diffs) > price_tolerance:
                ohlc_mismatches += 1
            if abs(db_bar.volume - truth_bar.volume) > volume_tolerance:
                volume_mismatches += 1
            if (db_bar.delta is not None and
                    db_bar.cumulative_delta is not None):
                cvd_overlap += 1
                if abs(db_bar.delta - truth_bar.delta) > 0.01:
                    delta_mismatches += 1
                if abs(
                        db_bar.cumulative_delta -
                        truth_bar.cumulative_delta) > 0.01:
                    cumulative_mismatches += 1

        quality.metrics.update({
            "scid_close_matches": close_matches,
            "scid_ohlc_mismatches": ohlc_mismatches,
            "scid_volume_mismatches": volume_mismatches,
            "scid_cvd_overlap": cvd_overlap,
            "scid_delta_mismatches": delta_mismatches,
            "scid_cumulative_mismatches": cumulative_mismatches,
        })
        if ohlc_mismatches:
            quality.add(
                "SCID_OHLC_MISMATCH",
                f"{ohlc_mismatches}/{len(truth)} bars exceed "
                f"{price_tolerance}pt")
        if volume_mismatches:
            quality.add(
                "SCID_VOLUME_MISMATCH",
                f"{volume_mismatches}/{len(truth)} bars exceed "
                f"volume tolerance {volume_tolerance}")
        if delta_mismatches:
            quality.add(
                "SCID_DELTA_MISMATCH",
                f"{delta_mismatches}/{cvd_overlap} overlapping bars")
        if cumulative_mismatches:
            quality.add(
                "SCID_CUMULATIVE_MISMATCH",
                f"{cumulative_mismatches}/{cvd_overlap} overlapping bars")
        return quality
