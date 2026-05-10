"""TPO System API — GET endpoints for profile and levels.

These are system-level endpoints (not the raw bar CRUD in /api/v9/bars/tpo).
Intended for dashboard consumption.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.v9.db.session import get_db
from backend.v9.db.models import V9TpoBar
from .schemas import TPOConfig, TPOProfile, TPOLevels
from . import profile_builder as pb
from . import levels as calc
from . import detector

router = APIRouter(prefix="/api/v9/tpo", tags=["tpo"])


def _build_profile_from_bars(
    bars: List[V9TpoBar],
    config: TPOConfig,
) -> TPOProfile:
    """Build a TPO profile from stored TPO bar records."""
    profile = pb.init_profile(config)

    # Group bars by period_id to determine letter
    period_ids = sorted(set(b.period_id for b in bars))
    period_to_letter = {
        pid: pb.LETTERS[i] if i < pb.MAX_LETTERS else pb.LETTERS[-1]
        for i, pid in enumerate(period_ids)
    }

    for bar in bars:
        letter = period_to_letter.get(bar.period_id, "A")
        profile.current_letter = letter
        profile = pb.add_price(profile, bar.price, config)

    if period_ids:
        last_idx = min(len(period_ids) - 1, pb.MAX_LETTERS - 1)
        profile.current_letter = pb.LETTERS[last_idx]
        profile.letter_count = last_idx + 1

    # Lock IB if we have letters beyond B
    if len(period_ids) > 2:
        profile = pb.lock_ib(profile, config)

    # Refresh derived levels
    profile = pb.refresh_levels(profile, config)

    # Detect shape and intent
    profile = detector.classify_shape(profile, config)
    profile = detector.detect_intent(profile, config)
    profile = detector.detect_migration_pattern(profile, config)
    profile = detector.infer_otf_clarity(profile, config)

    return profile


@router.get("/profile")
def get_tpo_profile(
    limit: int = Query(default=500, le=2000),
    period_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Get computed TPO profile from stored bars.

    Returns full profile with POC/VAH/VAL, shape, intent, OTF clarity.
    """
    config = TPOConfig()
    query = db.query(V9TpoBar).order_by(V9TpoBar.ts.desc())
    if period_id is not None:
        query = query.filter(V9TpoBar.period_id >= period_id)
    bars = query.limit(limit).all()

    if not bars:
        return {"profile": TPOProfile().dict(), "bar_count": 0}

    profile = _build_profile_from_bars(bars, config)
    return {
        "profile": profile.dict(exclude={"levels"}),
        "bar_count": len(bars),
    }


@router.get("/levels")
def get_tpo_levels(
    db: Session = Depends(get_db),
):
    """Get current TPO levels (POC/VAH/VAL + IB + naked POCs).

    Lightweight endpoint for dashboard level lines overlay.
    """
    config = TPOConfig()
    bars = db.query(V9TpoBar).order_by(V9TpoBar.ts.desc()).limit(1000).all()

    if not bars:
        return TPOLevels().dict()

    profile = _build_profile_from_bars(bars, config)
    return TPOLevels(
        poc=profile.poc,
        vah=profile.vah,
        val=profile.val,
        session_high=profile.session_high,
        session_low=profile.session_low,
        ib_high=profile.ib.high,
        ib_low=profile.ib.low,
        naked_pocs=profile.naked_pocs,
        hvn_prices=profile.hvn_prices,
        lvn_prices=profile.lvn_prices,
    ).dict()
