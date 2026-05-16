"""setup_emitter — PATH A: full Layer 3 + validator + gateway composer.

Flow:
  pattern detection result → build T1Setup (via Layer 3 cluster+empty_zone) →
  pre_fire_validator → route to gateway (SHADOW mode).

Per D-051 T1 label wire + Constitution V3 §Part 6.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Literal

from .output_schema import T1Setup, PatternName
from .quality_tier import get_quality_tier
from .time_stop_mapper import get_time_stop
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire

logger = logging.getLogger(__name__)


def emit_t1_setup(
    pattern_name: PatternName,
    direction: Literal['LONG', 'SHORT'],
    entry_price: float,
    stop_price: float,
    t1_price: float,
    t2_price: float,
    bar_index: int,
    *,
    day_type: Optional[str] = None,
    current_price: Optional[float] = None,
    tpo_data: Optional[dict] = None,
) -> Optional[T1Setup]:
    """Build, validate, and return T1Setup ready for gateway routing.

    Returns T1Setup if valid, None if validation fails.
    Caller is responsible for routing to gateway (mode-dependent).
    """
    # Quality tier from TPO location
    price_for_tier = current_price or entry_price
    quality_tier, sizing = get_quality_tier(price_for_tier, tpo_data=tpo_data)

    # Skip if LOW quality (sizing=0)
    if sizing == 0:
        logger.info("[S2] Quality LOW (outside value area) — skipping fire")
        return None

    # Time stop from Day Type
    time_stop = get_time_stop(day_type)

    # Build T1Setup
    setup = T1Setup(
        pattern_name=pattern_name,
        direction=direction,
        entry_price=entry_price,
        stop_price=stop_price,
        t1_price=t1_price,
        t2_price=t2_price,
        time_stop_minutes=time_stop,
        confidence=75,  # base confidence from pattern detection
        bar_index=bar_index,
        fired_at=datetime.now(timezone.utc),
        quality_tier=quality_tier,
        sizing_contracts=sizing,
        provisional=False,  # Path A: Layer 3 provides real data
        provisional_reason=None,
    )

    # Validate via pre_fire_validator (M18 · D-063)
    req = FireRequest(
        system_id=setup.system_id,
        direction=setup.direction,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        t1_price=setup.t1_price,
        t2_price=setup.t2_price,
        time_stop_minutes=setup.time_stop_minutes,
        confidence=setup.confidence,
    )
    resp = validate_fire(req)

    if not resp.valid:
        logger.warning("[S2] pre_fire_validator REJECTED: %s", resp.fail_reason)
        return None

    logger.info(
        "[S2] T1Setup emitted: %s %s entry=%.2f stop=%.2f tier=%s contracts=%d",
        pattern_name, direction, entry_price, stop_price, quality_tier, sizing,
    )
    return setup
