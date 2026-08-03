"""EDGE_FADE_V1 — responsive edge-fade for balance days (DEV_PLAN 02.08 §P1).

The single biggest detection gap in the 13-day Dalton audit (~$1,550): the
system owns ONLY continuation/trend-class patterns, while most days are
balance-class (Normal / Neutral) where the book play is the opposite —
sell the expensive edge, buy the cheap edge, target the middle. Four audit
days (07-15, 07-17, 07-27, 07-31) each contained a textbook edge rejection
that no pattern attacked; on 07-31 the system even took the INVERSE trade
(bought the opening spike top on a giant-IB Normal day, #575).

Doctrine (Dalton, Mind Over Markets — responsive trade on balance days):
  • Balance-class day only: Normal / Neutral_Center / Neutral_Extreme.
    (Variation/Trend keep their continuation playbook; Nontrend = no-trade.)
  • Meaningful range: day range >= EDGE_MIN_RANGE_PTS — fading a tight
    coil is noise, not responsiveness.
  • The EDGE: today's session high/low (which on these days ≈ the IB edge).
    A probe INTO/через the edge zone that CLOSES back away from it, with the
    close in the far half of the probing bar's range = the rejection bar.
  • Entry on the rejection close · stop beyond the probe extreme (+offset,
    capped) · T1 = 1R bank (system norm) · T2 = day mid (the rotation
    objective), clamped by the emit-path 3R rule.
  • One fade per side per session (re-arms only after a stop-out is NOT
    implemented in v1 — honesty over cleverness).

ARM → RELEASE two-stage design (2026-08-02 simulation finding): the naive
"enter on the rejection bar" lost −$372 on the four specimen days (1W/6L) —
one rejection bar is not a turn (the 07-28 lesson again). And routing the
edge-trigger through awaiting_release took ZERO trades, because the trigger
requires proximity to the edge while the release confirms only after LEAVING
it — mutually exclusive by construction. The correct mechanization:

  STAGE 1 (ARM):   an edge probe+rejection ARMS the fade for that side.
  STAGE 2 (ENTRY): within ARM_WINDOW_BARS, the release-gate confirmation
                   (structure turn + volume + zone exit) IS the entry; the
                   stop is the release's structural stop (beyond the edge
                   extreme, capped). This exactly reproduces the 07-27
                   winner (armed 19:10 low probe → entered 19:50 @7433).

VALIDATION STATUS: on available bars, armed→release scored +$150 on the two
clean-data days (07-27, 07-31) and lost on the two contamination-suspect
days (07-15, 07-17) — NOT enabled; enabling requires validation on the
.scid truth bars (level D) per the evidence discipline.

Pure logic — no env, no I/O; caller gates on EDGE_FADE_V1 + day_type.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

EDGE_ZONE_PTS = 3.0          # probe must reach within this of the session extreme
EDGE_MIN_RANGE_PTS = 20.0    # no fading inside a coil
EDGE_STOP_OFFSET_PTS = 1.5   # stop beyond the probe extreme
EDGE_STOP_CAP_PTS = 15.0     # same cap doctrine as opening/ZLR (rulings 06-12/07-31)
FADE_DAY_TYPES = ("Normal", "Neutral_Center", "Neutral_Extreme")
# D1 (2026-08-03): contained Normal_Variation (rib < 1.5) is functionally
# a balance day — the extension is minor. Eligible for edge-fade when
# EDGE_FADE_CONTAINED_NV_V1 is ON.
FADE_DAY_TYPES_EXTENDED = FADE_DAY_TYPES + ("Normal_Variation",)
CONTAINED_NV_RIB_MAX = 1.5


def _f(bar: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def evaluate_edge_fade(session_bars: List[Dict[str, Any]],
                       day_type: Optional[str],
                       already_fired: Optional[Set[str]] = None,
                       *, min_bars: int = 6,
                       rib: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Evaluate the LAST closed bar for an edge rejection. Returns a trigger
    dict {type, direction, entry, stop, edge, probe_extreme} or None.

    `session_bars` = today's closed RTH 5-min bars oldest→newest.
    `day_type` must be one of FADE_DAY_TYPES (caller passes the live label);
    None/other → no trade (the fade is a balance-day tool, full stop).

    D1 (2026-08-03): contained Normal_Variation (rib < 1.5) is also eligible
    when the day range is large enough but the extension is minor."""
    import os as _ef_os
    fired = already_fired or set()
    # D1: extend to contained NV when flag ON + rib available + rib < threshold
    _contained_nv_on = _ef_os.getenv("EDGE_FADE_CONTAINED_NV_V1", "0").lower() in (
        "1", "true", "yes")
    _valid_types = FADE_DAY_TYPES
    if _contained_nv_on and day_type == "Normal_Variation" and rib is not None and rib < CONTAINED_NV_RIB_MAX:
        _valid_types = FADE_DAY_TYPES_EXTENDED
    if day_type not in _valid_types:
        return None
    n = len(session_bars)
    if n < min_bars:                      # session too young for "edges"
        return None

    highs = [_f(b, "h", "high") for b in session_bars]
    lows = [_f(b, "l", "low") for b in session_bars]
    if any(v is None for v in highs) or any(v is None for v in lows):
        return None
    day_hi, day_lo = max(highs), min(lows)
    rng = day_hi - day_lo
    if rng < EDGE_MIN_RANGE_PTS:
        return None

    last = session_bars[-1]
    lh, ll = _f(last, "h", "high"), _f(last, "l", "low")
    lc, lo = _f(last, "c", "close"), _f(last, "o", "open")
    if None in (lh, ll, lc, lo):
        return None
    bar_rng = lh - ll
    if bar_rng <= 0:
        return None
    close_pos = (lc - ll) / bar_rng       # 0 = at the low, 1 = at the high
    mid = (day_hi + day_lo) / 2.0

    # ── UPPER edge rejection → SHORT ──
    # the bar probed the high zone (or set the high itself), then closed in
    # the lower half AND back below the edge zone.
    if ("FADE_HIGH" not in fired
            and lh >= day_hi - EDGE_ZONE_PTS
            and close_pos <= 0.5
            and lc < day_hi - EDGE_ZONE_PTS):
        stop = min(lh + EDGE_STOP_OFFSET_PTS, lc + EDGE_STOP_CAP_PTS)
        return {"type": "FADE_HIGH", "direction": "SHORT", "entry": lc,
                "stop": round(stop, 2), "edge": day_hi, "probe_extreme": lh,
                "target_mid": round(mid, 2), "day_range": round(rng, 2)}

    # ── LOWER edge rejection → LONG ──
    if ("FADE_LOW" not in fired
            and ll <= day_lo + EDGE_ZONE_PTS
            and close_pos >= 0.5
            and lc > day_lo + EDGE_ZONE_PTS):
        stop = max(ll - EDGE_STOP_OFFSET_PTS, lc - EDGE_STOP_CAP_PTS)
        return {"type": "FADE_LOW", "direction": "LONG", "entry": lc,
                "stop": round(stop, 2), "edge": day_lo, "probe_extreme": ll,
                "target_mid": round(mid, 2), "day_range": round(rng, 2)}
    return None


