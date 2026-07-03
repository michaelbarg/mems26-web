"""Item-22 — TARGET_ZONES_V1: level-confluence target zones beyond T1.

Michael (2026-07-02): "המערכת תזהה אזורים לקביעת מימושים חוץ מה-T1" — recurring
complaint that C2/C3 land on a single arbitrary level (crude R-multiple) and the
runner exits too early or misses a real shelf. This clusters the day's + prior
day's structural levels (IB high/low, POC, VAH/VAL, prior-day H/L/POC/VA, session
extremes, swing highs/lows) into CONFLUENCE ZONES, then picks the target zones
beyond T1 in the trade direction. Target price = the NEAR edge of the zone (price
reaches it first), so the fill is realistic, and a zone's strength = how many
levels stacked there.

Pure + fail-safe. Layers on the structural-targets resolver (does not replace
T1). Flag: TARGET_ZONES_V1 (default OFF). Wiring at the gateway structural-targets
block; this module is the level-math.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

TICK = 0.25


@dataclass
class Zone:
    low: float
    high: float
    center: float
    strength: int                       # how many levels clustered here
    members: List[str] = field(default_factory=list)

    def near_edge(self, direction: str) -> float:
        """The edge price reaches first from entry, in the trade direction."""
        return self.low if direction.upper() == "LONG" else self.high


def cluster_levels(levels: List[Tuple[float, str]], tol_pts: float) -> List[Zone]:
    """Greedy 1-D clustering of (price, label) levels within tol_pts.

    Two levels join the same zone if the next price is within tol_pts of the
    current cluster's running max. Returns zones sorted ascending by center.
    """
    clean = sorted((float(p), str(lbl)) for p, lbl in levels
                   if p is not None and p > 0)
    if not clean:
        return []
    zones: List[Zone] = []
    cur = [clean[0]]
    for price, lbl in clean[1:]:
        if price - cur[-1][0] <= tol_pts:
            cur.append((price, lbl))
        else:
            zones.append(_finish(cur))
            cur = [(price, lbl)]
    zones.append(_finish(cur))
    return zones


def _finish(members: List[Tuple[float, str]]) -> Zone:
    prices = [p for p, _ in members]
    lo, hi = min(prices), max(prices)
    return Zone(low=round(lo, 2), high=round(hi, 2),
                center=round(sum(prices) / len(prices), 2),
                strength=len(members), members=[l for _, l in members])


def select_target_zones(
    *,
    direction: str,
    entry_price: float,
    t1_price: float,
    zones: List[Zone],
    min_strength: int = 1,
) -> dict:
    """Pick C2/C3 zones beyond T1 in the profit direction.

    LONG: zones whose near edge is above T1, nearest first.
    SHORT: zones whose near edge is below T1, nearest first.
    Returns {"c2": price|None, "c3": price|None, "c2_zone": Zone|None, ...}.
    Target price = near edge (grid-snapped). Fail-safe: no zones → all None.
    """
    d = direction.upper()
    out = {"c2": None, "c3": None, "c2_zone": None, "c3_zone": None}
    usable = [z for z in zones if z.strength >= min_strength]
    if d == "LONG":
        beyond = [z for z in usable if z.near_edge("LONG") > t1_price]
        beyond.sort(key=lambda z: z.near_edge("LONG"))       # nearest above first
    else:
        beyond = [z for z in usable if z.near_edge("SHORT") < t1_price]
        beyond.sort(key=lambda z: z.near_edge("SHORT"), reverse=True)  # nearest below first
    picks = beyond[:2]
    keys = ["c2", "c3"]
    for k, z in zip(keys, picks):
        px = round(round(z.near_edge(d) / TICK) * TICK, 2)
        out[k] = px
        out[k + "_zone"] = z
    return out


def zone_tol_pts(atr_5m: Optional[float]) -> float:
    """Confluence tolerance: default 0.5×ATR (a 'shelf' band), floor 1.5pt.
    Tunable via TARGET_ZONE_TOL_PTS (absolute points, overrides ATR)."""
    override = os.getenv("TARGET_ZONE_TOL_PTS")
    if override:
        try:
            return max(0.25, float(override))
        except (TypeError, ValueError):
            pass
    if atr_5m and atr_5m > 0:
        return max(0.5 * atr_5m, 1.5)
    return 1.5
