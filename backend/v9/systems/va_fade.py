"""VA_FADE_V1 — Value Area rotation generator for balance days (Phase 2).

Michael 26.08: the system owns only continuation/trend patterns, while most
days are balance-class where the play is: sell VAH, buy VAL, target the middle.

25.08 anchor: 4 rotations VAL↔VAH, zero doctrine-fires; the shadow faded
INVERSE −$863.75, and the two that faded correctly — both won.

Dalton binary: zero percentage thresholds. A rejection bar is a geometric
definition (probe into edge zone, close back away, in the far half of range).

ADAPTED from edge_fade.py: replaces day_hi/day_lo with VAH/VAL from the live
TPO system. Enters as a regular pattern through the full gateway chain —
no gate bypasses.

Flag VA_FADE_V1 (default OFF). Pure logic — no env reads in the module.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Edge zone: how close to VAH/VAL to consider "at the edge"
VA_EDGE_ZONE_PTS = 2.0
# Minimum IB width to consider fading (no fading in a coil)
VA_MIN_IB_WIDTH_PTS = 12.0
# Stop beyond the probe extreme
VA_STOP_OFFSET_PTS = 1.5
# Stop cap
VA_STOP_CAP_PTS = 12.0
# Variation + Trend days: eligible subtypes
VA_FADE_DAY_TYPES = frozenset({
    "Variation", "Normal_Variation", "Normal",
    "Neutral_Center", "Neutral_Extreme",
})


def _f(bar: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def detect_va_fade(
    session_bars: List[Dict[str, Any]],
    day_type: Optional[str],
    vah: Optional[float],
    val: Optional[float],
    *,
    already_fired: Optional[Set[str]] = None,
    min_bars: int = 12,
    ib_width: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Detect a VA edge rejection on the LAST closed bar.

    Returns a trigger dict or None. Pure function — the caller gates on
    VA_FADE_V1 and routes through the gateway.
    """
    if day_type not in VA_FADE_DAY_TYPES:
        return None
    if vah is None or val is None:
        return None
    va_range = vah - val
    if va_range < VA_MIN_IB_WIDTH_PTS:
        return None
    n = len(session_bars)
    if n < min_bars:
        return None
    fired = already_fired or set()

    last = session_bars[-1]
    lh = _f(last, "h", "high")
    ll = _f(last, "l", "low")
    lc = _f(last, "c", "close")
    lo = _f(last, "o", "open")
    if None in (lh, ll, lc, lo):
        return None
    bar_rng = lh - ll
    if bar_rng <= 0:
        return None
    close_pos = (lc - ll) / bar_rng  # 0=low, 1=high

    poc = (vah + val) / 2.0  # approximation — live POC from TPO is better

    # ── VAH rejection → SHORT ──
    # Bar probed into the VAH zone, then closed back BELOW VAH
    if ("VA_FADE_HIGH" not in fired
            and lh >= vah - VA_EDGE_ZONE_PTS
            and close_pos <= 0.5
            and lc < vah):
        stop = min(lh + VA_STOP_OFFSET_PTS, lc + VA_STOP_CAP_PTS)
        return {
            "type": "VA_FADE_HIGH",
            "direction": "SHORT",
            "entry": round(lc, 2),
            "stop": round(stop, 2),
            "vah": round(vah, 2),
            "val": round(val, 2),
            "poc": round(poc, 2),
            "probe_extreme": round(lh, 2),
            "target_mid": round(poc, 2),
        }

    # ── VAL rejection → LONG ──
    if ("VA_FADE_LOW" not in fired
            and ll <= val + VA_EDGE_ZONE_PTS
            and close_pos >= 0.5
            and lc > val):
        stop = max(ll - VA_STOP_OFFSET_PTS, lc - VA_STOP_CAP_PTS)
        return {
            "type": "VA_FADE_LOW",
            "direction": "LONG",
            "entry": round(lc, 2),
            "stop": round(stop, 2),
            "vah": round(vah, 2),
            "val": round(val, 2),
            "poc": round(poc, 2),
            "probe_extreme": round(ll, 2),
            "target_mid": round(poc, 2),
        }

    return None


def build_va_fade_setup(trigger: Dict[str, Any],
                        contracts: int = 3) -> Dict[str, Any]:
    """Build a gateway-routable setup from a VA_FADE trigger."""
    entry = float(trigger["entry"])
    stop = float(trigger["stop"])
    direction = trigger["direction"]
    risk = abs(entry - stop)
    sign = 1.0 if direction == "LONG" else -1.0
    t1 = entry + sign * 1.0 * risk  # 1R bank
    t2 = float(trigger["target_mid"])  # POC target
    # T2 must be beyond T1
    if (direction == "LONG" and t2 <= t1) or (direction == "SHORT" and t2 >= t1):
        t2 = entry + sign * 2.0 * risk
    pat = f"VA_FADE_{direction}"
    return {
        "firing_system": 2,
        "pattern": pat,
        "classification": pat,
        "direction": direction,
        "entry_price": round(entry, 2),
        "stop": round(stop, 2),
        "t1": round(t1, 2),
        "t2": round(t2, 2),
        "t3": None,
        "metadata": {
            "pattern": pat,
            "source": "va_fade_v1",
            "vah": trigger.get("vah"),
            "val": trigger.get("val"),
            "poc": trigger.get("poc"),
            "probe_extreme": trigger.get("probe_extreme"),
            "shadow_only": True,  # shadow until Michael ruling
        },
    }
