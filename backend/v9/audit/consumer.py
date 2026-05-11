"""AuditConsumer — reads all Event Bus streams, writes to AuditEvent table.

Runs as a background loop. Reads in batches from Redis Streams (XRANGE),
writes to SQLite/PostgreSQL in batches of BATCH_SIZE. Idempotent via
unique constraint on (correlation_id, ts_ms).
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from typing import Dict, List, Tuple

from sqlalchemy.exc import IntegrityError

from backend.v9.db.session import SessionLocal
from backend.v9.db.models.audit import AuditEvent
from backend.v9.event_bus.channels import ALL_CHANNELS

logger = logging.getLogger("mems26.audit")

REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
BATCH_SIZE = int(os.getenv("AUDIT_BATCH_SIZE", "100"))
POLL_MS = int(os.getenv("AUDIT_POLL_MS", "200"))


def _redis_cmd(args: list):
    if not REDIS_URL or not REDIS_TOKEN:
        return None
    try:
        body = json.dumps(args).encode()
        req = urllib.request.Request(
            REDIS_URL, data=body,
            headers={"Authorization": f"Bearer {REDIS_TOKEN}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()).get("result")
    except urllib.error.URLError as e:
        logger.warning("[Audit] Redis error: %s", e)
        return None


class AuditConsumer:
    """Consumes events from all Redis Streams, persists to AuditEvent table."""

    def __init__(self):
        self._offsets: Dict[str, str] = {}
        self._running = False
        self.events_written = 0
        self.events_skipped = 0
        self.errors = 0
        self.last_write_ts = 0.0
        self._start_ts = 0.0

    def _init_offsets(self):
        """Start from the beginning to consume all existing events.

        The dedup unique constraint on stream_id prevents re-processing
        on subsequent restarts — already-consumed entries are skipped.
        """
        for channel in ALL_CHANNELS:
            self._offsets[channel] = "0"
        logger.info("[Audit] Initialized offsets for %d channels (from start)", len(self._offsets))

    def poll_once(self) -> int:
        """Poll all channels once, write to DB. Returns total events written."""
        total = 0
        for channel in ALL_CHANNELS:
            entries = self._read_stream(channel)
            if entries:
                written = self._write_batch(channel, entries)
                total += written
        return total

    def _read_stream(self, channel: str) -> List[Tuple[str, dict]]:
        """Read new entries from a single stream."""
        last_id = self._offsets.get(channel, "0")
        # Increment for exclusive start
        if last_id != "0":
            parts = last_id.split("-")
            if len(parts) == 2:
                last_id = f"{parts[0]}-{int(parts[1]) + 1}"

        result = _redis_cmd(["XRANGE", channel, last_id, "+", "COUNT", str(BATCH_SIZE)])
        if not result:
            return []

        entries = []
        for entry in result:
            entry_id = entry[0]
            fields = entry[1]
            if isinstance(fields, list):
                d = {}
                for i in range(0, len(fields), 2):
                    d[fields[i]] = fields[i + 1]
                entries.append((entry_id, d))
            elif isinstance(fields, dict):
                entries.append((entry_id, fields))
            self._offsets[channel] = entry_id

        return entries

    def _write_batch(self, channel: str, entries: List[Tuple[str, dict]]) -> int:
        """Write a batch of entries to the AuditEvent table."""
        db = SessionLocal()
        written = 0
        try:
            for entry_id, fields in entries:
                data = self._parse_fields(fields)
                audit = AuditEvent(
                    ts_ms=data.get("ts_ms", 0),
                    event_type=data.get("event_type", "unknown"),
                    correlation_id=data.get("correlation_id", ""),
                    source=data.get("source", "unknown"),
                    price=data.get("price"),
                    payload=data,
                    stream_id=entry_id,
                )
                db.add(audit)
                try:
                    db.flush()
                    written += 1
                except IntegrityError:
                    db.rollback()
                    self.events_skipped += 1
                    continue
            db.commit()
            self.events_written += written
            if written > 0:
                self.last_write_ts = time.time()
        except Exception:
            logger.exception("[Audit] batch write error on %s", channel)
            db.rollback()
            self.errors += 1
        finally:
            db.close()
        return written

    def _parse_fields(self, fields: dict) -> dict:
        """Parse stream entry fields into a flat dict."""
        if "data" in fields:
            try:
                return json.loads(fields["data"])
            except (json.JSONDecodeError, TypeError):
                pass
        # Fallback: coerce field types
        result = dict(fields)
        for int_field in ("ts_ms",):
            if int_field in result:
                try:
                    result[int_field] = int(result[int_field])
                except (ValueError, TypeError):
                    pass
        for float_field in ("price",):
            if float_field in result:
                try:
                    result[float_field] = float(result[float_field])
                except (ValueError, TypeError):
                    pass
        return result

    @property
    def events_per_minute(self) -> float:
        if self._start_ts == 0:
            return 0
        elapsed = time.time() - self._start_ts
        if elapsed < 1:
            return 0
        return (self.events_written / elapsed) * 60

    @property
    def is_running(self) -> bool:
        return self._running
