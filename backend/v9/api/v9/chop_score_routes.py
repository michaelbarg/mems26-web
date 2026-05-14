"""API routes for Chop Score / Layer 0 state (Constitution V3 D-044)."""

from fastapi import APIRouter

router = APIRouter(tags=["layer0"])


@router.get("/api/v9/chop_score/current")
def chop_score_current():
    """Return all 6 Chop Score indicators + composite + 4-state.

    Flattened: indicators promoted to top level for frontend Layer0Strip.
    """
    from backend.v9.systems.layer0.chop_score import get_chop_score
    data = get_chop_score()
    # Flatten indicators to top level (frontend reads d.vegas_flips_60m etc.)
    indicators = data.get("indicators", {})
    return {**indicators, "chop_score": data["chop_score"],
            "composite_score": data["chop_score"],  # backward compat — to be removed Wave 2
            "state": data["state"], "computed_at": data["computed_at"]}


@router.get("/api/v9/layer0/state")
def layer0_state():
    """Layer 0 market state — γ.4 spec endpoint.

    Shape: {chop_score: 0-100, state: SEARCHING|RESPECTING|EXPANDING|FOUND,
            indicators: {...}, computed_at: iso_ts}
    """
    from backend.v9.systems.layer0.chop_score import get_chop_score
    return get_chop_score()
