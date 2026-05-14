"""BarIngestionService — persists incoming 5-min bars to DB.

Must run BEFORE any system tries to hydrate (D-077).
Uses existing V9Bar5Min model (table v9_bars_5min).
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.v9.db.session import SessionLocal
from backend.v9.db.models.bars_5min import V9Bar5Min

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

    def ingest_bar(self, bar_data: dict) -> None:
        """Persist a single bar to DB. UPSERT on (ts, symbol) — no duplicates."""
        db = SessionLocal()
        try:
            ts = bar_data.get("ts", datetime.now(timezone.utc))
            symbol = bar_data.get("symbol", "MES")

            # Check for existing bar at same timestamp (UPSERT logic)
            existing = db.query(V9Bar5Min).filter(
                V9Bar5Min.ts == ts,
                V9Bar5Min.symbol == symbol,
            ).first()

            if existing:
                # Update in place (last write wins)
                existing.open = bar_data["open"]
                existing.high = bar_data["high"]
                existing.low = bar_data["low"]
                existing.close = bar_data["close"]
                existing.volume = bar_data.get("volume", 0)
                existing.cumulative_delta = bar_data.get("delta")
            else:
                bar = V9Bar5Min(
                    ts=ts, symbol=symbol,
                    open=bar_data["open"],
                    high=bar_data["high"],
                    low=bar_data["low"],
                    close=bar_data["close"],
                    volume=bar_data.get("volume", 0),
                    cumulative_delta=bar_data.get("delta"),
                )
                db.add(bar)

            db.commit()
            self._bars_ingested += 1
        except Exception:
            db.rollback()
            logger.exception("[BarIngestion] Failed to ingest bar")
        finally:
            db.close()

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
