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


def _opening_window_check(direction: str):
    """Item-10 (OPENING_WINDOW_FIRE_V1, default OFF): positive with-drive
    confirmation in the first 30 min of RTH. Import at call time so tests can
    monkeypatch the source module. Fail-safe: error → no override."""
    try:
        from backend.v9.systems.opening_type_gate import opening_window_override
        return opening_window_override(direction=direction)
    except Exception as _e:  # never let the override itself break emission
        logger.warning("[S2] opening-window check errored (no override): %s", _e)
        return (False, f"error: {_e}")


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
            # Item-10: in the first 30 min the day-type label is an immature
            # stage-1 guess — a POSITIVE with-drive opening signal overrides.
            _ow_ok, _ow_reason = _opening_window_check(direction)
            if _ow_ok:
                logger.warning(
                    "[S2] OPENING_WINDOW override: NO_TRADE day_type=%s bypassed — %s",
                    day_type, _ow_reason,
                )
            else:
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
        # Item-10: live incident 2026-07-02 16:45 IL — "INITIATIVE_LONG
        # day_type=UNKNOWN · Auth Table SKIP" killed the opening fire in-system.
        _ow_ok, _ow_reason = _opening_window_check(direction)
        if _ow_ok:
            if sizing <= 0:  # SKIP rows carry 0 contracts — floor for the override
                # L7 (2026-07-08): honor FIXED_CONTRACTS_2 (precedence over _3, same
                # as every other sizing site) — this floor ignored it and sent 1.
                import os as _os
                if _os.environ.get("FIXED_CONTRACTS_4", "0").lower() in ("1", "true", "yes"):
                    sizing = 4  # Michael 2026-07-15
                elif _os.environ.get("FIXED_CONTRACTS_2", "0").lower() in ("1", "true", "yes"):
                    sizing = 2
                elif _os.environ.get("FIXED_CONTRACTS_3", "0").lower() in ("1", "true", "yes"):
                    sizing = 3
                else:
                    sizing = 1
            logger.warning(
                "[S2] OPENING_WINDOW override: Auth Table SKIP (%s × %s) bypassed — %s · contracts=%d",
                pattern_name, _day_type, _ow_reason, sizing,
            )
        else:
            # AUTH_LOWCONF_REDUCED_V1 (Michael ruling 2026-07-30 "תבצע אתה"):
            # a SKIP is only as good as the day-type label it reasons from.
            # 07-29: INITIATIVE_SHORT×UNKNOWN (17:00, the day's biggest trade)
            # and INITIATIVE_LONG×"Normal" at classifier confidence 0.0 (21:55,
            # the breakout) both died here on noise labels. When the classifier's
            # own confidence is below DAYTYPE_PLAYBOOK_MIN_CONF (0.4) — same
            # threshold as the gateway playbook fix — the table's SKIP degrades
            # to REDUCED sizing (2 contracts), not zero. A trustworthy label
            # (conf >= 0.4) keeps the full SKIP: the table's statistics stand.
            import os as _lc_os
            _lc_on = _lc_os.getenv("AUTH_LOWCONF_REDUCED_V1", "0").lower() in ("1", "true", "yes")
            _lc_conf = None
            if _lc_on:
                try:
                    from backend.v9.db.read import read_one as _lc_read
                    _lc_row = _lc_read(
                        "SELECT confidence FROM v9_day_type_state ORDER BY id DESC LIMIT 1", {})
                    _lc_conf = float(_lc_row["confidence"]) if _lc_row and _lc_row["confidence"] is not None else None
                except Exception:
                    _lc_conf = None
            _lc_min = float(_lc_os.getenv("DAYTYPE_PLAYBOOK_MIN_CONF", "0.4") or 0.4)
            if _lc_on and _lc_conf is not None and _lc_conf < _lc_min:
                verdict, sizing = 'REDUCED', 2
                logger.warning(
                    "[S2] AUTH_LOWCONF_REDUCED: Auth Table SKIP (%s × %s) degraded to "
                    "REDUCED-2 — day-type conf %.2f < %.2f (label untrustworthy)",
                    pattern_name, _day_type, _lc_conf, _lc_min,
                )
            else:
                logger.info(
                    "[S2] T1Setup skipped: pattern=%s day_type=%s tier=%s · Auth Table SKIP",
                    pattern_name, _day_type, quality_tier,
                )
                return None

    # T2/T3 SANITY CLAMP (2026-07-31 night, "לתקן את הכל"): trade #579 shipped
    # t2 at 11R and t3 at 21R of the FINAL stop — the day-type R-ladder was
    # computed off the RAW structural stop (40pt) and never re-based after the
    # stop tightened to 8.75pt. Until cc fixes the order-of-operations, clamp
    # runner targets to sane multiples of the FINAL risk so contracts 2-3 have
    # reachable targets instead of riding to the stop. Env-tunable.
    try:
        import os as _tc_os
        # Chart-measure patterns (HNS/DOUBLE/FLAG) target their MEASURED
        # objective — a legitimate structural target, not an R-ladder; the
        # #579 bug lives in the day-type R-LADDER path only. Skip them.
        _tc_skip = any(k in str(pattern_name).upper()
                       for k in ("HNS", "DOUBLE", "FLAG"))
        if _tc_skip:
            raise StopIteration  # exits the clamp block via except below
        _risk_f = abs(float(entry_price) - float(stop_price))
        _sgn = 1.0 if direction == "LONG" else -1.0
        _t2_max = float(_tc_os.getenv("T2_MAX_R", "3.0") or 3.0)
        _t3_max = float(_tc_os.getenv("T3_MAX_R", "5.0") or 5.0)
        if _risk_f > 0 and t2_price is not None and \
                abs(float(t2_price) - entry_price) > _t2_max * _risk_f:
            _t2_old = t2_price
            t2_price = entry_price + _sgn * _t2_max * _risk_f
            logger.warning("[S2] T2 clamp: %.2f (%.1fR of final stop) -> %.2f (%.1fR)",
                           float(_t2_old), abs(float(_t2_old)-entry_price)/_risk_f,
                           t2_price, _t2_max)
        if _risk_f > 0 and t3_price is not None and \
                abs(float(t3_price) - entry_price) > _t3_max * _risk_f:
            _t3_old = t3_price
            t3_price = entry_price + _sgn * _t3_max * _risk_f
            logger.warning("[S2] T3 clamp: %.2f (%.1fR of final stop) -> %.2f (%.1fR)",
                           float(_t3_old), abs(float(_t3_old)-entry_price)/_risk_f,
                           t3_price, _t3_max)
    except StopIteration:
        pass  # chart-measure pattern — clamp intentionally not applied
    except Exception as _tc_err:
        logger.warning("[S2] T2/T3 clamp failed (targets kept): %s", _tc_err)

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
