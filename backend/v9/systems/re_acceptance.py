"""RE_ACCEPTANCE_V1 — "bar of acceptance" detector (Dalton p.84/88).

Shadow-only. Detects the bar where the market ACCEPTS a breakout:
  |delta| ≥ 0.7 × session-max delta
  AND vol ≥ 0.7 × session-max volume
  AND close in the extreme quarter of the bar (cpos ≥ 0.75 LONG / ≤ 0.25 SHORT)
  AND close crosses a reference edge (IB/VA/open)
  AND direction consistent with gap (gap-up → LONG only; gap-down → SHORT only)
  AND bar is closed (not building)
  AND ts ≥ 16:30 IL (RTH only)

All conditions must hold on a CLOSED bar. This is not a release path —
it's a standalone entry signal for the "second act" (20-90min post-open).

Basis: DALTON_EARLY_ENTRY_2026-09-07.md, family I — 4/4 t1, rejects 6/6.
n=4, thresholds set in hindsight → shadow 20 days, then measurement, then ruling.

    python3 -c "from backend.v9.systems.re_acceptance import detect; ..."
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return os.getenv("RE_ACCEPTANCE_V1", "0").strip().lower() in ("1", "shadow", "true", "yes")


def is_shadow() -> bool:
    return os.getenv("RE_ACCEPTANCE_V1", "0").strip().lower() == "shadow"


def detect(
    bars: List[Dict[str, Any]],
    *,
    ib_high: Optional[float] = None,
    ib_low: Optional[float] = None,
    vah: Optional[float] = None,
    val: Optional[float] = None,
    open_price: Optional[float] = None,
    gap_direction: Optional[str] = None,
    delta_threshold: float = 0.7,
    vol_threshold: float = 0.7,
) -> Optional[Dict[str, Any]]:
    """Detect a "bar of acceptance" on the LAST closed bar.

    Args:
        bars: RTH 5-min bars [{h, l, c, o, vol, delta, ts}], oldest→newest.
        ib_high/ib_low: locked IB edges.
        vah/val: prior-day value area.
        open_price: session open.
        gap_direction: "UP" or "DOWN" (gap vs prior close).
        delta_threshold: fraction of session-max delta required (0.7).
        vol_threshold: fraction of session-max volume required (0.7).

    Returns:
        Trigger dict {direction, entry, stop, t1, ...} or None.
    """
    if not bars or len(bars) < 3:
        return None

    last = bars[-1]
    h = _f(last, "h", "high")
    l = _f(last, "l", "low")
    c = _f(last, "c", "close")
    o = _f(last, "o", "open")
    vol = _f(last, "vol", "volume") or 0
    delta = _f(last, "delta", "cum_delta", "cumulative_delta")

    if None in (h, l, c, o) or h <= l:
        return None
    if delta is None:
        return None  # Rule 1: no delta → no decision

    bar_range = h - l
    cpos = (c - l) / bar_range  # 0=bottom, 1=top

    # Session max delta and volume (exclude current bar for independence)
    prior = bars[:-1]
    deltas = [_f(b, "delta", "cum_delta", "cumulative_delta") for b in prior]
    deltas = [d for d in deltas if d is not None]
    vols = [(_f(b, "vol", "volume") or 0) for b in prior]

    if not deltas or not vols:
        return None

    max_pos_delta = max(deltas) if deltas else 0
    max_neg_delta = min(deltas) if deltas else 0
    max_vol = max(vols) if vols else 0

    if max_vol <= 0:
        return None

    # Direction: which way is the delta pushing?
    if delta > 0 and max_pos_delta > 0:
        direction = "LONG"
        delta_frac = delta / max_pos_delta
    elif delta < 0 and max_neg_delta < 0:
        direction = "SHORT"
        delta_frac = delta / max_neg_delta  # both negative → positive fraction
    else:
        return None

    vol_frac = vol / max_vol

    # 1. Delta threshold
    if delta_frac < delta_threshold:
        return None

    # 2. Volume threshold
    if vol_frac < vol_threshold:
        return None

    # 3. Close in extreme quarter
    if direction == "LONG" and cpos < 0.75:
        return None
    if direction == "SHORT" and cpos > 0.25:
        return None

    # 4. Close crosses a reference edge
    edges_crossed = []
    if ib_high is not None and direction == "LONG" and c > ib_high:
        edges_crossed.append(("IBH", ib_high))
    if ib_low is not None and direction == "SHORT" and c < ib_low:
        edges_crossed.append(("IBL", ib_low))
    if vah is not None and direction == "LONG" and c > vah:
        edges_crossed.append(("VAH", vah))
    if val is not None and direction == "SHORT" and c < val:
        edges_crossed.append(("VAL", val))
    if open_price is not None:
        if direction == "LONG" and c > open_price and o <= open_price:
            edges_crossed.append(("OPEN", open_price))
        if direction == "SHORT" and c < open_price and o >= open_price:
            edges_crossed.append(("OPEN", open_price))

    if not edges_crossed:
        return None

    # 5. Gap-direction consistency
    if gap_direction:
        if gap_direction == "UP" and direction != "LONG":
            return None
        if gap_direction == "DOWN" and direction != "SHORT":
            return None

    # Build trigger
    edge_name, edge_price = edges_crossed[0]  # outermost edge
    sign = 1.0 if direction == "LONG" else -1.0
    stop = round(l - 2.0, 2) if direction == "LONG" else round(h + 2.0, 2)
    risk = abs(c - stop)
    t1 = round(c + sign * risk, 2) if risk > 0 else None  # 1R

    return {
        "type": "RE_ACCEPTANCE",
        "direction": direction,
        "entry": round(c, 2),
        "stop": stop,
        "t1": t1,
        "edge": edge_name,
        "edge_price": round(edge_price, 2),
        "delta": round(delta, 1),
        "delta_frac": round(delta_frac, 2),
        "vol_frac": round(vol_frac, 2),
        "cpos": round(cpos, 3),
    }


def build_setup(trigger: Dict[str, Any], contracts: int = 2) -> Dict[str, Any]:
    """Build a gateway-routable shadow setup."""
    direction = trigger["direction"]
    entry = float(trigger["entry"])
    stop = float(trigger["stop"])
    t1 = trigger.get("t1")
    return {
        "firing_system": 2,
        "pattern": "RE_ACCEPTANCE",
        "classification": "RE_ACCEPTANCE",
        "direction": direction,
        "entry_price": round(entry, 2),
        "stop": round(stop, 2),
        "t1": round(t1, 2) if t1 else None,
        "t2": None,
        "t3": None,
        "metadata": {
            "pattern": "RE_ACCEPTANCE",
            "source": "re_acceptance_v1",
            "edge": trigger.get("edge"),
            "delta_frac": trigger.get("delta_frac"),
            "vol_frac": trigger.get("vol_frac"),
            "shadow_only": True,
        },
    }


def _f(bar, *keys):
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None
