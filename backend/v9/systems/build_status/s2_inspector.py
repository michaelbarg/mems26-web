"""S2 Five-Minute inspector — produces 10 pattern status objects.

Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.1
Pattern list: S2_AUTH_TABLE_V1.md §2
"""

import logging
import sqlite3
import time
from datetime import date, datetime, timezone
from typing import Optional, List

from .types import PatternStatus, Component, SystemStatus, DataFreshness, GlobalGate
from .auth_table_lookup import S2_PATTERN_IDS, lookup_auth_cell, is_skip

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

    # Data freshness: last bar timestamp from DB
    last_bar_ts = None
    lag_seconds = None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)
        row = conn.execute("SELECT MAX(ts) FROM v9_bars_5min WHERE symbol='MES'").fetchone()
        conn.close()
        if row and row[0]:
            last_bar_ts = str(row[0])
            try:
                bar_dt = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
                if bar_dt.tzinfo is None:
                    bar_dt = bar_dt.replace(tzinfo=timezone.utc)
                lag_seconds = (datetime.now(timezone.utc) - bar_dt).total_seconds()
            except (ValueError, TypeError):
                pass
    except Exception as e:
        logger.warning("[BuildStatus/S2] DB read for freshness failed: %s", e)

    fresh = lag_seconds is not None and lag_seconds < 360
    system.data_freshness = DataFreshness(
        last_bar_ts=last_bar_ts,
        lag_seconds=round(lag_seconds, 1) if lag_seconds is not None else None,
        fresh=fresh,
        threshold_seconds=360,
    )

    # Buffer size for CCI check
    buffer_size = state.get("buffer_size", 0)
    bar_buffer = getattr(five_min_system, "_bar_buffer", [])
    actual_buffer_size = len(bar_buffer) if bar_buffer else buffer_size

    # Global gates
    is_nt = day_type_str == "Nontrend" if day_type_str else False
    system.global_gates.append(GlobalGate(
        key="nt_day_type",
        spec="DayType != Nontrend",
        present=not is_nt,
        value=day_type_str or "unknown",
    ))

    # Load today's fires from v9_five_min_setups
    today_fires = {}
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)
        conn.row_factory = sqlite3.Row
        today_str = date.today().isoformat()
        rows = conn.execute(
            "SELECT pattern, ts FROM v9_five_min_setups WHERE DATE(ts) = ? ORDER BY ts DESC",
            (today_str,),
        ).fetchall()
        conn.close()
        for r in rows:
            p = r["pattern"]
            if p not in today_fires:
                today_fires[p] = str(r["ts"])
    except Exception as e:
        logger.warning("[BuildStatus/S2] DB read for fires failed: %s", e)

    # Build per-pattern status
    for pid in S2_PATTERN_IDS:
        components = []

        # data: five_min_bar_recency
        components.append(Component(
            stage="data",
            key="five_min_bar_recency",
            spec="max(ts) within last 6 min",
            present=fresh,
            value=f"lag={round(lag_seconds, 0)}s" if lag_seconds is not None else "unknown",
        ))

        # data: cci_14_history (≥14 5-min bars buffered)
        cci_ok = actual_buffer_size >= 14
        components.append(Component(
            stage="data",
            key="cci_14_history",
            spec="≥14 5-min bars buffered",
            present=cci_ok,
            value=f"buffer={actual_buffer_size}",
        ))

        # day_type_gate: day_type_known
        components.append(Component(
            stage="day_type_gate",
            key="day_type_known",
            spec="v9_day_type_history today row classified",
            present=day_type_str is not None and day_type_str != "UNKNOWN",
            value=day_type_str or "unknown",
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
            ))
        else:
            components.append(Component(
                stage="day_type_gate",
                key="auth_table_cell",
                spec=f"S2_AUTH_TABLE_V1[{pid}][?] ≠ SKIP",
                present=False,
                value="day_type unknown — cannot evaluate",
            ))

        # day_type_gate: nt_skip
        components.append(Component(
            stage="day_type_gate",
            key="nt_skip",
            spec="not Nontrend day type",
            present=not is_nt,
            value="NT → all patterns blocked" if is_nt else "OK",
        ))

        # Determine status
        fired_today = pid in today_fires
        last_fire_ts = today_fires.get(pid)

        if fired_today:
            status = "fired"
            label = "✅ Fired"
            reason = f"Setup emitted today at {last_fire_ts}"
        elif is_nt:
            status = "vetoed"
            label = "🟠 Vetoed"
            reason = "Nontrend day type — global NO_TRADE gate (D-091)"
        elif day_type_str and is_skip(pid, day_type_str):
            status = "blocked"
            label = "❌ Blocked"
            reason = f"Auth Table SKIP for {pid} × {day_type_str}"
        elif all(c.present for c in components):
            status = "armed"
            label = "🟡 Armed"
            reason = "All data requirements met — awaiting pattern trigger"
        else:
            status = "blocked"
            label = "❌ Blocked"
            blockers_list = [f"{c.stage}.{c.key}" for c in components if not c.present]
            reason = f"Missing: {', '.join(blockers_list)}"

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

    return system
