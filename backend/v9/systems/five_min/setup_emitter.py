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
from .quality_tier import get_quality_tier_v2
from .time_stop_mapper import get_time_stop
from .contract_split import get_contract_split
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
    t3_price: Optional[float] = None,
    current_price: Optional[float] = None,
    tpo_data: Optional[dict] = None,
) -> Optional[T1Setup]:
    """Build, validate, and return T1Setup ready for gateway routing.

    Returns T1Setup if valid, None if validation fails.
    Caller is responsible for routing to gateway (mode-dependent).
    """
    # D-091.Q2 defense-in-depth: refuse NT setups at emit layer
    if day_type:
        from backend.v9.systems.day_type.targets_table import get_targets as _get_targets
        _targets = _get_targets(day_type)
        if _targets is not None and _targets.get("no_trade", False):
            logger.warning(
                "[S2] emit_t1_setup refused: day_type=%s is NO_TRADE (D-091.Q2)",
                day_type,
            )
            return None

    # Quality tier + sizing from Auth Table V1 (pattern x day_type x tier)
    price_for_tier = current_price or entry_price
    _day_type = day_type if day_type else "Neutral_Center"
    verdict, quality_tier, sizing = get_quality_tier_v2(
        pattern_name, _day_type, price_for_tier, tpo_data=tpo_data,
    )

    # SKIP verdict short-circuits (Lock #2)
    if verdict == 'SKIP':
        logger.info(
            "[S2] T1Setup skipped: pattern=%s day_type=%s tier=%s · Auth Table SKIP",
            pattern_name, _day_type, quality_tier,
        )
        return None

    # Time stop from Day Type
    time_stop = get_time_stop(day_type)

    # Pkg 3c · contract split per pattern
    t1_pct, t2_pct, t3_pct = get_contract_split(pattern_name)

    # Build T1Setup (time_stop_minutes now Optional · t3_price NEW)
    setup = T1Setup(
        pattern_name=pattern_name,
        direction=direction,
        entry_price=entry_price,
        stop_price=stop_price,
        t1_price=t1_price,
        t2_price=t2_price,
        t3_price=t3_price,
        time_stop_minutes=time_stop,
        confidence=75,  # base confidence from pattern detection
        t1_pct=t1_pct,
        t2_pct=t2_pct,
        t3_pct=t3_pct,
        bar_index=bar_index,
        fired_at=datetime.now(timezone.utc),
        quality_tier=quality_tier,
        sizing_contracts=sizing,
        provisional=False,  # Path A: Layer 3 provides real data
        provisional_reason=None,
    )

    # Validate via pre_fire_validator (M18 · D-063)
    # time_stop_minutes is Optional (None for Trend_Normal) — use 180 as passthrough for validator
    _ts_for_validator = setup.time_stop_minutes if setup.time_stop_minutes is not None else 180
    req = FireRequest(
        system_id=setup.system_id,
        direction=setup.direction,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        t1_price=setup.t1_price,
        t2_price=setup.t2_price,
        time_stop_minutes=_ts_for_validator,
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
