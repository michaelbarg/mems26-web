"""SCALE_IN_V1 (Michael ruling 2026-08-13: "אם הכיוון ממשיך אפשר לחזק בעוד חוזים").

Reinforce a WINNING trade with extra contracts — a pure position-management add-on.
It NEVER touches the entry path (no gate, no filter): it only fires on an already-open
trade that has proven itself (T1 banked) and whose direction keeps going. The add-on
gets its own protective stop at the parent's entry (breakeven), so a scale-in can never
turn the winning parent into a loss beyond the entry level. Once per parent, capped size,
with-trend only, flag-gated OFF.

Pure function — no I/O, no env reads here (caller passes cfg + live dir_bias). Fully
testable; the caller (bar_level_detector.on_bar) does the flag check + child-trade PLACE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScaleInCfg:
    min_profit_pts: float = 6.0      # price must have run this far past entry (proof it works)
    add_contracts: int = 2           # how many to add
    max_total_contracts: int = 8     # never let parent+add exceed this
    require_with_trend: bool = True  # only reinforce WITH the day trend
    add_stop_at_entry: bool = True   # add-on stop = parent entry (BE) — bounded downside


@dataclass
class ScaleInDecision:
    add_contracts: int
    direction: str
    entry: float          # approx current favorable price (add-on entry)
    stop: float           # protective stop for the add-on (parent BE by default)
    reason: str


def should_scale_in(
    *,
    direction: str,
    entry_price: Optional[float],
    t1_hit: bool,
    already_scaled: bool,
    n_contracts_open: int,
    bar_high: float,
    bar_low: float,
    dir_bias: Optional[str],
    cfg: Optional[ScaleInCfg] = None,
) -> Optional[ScaleInDecision]:
    """Return a ScaleInDecision to reinforce the trade, or None to do nothing.

    Fires only when ALL hold:
      • t1_hit — the entry proved itself (banked T1); we never add before proof.
      • not already_scaled — once per parent.
      • n_contracts_open > 0 — there is a live position to reinforce.
      • with-trend — dir_bias agrees with the trade direction (when known + required).
      • price continued ≥ min_profit_pts past entry (the move has legs).
      • parent + add-on ≤ max_total_contracts.
    The add-on stop sits at the parent entry (breakeven) → its worst case is giving back
    only its own paper gain; the parent's banked T1 already cushions the trade.
    """
    cfg = cfg or ScaleInCfg()
    d = (direction or "").upper()
    if d not in ("LONG", "SHORT"):
        return None
    if not t1_hit or already_scaled:
        return None
    if entry_price is None or n_contracts_open <= 0:
        return None
    if n_contracts_open + cfg.add_contracts > cfg.max_total_contracts:
        return None
    if cfg.require_with_trend and dir_bias in ("UP", "DOWN"):
        counter = (d == "LONG" and dir_bias != "UP") or (d == "SHORT" and dir_bias != "DOWN")
        if counter:
            return None
    e = float(entry_price)
    # favorable excursion of THIS bar past entry
    fav = (float(bar_high) - e) if d == "LONG" else (e - float(bar_low))
    if fav < cfg.min_profit_pts:
        return None
    add_entry = float(bar_high) if d == "LONG" else float(bar_low)
    add_stop = e if cfg.add_stop_at_entry else (
        add_entry - cfg.min_profit_pts if d == "LONG" else add_entry + cfg.min_profit_pts)
    return ScaleInDecision(
        add_contracts=cfg.add_contracts,
        direction=d,
        entry=round(add_entry, 2),
        stop=round(add_stop, 2),
        reason=(f"reinforce {d}: T1 banked + {fav:.1f}pt past entry + with-trend "
                f"({dir_bias}) → +{cfg.add_contracts}c, stop@parent-entry {e:.2f}"),
    )
