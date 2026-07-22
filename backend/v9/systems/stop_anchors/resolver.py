"""Stop-anchor resolver — pure functions over bars + ladders + mode classifier.

Every function here is pure (no I/O, no state) and unit-tested. The per-pattern
WIRING (which bars/window to pass, reading trend_state) lives in the pattern
files; this module provides the primitives the spec is built from:

  - anchor price from a window of bars (cluster/excursion/swing extremes)
  - apply the 3-tick structural offset to a known structural price
  - T1 ladder (continuation + reversal ×mult, with absolute floor)
  - contract ladder by risk, and the min(ladder, auth, mode) combiner
  - tactical/strategic mode classifier (from trend_state + auth + value-area)

All spec numbers come from `config/stop_anchors.yaml` (passed in), never
hardcoded here — so calibration is a YAML edit, not a code change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

MES_TICK = 0.25


def _lows(bars: Sequence[Any]) -> List[float]:
    return [(b["l"] if isinstance(b, dict) else b.low) for b in bars]


def _highs(bars: Sequence[Any]) -> List[float]:
    return [(b["h"] if isinstance(b, dict) else b.high) for b in bars]


# ── Anchor price ─────────────────────────────────────────────────────

def window_extreme(bars: Sequence[Any], direction: str) -> float:
    """The structural extreme of a window of bars: lowest low for LONG (stop
    sits below), highest high for SHORT. Caller selects the window per the
    anchor `type`+`window` (cluster_low=last N, zl_excursion=the excursion bars,
    etc.). Raises on empty input — an empty window is a wiring bug, not a price."""
    if not bars:
        raise ValueError("window_extreme: empty bar window")
    return min(_lows(bars)) if direction == "LONG" else max(_highs(bars))


def apply_offset(anchor_price: float, direction: str, offset_ticks: int,
                 tick_size: float = MES_TICK) -> float:
    """Push the anchor `offset_ticks` BEYOND the structural extreme (the −3T /
    +3T buffer so a retest of the level doesn't tag the stop). LONG stop is
    below the low; SHORT stop is above the high."""
    off = offset_ticks * tick_size
    return round((anchor_price - off) if direction == "LONG" else (anchor_price + off), 2)


def resolve_anchor_from_window(bars: Sequence[Any], direction: str,
                               offset_ticks: int, tick_size: float = MES_TICK) -> float:
    """Convenience: window extreme + structural offset, in one call."""
    return apply_offset(window_extreme(bars, direction), direction, offset_ticks, tick_size)


# ── Structure-end T1 + structure-extreme stop (Michael rulings 2026-07-21/22) ──
#
# Ruling C (Michael 2026-07-21 ~18:15): "T1 צריך להיות בסוף מבנה-הכניסה; לבטל
# את האופן שבו הוא מחושב היום."  T1 = the PROFIT-side extreme of the SAME
# structural window that anchors the stop — R:R becomes real structure geometry.
#
# Ruling D (Michael 2026-07-21 22:22): stop behind the STRUCTURE extreme, not a
# single bar (supersedes breakout_bar/window:1 anchors — evidence: 1.75-3.5pt
# stops vs a 7554.25 structure edge).

def structure_end_t1(bars: Sequence[Any], direction: str) -> float:
    """The END of the entry structure in the PROFIT direction: highest high of
    the window for LONG, lowest low for SHORT (mirror of window_extreme, which
    returns the RISK-side extreme). Raises on empty input (wiring bug)."""
    if not bars:
        raise ValueError("structure_end_t1: empty bar window")
    return max(_highs(bars)) if direction == "LONG" else min(_lows(bars))


def t1_structure_valid(entry_price: float, t1: float, direction: str,
                       min_ticks: int = 2, tick_size: float = MES_TICK) -> bool:
    """Is the structure-end T1 tradeable? It must sit at least `min_ticks`
    BEYOND entry on the profit side; otherwise the structure is exhausted
    (price already AT the structure end) → honest reject, no invented target."""
    dist = (t1 - entry_price) if direction == "LONG" else (entry_price - t1)
    return dist >= min_ticks * tick_size


def widen_stop_to_structure(current_stop: float, structure_stop: float,
                            direction: str) -> float:
    """Ruling D: the stop must sit BEHIND the structure extreme. Returns the
    FARTHER-from-entry of the two (widen-only — never tightens an already
    structure-wide stop). LONG: lower wins; SHORT: higher wins."""
    if direction == "LONG":
        return min(current_stop, structure_stop)
    return max(current_stop, structure_stop)


# ── Risk + ladders ───────────────────────────────────────────────────

def risk_points(entry_price: float, stop_price: float) -> float:
    return round(abs(entry_price - stop_price), 4)


def _ladder_pick(ladder: List[dict], risk_pts: float, key: str) -> Any:
    """First ladder row whose `max_risk_points` >= risk wins (ascending)."""
    for row in sorted(ladder, key=lambda r: r["max_risk_points"]):
        if risk_pts <= row["max_risk_points"]:
            return row[key]
    return ladder[-1][key]  # beyond the top band → last row


def contracts_from_risk(risk_pts: float, contract_ladder: List[dict]) -> int:
    """Risk → contracts (≤15→3, 15-25→2, >25→1 per the locked ladder)."""
    return int(_ladder_pick(contract_ladder, risk_pts, "contracts"))


def final_contracts(risk_pts: float, contract_ladder: List[dict],
                    auth_contracts: int, mode_cap: int) -> int:
    """The locked rule: min(risk-ladder, auth/Table-B, mode cap). The most
    conservative of the three always wins — no dimension can be overridden."""
    return max(0, min(contracts_from_risk(risk_pts, contract_ladder),
                      int(auth_contracts), int(mode_cap)))


def t1_price(entry_price: float, stop_price: float, direction: str, *,
             t1_ladder_cont: List[dict], reversal: bool, reversal_mult: float,
             t1_floor_points: float, ladder_shift: int = 0) -> float:
    """T1 price from the risk-keyed R-ladder. reversal=True applies ×mult.
    `t1_floor_points` enforces the absolute 3-pt minimum (commission floor).
    `ladder_shift=-1` moves one band more conservative (HFE, the weak pattern)."""
    risk = risk_points(entry_price, stop_price)
    rows = sorted(t1_ladder_cont, key=lambda r: r["max_risk_points"])
    # locate band index, then shift
    idx = next((i for i, r in enumerate(rows) if risk <= r["max_risk_points"]), len(rows) - 1)
    idx = max(0, min(len(rows) - 1, idx + ladder_shift))
    t1_r = rows[idx]["t1_r"]
    if reversal:
        t1_r *= reversal_mult
    dist = max(t1_r * risk, float(t1_floor_points))   # absolute floor (6א)
    return round((entry_price + dist) if direction == "LONG" else (entry_price - dist), 2)


# ── Tactical / Strategic classifier ──────────────────────────────────

@dataclass(frozen=True)
class ModeResult:
    mode: str       # "strategic" | "tactical"
    cap: int        # contracts cap for that mode
    reason: str


def classify_mode(*, day_has_direction: bool, trade_with_trend: Optional[bool],
                  value_area_full_traverse: Optional[bool],
                  strategic_cap: int, tactical_cap: int) -> ModeResult:
    """Locked classification (no new numbers — derived from trend_state + auth):
      Trend days: with-trend = strategic, against = tactical.
      Value days: full VAH↔VAL traverse = strategic, POC→edge = tactical.
    Inputs come from existing sources (trend_state, auth verdict, S5 VA levels).
    """
    if day_has_direction:
        strat = bool(trade_with_trend)
        reason = "trend_day:with-trend" if strat else "trend_day:counter-trend"
    else:
        strat = bool(value_area_full_traverse)
        reason = "value_day:VAH<->VAL" if strat else "value_day:POC->edge"
    return ModeResult(mode=("strategic" if strat else "tactical"),
                      cap=(strategic_cap if strat else tactical_cap),
                      reason=reason)
