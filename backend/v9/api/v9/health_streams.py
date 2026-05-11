"""V9 API: Stream Health endpoint — GET /api/v9/health/streams.

Returns per-stream status for the 10 Bridge streams (in-memory, no auth).
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v9/health", tags=["v9-health"])

# Module-level reference, set at startup by app.py
_stream_health_service = None


def set_stream_health_service(service) -> None:
    """Called once at startup to inject the StreamHealthService instance."""
    global _stream_health_service
    _stream_health_service = service


@router.get("/streams")
def get_stream_health():
    """Return per-stream health status for all 10 Bridge streams.

    No auth required (health endpoint).
    Response is cached for 1 second inside StreamHealthService.
    """
    if _stream_health_service is None:
        return {"streams": [], "summary": {"green": 0, "yellow": 0, "red": 0, "grey": 0}, "ts": None}
    return _stream_health_service.get_all_streams()
