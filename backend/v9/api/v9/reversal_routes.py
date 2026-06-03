"""API routes for 15-tick reversal bar enrichment (P-15TR.5)."""

from fastapi import APIRouter, Request

from backend.v9.db.read import read_all

router = APIRouter(prefix="/api/v9/reversal", tags=["reversal"])


@router.get("/current")
async def reversal_current(request: Request):
    """Return latest reversal bar enrichment (cluster + empty zone)."""
    handler = getattr(request.app.state, "reversal_handler", None)
    if handler is None:
        return {"running": False, "error": "ReversalBarHandler not initialized"}
    return handler.get_current()


@router.get("/history")
async def reversal_history(limit: int = 20):
    """Return recent reversal enrichment records."""
    try:
        rows = read_all(
            "SELECT * FROM v9_reversal_enrichment ORDER BY bar_ts DESC LIMIT :limit",
            {"limit": limit},
        )
        return {"entries": rows}
    except Exception as e:
        return {"entries": [], "error": str(e)}
