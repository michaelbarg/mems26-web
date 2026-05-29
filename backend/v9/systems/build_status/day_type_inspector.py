"""Day Type inspector — produces a single entity for S1 Day Type system.

Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.3
"""

import logging
import sqlite3
from datetime import date, datetime, timezone
from typing import Optional

from backend.v9.common.trading_date import et_today
from .types import PatternStatus, Component, SystemStatus, DataFreshness
from .row_helpers import make_freshness, freshness_now

logger = logging.getLogger(__name__)

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"


def inspect(day_type_machine=None) -> SystemStatus:
    """Build the day-type system status.

    Reads from v9_day_type_history (same SQL as day_type_v9_routes.py).
    Optionally uses the live DayTypeStateMachine from app.state if provided.
    """
    system = SystemStatus(
        id="day_type",
        name="S1 · Day Type Classification",
    )

    today = et_today().isoformat()
    row = None

    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM v9_day_type_history WHERE date = ? LIMIT 1",
            (today,),
        ).fetchone()
        conn.close()
    except Exception as e:
        logger.warning("[BuildStatus/DayType] DB read failed: %s", e)
        system.patterns.append(PatternStatus(
            id="day_type_current",
            name="Day Type Classification",
            status="unknown",
            label="❓ Unknown",
            reason=f"DB read failed: {e}",
        ))
        return system

    system.running = True
    system.hydrated = row is not None

    if row is None:
        system.patterns.append(PatternStatus(
            id="day_type_current",
            name="Day Type Classification",
            status="unknown",
            label="❓ Unknown",
            reason="No classification for today",
        ))
        return system

    r = dict(row)
    day_type_val = r.get("day_type")
    # Safe float conversion — DB may have string values like "PENDING"
    raw_prob = r.get("probability")
    try:
        probability = float(raw_prob) if raw_prob is not None else None
    except (ValueError, TypeError):
        probability = None
    raw_dir = r.get("directional_certainty")
    try:
        directional = float(raw_dir) if raw_dir is not None else None
    except (ValueError, TypeError):
        directional = None
    ib_width_class = r.get("ib_width_class")
    opening_type = r.get("opening_type")
    zohar_rules_raw = r.get("active_zohar_rules")
    last_updated = r.get("last_updated_at")

    # Parse zohar rules
    zohar_rules = []
    if isinstance(zohar_rules_raw, str):
        import json
        try:
            zohar_rules = json.loads(zohar_rules_raw)
        except (json.JSONDecodeError, TypeError):
            zohar_rules = []
    elif isinstance(zohar_rules_raw, list):
        zohar_rules = zohar_rules_raw

    is_developing = ib_width_class == "DEVELOPING"
    is_classified = (not is_developing) and day_type_val not in (None, "UNKNOWN")

    ib_h = r.get("ib_high")
    ib_l = r.get("ib_low")
    ib_locked = ib_width_class not in (None, "DEVELOPING", "UNKNOWN")
    ib_range_pts = round(ib_h - ib_l, 2) if (ib_h is not None and ib_l is not None) else None
    trading_conf = r.get("trading_confidence")

    _DRIVE_TYPES = {"OPEN_DRIVE", "OPEN_TEST_DRIVE"}
    opening_run = opening_type in _DRIVE_TYPES if opening_type else False

    # All Day Type rows are sourced from the same v9_day_type_history row;
    # use `last_updated_at` as the freshness anchor so the UI can see when
    # the classifier last touched today's row. Inspector-eval fallback
    # ensures the row still has a Freshness object when the DB column is null.
    _row_freshness = (
        make_freshness(last_updated, "db") if last_updated else freshness_now("db")
    )

    components = [
        Component(
            stage="data",
            key="ib_locked",
            spec="IB range locked (width_class ≠ DEVELOPING)",
            present=ib_locked,
            value=f"ib_width_class={ib_width_class}" if ib_width_class else "not set",
            live=str(ib_width_class) if ib_width_class is not None else "null",
            required="not in {None, DEVELOPING, UNKNOWN}",
            freshness=_row_freshness,
        ),
        Component(
            stage="data",
            key="opening_type_set",
            spec="opening_type not null",
            present=opening_type is not None and opening_type != "UNKNOWN",
            value=str(opening_type) if opening_type else "not set",
            live=str(opening_type) if opening_type is not None else "null",
            required="not in {None, UNKNOWN}",
            freshness=_row_freshness,
        ),
        Component(
            stage="data",
            key="opening_run_detected",
            spec="opening run detected (OPEN_DRIVE or OPEN_TEST_DRIVE)",
            present=opening_run,
            value=str(opening_type) if opening_run else f"{opening_type or 'not set'} (not a run)",
            live=str(opening_type) if opening_type is not None else "null",
            required="in {OPEN_DRIVE, OPEN_TEST_DRIVE}",
            freshness=_row_freshness,
        ),
        Component(
            stage="data",
            key="ib_range_pts",
            spec="IB range in points (context: NARROW <15 / MEDIUM 15-25 / WIDE >25)",
            present=ib_range_pts is not None,
            value=(
                f"{ib_range_pts:.1f} pt → {ib_width_class}"
                if ib_range_pts is not None
                else "not yet available"
            ),
            live=f"{ib_range_pts:.2f}" if ib_range_pts is not None else "null",
            required="!= null",
            freshness=_row_freshness,
        ),
        Component(
            stage="classification",
            key="trading_confidence",
            spec="trading_confidence set (HIGH / MEDIUM / LOW)",
            present=trading_conf is not None and str(trading_conf) not in ("", "None"),
            value=str(trading_conf) if trading_conf is not None else "not set",
            live=str(trading_conf) if trading_conf is not None else "null",
            required="in {HIGH, MEDIUM, LOW}",
            freshness=_row_freshness,
        ),
        Component(
            stage="classification",
            key="day_type_assigned",
            spec="day_type classified (not UNKNOWN, not null)",
            present=day_type_val not in (None, "UNKNOWN"),
            value=str(day_type_val) if day_type_val else "not set",
            live=str(day_type_val) if day_type_val is not None else "null",
            required="not in {None, UNKNOWN}",
            freshness=_row_freshness,
        ),
        Component(
            stage="classification",
            key="probability_above_threshold",
            spec="probability ≥ 0.55 (per spec)",
            present=probability is not None and float(probability) >= 0.55,
            value=f"{float(probability):.2f}" if probability is not None else "not set",
            live=f"{float(probability):.4f}" if probability is not None else "null",
            required=">= 0.55",
            freshness=_row_freshness,
        ),
        Component(
            stage="classification",
            key="directional_certainty",
            spec="directional_certainty ≥ threshold",
            present=directional is not None and float(directional) > 0,
            value=f"{float(directional):.2f}" if directional is not None else "not set",
            live=f"{float(directional):.4f}" if directional is not None else "null",
            required="> 0.0",
            freshness=_row_freshness,
        ),
        Component(
            stage="classification",
            key="zohar_rules_evaluated",
            spec="len(active_zohar_rules) > 0",
            present=len(zohar_rules) > 0,
            value=f"{len(zohar_rules)} rules" if zohar_rules else "none",
            live=str(len(zohar_rules)),
            required="> 0",
            freshness=_row_freshness,
        ),
        Component(
            stage="classification",
            key="not_developing",
            spec="developing == false (IB locked, classification stable)",
            present=not is_developing,
            value="developing" if is_developing else "stable",
            live="developing" if is_developing else "stable",
            required="== stable",
            freshness=_row_freshness,
        ),
    ]

    # Determine status per §4.3
    if is_classified and probability is not None and float(probability) >= 0.55:
        status = "fired"
        label = "✅ Fired"
        reason = f"Classification COMPLETE: {day_type_val} (p={float(probability):.2f})"
    elif ib_locked and opening_type and opening_type != "UNKNOWN":
        status = "armed"
        label = "🟡 Armed"
        reason = f"IB locked, opening_type={opening_type}, awaiting probability"
    elif is_developing:
        status = "armed"
        label = "🟡 Armed"
        reason = "IB developing — classification in progress"
    else:
        status = "blocked"
        label = "❌ Blocked"
        blockers_list = [c.key for c in components if not c.present]
        reason = f"Missing: {', '.join(blockers_list)}" if blockers_list else "Missing data"

    # Check for zohar veto forcing UNKNOWN
    if day_type_val == "UNKNOWN" and len(zohar_rules) > 0:
        status = "vetoed"
        label = "🟠 Vetoed"
        reason = "Zohar rules force UNKNOWN"

    blockers = [f"classification.{c.key}" for c in components if not c.present and c.stage == "classification"]

    system.data_freshness = DataFreshness(
        last_bar_ts=last_updated,
        lag_seconds=None,
        fresh=is_classified,
        threshold_seconds=360,
    )

    system.patterns.append(PatternStatus(
        id="day_type_current",
        name="Day Type Classification",
        status=status,
        label=label,
        reason=reason,
        fired_today=is_classified,
        last_fire_ts=last_updated if is_classified else None,
        components=components,
        blockers=blockers,
    ))

    return system
