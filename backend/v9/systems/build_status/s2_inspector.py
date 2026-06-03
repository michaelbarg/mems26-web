"""S2 Five-Minute inspector — produces 10 pattern status objects.

Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.1
Pattern list: S2_AUTH_TABLE_V1.md §2
"""

import logging
import time
from datetime import date, datetime, timezone
from typing import Optional, List

from .types import PatternStatus, Component, SystemStatus, DataFreshness, GlobalGate
from .auth_table_lookup import S2_PATTERN_IDS, lookup_auth_cell, is_skip
from .s2_pattern_probe import probe_pattern as _probe_pattern
from .row_helpers import (
    fires_today,
    freshness_now,
    latest_valid_db_ts,
    make_freshness,
)

# firing_system enum value for the S2 Five-Minute setup emitter
# (`backend/v9/services/trade_manager/manager.py` write path).
_FIRING_SYSTEM_FIVE_MIN = 2

logger = logging.getLogger(__name__)

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

# Human-readable names for patterns
_PATTERN_NAMES = {
    "REACTIVE_LONG": "Reactive Long",
    "REACTIVE_SHORT": "Reactive Short",
    "INITIATIVE_LONG": "Initiative Long",
    "INITIATIVE_SHORT": "Initiative Short",
    "INVERSE_HNS_LONG": "Inverse H&S Long",
    "HNS_TOP_SHORT": "H&S Top Short",
    "DOUBLE_BOTTOM_EE_LONG": "Double Bottom EE Long",
    "DOUBLE_TOP_AA_SHORT": "Double Top AA Short",
    "BULL_FLAG_LONG": "Bull Flag Long",
    "BEAR_FLAG_SHORT": "Bear Flag Short",
}


