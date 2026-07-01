"""P30 C1 — Mid-session restart IB seeding for Day Type Engine.

Root cause (investigation 651647eb, 2026-05-19):
  Every FastAPI restart spawns a fresh `DayTypeStateMachine` with
  `bar_count=0`, `ib_high=0`, `ib_low=inf`. The first 5-min bar after
  the restart sees `session_min > ib_period_min (60)`, so `_stage_a3`
  advances to `_stage_a4` immediately and locks IB from one single
  bar's high/low (≈5 pt → NARROW). The Decision Matrix's
  `(UNKNOWN, NARROW)` slot is empty, so `_stage_b1` falls through to
  `DayType.Normal`, and `_rescore_from_behavior` later keeps a
  Nontrend cluster forming as more post-restart bars accumulate.
  This skewed 2026-05-19 to a `Nontrend` verdict despite the day
  showing a 79-pt range with clear directional movement.

Fix:
  When the engine is fresh and we are already past the IB window,
  seed `ib_high`, `ib_low`, `ib_class`, mark `ib_locked=True`, and
  jump straight to `Stage.B1`. TPO holds the authoritative IB
  (Sierra Initial Balance study) so we trust it over re-derivation
  from a partial bar window.

Guardrails:
  * `bar_count == 0` only — never overwrite a running engine.
  * Requires TPO IB to be marked locked AND both ib_high / ib_low
    finite + positive + `ib_high > ib_low`.
  * If any guard fails, do nothing — engine proceeds with default A1
    flow (which is correct when restart happens before 10:30 ET).
"""

from __future__ import annotations

import logging
from typing import Any, Optional


def maybe_seed_ib_from_tpo(
    *,
    machine: Any,
    session_min: int,
    tpo_ib_locked: bool,
    tpo_ib_high: Optional[float],
    tpo_ib_low: Optional[float],
    logger: Optional[logging.Logger] = None,
) -> bool:
    """Seed the Day Type machine's IB from TPO on the first post-restart bar.

    Returns True if seeding happened, False otherwise. Caller should
    invoke this **before** `machine.process_bar(bar_input)` so that the
    machine has already been advanced past stage A3/A4 before its
    standard pipeline runs.
    """
    if machine is None:
        return False

    # Lazy imports — keep this module light at startup
    from backend.v9.systems.day_type.detector import classify_ib_width
    from backend.v9.systems.day_type.schemas import (
        IBClassification, OpeningDetection, OpeningType, Stage,
    )

    bar_count = int(getattr(machine, "bar_count", 0) or 0)
    if bar_count != 0:
        return False

    config = getattr(machine, "config", None)
    ib_period_min = int(getattr(config, "ib_period_min", 60))
    if int(session_min) <= ib_period_min:
        return False

    if not tpo_ib_locked:
        return False

    if tpo_ib_high is None or tpo_ib_low is None:
        return False

    try:
        ih = float(tpo_ib_high)
        il = float(tpo_ib_low)
    except (TypeError, ValueError):
        return False

    if not (ih > 0 and il > 0 and ih > il):
        return False

    ib_range = ih - il
    narrow_max = float(getattr(config, "ib_narrow_max_pt", 15.0))
    medium_max = float(getattr(config, "ib_medium_max_pt", 25.0))
    ib_width = classify_ib_width(ib_range, narrow_max=narrow_max, medium_max=medium_max)

    machine.ib_high = ih
    machine.ib_low = il
    machine.ib_class = IBClassification(
        ib_high=ih,
        ib_low=il,
        ib_range=ib_range,
        ib_width=ib_width,
    )
    machine.ib_locked = True
    # Restart recovery (v2, Michael-approved 2026-05-30):
    # Load opening_type / day_type / lock_state / confidence from today's
    # v9_day_type_history row instead of forcing INDETERMINATE. Only fall
    # back to INDETERMINATE if no saved row exists for today.
    _loaded_opening = None
    try:
        from backend.v9.common.trading_date import et_today
        from backend.v9.db.session import SessionLocal
        from backend.v9.systems.day_type.schemas import DayType
        from sqlalchemy import text as _text
        _db = SessionLocal()
        _today = et_today().isoformat()
        _row = _db.execute(
            _text(
                "SELECT opening_type, day_type, confidence "
                "FROM v9_day_type_history "
                "WHERE date = :d AND status != 'ROLLED_OVER' "
                "ORDER BY last_updated_at DESC LIMIT 1"
            ),
            {"d": _today},
        ).fetchone()
        _db.close()
        if _row and _row[0]:
            _ot_str = _row[0]
            try:
                _ot = OpeningType(_ot_str)
            except ValueError:
                _ot = OpeningType.INDETERMINATE
            _loaded_opening = _ot
            # Also restore day_type + confidence if available
            if _row[1]:
                try:
                    machine.day_type = DayType(_row[1])
                except ValueError:
                    pass
            if _row[2] is not None:
                machine.confidence = float(_row[2]) / 100.0  # DB stores 0-100
            if logger is not None:
                logger.info(
                    "[DayType] restart recovery: loaded opening_type=%s day_type=%s "
                    "conf=%.2f from v9_day_type_history (date=%s)",
                    _ot_str, _row[1], machine.confidence, _today,
                )
    except Exception as _e:
        if logger is not None:
            logger.warning("[DayType] restart recovery DB load failed: %s", _e)

    if machine.opening is None:
        if _loaded_opening is not None:
            machine.opening = OpeningDetection(
                opening_type=_loaded_opening,
                drive_direction="NEUTRAL",
                confidence=0.4,
            )
        else:
            # No saved row for today — true INDETERMINATE (degrades to Normal)
            machine.opening = OpeningDetection(
                opening_type=OpeningType.INDETERMINATE,
                drive_direction="NEUTRAL",
                confidence=0.0,
            )
    machine.stage = Stage.B1

    # P4 warm-start: restore session_high/session_low from today's RTH bars
    # so range-based re-scoring (behavior detector) doesn't see a near-zero range.
    try:
        from backend.v9.db.read import read_one as _r1_range
        _range_row = _r1_range(
            "SELECT max(high) as sh, min(low) as sl FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = :d "
            "  AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
            "  AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'",
            {"d": _today if '_today' in dir() else et_today().isoformat()},
        )
        if _range_row and _range_row.get("sh") and _range_row.get("sl"):
            _sh, _sl = float(_range_row["sh"]), float(_range_row["sl"])
            if hasattr(machine, "session_high"):
                machine.session_high = _sh
            if hasattr(machine, "session_low"):
                machine.session_low = _sl
            if hasattr(machine, "rth_session_h"):
                machine.rth_session_h = _sh
            if hasattr(machine, "rth_session_l"):
                machine.rth_session_l = _sl
            if logger is not None:
                logger.info("[DayType] warm-start: session hi=%.2f lo=%.2f (range=%.1f) from DB", _sh, _sl, _sh - _sl)
    except Exception as _rng_err:
        if logger is not None:
            logger.warning("[DayType] warm-start session range failed (non-fatal): %s", _rng_err)

    if logger is not None:
        logger.warning(
            "[DayType] mid-session restart at session_min=%d — seeded IB from TPO "
            "(ib_high=%.2f ib_low=%.2f range=%.2f width=%s); jumped to %s to "
            "avoid the single-bar NARROW IB bug (P30 C1 fix).",
            session_min,
            ih,
            il,
            ib_range,
            ib_width.value if hasattr(ib_width, "value") else str(ib_width),
            machine.stage.value if hasattr(machine.stage, "value") else str(machine.stage),
        )

    return True
