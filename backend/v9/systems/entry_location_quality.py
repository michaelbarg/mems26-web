"""ENTRY_LOCATION_QUALITY_V1 — relative position quality gate (Michael 28.08 18:50).

"הרבה מהסיבה שנכנס ללונג במיקום מאוחר — אם היה נכנס במקום נכון היינו מרוויחים
הרבה כסף." + "זה היה צריך להיות יחסי" (18:55).

Three binary disqualifiers, all relative to the day's structure:

  1. CHASER (pos > pos_max):
     pos = |entry - R| / L   where R = leg base, L = leg length.
     pos > 0.66 with no pullback = entering in the top third of the move.

  2. EXPENSIVE STOP (rr > rr_max):
     rr = stop_distance / ATR.
     rr > 1.5 = the stop is too far relative to today's volatility.

  3. BEYOND VALUE (ex > ex_max):
     ex = (entry - VAH) / VA_width   for LONG continuation.
     ex > 0.25 = chasing past the value area.

Params live in config/entry_location_quality.yaml (YAML, not env);
code defaults serve as the fallback. Pure function — no I/O.

Anchor 28.08 (MUST pass):
  17:00 @7749.75 → pos ≈ 0.38 → PASS
  17:35 @7750.75 → pos ≈ 0.40 → PASS
  18:15 @7774.00 → pos ≈ 0.84 → FAIL (chaser)
  18:25 @7777.75 → pos ≈ 0.91 → FAIL (chaser)
"""
from __future__ import annotations

from typing import Any, Dict, Optional

DEFAULTS: Dict[str, float] = {
    "pos_max": 0.66,   # position in leg — above = chaser
    "rr_max": 1.5,     # stop/ATR ratio — above = expensive
    "ex_max": 0.25,    # beyond-value — above = chasing past VA
}


def _cfg(yaml_cfg: Optional[Dict[str, Any]]) -> Dict[str, float]:
    out = dict(DEFAULTS)
    if isinstance(yaml_cfg, dict):
        for k in DEFAULTS:
            v = yaml_cfg.get(k)
            if v is not None:
                try:
                    out[k] = float(v)
                except (TypeError, ValueError):
                    pass
    return out


def assess_entry_quality(
    *,
    entry_price: float,
    direction: str,
    leg_base: Optional[float],
    leg_extreme: Optional[float],
    stop_distance: Optional[float],
    atr: Optional[float],
    vah: Optional[float],
    val: Optional[float],
    has_pullback: bool = False,
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assess entry quality. Returns {"pass": bool, "reasons": [...], ...}.

    Pure function. None on any input → that check is skipped (Rule 1:
    honest missing, never a synthetic block).
    """
    c = _cfg(cfg)
    d = (direction or "").upper()
    reasons = []

    pos = None
    rr = None
    ex = None

    # 1. Position in leg (chaser check)
    if leg_base is not None and leg_extreme is not None:
        L = abs(leg_extreme - leg_base)
        if L > 0:
            if d == "LONG":
                pos = (entry_price - leg_base) / L
            elif d == "SHORT":
                pos = (leg_base - entry_price) / L
            else:
                pos = None

            if pos is not None and pos > c["pos_max"] and not has_pullback:
                reasons.append(
                    f"chaser: pos={pos:.2f} > {c['pos_max']:.2f} "
                    f"(top {100*(1-c['pos_max']):.0f}% of leg, no pullback)")

    # 2. Expensive stop
    if stop_distance is not None and atr is not None and atr > 0:
        rr = stop_distance / atr
        if rr > c["rr_max"]:
            reasons.append(
                f"expensive_stop: rr={rr:.2f} > {c['rr_max']:.2f} "
                f"(stop {stop_distance:.1f} vs ATR {atr:.1f})")

    # 3. Beyond value
    if vah is not None and val is not None:
        va_width = vah - val
        if va_width > 0:
            if d == "LONG":
                ex = (entry_price - vah) / va_width
            elif d == "SHORT":
                ex = (val - entry_price) / va_width

            if ex is not None and ex > c["ex_max"]:
                reasons.append(
                    f"beyond_value: ex={ex:.2f} > {c['ex_max']:.2f} "
                    f"(entry past value area)")

    return {
        "pass": len(reasons) == 0,
        "reasons": reasons,
        "pos": round(pos, 4) if pos is not None else None,
        "rr": round(rr, 4) if rr is not None else None,
        "ex": round(ex, 4) if ex is not None else None,
        "label": "base" if (pos is not None and pos <= 0.33)
                 else "mid" if (pos is not None and pos <= 0.66)
                 else "chaser" if (pos is not None and pos > 0.66)
                 else None,
    }