def inspect(five_min_system=None, day_type_str: Optional[str] = None) -> SystemStatus:
    """Build the S2 Five-Minute system status with 10 patterns.

    Args:
        five_min_system: FiveMinSystem instance from app.state (may be None)
        day_type_str: Current day type string (e.g. "Neutral_Center")
    """
    system = SystemStatus(
        id="five_min",
        name="S2 · Five-Minute Patterns",
    )

    if five_min_system is None:
        system.running = False
        system.hydrated = False
        for pid in S2_PATTERN_IDS:
            system.patterns.append(PatternStatus(
                id=pid,
                name=_PATTERN_NAMES.get(pid, pid),
                status="unknown",
                label="❓ Unknown",
                reason="FiveMinSystem not initialized",
            ))
        return system

    # Read system state
    state = five_min_system.get_state()
    system.running = state.get("running", False)
    system.hydrated = state.get("hydrated", False)
    system.mode = state.get("mode")

    # D-OBS: Populate live inputs + interpretations
    from .types import LiveInput, Interpretation
    system.live_inputs = [
        LiveInput(field="buffer_size", value=str(state.get("buffer_size", 0)), source="in_memory"),
        LiveInput(field="mode", value=str(state.get("mode")), source="in_memory"),
        LiveInput(field="opening_type", value=str(state.get("opening_type")), source="S1_classification"),
        LiveInput(field="last_pattern", value=str(state.get("last_pattern")), source="detection_engine"),
        LiveInput(field="last_classification", value=str(state.get("last_classification")), source="detection_engine"),
    ]
    system.interpretations = [
        Interpretation(key="mode", value=str(state.get("mode")), from_input="session_time+IB_lock", detail="OVERNIGHT→FIRST_HOUR→DAY_TYPE"),
        Interpretation(key="day_type_gate", value=f"{day_type_str or 'UNKNOWN'}", from_input="S1_day_type", detail="Controls Auth Table gating"),
        Interpretation(key="opening_type", value=str(state.get("opening_type")), from_input="S1_classification"),
    ]

    # Data freshness: latest non-future bar from DB (lex-sorted MAX(ts)
    # would be poisoned by sentinel future rows — use latest_valid_db_ts).
    last_bar_ts = None
    lag_seconds = None
    try:
        last_bar_ts, _, lag_seconds = latest_valid_db_ts(
            "v9_bars_5min",
            where="symbol = ?",
            params=("MES",),
        )
    except Exception as e:
        logger.warning("[BuildStatus/S2] DB read for freshness failed: %s", e)

    # 5-min bars close every 300s; lag up to 600s between closes is normal.
    # Threshold 660s = 1 full bar period + 60s grace (not "stale" between closes).
    fresh = lag_seconds is not None and lag_seconds < 660
    # Fallback: if in-memory system has a buffer, data is live
    if not fresh and five_min_system is not None:
        try:
            _s = five_min_system.get_state() if hasattr(five_min_system, 'get_state') else {}
            if isinstance(_s, dict) and (_s.get("buffer_size") or 0) > 0:
                fresh = True
        except Exception:
            pass
    system.data_freshness = DataFreshness(
        last_bar_ts=last_bar_ts,
        lag_seconds=round(lag_seconds, 1) if lag_seconds is not None else None,
        fresh=fresh,
        threshold_seconds=660,
    )

    # Buffer size for CCI check
    buffer_size = state.get("buffer_size", 0)
    bar_buffer = getattr(five_min_system, "_bar_buffer", [])
    actual_buffer_size = len(bar_buffer) if bar_buffer else buffer_size

    # Mode context (must be resolved BEFORE fhb_eligible since fhb gate
    # short-circuits to eligible once we're past the first hour).
    mode_val = state.get("mode")
    mode_str = mode_val.value if hasattr(mode_val, "value") else str(mode_val) if mode_val else "UNKNOWN"
    mode_trading = mode_str in ("FIRST_HOUR_TACTICAL", "DAY_TYPE_MODE", "INTRADAY")

    # FHB state — from wired FirstHourBuffer instance
    _fhb = getattr(five_min_system, "_fhb", None)
    fhb_state_val = _fhb.state.value if _fhb is not None else "UNKNOWN"
    fhb_bar_count = _fhb.bar_count if _fhb is not None else 0
    # FHB blocks when ACCUMULATING (< bar 4); all other states are eligible for at least some patterns.
    # After first hour (DAY_TYPE_MODE / INTRADAY), FHB is no longer relevant — treat as eligible.
    fhb_eligible = mode_str in ("DAY_TYPE_MODE", "INTRADAY") or fhb_state_val not in ("ACCUMULATING", "UNKNOWN")

    # Choppiness score — lower is better (trending); ≥70 = choppy market
    choppiness_score = getattr(five_min_system, "choppiness_score", 0)
    chop_ok = choppiness_score < 70

    # Global gates
    is_nt = day_type_str == "Nontrend" if day_type_str else False
    system.global_gates.append(GlobalGate(
        key="nt_day_type",
        spec="DayType != Nontrend",
        present=not is_nt,
        value=day_type_str or "unknown",
        live=day_type_str or "unknown",
        required="!= Nontrend",
        freshness=freshness_now("db"),
    ))

    # Authoritative "fired today" surface — read v9_trades filtered by
    # firing_system=2 (S2 setup emitter), NOT the momentary in-memory state.
    # v9_five_min_setups is the DETECTION-time table (last_signal_ts); the
    # routed FIRE is the v9_trades insert that the trade_manager performs
    # after auth-table approval. Using v9_trades keeps S2 consistent with
    # Woodies and avoids reporting detections that the manager ultimately
    # vetoed.
    fires_dict: dict = {}
    try:
        fires_dict = fires_today(_FIRING_SYSTEM_FIVE_MIN)
    except Exception as e:
        logger.warning("[BuildStatus/S2] DB read for fires failed: %s", e)

    # Pre-compute freshness anchors used across every pattern row.
    # - `bar_fresh` reflects the actual last bar in the DB → DB source.
    # - `state_fresh` reflects the in-memory FiveMinSystem snapshot →
    #   anchored at the same bar (in-memory state advances per bar).
    # - `eval_fresh` is the inspector wall-clock for synthesized rows.
    bar_fresh = (
        make_freshness(last_bar_ts, "db") if last_bar_ts else freshness_now("db")
    )
    state_fresh = (
        make_freshness(last_bar_ts, "in_memory") if last_bar_ts else freshness_now("in_memory")
    )
    eval_fresh = freshness_now("inspector_eval")

    # Build per-pattern status
    for pid in S2_PATTERN_IDS:
        components = []

        # data: five_min_bar_recency
        # `live` is the actual lag value (the thing being checked);
        # `required` is the threshold the check enforces.
        components.append(Component(
            stage="data",
            key="five_min_bar_recency",
            spec="max(ts) within last 6 min",
            present=fresh,
            value=f"lag={round(lag_seconds, 0)}s" if lag_seconds is not None else "unknown",
            live=f"{round(lag_seconds, 1)}s" if lag_seconds is not None else "unknown",
            required="<= 360s",
            freshness=bar_fresh,
        ))

        # data: cci_14_history (≥14 5-min bars buffered)
        cci_ok = actual_buffer_size >= 14
        components.append(Component(
            stage="data",
            key="cci_14_history",
            spec="≥14 5-min bars buffered",
            present=cci_ok,
            value=f"buffer={actual_buffer_size}",
            live=str(actual_buffer_size),
            required=">= 14",
            freshness=state_fresh,
        ))

        # day_type_gate: day_type_known
        components.append(Component(
            stage="day_type_gate",
            key="day_type_known",
            spec="v9_day_type_history today row classified",
            present=day_type_str is not None and day_type_str != "UNKNOWN",
            value=day_type_str or "unknown",
            live=day_type_str if day_type_str is not None else "null",
            required="not in {None, UNKNOWN}",
            freshness=freshness_now("db"),
        ))

        # day_type_gate: auth_table_cell
        if day_type_str and day_type_str not in (None, "UNKNOWN"):
            cell = lookup_auth_cell(pid, day_type_str)
            verdict = cell[0]
            cell_skip = verdict == "SKIP"
            components.append(Component(
                stage="day_type_gate",
                key="auth_table_cell",
                spec=f"S2_AUTH_TABLE_V1[{pid}][{day_type_str}] ≠ SKIP",
                present=not cell_skip,
                value=f"{verdict} {cell[1]}/{cell[2]}/{cell[3]}",
                live=verdict,
                required="!= SKIP",
                freshness=eval_fresh,
            ))
        else:
            components.append(Component(
                stage="day_type_gate",
                key="auth_table_cell",
                spec=f"S2_AUTH_TABLE_V1[{pid}][?] ≠ SKIP",
                present=False,
                value="day_type unknown — cannot evaluate",
                live="day_type=unknown",
                required="!= SKIP",
                freshness=eval_fresh,
            ))

        # day_type_gate: nt_skip
        components.append(Component(
            stage="day_type_gate",
            key="nt_skip",
            spec="not Nontrend day type",
            present=not is_nt,
            value="NT → all patterns blocked" if is_nt else "OK",
            live=day_type_str if day_type_str is not None else "null",
            required="!= Nontrend",
            freshness=eval_fresh,
        ))

        # data: mode_context — must be in trading window (FHT or INTRADAY)
        components.append(Component(
            stage="data",
            key="mode_context",
            spec="FiveMinMode in {FIRST_HOUR_TACTICAL, INTRADAY}",
            present=mode_trading,
            value=mode_str,
            live=mode_str,
            required="in {FIRST_HOUR_TACTICAL, INTRADAY}",
            freshness=state_fresh,
        ))

        # data: fhb_eligible — First Hour Buffer gate
        components.append(Component(
            stage="data",
            key="fhb_eligible",
            spec="FHB state not ACCUMULATING (bars 4+ since RTH open)",
            present=fhb_eligible,
            value=f"fhb={fhb_state_val} bar={fhb_bar_count}",
            live=f"{fhb_state_val}@bar{fhb_bar_count}",
            required="not in {ACCUMULATING, UNKNOWN}",
            freshness=state_fresh,
        ))

        # data: choppiness_ok — choppiness score < 70
        components.append(Component(
            stage="data",
            key="choppiness_ok",
            spec="choppiness_score < 70 (trending, not choppy)",
            present=chop_ok,
            value=f"chop={choppiness_score}",
            live=str(choppiness_score),
            required="< 70",
            freshness=state_fresh,
        ))

        # detection sub-layer — geometric probe per pattern
        probe_comps = _probe_pattern(pid, bar_buffer, five_min_system)
        # Enrich probe rows with live/required/freshness. The probe module
        # returns rows whose `value` already contains the live measurement
        # and whose `spec` contains the threshold; we mirror them into the
        # explicit machine-friendly columns and anchor freshness to the
        # latest in-memory bar (probes operate on the bar buffer).
        for _pc in probe_comps:
            if _pc.live is None:
                _pc.live = _pc.value
            if _pc.required is None:
                _pc.required = _pc.spec
            if _pc.freshness is None:
                _pc.freshness = state_fresh
        components.extend(probe_comps)

        # Determine status — history (v9_trades) wins over momentary state.
        fire_entry = fires_dict.get(pid)
        fired_today = fire_entry is not None
        last_fire_ts = fire_entry["last_ts"] if fire_entry else None

        if fired_today:
            status = "fired"
            label = "✅ Fired today"
            reason = (
                f"Setup fired today at {last_fire_ts} "
                f"(v9_trades, firing_system=2) · count={fire_entry['count']}"
            )
        elif is_nt:
            status = "vetoed"
            label = "🟠 Vetoed"
            reason = "Nontrend day type — global NO_TRADE gate (D-091)"
        elif day_type_str and is_skip(pid, day_type_str):
            status = "blocked"
            label = "❌ Blocked"
            reason = f"Auth Table SKIP for {pid} × {day_type_str}"
        else:
            # Separate infrastructure (data + gates) from detection (pattern trigger)
            infra_comps = [c for c in components if c.stage in ("data", "day_type_gate")]
            detect_comps = [c for c in components if c.stage == "detection"]
            infra_ok = all(c.present for c in infra_comps)
            detect_ok = all(c.present for c in detect_comps)

            if infra_ok and not detect_ok:
                # Data + gates ready, pattern not detected yet = ARMED
                status = "armed"
                label = "🟡 Armed"
                failing = next((c for c in detect_comps if not c.present), None)
                reason = f"Awaiting: {failing.key} — {failing.value}" if failing else "Awaiting trigger"
            elif infra_ok and detect_ok:
                status = "armed"
                label = "🟡 Armed"
                reason = "All conditions met — awaiting trigger signal"
            else:
                # Infrastructure missing = truly BLOCKED
                status = "blocked"
                label = "❌ Blocked"
                blockers_list = [f"{c.stage}.{c.key}" for c in infra_comps if not c.present]
                reason = f"Missing: {', '.join(blockers_list)}" if blockers_list else "Missing data"

        blockers = [f"{c.stage}.{c.key}" for c in components if not c.present]

        system.patterns.append(PatternStatus(
            id=pid,
            name=_PATTERN_NAMES.get(pid, pid),
            status=status,
            label=label,
            reason=reason,
            fired_today=fired_today,
            last_fire_ts=last_fire_ts,
            components=components,
            blockers=blockers,
        ))

    # System-level aggregation: sum per-pattern counts, max per-pattern ts.
    system.fired_today_count = sum(v["count"] for v in fires_dict.values())
    last_ts_candidates = [v["last_ts"] for v in fires_dict.values() if v.get("last_ts")]
    system.last_fire_ts = max(last_ts_candidates) if last_ts_candidates else None

    return system
