"""value_migration — P1-6: value-migration classification feature (Michael 2026-07-12).

Doctrine (DALTON_DOCTRINE.md §4 P1-6; pp.49, 55): a REAL Trend day migrates VALUE —
the developing value-area moves away from yesterday's; overlapping value = balance /
bracket signal. Geometry (range, stair-steps) says what price did; value says what
the MARKET ACCEPTED. Trend continuation requires migrating value.

Pure functions, bar-based (no Sierra dependency, no lookahead when called on a
prefix): volume-at-price profile from 5-min bars (volume at typical price, same
bucketing technique as dd_features), POC = heaviest bucket, VA = Dalton 70%
expansion around the POC.

Emitted features (consumed by classify() only under S1_VALUE_MIGRATION_V1):
  dev_poc / dev_vah / dev_val — the developing profile so far.
  va_overlap_pct — overlap(developing VA, prior VA) / min(width) ∈ [0,1] (None if no prior VA).
  value_migration — "UP" | "DOWN" | None:
      UP   = developing VAL sits at/above prior VAH (value fully migrated up)
      DOWN = developing VAH sits at/below prior VAL
      None = value overlaps yesterday's (balance).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional


def _g(bar: Any, *keys: str):
    if isinstance(bar, dict):
        for k in keys:
            v = bar.get(k)
            if v is not None:
                return v
        return None
    for k in keys:
        v = getattr(bar, k, None)
        if v is not None:
            return v
    return None


def developing_value(bars: List[Any], bucket: float = 1.0) -> Dict[str, Optional[float]]:
    """Volume-at-price POC + 70% value area from the session's bars so far.

    Volume is booked at each bar's typical price (H+L+C)/3, bucketed. Bars with
    no volume fall back to count=1 per bar (synthetic tests) — honest degrade.
    """
    out: Dict[str, Optional[float]] = {"poc": None, "vah": None, "val": None}
    if not bars:
        return out
    vol: Dict[float, float] = defaultdict(float)
    for b in bars:
        h, l, c = _g(b, "h", "high"), _g(b, "l", "low"), _g(b, "c", "close")
        if None in (h, l, c):
            continue
        tp = round(((h + l + c) / 3.0) / bucket) * bucket
        vol[tp] += (_g(b, "v", "volume") or 1.0)
    if not vol:
        return out
    prices = sorted(vol)
    poc = max(prices, key=lambda p: (vol[p], p))
    total = sum(vol.values())
    target = 0.70 * total
    acc = vol[poc]
    i = prices.index(poc)
    lo = hi = i
    while acc < target and (lo > 0 or hi < len(prices) - 1):
        up_v = vol[prices[hi + 1]] if hi < len(prices) - 1 else -1.0
        dn_v = vol[prices[lo - 1]] if lo > 0 else -1.0
        if up_v >= dn_v:
            hi += 1
            acc += up_v
        else:
            lo -= 1
            acc += dn_v
    out["poc"] = round(poc, 2)
    out["vah"] = round(prices[hi] + bucket / 2, 2)
    out["val"] = round(prices[lo] - bucket / 2, 2)
    return out


def value_migration(
    bars: List[Any],
    prior_vah: Optional[float],
    prior_val: Optional[float],
    bucket: float = 1.0,
) -> Dict[str, Any]:
    """Developing-VA vs prior-day VA: overlap fraction + migration direction."""
    dev = developing_value(bars, bucket)
    out: Dict[str, Any] = {
        "dev_poc": dev["poc"], "dev_vah": dev["vah"], "dev_val": dev["val"],
        "va_overlap_pct": None, "value_migration": None,
    }
    if None in (dev["vah"], dev["val"]) or prior_vah is None or prior_val is None:
        return out
    p_hi, p_lo = max(prior_vah, prior_val), min(prior_vah, prior_val)
    d_hi, d_lo = dev["vah"], dev["val"]
    inter = max(0.0, min(d_hi, p_hi) - max(d_lo, p_lo))
    denom = min(d_hi - d_lo, p_hi - p_lo)
    out["va_overlap_pct"] = round(inter / denom, 3) if denom > 0 else (1.0 if inter > 0 else 0.0)
    if d_lo >= p_hi:
        out["value_migration"] = "UP"
    elif d_hi <= p_lo:
        out["value_migration"] = "DOWN"
    return out
