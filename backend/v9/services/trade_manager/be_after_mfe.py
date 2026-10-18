# -*- coding: utf-8 -*-
"""be_after_mfe — BRIEF §2.3 variant 1 (T-598, fix-agent night 18→19.10): stop → break-even once the open
trade's MFE has reached R × the initial risk.

METHOD_AUDIT 05.10 (ז): "34% of the losers were at +1R before the stop; management after +1R does not exist".
The live protective BE today is "after T1" (ruling 07-14), which a 1-contract ladder never reaches before the
exit — so this is the first exit rule measured on the whole day in the harness.

Pure functions, no os.getenv, no Sierra, no DB. The ONLY caller is scripts/fwd_harness.py under
BE_AFTER_MFE_R_V1 (harness measurement, default 0 ⇒ byte-identical replay). The live counterpart — a
closed-bar MODIFY_STOP in bar_level_detector — is NOT wired here: nothing in the live path imports this module.
"""
from __future__ import annotations

from typing import Optional, Sequence


def mfe_pts(direction: str, fill: float, highs: Sequence[float], lows: Sequence[float]) -> float:
    """Max favourable excursion in points from `fill` over the given CLOSED bars (the current bar included).
    LONG → max(high) − fill; SHORT → fill − min(low)."""
    if str(direction).upper() == "LONG":
        return max(float(h) for h in highs) - float(fill)
    return float(fill) - min(float(l) for l in lows)


def be_stop_after_mfe(direction: str, fill: float, stop_now: float, stop_initial: float,
                      highs: Sequence[float], lows: Sequence[float], r: float) -> Optional[float]:
    """The new stop (= the fill price, break-even) when the MFE since the fill is ≥ r × |fill − stop_initial|
    and that move is a TIGHTEN (never widen); otherwise None.

    r ≤ 0 / missing bars ⇒ None — the flag-off path, byte-identical to a replay without the rule.
    A zero-distance initial stop counts as one tick (0.25) so the rule can never divide by zero."""
    try:
        r = float(r or 0)
    except (TypeError, ValueError):
        return None
    if r <= 0 or not highs or not lows:
        return None
    d = str(direction).upper()
    fill = float(fill)
    risk = abs(fill - float(stop_initial)) or 0.25
    if mfe_pts(d, fill, highs, lows) < r * risk:
        return None
    stop_now = float(stop_now)
    if d == "LONG" and fill > stop_now:
        return fill
    if d == "SHORT" and fill < stop_now:
        return fill
    return None
