"""Woodies CCI inspector — produces 9 pattern status objects.

Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2
Pattern list: D-092_S4_WOODIES_UPDATE.md §2 (🔒 LOCKED)
Decision tree stages: MEMS26_WOODIES_DECISION_TREE_V1.md A1..A7, B1..B14
"""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .types import PatternStatus, Component, SystemStatus, DataFreshness
from .auth_table_lookup import WOODIES_PATTERN_IDS

logger = logging.getLogger(__name__)

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

# Human-readable names per D-092 §2
_PATTERN_NAMES = {
    "ZLR": "Zero Line Reject",
    "TLB": "Trend Line Break",
    "TT": "Tony Trade / Turbo Touch",
    "GB100": "Ghost Bar at ±100",
    "Vegas": "Vegas Divergence / Cup-and-Handle",
    "Ghost": "CCI Head-and-Shoulders",
    "FaMir": "Failed ZLR at ±200",
    "HTLB": "Horizontal Trend Line Break",
    "HFE": "Hook From Extreme",
}

# Map spec IDs (per D-092 §2) → actual engine pattern_ids (PatternResult.pattern_id)
# PatternResult uses ALL_CAPS; spec uses mixed-case for VEGAS/GHOST/FAMIR
_SPEC_ID_TO_ENGINE = {
    "ZLR": "ZLR",
    "TLB": "TLB",
    "TT": "TT",
    "GB100": "GB100",
    "Vegas": "VEGAS",
    "Ghost": "GHOST",
    "FaMir": "FAMIR",
    "HTLB": "HTLB",
    "HFE": "HFE",
}

# Trend states that allow trading (from MEMS26_WOODIES_DECISION_TREE_V1.md §4 A1)
_TRADING_TREND_STATES = {"BLUE", "RED"}


