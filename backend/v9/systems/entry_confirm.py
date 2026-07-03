"""Item-6 — S4_ENTRY_CONFIRM_V1: require confirmation before entry.

Two composable, pure pieces:

  entry_confirmed()   — momentum/CVD confirmation. Michael (item-16, volatile
                        days): "עוד ודאות/ריטסט בכניסה". The signal bar must
                        close in the trade direction; optionally CVD-aligned.

  at_fresh_extreme()  — the item-10 counter-fixture guard. On 2026-07-02 the
                        08:45 with-drive entry sat at the very top of the drive
                        (7585, high 7594) and would have stopped -1R. This flags
                        an entry that is at a brand-new N-bar extreme, so item-10
                        can require "not at a fresh extreme" before firing.

Flag: S4_ENTRY_CONFIRM_V1 (default OFF). Fail-safe: missing data → not confirmed
(entry_confirmed) / not-at-extreme=False (never blocks on missing data).
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple


def _oc(bar: Dict) -> Tuple[Optional[float], Optional[float]]:
    o = bar.get("o", bar.get("open"))
    c = bar.get("c", bar.get("close"))
    return o, c


def entry_confirmed(
    *,
    direction: str,
    bars: List[Dict],
    cvd_pos: Optional[float] = None,
    require_cvd: bool = False,
) -> Tuple[bool, str]:
    """True if the most recent (signal) bar confirms the trade direction.

    Confirm bar: LONG → close > open; SHORT → close < open.
    If require_cvd and cvd_pos is provided: also require CVD alignment
    (LONG → cvd_pos >= 0.5, SHORT → cvd_pos <= 0.5).
    Fail-safe: no bars / missing o,c → (False, reason).
    """
    if not bars:
        return (False, "no bars")
    o, c = _oc(bars[-1])
    if o is None or c is None:
        return (False, "signal bar missing o/c")
    d = direction.upper()
    if d == "LONG" and not (c > o):
        return (False, f"no bullish confirm bar (c={c} <= o={o})")
    if d == "SHORT" and not (c < o):
        return (False, f"no bearish confirm bar (c={c} >= o={o})")
    if require_cvd and cvd_pos is not None:
        if d == "LONG" and cvd_pos < 0.5:
            return (False, f"CVD not buy-aligned ({cvd_pos:.2f})")
        if d == "SHORT" and cvd_pos > 0.5:
            return (False, f"CVD not sell-aligned ({cvd_pos:.2f})")
    return (True, "confirm bar" + (" + CVD" if (require_cvd and cvd_pos is not None) else ""))


def at_fresh_extreme(
    *,
    direction: str,
    entry_price: float,
    bars: List[Dict],
    lookback: int = 6,
    tol_pts: float = 0.5,
) -> bool:
    """True if entry sits at a brand-new N-bar extreme in the trade direction.

    LONG at a fresh HIGH (entry >= max high of the last `lookback` bars − tol)
    or SHORT at a fresh LOW → chasing the extreme (the 08:45 fixture).
    Fail-safe: too few bars → False (do not block on missing data).
    """
    highs = [b.get("h", b.get("high")) for b in bars[-lookback:]]
    lows = [b.get("l", b.get("low")) for b in bars[-lookback:]]
    highs = [h for h in highs if h is not None]
    lows = [l for l in lows if l is not None]
    if len(highs) < 2 or len(lows) < 2:
        return False
    d = direction.upper()
    if d == "LONG":
        return entry_price >= (max(highs) - tol_pts)
    if d == "SHORT":
        return entry_price <= (min(lows) + tol_pts)
    return False


def enabled() -> bool:
    return os.getenv("S4_ENTRY_CONFIRM_V1", "0").lower() in ("1", "true", "yes")
