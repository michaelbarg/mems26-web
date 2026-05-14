"""TPO Level calculations — POC, Value Area (VAH/VAL), HVN, LVN.

POC = price level with highest TPO count.
Value Area = 70% of total TPO volume, expanding outward from POC.
HVN = High Volume Nodes (top 20% by count).
LVN = Low Volume Nodes (bottom 10% by count).

ACSIL note: TPO Value Area subgraphs are 1-indexed:
  SG1 = POC, SG2 = VAH, SG3 = VAL
"""

from typing import Dict, List, Tuple, Optional
from .schemas import TPOLevel, TPOConfig


def compute_poc(levels: Dict[str, TPOLevel]) -> Tuple[Optional[float], int]:
    """Find POC — price with most TPO letters.

    Returns (poc_price, poc_count). On tie, pick higher price (buyers).
    """
    if not levels:
        return None, 0

    best_price: Optional[float] = None
    best_count = 0

    for lvl in levels.values():
        c = lvl.count
        if c > best_count or (c == best_count and best_price is not None
                              and lvl.price > best_price):
            best_count = c
            best_price = lvl.price

    return best_price, best_count


def compute_value_area(
    levels: Dict[str, TPOLevel],
    poc_price: Optional[float],
    config: TPOConfig,
) -> Tuple[Optional[float], Optional[float]]:
    """Compute Value Area High/Low — 70% of TPO volume around POC.

    Algorithm (Dalton):
    1. Start at POC
    2. Total = sum of all TPO counts
    3. Target = total * value_area_pct
    4. Alternately add the row above and below with more TPOs
    5. Stop when accumulated >= target

    Returns (vah, val).
    """
    if not levels or poc_price is None:
        return None, None

    # Sort prices ascending
    sorted_prices = sorted(lvl.price for lvl in levels.values())
    if not sorted_prices:
        return None, None

    price_to_count = {lvl.price: lvl.count for lvl in levels.values()}
    total_tpo = sum(price_to_count.values())
    target = total_tpo * config.value_area_pct

    # Find POC index
    try:
        poc_idx = sorted_prices.index(poc_price)
    except ValueError:
        return None, None

    accumulated = price_to_count.get(poc_price, 0)
    upper_idx = poc_idx + 1
    lower_idx = poc_idx - 1
    vah = poc_price
    val = poc_price

    while accumulated < target:
        upper_count = (price_to_count[sorted_prices[upper_idx]]
                       if upper_idx < len(sorted_prices) else 0)
        lower_count = (price_to_count[sorted_prices[lower_idx]]
                       if lower_idx >= 0 else 0)

        if upper_count == 0 and lower_count == 0:
            break

        if upper_count >= lower_count:
            if upper_idx < len(sorted_prices):
                accumulated += upper_count
                vah = sorted_prices[upper_idx]
                upper_idx += 1
        else:
            if lower_idx >= 0:
                accumulated += lower_count
                val = sorted_prices[lower_idx]
                lower_idx -= 1

        # Safety: if both exhausted
        if upper_idx >= len(sorted_prices) and lower_idx < 0:
            break

    return vah, val


def compute_hvn_lvn(
    levels: Dict[str, TPOLevel],
    config: TPOConfig,
) -> Tuple[List[float], List[float]]:
    """Identify High Volume Nodes and Low Volume Nodes.

    HVN = top hvn_top_pct (20%) by TPO count.
    LVN = bottom lvn_bottom_pct (10%) by TPO count.
    """
    if not levels:
        return [], []

    counts = sorted(
        [(lvl.price, lvl.count) for lvl in levels.values()],
        key=lambda x: x[1],
        reverse=True,
    )
    n = len(counts)
    if n == 0:
        return [], []

    hvn_cutoff = max(1, int(n * config.hvn_top_pct))
    lvn_cutoff = max(1, int(n * config.lvn_bottom_pct))

    hvn = sorted([c[0] for c in counts[:hvn_cutoff]])
    lvn = sorted([c[0] for c in counts[-lvn_cutoff:]])

    return hvn, lvn


def compute_single_prints(
    levels: Dict[str, TPOLevel],
    config: TPOConfig,
) -> List[float]:
    """Find single-print prices — levels with <= single_print_min_letters."""
    return sorted([
        lvl.price for lvl in levels.values()
        if lvl.count <= config.single_print_min_letters
    ])


def compute_tails(
    levels: Dict[str, TPOLevel],
    session_low: Optional[float],
    session_high: Optional[float],
    config: TPOConfig,
) -> Tuple[int, int]:
    """Detect buying and selling tails.

    Buying tail: consecutive single-print levels at session LOW
      (buyers rejected lower prices).
    Selling tail: consecutive single-print levels at session HIGH
      (sellers rejected higher prices).

    Returns (buying_tail_count, selling_tail_count).
    """
    if not levels or session_low is None or session_high is None:
        return 0, 0

    sorted_prices = sorted(lvl.price for lvl in levels.values())
    price_to_count = {lvl.price: lvl.count for lvl in levels.values()}

    # Buying tail: from bottom up, count consecutive single-prints
    buying_tail = 0
    for p in sorted_prices:
        if price_to_count.get(p, 0) <= 1:
            buying_tail += 1
        else:
            break

    # Selling tail: from top down, count consecutive single-prints
    selling_tail = 0
    for p in reversed(sorted_prices):
        if price_to_count.get(p, 0) <= 1:
            selling_tail += 1
        else:
            break

    # Must meet minimum letter threshold
    if buying_tail < config.tail_min_letters:
        buying_tail = 0
    if selling_tail < config.tail_min_letters:
        selling_tail = 0

    return buying_tail, selling_tail


def detect_ufl_ufh(
    levels: Dict[str, TPOLevel],
    session_low: Optional[float],
    session_high: Optional[float],
) -> Dict[str, Optional[float]]:
    """Detect Unfair Low (UFL) and Unfair High (UFH).

    Per V3 Layer 2: UFL/UFH = single-letter close at session extreme.
    A single TPO letter at the extreme price means the market moved
    there and left immediately — "unfair" price, likely to be revisited.

    Per AP-SY02: includes reasoning_notes.

    Returns: {"ufl": price|None, "ufh": price|None, "reasoning_notes": str}
    """
    if not levels or session_low is None or session_high is None:
        return {"ufl": None, "ufh": None, "reasoning_notes": "No data for UFL/UFH"}

    price_to_count = {lvl.price: lvl.count for lvl in levels.values()}
    notes_parts = []

    # UFH: single letter at session high
    high_count = price_to_count.get(session_high, 0)
    ufh = session_high if high_count == 1 else None
    if ufh:
        notes_parts.append(f"UFH at {ufh:.2f} (1 letter at session high)")

    # UFL: single letter at session low
    low_count = price_to_count.get(session_low, 0)
    ufl = session_low if low_count == 1 else None
    if ufl:
        notes_parts.append(f"UFL at {ufl:.2f} (1 letter at session low)")

    if not notes_parts:
        notes_parts.append("No UFL/UFH (extremes have multiple letters)")

    return {
        "ufl": ufl,
        "ufh": ufh,
        "reasoning_notes": "; ".join(notes_parts),
    }