ARM_WINDOW_BARS = 24         # release must confirm within ~2h of arming


def build_release_entry_setup(direction: str, entry: float,
                              structural_stop: Optional[float],
                              target_mid: float, fallback_stop: float,
                              contracts: int = 3,
                              t1_bank_r: float = 1.0) -> Dict[str, Any]:
    """Stage-2 setup: entry at the RELEASE confirmation close, stop = the
    release's structural stop (beyond the edge extreme), capped at
    EDGE_STOP_CAP_PTS. T1 = 1R bank, T2 = day mid (degrades to 2R when the
    mid sits inside T1)."""
    sign = 1.0 if direction == "LONG" else -1.0
    stop = structural_stop if structural_stop is not None else fallback_stop
    if abs(entry - stop) > EDGE_STOP_CAP_PTS:
        stop = entry - sign * EDGE_STOP_CAP_PTS
    risk = abs(entry - stop)
    t1 = entry + sign * t1_bank_r * risk
    t2 = float(target_mid)
    if (direction == "LONG" and t2 <= t1) or (direction == "SHORT" and t2 >= t1):
        t2 = entry + sign * 2.0 * risk
    pat = f"EDGE_{'FADE_SHORT' if direction == 'SHORT' else 'FADE_LONG'}"
    return {
        "firing_system": 2, "pattern": pat, "direction": direction,
        "entry_price": round(entry, 2), "stop": round(stop, 2),
        "t1": round(t1, 2), "t2": round(t2, 2), "t3": None,
        "contracts": contracts, "confidence": 65,
        "metadata": {"pattern_id": pat, "source": "edge_fade_v1_arm_release"},
    }


def build_edge_fade_setup(trigger: Dict[str, Any],
                          contracts: int = 3,
                          t1_bank_r: float = 1.0) -> Dict[str, Any]:
    """Gateway-routable setup from a trigger. T1 = 1R bank; T2 = day mid
    (the rotation objective — emit-path clamps to 3R). Same shape the
    opening-entry setups use."""
    entry = float(trigger["entry"])
    stop = float(trigger["stop"])
    direction = trigger["direction"]
    risk = abs(entry - stop)
    sign = 1.0 if direction == "LONG" else -1.0
    t1 = entry + sign * t1_bank_r * risk
    t2 = float(trigger["target_mid"])
    # monotonicity: T2 must sit beyond T1 in the trade direction; a mid
    # closer than T1 degrades honestly to 2R.
    if (direction == "LONG" and t2 <= t1) or (direction == "SHORT" and t2 >= t1):
        t2 = entry + sign * 2.0 * risk
    return {
        "firing_system": 2,
        "pattern": f"EDGE_{'FADE_SHORT' if direction == 'SHORT' else 'FADE_LONG'}",
        "direction": direction,
        "entry_price": entry,
        "stop": round(stop, 2),
        "t1": round(t1, 2),
        "t2": round(t2, 2),
        "t3": None,
        "contracts": contracts,
        "confidence": 65,
        "metadata": {
            "pattern_id": f"EDGE_{'FADE_SHORT' if direction == 'SHORT' else 'FADE_LONG'}",
            "source": "edge_fade_v1",
            "edge": trigger.get("edge"),
            "probe_extreme": trigger.get("probe_extreme"),
            "day_range": trigger.get("day_range"),
        },
    }
