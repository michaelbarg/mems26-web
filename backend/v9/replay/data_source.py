"""Read-only validated Postgres source for Replay Kernel Stage 0B."""
from __future__ import annotations

import datetime as dt
import os
from collections import defaultdict
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extensions import parse_dsn
from psycopg2.extras import RealDictCursor

from .manifest import bars_hash, sha256_value
from .scid_validator import SCIDValidator
from .types import (
    ReplayBar,
    ReplayRequest,
    ReplaySession,
    SessionNotJudgeable,
    SessionQuality,
    TPOEvent,
)


ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc


def _utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ValidatedDBSource:
    """Official replay datasource.

    The class never writes. Every connection is read-only and fail-closed by
    default when a session has fatal quality issues.
    """

    def __init__(self, dsn: str):
        if not self._local_dsn(dsn):
            raise ValueError(
                "Replay Kernel accepts local Postgres only "
                "(localhost/127.0.0.1/unix socket)")
        self.dsn = dsn

    @staticmethod
    def _local_dsn(dsn: str) -> bool:
        try:
            params = parse_dsn(dsn)
        except Exception:
            return False
        if params.get("service") or os.getenv("PGSERVICE"):
            return False
        host = params.get("host") or os.getenv("PGHOST")
        hostaddr = params.get("hostaddr") or os.getenv("PGHOSTADDR")
        if hostaddr not in (None, "", "127.0.0.1", "::1"):
            return False
        if host in (None, "", "localhost", "127.0.0.1", "::1"):
            return True
        # Explicit local Unix-domain socket directories are allowed.
        return host.startswith("/")

    def _connect(self):
        connection = psycopg2.connect(self.dsn)
        connection.set_session(
            readonly=True,
            autocommit=False,
            isolation_level="REPEATABLE READ",
        )
        return connection

    @staticmethod
    def _expected_grid(session_date: dt.date) -> List[dt.datetime]:
        start = dt.datetime.combine(
            session_date, dt.time(9, 30), tzinfo=ET).astimezone(UTC)
        return [start + dt.timedelta(minutes=5 * i) for i in range(78)]

    def load_session(
        self,
        request: ReplayRequest,
        *,
        scid_validator: Optional[SCIDValidator] = None,
        fail_closed: bool = True,
    ) -> ReplaySession:
        quality = SessionQuality(
            session_date=request.session_date,
            expected_bars=request.expected_rth_bars,
        )
        with self._connect() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT ts, open, high, low, close, COALESCE(volume, 0) volume
                    FROM v9_bars_5min_woodies
                    WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
                      AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
                      AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'
                      AND symbol = %s
                    ORDER BY ts
                    """,
                    (request.session_date, request.symbol),
                )
                raw_bars = list(cursor.fetchall())
                cvd_rows = self._load_cvd(cursor, request.session_date)
                tpo_events = self._load_tpo(cursor, request.session_date)

        quality.actual_bars = len(raw_bars)
        if len(raw_bars) != request.expected_rth_bars:
            quality.add(
                "RTH_CARDINALITY",
                f"db={len(raw_bars)}, expected={request.expected_rth_bars}")

        timestamps = [_utc(row["ts"]).replace(second=0, microsecond=0)
                      for row in raw_bars]
        duplicate_count = len(timestamps) - len(set(timestamps))
        quality.metrics["duplicate_bar_timestamps"] = duplicate_count
        if duplicate_count:
            quality.add(
                "RTH_DUPLICATE_TIMESTAMPS",
                f"duplicates={duplicate_count}")

        expected_grid = set(self._expected_grid(request.session_date))
        missing = sorted(expected_grid - set(timestamps))
        extra = sorted(set(timestamps) - expected_grid)
        quality.metrics.update({
            "missing_grid_bars": len(missing),
            "extra_grid_bars": len(extra),
        })
        if missing or extra:
            quality.add(
                "RTH_GRID_MISMATCH",
                f"missing={len(missing)}, extra={len(extra)}")

        conflict_timestamps = cvd_rows["conflict_timestamps"]
        timestamp_set = set(timestamps)
        cvd_bar_count = sum(
            1 for timestamp in cvd_rows["values"]
            if timestamp in timestamp_set)
        cvd_coverage = (
            cvd_bar_count / request.expected_rth_bars
            if request.expected_rth_bars else 0.0)
        quality.metrics.update({
            "cvd_rows": cvd_rows["row_count"],
            "cvd_unique_timestamps": len(cvd_rows["values"]),
            "cvd_conflict_timestamps": conflict_timestamps,
            "cvd_bar_count": cvd_bar_count,
            "cvd_coverage": round(cvd_coverage, 4),
            "tpo_events": len(tpo_events),
            "tpo_future_nominal": sum(
                1 for event in tpo_events
                if event.available_at > event.market_ts),
        })
        if conflict_timestamps:
            quality.add(
                "CVD_CONFLICTS",
                f"conflicting_timestamps={conflict_timestamps}")
        if cvd_coverage < request.min_cvd_coverage:
            quality.add(
                "CVD_COVERAGE",
                f"coverage={cvd_coverage:.4f}, "
                f"required={request.min_cvd_coverage:.4f}")

        bars: List[ReplayBar] = []
        previous: Optional[ReplayBar] = None
        seams = 0
        nonpositive_volume = 0
        for row in raw_bars:
            timestamp = _utc(row["ts"]).replace(second=0, microsecond=0)
            cvd = cvd_rows["values"].get(timestamp)
            bar = ReplayBar(
                ts=timestamp,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"] or 0),
                delta=(cvd["delta"] if cvd else None),
                cumulative_delta=(cvd["cumulative"] if cvd else None),
            )
            if bar.volume <= 0:
                nonpositive_volume += 1
            if previous is not None:
                gap = max(
                    bar.low - previous.high,
                    previous.low - bar.high,
                    0.0,
                )
                if gap > request.seam_limit_points:
                    seams += 1
            bars.append(bar)
            previous = bar
        quality.metrics.update({
            "seams": seams,
            "nonpositive_volume_bars": nonpositive_volume,
        })
        if seams:
            quality.add(
                "RTH_SEAMS",
                f"seams={seams}, limit={request.seam_limit_points}")
        if nonpositive_volume:
            quality.add(
                "RTH_BAD_VOLUME",
                f"nonpositive={nonpositive_volume}")

        session = ReplaySession(
            session_date=request.session_date,
            symbol=request.symbol,
            bars=bars,
            tpo_events=tpo_events,
            quality=quality,
        )
        session.source_hashes["bars"] = bars_hash(bars)
        session.source_hashes["cvd"] = sha256_value(cvd_rows["hash_rows"])
        session.source_hashes["tpo"] = sha256_value([
            (event.market_ts, event.available_at, event.poc, event.vah, event.val)
            for event in tpo_events
        ])

        if scid_validator is not None:
            scid_validator.validate(session)
        if fail_closed and not quality.judgeable:
            raise SessionNotJudgeable(quality)
        return session

    @staticmethod
    def _load_cvd(cursor, session_date: dt.date) -> Dict:
        cursor.execute(
            """
            SELECT id, ts, delta, cumulative
            FROM v9_bars_cumulative_delta
            WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
            ORDER BY ts, id
            """,
            (session_date,),
        )
        grouped = defaultdict(list)
        rows = list(cursor.fetchall())
        for row in rows:
            grouped[_utc(row["ts"]).replace(
                second=0, microsecond=0)].append(row)

        values = {}
        conflicts = 0
        hash_rows = []
        for timestamp in sorted(grouped):
            group = grouped[timestamp]
            cumulatives = {
                float(row["cumulative"])
                for row in group if row["cumulative"] is not None
            }
            deltas = {
                float(row["delta"])
                for row in group if row["delta"] is not None
            }
            if len(cumulatives) > 1 or len(deltas) > 1:
                conflicts += 1
                hash_rows.extend(
                    (timestamp, row["id"], row["delta"], row["cumulative"])
                    for row in group)
                continue
            usable = [
                row for row in group
                if row["delta"] is not None and row["cumulative"] is not None
            ]
            if not usable:
                hash_rows.extend(
                    (timestamp, row["id"], row["delta"], row["cumulative"])
                    for row in group)
                continue
            # Identical duplicate: highest non-null id, deterministic. A NULL
            # duplicate can never overwrite the usable value.
            selected = usable[-1]
            values[timestamp] = {
                "delta": (
                    float(selected["delta"])
                    if selected["delta"] is not None else None),
                "cumulative": (
                    float(selected["cumulative"])
                    if selected["cumulative"] is not None else None),
            }
            hash_rows.append(
                (timestamp, selected["id"], selected["delta"],
                 selected["cumulative"]))
        return {
            "row_count": len(rows),
            "conflict_timestamps": conflicts,
            "values": values,
            "hash_rows": hash_rows,
        }

    @staticmethod
    def _load_tpo(cursor, session_date: dt.date) -> List[TPOEvent]:
        cursor.execute(
            """
            SELECT ts, created_at, poc, vah, val
            FROM v9_tpo_history
            WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
            ORDER BY created_at, id
            """,
            (session_date,),
        )
        return [
            TPOEvent(
                market_ts=_utc(row["ts"]),
                available_at=_utc(row["created_at"]),
                poc=(float(row["poc"]) if row["poc"] is not None else None),
                vah=(float(row["vah"]) if row["vah"] is not None else None),
                val=(float(row["val"]) if row["val"] is not None else None),
            )
            for row in cursor.fetchall()
        ]
