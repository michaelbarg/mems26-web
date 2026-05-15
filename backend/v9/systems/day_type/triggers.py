"""Trigger Dispatcher — routes 6 trigger types to handler callbacks.

Trigger types per Zohar Chapter 5 + Mind Over Markets pp.87-102:
  BAR_CLOSE      — every RTH bar close
  PERIODIC       — every 30 min (1800s) for re-evaluation
  EXTENSION      — IB extension detected (up or down)
  FAILED_EXT     — extension that failed (returned to IB range)
  NEWS_EVENT     — external news/economic event
  VOLUME_SPIKE   — z-score spike from VolumeSpikeDetector
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional


class TriggerType(str, Enum):
    """Six trigger types that can fire the Day Type Engine."""
    BAR_CLOSE = "BAR_CLOSE"            # Zohar Ch.5: bar-by-bar evaluation
    PERIODIC = "PERIODIC"              # Mind Over Markets p.92: periodic re-check
    EXTENSION = "EXTENSION"            # Zohar Ch.5: IB extension event
    FAILED_EXT = "FAILED_EXT"          # Zohar Ch.5: failed extension event
    NEWS_EVENT = "NEWS_EVENT"          # Mind Over Markets p.98: news catalyst
    VOLUME_SPIKE = "VOLUME_SPIKE"      # Mind Over Markets p.102: abnormal volume


@dataclass(frozen=True)
class TriggerEvent:
    """Immutable trigger event dispatched to handlers."""
    trigger_type: TriggerType
    ts: float                          # epoch seconds
    payload: Optional[Dict[str, Any]] = None


# Handler type alias
TriggerHandler = Callable[[TriggerEvent], None]


class TriggerDispatcher:
    """Routes trigger events to registered handler callbacks.

    Constants:
        PERIODIC_INTERVAL_SEC — 1800s (30 min), per Mind Over Markets p.92
            re-evaluation interval for day-type confidence scoring.
    """

    # 30-minute periodic re-evaluation interval (Mind Over Markets p.92)
    PERIODIC_INTERVAL_SEC: int = 1800

    def __init__(self) -> None:
        self._handlers: Dict[TriggerType, TriggerHandler] = {}
        self._last_periodic_ts: float = 0.0

    def register(self, trigger_type: TriggerType, handler: TriggerHandler) -> None:
        """Register a handler callback for a trigger type."""
        self._handlers[trigger_type] = handler

    def dispatch(self, event: TriggerEvent) -> bool:
        """Dispatch a trigger event to its registered handler.

        Returns True if a handler was found and called, False otherwise.
        """
        handler = self._handlers.get(event.trigger_type)
        if handler is None:
            return False
        handler(event)
        return True

    # ── Convenience dispatch methods ────────────────────────────────────

    def on_bar_close(self, ts: float, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Dispatch BAR_CLOSE trigger."""
        return self.dispatch(TriggerEvent(TriggerType.BAR_CLOSE, ts, payload))

    def on_periodic(self, ts: float, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Dispatch PERIODIC trigger if interval has elapsed.

        Returns True if dispatched, False if interval not yet reached or no handler.
        """
        if self._last_periodic_ts > 0 and (ts - self._last_periodic_ts) < self.PERIODIC_INTERVAL_SEC:
            return False
        event = TriggerEvent(TriggerType.PERIODIC, ts, payload)
        dispatched = self.dispatch(event)
        if dispatched:
            self._last_periodic_ts = ts
        return dispatched

    def on_extension(self, ts: float, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Dispatch EXTENSION trigger."""
        return self.dispatch(TriggerEvent(TriggerType.EXTENSION, ts, payload))

    def on_failed_ext(self, ts: float, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Dispatch FAILED_EXT trigger."""
        return self.dispatch(TriggerEvent(TriggerType.FAILED_EXT, ts, payload))

    def on_news_event(self, ts: float, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Dispatch NEWS_EVENT trigger."""
        return self.dispatch(TriggerEvent(TriggerType.NEWS_EVENT, ts, payload))

    def on_volume_spike(self, ts: float, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Dispatch VOLUME_SPIKE trigger."""
        return self.dispatch(TriggerEvent(TriggerType.VOLUME_SPIKE, ts, payload))
