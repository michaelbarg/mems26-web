"""§2 safety: global exception-swallow counter.

334 silent exception swallows in the live path make it impossible to know
which ones fired.  This module provides a simple counter that any
`except Exception: pass` can call to make itself visible.

Usage: `from backend.v9.services.swallow_counter import swallowed; swallowed("gateway:1309")`

The counter is exposed via /api/v9/health as `swallow_counts`.
"""
import collections
import logging
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_counts: dict = collections.Counter()


def swallowed(location: str, exc: BaseException = None) -> None:
    """Record one swallowed exception at `location` (file:line or label)."""
    with _lock:
        _counts[location] += 1
        n = _counts[location]
    # Rate-limited warning: first occurrence + every 100th
    if n == 1 or n % 100 == 0:
        logger.warning(
            "[SWALLOW] %s: exception #%d swallowed%s",
            location, n,
            f" ({type(exc).__name__}: {exc})" if exc else "")


def get_counts() -> dict:
    """Return a copy of all swallow counts for the health endpoint."""
    with _lock:
        return dict(_counts)


def reset() -> None:
    """Reset all counters (testing only)."""
    with _lock:
        _counts.clear()
