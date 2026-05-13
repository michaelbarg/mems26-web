"""API routes for Chop Score (Layer 0, Constitution V3)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v9/chop_score", tags=["chop-score"])


@router.get("/current")
def chop_score_current():
    """Return all 6 Chop Score indicators + composite."""
    from backend.v9.systems.layer0.chop_score import get_chop_score
    return get_chop_score()
