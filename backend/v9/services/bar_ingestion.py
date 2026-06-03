"""BarIngestionService — persists incoming 5-min bars to DB.

Must run BEFORE any system tries to hydrate (D-077).
Uses existing V9Bar5Min model (table v9_bars_5min).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.v9.db.session import SessionLocal
from backend.v9.db.models.bars_5min import V9Bar5Min
from backend.v9.services.bar_integrity import bar_is_valid

logger = logging.getLogger("mems26.bar_ingestion")


class BarIngestionService:
    """Persists bars and provides hydration query."""

    def __init__(self):
        self._running = False
        self._bars_ingested = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def bars_in_db(self) -> int:
        try:
            db = SessionLocal()
            count = db.query(V9Bar5Min).count()
            db.close()
            return count
        except Exception:
            return 0

    def start(self) -> None:
        """Mark service as running."""
        self._running = True
        logger.info("[BarIngestion] Started")

    def stop(self) -> None:
        self._running = False

    def ingest_bar(self, bar_data: dict) -> bool:
        """Persist a single bar to DB via safe_writer INSERT OR REPLACE.

        DB Root Fix (2026-06-03): replaces ORM db.add/db.commit with
        safe_execute to eliminate concurrent write race.
        """
        from backend.v9.db.safe_writer import safe_execute

        ok, reason = bar_is_valid(
            open=bar_data.get("open"),
            high=bar_data.get("high"),
            low=bar_data.get("low"),
            close=bar_data.get("close"),
        )
        if not ok:
            logger.warning(
                "[BarIngestion] Rejected invalid bar ts=%s symbol=%s reason=%s",
                bar_data.get("ts"),
                bar_data.get("symbol", "MES"),
                reason,
            )
            return False

        ts = bar_data.get("ts", datetime.now(timezone.utc))
        symbol = bar_data.get("symbol", "MES")

        # Guard: reject bars with ts > now + 2 minutes (future-ts bug)
        if isinstance(ts, datetime):
            _ts_check = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            if _ts_check > datetime.now(timezone.utc) + timedelta(minutes=2):
                logger.warning(
                    "[BarIngestion] Rejected FUTURE bar ts=%s (now+2m guard)", ts
                )
                return False

        ts_iso = ts.isoformat() if isinstance(ts, datetime) else str(ts)
        result = safe_execute(
            "INSERT OR REPLACE INTO v9_bars_5min "
            "(ts, symbol, open, high, low, close, volume, cumulative_delta) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ts_iso, symbol,
                bar_data["open"], bar_data["high"],
                bar_data["low"], bar_data["close"],
                bar_data.get("volume", 0),
                bar_data.get("delta"),
            ),
        )
        if result is not None:
            self._bars_ingested += 1
            return True
        return False

    def get_bars_since(self, since: datetime) -> List[dict]:
        """Query bars since a timestamp. Used by hydrate()."""
        db = SessionLocal()
        try:
            rows = (
                db.query(V9Bar5Min)
                .filter(V9Bar5Min.ts >= since)
                .order_by(V9Bar5Min.ts.asc())
                .all()
            )
            return [
                {
                    "ts": r.ts, "open": r.open, "high": r.high,
                    "low": r.low, "close": r.close, "volume": r.volume,
                    "delta": r.cumulative_delta,
                }
                for r in rows
            ]
        except Exception:
            return []
        finally:
            db.close()


# Singleton
bar_ingestion_service = BarIngestionService()
