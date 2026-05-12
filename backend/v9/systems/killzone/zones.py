"""11 Killzone definitions per MEMS26_KILLZONE_SPEC_V1.

All times are Eastern Time (America/New_York) — DST-aware.
"""

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class Zone:
    name: str
    start: time          # ET, inclusive
    end: time            # ET, exclusive (except AFTER_HOURS wraps midnight)
    quality: str         # HIGH, MEDIUM, LOW, OFF
    volatility: str      # HIGH, VERY_HIGH, MEDIUM, LOW
    sizing_modifier: float  # 1.0 / 0.5 / 0.25 / 0.0
    is_blocked_default: bool
    session_phase: str
    notes: str


# ── 11 Zones (ordered by start time within trading day) ──

ZONES: list[Zone] = [
    Zone(
        name="PRE_MARKET",
        start=time(5, 0), end=time(9, 30),
        quality="LOW", volatility="LOW",
        sizing_modifier=0.25, is_blocked_default=False,
        session_phase="PRE",
        notes="Watch only (no live trading)",
    ),
    Zone(
        name="NY_OPEN_VOLATILITY",
        start=time(9, 30), end=time(9, 45),
        quality="MEDIUM", volatility="VERY_HIGH",
        sizing_modifier=0.5, is_blocked_default=False,
        session_phase="OPEN",
        notes="Wild moves / sweep alerts / initial direction",
    ),
    Zone(
        name="NY_OPEN_IB",
        start=time(9, 45), end=time(10, 30),
        quality="HIGH", volatility="HIGH",
        sizing_modifier=1.0, is_blocked_default=False,
        session_phase="OPEN",
        notes="IB completing / best risk-reward",
    ),
    Zone(
        name="NY_PRIME",
        start=time(10, 30), end=time(11, 30),
        quality="HIGH", volatility="HIGH",
        sizing_modifier=1.0, is_blocked_default=False,
        session_phase="PRIME",
        notes="Prime session / post-IB initiatives / best entries",
    ),
    Zone(
        name="PRE_LUNCH",
        start=time(11, 30), end=time(12, 0),
        quality="MEDIUM", volatility="MEDIUM",
        sizing_modifier=0.5, is_blocked_default=False,
        session_phase="MID",
        notes="Transition / volume drops / fade signals",
    ),
    Zone(
        name="LUNCH",
        start=time(12, 0), end=time(13, 0),
        quality="LOW", volatility="LOW",
        sizing_modifier=0.0, is_blocked_default=True,
        session_phase="MID",
        notes="Choppy / whipsaw / low liquidity",
    ),
    Zone(
        name="PM_RECOVERY",
        start=time(13, 0), end=time(14, 0),
        quality="MEDIUM", volatility="MEDIUM",
        sizing_modifier=0.5, is_blocked_default=False,
        session_phase="PM",
        notes="Second wind possible / re-evaluate Day Type",
    ),
    Zone(
        name="PM_PRIME",
        start=time(14, 0), end=time(15, 0),
        quality="HIGH", volatility="HIGH",
        sizing_modifier=1.0, is_blocked_default=False,
        session_phase="PM",
        notes="Strong directional moves / positioning",
    ),
    Zone(
        name="CLOSE_APPROACH",
        start=time(15, 0), end=time(15, 45),
        quality="MEDIUM", volatility="HIGH",
        sizing_modifier=0.5, is_blocked_default=False,
        session_phase="CLOSE",
        notes="Position squaring / funds rebalancing",
    ),
    Zone(
        name="CLOSE_FINAL",
        start=time(15, 45), end=time(16, 0),
        quality="LOW", volatility="VERY_HIGH",
        sizing_modifier=0.0, is_blocked_default=True,
        session_phase="CLOSE",
        notes="MOC orders / whipsaw / no new entries",
    ),
    Zone(
        name="AFTER_HOURS",
        start=time(16, 0), end=time(5, 0),  # wraps midnight
        quality="OFF", volatility="LOW",
        sizing_modifier=0.0, is_blocked_default=True,
        session_phase="CLOSED",
        notes="Out of session / no trading",
    ),
]

ZONE_BY_NAME: dict[str, Zone] = {z.name: z for z in ZONES}
