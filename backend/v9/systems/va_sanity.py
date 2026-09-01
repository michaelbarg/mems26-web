"""VA sanity check — flags impossible Value Areas before consumers use them.

Michael 01.09: "לתקן קודם את חישוב אזור-הערך, ואז לחקור."

A Value Area is 70% of volume by definition. When VA_width is <50% of
RTH range or >90% of RTH range, something is structurally wrong (partial
profile, stale data, wrong session boundary). Consumers must get None
(Rule 1: honest failure), not a number that makes them decide on fiction.

The 31.08 case: VA=3.50 with IB=29.50 — the VA was 8× smaller than the
IB, which is definitionally impossible (IB is 1 hour, VA is the whole day).
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def va_quality(
    *,
    vah: Optional[float],
    val: Optional[float],
    session_high: Optional[float] = None,
    session_low: Optional[float] = None,
    ib_high: Optional[float] = None,
    ib_low: Optional[float] = None,
    min_ratio: float = 0.15,
    max_ratio: float = 0.95,
) -> dict:
    """Assess whether the VA is structurally plausible.

    Returns {"ok": bool, "vah", "val", "width", "ratio", "reason"}.
    ok=False → consumers should treat vah/val as None.
    """
    if vah is None or val is None:
        return {"ok": False, "vah": None, "val": None, "width": None,
                "ratio": None, "reason": "missing"}

    width = vah - val
    if width <= 0:
        return {"ok": False, "vah": vah, "val": val, "width": width,
                "ratio": None, "reason": "inverted_or_zero"}

    # Check against RTH range
    rth_range = None
    if session_high is not None and session_low is not None:
        rth_range = session_high - session_low
        if rth_range > 0:
            ratio = width / rth_range
            if ratio < min_ratio:
                logger.warning(
                    "[VA_SANITY] SUSPECT: VA=%.2f (%.1f%% of range %.2f) — "
                    "too narrow, profile may be partial",
                    width, ratio * 100, rth_range)
                return {"ok": False, "vah": vah, "val": val, "width": width,
                        "ratio": round(ratio, 3),
                        "reason": f"too_narrow ({ratio:.1%} < {min_ratio:.0%})"}
            if ratio > max_ratio:
                return {"ok": False, "vah": vah, "val": val, "width": width,
                        "ratio": round(ratio, 3),
                        "reason": f"too_wide ({ratio:.1%} > {max_ratio:.0%})"}

    # Check against IB (VA must be >= IB width by definition for a full day)
    if ib_high is not None and ib_low is not None:
        ib_width = ib_high - ib_low
        if ib_width > 0 and width < ib_width * 0.5:
            logger.warning(
                "[VA_SANITY] SUSPECT: VA=%.2f < 50%% of IB=%.2f — "
                "impossible for a full-day profile", width, ib_width)
            return {"ok": False, "vah": vah, "val": val, "width": width,
                    "ratio": round(width / ib_width, 3) if ib_width > 0 else None,
                    "reason": f"smaller_than_ib (VA={width:.1f} < IB/2={ib_width/2:.1f})"}

    return {"ok": True, "vah": vah, "val": val, "width": round(width, 2),
            "ratio": round(width / rth_range, 3) if rth_range and rth_range > 0 else None,
            "reason": "ok"}