def inspect(woodies_system=None) -> SystemStatus:
    """Build the Woodies CCI system status with 9 patterns.

    Reads WoodiesSystem.get_current() state — no self-HTTP calls.
    Per BUILD_STATUS_ENDPOINT_DESIGN.md §5.4: all inspectors run in-process.

    Args:
        woodies_system: WoodiesSystem instance from app.state (may be None)
    """
    system = SystemStatus(
        id="woodies",
        name="S4 · Woodies CCI Patterns",
    )

    if woodies_system is None:
        # BUILD_STATUS_ENDPOINT_DESIGN.md §5.5:
        # "If app.state.woodies_system is None → running=false, hydrated=false"
        system.running = False
        system.hydrated = False
        for pid in WOODIES_PATTERN_IDS:
            system.patterns.append(PatternStatus(
                id=pid,
                name=_PATTERN_NAMES.get(pid, pid),
                status="unknown",
                label="❓ Unknown",
                reason="WoodiesSystem not initialized",
            ))
        return system

    # Read state via get_current() — returns dict(self.current_state)
    state = woodies_system.get_current()
    system.running = state.get("running", False)
    system.hydrated = state.get("hydrated", False)
    system.mode = None  # Woodies has no mode field per woodies_system.py

    # Data freshness: last Woodies bar from DB
    last_bar_ts = None
    lag_seconds = None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)
        row = conn.execute(
            "SELECT MAX(ts) FROM v9_bars_5min_woodies"
        ).fetchone()
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
        logger.warning("[BuildStatus/Woodies] DB read for freshness failed: %s", e)

    fresh = lag_seconds is not None and lag_seconds < 360
    system.data_freshness = DataFreshness(
        last_bar_ts=last_bar_ts,
        lag_seconds=round(lag_seconds, 1) if lag_seconds is not None else None,
        fresh=fresh,
        threshold_seconds=360,
    )

    # Extract key state fields from WoodiesSystem.current_state
    # Fields per woodies_system.py lines 54-75 (verified against source)
    cci_14 = state.get("cci_14")
    tcci = state.get("cci_6_tcci")
    trend_state = state.get("trend_state", "GRAY")
    active_patterns_raw = state.get("active_patterns", [])
    ready_to_route = state.get("ready_to_route", False)
    decision_tree = state.get("decision_tree", {})

    cci_present = cci_14 is not None
    tcci_present = tcci is not None

    # Build set of active engine pattern_ids for fast lookup
    active_engine_ids = set()
    for ap in active_patterns_raw:
        if isinstance(ap, dict):
            pid = ap.get("pattern_id")
        else:
            pid = getattr(ap, "pattern_id", None)
        if pid:
            active_engine_ids.add(str(pid).upper())

    # Stage A1: strategic gate — BLUE/RED required for any trade
    # Source: MEMS26_WOODIES_DECISION_TREE_V1.md §4 Stage A1
    # "IF cci_14 > 0 for 6+ consecutive bars → color = BLUE → LONG allowed"
    # "IF cci_14 < 0 for 6+ consecutive bars → color = RED → SHORT allowed"
    # "GREY/YELLOW → stand aside"
    trend_ok = trend_state in _TRADING_TREND_STATES

    for pid in WOODIES_PATTERN_IDS:
        engine_id = _SPEC_ID_TO_ENGINE.get(pid, pid.upper())
        components = []

        # Stage: data — cci_14_present
        # Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2 "state.cci_14 is not None"
        components.append(Component(
            stage="data",
            key="cci_14_present",
            spec="state.cci_14 is not None",
            present=cci_present,
            value=f"CCI14={cci_14:.2f}" if cci_14 is not None else "None",
        ))

        # Stage: data — tcci_present
        # Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2 "state.get('tcci_value')"
        components.append(Component(
            stage="data",
            key="tcci_present",
            spec="state.cci_6_tcci is not None",
            present=tcci_present,
            value=f"TCCI={tcci:.2f}" if tcci is not None else "None",
        ))

        # Stage: data — 5min bar recency
        components.append(Component(
            stage="data",
            key="5min_bar_recency",
            spec="max(ts) from v9_bars_5min_woodies within last 6 min",
            present=fresh,
            value=f"lag={round(lag_seconds, 0)}s" if lag_seconds is not None else "unknown",
        ))

        # Stage: stage_a1 — strategic gate
        # Source: MEMS26_WOODIES_DECISION_TREE_V1.md §4 A1_strategic_gate
        components.append(Component(
            stage="stage_a1",
            key="strategic_gate",
            spec="trend_state in {BLUE, RED} (color veto from A1)",
            present=trend_ok,
            value=f"trend_state={trend_state}",
        ))

        # Stage: detection — pattern_specific
        # Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2 "check pattern.id in state.active_patterns"
        pattern_detected = engine_id in active_engine_ids
        components.append(Component(
            stage="detection",
            key="pattern_specific",
            spec=f"pattern_id={pid} in state.active_patterns",
            present=pattern_detected,
            value=f"active={pattern_detected} · engine_id={engine_id}",
        ))

        # Stage: sizing — confidence_score
        # Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2 "pattern.confidence >= threshold"
        best_conf = None
        for ap in active_patterns_raw:
            if isinstance(ap, dict):
                apid = ap.get("pattern_id", "")
            else:
                apid = getattr(ap, "pattern_id", "")
            if str(apid).upper() == engine_id:
                if isinstance(ap, dict):
                    best_conf = ap.get("confidence")
                else:
                    best_conf = getattr(ap, "confidence", None)
                break

        conf_ok = best_conf is not None and float(best_conf) >= 0.5
        components.append(Component(
            stage="sizing",
            key="confidence_score",
            spec="pattern.confidence >= 0.5",
            present=conf_ok,
            value=f"conf={best_conf:.3f}" if best_conf is not None else "not active",
        ))

        # Stage: exit_rules — ready_to_route
        # Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2 "state.ready_to_route"
        route_present = ready_to_route and pattern_detected
        components.append(Component(
            stage="exit_rules",
            key="ready_to_route",
            spec="state.ready_to_route == True and pattern active",
            present=route_present,
            value="✅" if route_present else "not ready",
        ))

        # Determine status
        blockers = [f"{c.stage}.{c.key}" for c in components if not c.present]

        if not cci_present:
            status = "unknown"
            label = "❓ Unknown"
            reason = "CCI-14 not computed — insufficient bar history"
        elif not trend_ok:
            # MEMS26_WOODIES_DECISION_TREE_V1.md §4 A1: GREY/YELLOW = stand aside
            status = "blocked"
            label = "❌ Blocked"
            reason = (
                f"Stage A1 veto: trend_state={trend_state} "
                "(GREY/YELLOW/INDETERMINATE — Woodies WSI rule)"
            )
        elif pattern_detected and route_present:
            status = "fired"
            label = "✅ Fired"
            reason = (
                f"{pid} detected · ready_to_route=True · "
                f"conf={best_conf:.3f}" if best_conf is not None else f"{pid} ready"
            )
        elif pattern_detected:
            status = "armed"
            label = "🟡 Armed"
            reason = f"{pid} pattern detected · awaiting decision tree approval"
        elif fresh and trend_ok and cci_present:
            status = "armed"
            label = "🟡 Armed"
            reason = f"Data ready, trend {trend_state} · {pid} not yet detected"
        else:
            status = "blocked"
            label = "❌ Blocked"
            reason = f"Missing: {', '.join(blockers)}" if blockers else "Insufficient data"

        system.patterns.append(PatternStatus(
            id=pid,
            name=_PATTERN_NAMES.get(pid, pid),
            status=status,
            label=label,
            reason=reason,
            fired_today=pattern_detected and ready_to_route,
            last_fire_ts=None,  # Woodies fires are not persisted per-pattern by table
            components=components,
            blockers=blockers,
        ))

    return system
