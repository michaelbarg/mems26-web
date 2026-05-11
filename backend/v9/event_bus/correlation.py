"""Correlation ID propagation for the Event Bus.

Each bridge session gets a unique correlation_id that flows through
all events in that session's pipeline. This enables tracing a price tick
from DLL -> Bridge -> Event Bus -> WS -> Frontend.
"""

import uuid
import threading

_session_correlation_id: str = ""
_lock = threading.Lock()


def new_session_id() -> str:
    """Generate and store a new session correlation ID."""
    global _session_correlation_id
    with _lock:
        _session_correlation_id = uuid.uuid4().hex[:12]
        return _session_correlation_id


def get_session_id() -> str:
    """Get the current session correlation ID, creating one if needed."""
    global _session_correlation_id
    with _lock:
        if not _session_correlation_id:
            _session_correlation_id = uuid.uuid4().hex[:12]
        return _session_correlation_id
