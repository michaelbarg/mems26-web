"""5-min Bar Aggregator — builds OHLCV bars from incoming ticks.

Principle 10: DATA-DRIVEN-NOT-CLOCK-GATED
Bars are built ALWAYS when ticks flow. Session is a tag, not a gate.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

import pytz

from backend.v9.common.session_classifier import SessionClassifier

logger = logging.getLogger("mems26.bar_aggregator")
ET = pytz.timezone('America/New_York')


@dataclass
class TickEvent:
    ts: datetime
    price: float
    size: int = 1


@dataclass
class Bar5Min:
    start_ts: datetime
    end_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    tick_count: int
    session: str


class FiveMinAggregator:
    """Aggregates ticks into 5-min bars. Always-on, no session gating."""

    def __init__(self, on_bar_close: Callable):
        self.session_clf = SessionClassifier()
        self.on_bar_close = on_bar_close
        self.current_bar: Optional[Bar5Min] = None
        self._lock = threading.Lock()
        self.bars_closed = 0
        self.ticks_processed = 0

    def _bar_start_for(self, ts: datetime) -> datetime:
        ts_et = ts.astimezone(ET) if ts.tzinfo else ET.localize(ts)
        minute_floor = (ts_et.minute // 5) * 5
        return ts_et.replace(minute=minute_floor, second=0, microsecond=0)

    def on_tick(self, tick: TickEvent) -> Optional[Bar5Min]:
        """Process a tick. Returns closed bar if boundary crossed, else None."""
        self.ticks_processed += 1
        bar_start = self._bar_start_for(tick.ts)
        closed = None

        with self._lock:
            if self.current_bar is None or self.current_bar.start_ts != bar_start:
                # Close previous bar
                if self.current_bar is not None:
                    closed = self.current_bar
                    self.bars_closed += 1

                # Start new bar
                session = self.session_clf.classify(tick.ts).session.value
                self.current_bar = Bar5Min(
                    start_ts=bar_start,
                    end_ts=bar_start + timedelta(minutes=5),
                    open=tick.price,
                    high=tick.price,
                    low=tick.price,
                    close=tick.price,
                    volume=tick.size,
                    tick_count=1,
                    session=session,
                )
            else:
                # Update current bar
                self.current_bar.high = max(self.current_bar.high, tick.price)
                self.current_bar.low = min(self.current_bar.low, tick.price)
                self.current_bar.close = tick.price
                self.current_bar.volume += tick.size
                self.current_bar.tick_count += 1

        if closed and self.on_bar_close:
            self.on_bar_close(closed)

        return closed

    def force_close_if_stale(self, now: Optional[datetime] = None) -> Optional[Bar5Min]:
        """Force-close current bar if >1 min past expected end."""
        if self.current_bar is None:
            return None
        now = now or datetime.now(ET)
        if now.tzinfo is None:
            now = ET.localize(now)
        if now > self.current_bar.end_ts + timedelta(minutes=1):
            with self._lock:
                if self.current_bar is not None:
                    closed = self.current_bar
                    self.current_bar = None
                    self.bars_closed += 1
                    if self.on_bar_close:
                        self.on_bar_close(closed)
                    return closed
        return None

    def get_status(self) -> dict:
        return {
            "ticks_processed": self.ticks_processed,
            "bars_closed": self.bars_closed,
            "current_bar_open": self.current_bar is not None,
            "current_bar_ticks": self.current_bar.tick_count if self.current_bar else 0,
        }


def _on_bar_close_default(bar: Bar5Min) -> None:
    """Default bar close handler: persist to DB via BarIngestionService."""
    try:
        from backend.v9.services.bar_ingestion import bar_ingestion_service
        bar_ingestion_service.ingest_bar({
            "ts": bar.start_ts,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "delta": 0,
            "symbol": "MES",
        })
        logger.info(
            "[Aggregator] Bar closed: %s O=%.2f H=%.2f L=%.2f C=%.2f V=%d session=%s",
            bar.start_ts.strftime("%H:%M"), bar.open, bar.high, bar.low,
            bar.close, bar.volume, bar.session,
        )
    except Exception as e:
        logger.error("[Aggregator] Bar persist error: %s", e)


# Singleton
five_min_aggregator = FiveMinAggregator(on_bar_close=_on_bar_close_default)
