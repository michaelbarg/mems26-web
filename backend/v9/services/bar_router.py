"""BarRouter — central distributor for bar events.

Receives bars from API endpoints, dispatches to subscribers + Event Bus.
Session is tagged on each event (Principle 10).
"""
import asyncio
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from backend.v9.common.session_classifier import SessionClassifier
from backend.v9.services import market_clock

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
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_main_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Capture FastAPI's running event loop for thread-safe publishing."""
        self._main_loop = loop
        logger.info("BarRouter: bound to main event loop")

    def publish_threadsafe(self, bar_type: str, bar_data: dict, mode: str = "LIVE") -> None:
        """Schedule publish on the captured FastAPI loop from any thread.

        P31-02 hotfix (2026-05-21): the previous implementation spawned a fresh
        OS thread + new asyncio loop (`threading.Thread` + `asyncio.run`) on every
        bar push. Under bridge load this leaked ~1 thread per 5min push (synthetic
        UAT reached 93 threads in 4 minutes; backend HTTP became unresponsive on
        new TCP connections). `run_coroutine_threadsafe` schedules the coroutine
        on the long-lived FastAPI loop instead — no thread/loop creation per bar.
        """
        if self._main_loop is not None and self._main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.publish(bar_type, bar_data, mode),
                self._main_loop,
            )
            return

        logger.warning(
            "BarRouter.publish_threadsafe: main_loop not bound or not running — "
            "falling back to thread+asyncio.run for %s (should not happen in production)",
            bar_type,
        )
        import threading

        threading.Thread(
            target=lambda: asyncio.run(self.publish(bar_type, bar_data, mode)),
            name=f"bar-router-{bar_type}",
            daemon=True,
        ).start()

    def subscribe(self, bar_type: str, handler: Callable):
        self._subscribers.setdefault(bar_type, []).append(handler)
        logger.info(f"BarRouter: subscribed {handler.__qualname__} to '{bar_type}'")

    async def publish(self, bar_type: str, bar_data: dict, mode: str = "LIVE"):
        self._stats["received"] += 1
        try:
            ts = bar_data.get("ts") or datetime.utcnow().isoformat()
            ts_dt = market_clock.parse_market_timestamp(ts)
            if ts_dt is not None:
                market_clock.update_replay_timestamp(ts_dt, source=f"bar_router.{bar_type}")
            try:
                session = self.session_clf.classify(ts_dt).session.value if ts_dt is not None else "UNKNOWN"
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

            publish_start = time.perf_counter()
            for handler in self._subscribers.get(bar_type, []):
                try:
                    h_start = time.perf_counter()
                    await handler(event)
                    h_ms = (time.perf_counter() - h_start) * 1000
                    self._stats["dispatched"] += 1
                    if h_ms > 100:
                        logger.warning(f"BarRouter: SLOW handler {handler.__qualname__} took {h_ms:.1f}ms")
                except Exception as e:
                    logger.error(f"BarRouter: handler {handler.__qualname__} failed: {e}", exc_info=True)
                    self._stats["failed"] += 1
            total_ms = (time.perf_counter() - publish_start) * 1000
            if total_ms > 50:
                logger.warning(f"BarRouter: dispatch total {total_ms:.1f}ms for {bar_type}")
            elif total_ms > 10:
                logger.info(f"BarRouter: dispatch {total_ms:.1f}ms for {bar_type}")

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
