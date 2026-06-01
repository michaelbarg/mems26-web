"""Footprint (S3) inspector — per-detector block reason for Build Status.

Shows why each of the 4 S3 detectors (absorption, stacked_imbalance,
sweep_return, exhaustion) is or isn't producing a signal.
"""

import logging
from .types import PatternStatus, Component, SystemStatus, DataFreshness
from .row_helpers import freshness_now

logger = logging.getLogger(__name__)

_DETECTOR_NAMES = {
    "absorption": "Absorption",
    "stacked_imbalance": "Stacked Imbalance",
    "sweep_return": "Sweep Return",
    "exhaustion": "Exhaustion",
}


def inspect(footprint_system=None) -> SystemStatus:
    """Build S3 Footprint system status with per-detector block reasons."""
    system = SystemStatus(
        id="footprint",
        name="S3 · Footprint Patterns",
    )

    if footprint_system is None:
        system.running = False
        system.hydrated = False
        system.patterns.append(PatternStatus(
            id="footprint_all",
            name="Footprint System",
            status="unknown",
            label="❓ Unknown",
            reason="FootprintSystem not initialized",
        ))
        return system

    try:
        state = footprint_system.get_state() if hasattr(footprint_system, 'get_state') else {}
    except Exception:
        state = {}

    system.running = state.get("running", True)
    system.hydrated = state.get("hydrated", True)

    buf_size = state.get("buffer_size", 0)
    last_class = state.get("last_classification", "NO_SETUP")
    last_pattern = state.get("last_pattern")
    bars_today = state.get("bars_processed_today", 0)
    dominance = state.get("dominance", "UNKNOWN")
    last_fire = state.get("last_fire")

    _f = freshness_now("in_memory")

    for det_id, det_name in _DETECTOR_NAMES.items():
        components = [
            Component(
                stage="data", key="buffer_size",
                spec="Buffer ≥ 5 bars for detection",
                present=buf_size >= 5,
                value=f"{buf_size} bars",
                live=str(buf_size), required=">= 5",
                freshness=_f,
            ),
            Component(
                stage="data", key="bars_today",
                spec="Bars processed today > 0",
                present=bars_today > 0,
                value=f"{bars_today} bars today",
                live=str(bars_today), required="> 0",
                freshness=_f,
            ),
        ]

        if last_pattern and last_pattern == det_id:
            status = "fired"
            label = "✅ Fired"
            reason = f"{det_name} detected · {last_class}"
        elif buf_size < 5:
            status = "blocked"
            label = "❌ Blocked"
            reason = f"Insufficient buffer ({buf_size} bars, need ≥ 5)"
        elif last_class == "NO_SETUP":
            status = "armed"
            label = "🟡 Armed"
            reason = f"Data ready (dominance={dominance}) · {det_name} not detected"
        else:
            status = "armed"
            label = "🟡 Armed"
            reason = f"Active: {last_class} · {det_name} awaiting trigger"

        blockers = [f"{c.stage}.{c.key}" for c in components if not c.present]

        system.patterns.append(PatternStatus(
            id=f"footprint_{det_id}",
            name=det_name,
            status=status,
            label=label,
            reason=reason,
            fired_today=last_fire is not None,
            components=components,
            blockers=blockers,
        ))

    return system
