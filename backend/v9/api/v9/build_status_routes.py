"""Router: GET /api/v9/build/pattern-status — Pattern Build Status aggregator.

Source: BUILD_STATUS_ENDPOINT_DESIGN.md §2.1
Read-only debug surface — no trades routed, no DB writes.

Per §5.4: endpoint must respond within 300ms p95.
Per §5.5: never raise 500 — all inspector failures are captured in errors[].
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, Query

from backend.v9.systems.build_status.aggregator import BuildStatusAggregator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v9/build", tags=["build-status"])


@router.get("/pattern-status")
def get_pattern_status(
    request: Request,
    systems: Optional[str] = Query(
        default="five_min,woodies,day_type",
        description="CSV of systems to include: five_min, woodies, day_type",
    ),
    include_history: bool = Query(
        default=False,
        description="Include last 5 fire/no-fire decisions per pattern (DB read)",
    ),
):
    """Aggregate live pattern build status across S2, Woodies, and Day Type systems.

    Returns per-pattern status (fired/armed/blocked/vetoed/not_applicable/unknown)
    with component-level detail for debugging why a pattern did or did not fire.

    Query params:
        systems: CSV subset of systems (default: all 3)
        include_history: include recent fire history (deferred — not yet implemented)

    Per BUILD_STATUS_ENDPOINT_DESIGN.md §5.5:
    "If app.state.five_min_system is None → running=false, hydrated=false · NOT 500"
    "If any inspector raises → partial result with status='unknown' · NOT 500"
    """
    # Access systems from app.state — may be None if startup failed
    five_min_system = getattr(request.app.state, "five_min_system", None)
    woodies_system = getattr(request.app.state, "woodies_system", None)
    day_type_machine = getattr(request.app.state, "day_type_machine", None)

    systems_list = [s.strip() for s in systems.split(",") if s.strip()]

    agg = BuildStatusAggregator(
        five_min_system=five_min_system,
        woodies_system=woodies_system,
        day_type_machine=day_type_machine,
    )
    result = agg.get_status(systems=systems_list)
    return result.model_dump()
