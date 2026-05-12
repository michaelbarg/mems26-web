"""BarRouter — central distributor for bar events.

Receives bars from API endpoints, dispatches to subscribers + Event Bus.
Session is tagged on each event (Principle 10).
"""
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Callable, Dict, List

from backend.v9.common.session_classifier import SessionClassifier

logger = logging.getLogger(__name__)


@dataclass
class BarEvent:
    bar_type: str
    bar_id: str
    ts: str
    payload: Dict[str, Any]
    session: str
    mode: str = "LIVE"


class BarRouter:
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.session_clf = SessionClassifier()
        self._subscribers: Dict[str, List[Callable]] = {}
        self._stats = {"received": 0, "dispatched": 0, "published_to_bus": 0, "failed": 0}

    def subscribe(self, bar_type: str, handler: Callable):
        self._subscribers.setdefault(bar_type, []).append(handler)
        logger.info(f"BarRouter: subscribed {handler.__qualname__} to '{bar_type}'")

    async def publish(self, bar_type: str, bar_data: dict, mode: str = "LIVE"):
        self._stats["received"] += 1
        try:
            ts = bar_data.get("ts") or datetime.utcnow().isoformat()
            try:
                ts_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                session = self.session_clf.classify(ts_dt).session.value
            except Exception:
                session = "UNKNOWN"

            event = BarEvent(
                bar_type=bar_type,
                bar_id=bar_data.get("bar_id") or f"{bar_type}_{ts}",
                ts=str(ts),
                payload=bar_data,
                session=session,
                mode=mode,
            )

            for handler in self._subscribers.get(bar_type, []):
                try:
                    await handler(event)
                    self._stats["dispatched"] += 1
                except Exception as e:
                    logger.error(f"BarRouter: handler {handler.__qualname__} failed: {e}", exc_info=True)
                    self._stats["failed"] += 1

            if self.event_bus:
                try:
                    await self.event_bus.publish(f"bars.{bar_type}", asdict(event))
                    self._stats["published_to_bus"] += 1
                except Exception as e:
                    logger.error(f"BarRouter: event_bus publish failed: {e}")
                    self._stats["failed"] += 1
        except Exception as e:
            logger.error(f"BarRouter.publish failed for {bar_type}: {e}", exc_info=True)
            self._stats["failed"] += 1

    def get_stats(self) -> dict:
        return {**self._stats, "subscribers": {k: len(v) for k, v in self._subscribers.items()}}
