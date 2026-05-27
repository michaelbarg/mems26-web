"""HFE Divergence Logger -- W-4 audit infrastructure.

Logs divergences between DLL and Python HFE detection paths.
Trade decisions use DLL ONLY; Python runs for audit/shadow comparison.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Literal, Optional


@dataclass(frozen=True)
class HFEDivergence:
    """Single divergence event between DLL and Python HFE detection."""
    timestamp: float
    bar_ts: float
    divergence_type: Literal[
        "state_mismatch",
        "direction_mismatch",
        "bars_ago_mismatch",
        "confidence_drift",
    ]
    dll_detected: bool
    dll_direction: str
    dll_bars_ago: int
    dll_confidence: float
    python_detected: bool
    python_direction: str
    python_bars_ago: int
    python_confidence: float
    notes: str = ""


class HFEDivergenceLogger:
    """Rate-limited divergence logger with optional shadow sink.

    The Python logger.warning is rate-limited per divergence_type.
    The shadow_sink always receives every event (no rate limiting).
    """

    def __init__(
        self,
        logger_name: str = "woodies.hfe.divergence",
        rate_limit_seconds: float = 60,
        shadow_sink: Optional[Callable[[HFEDivergence], None]] = None,
    ):
        self._logger = logging.getLogger(logger_name)
        self._rate_limit_seconds = rate_limit_seconds
        self._shadow_sink = shadow_sink
        self._last_logged: Dict[str, float] = {}

    def log_divergence(self, event: HFEDivergence) -> bool:
        """Log a divergence event.

        Returns True if the event was emitted to the Python logger
        (not rate-limited for this type). Always sends to shadow_sink.
        """
        # Always send to shadow sink (no rate limit)
        if self._shadow_sink is not None:
            self._shadow_sink(event)

        # Rate-limit Python logger output per divergence_type
        now = time.monotonic()
        if event.divergence_type in self._last_logged:
            last = self._last_logged[event.divergence_type]
            if now - last < self._rate_limit_seconds:
                return False

        self._last_logged[event.divergence_type] = now
        self._logger.warning(
            "HFE divergence [%s]: DLL(det=%s dir=%s ago=%d conf=%.2f) vs "
            "Python(det=%s dir=%s ago=%d conf=%.2f) | %s",
            event.divergence_type,
            event.dll_detected, event.dll_direction, event.dll_bars_ago, event.dll_confidence,
            event.python_detected, event.python_direction, event.python_bars_ago, event.python_confidence,
            event.notes,
        )
        return True

    def reset_rate_limit(self) -> None:
        """Clear rate-limit state (for testing)."""
        self._last_logged.clear()
