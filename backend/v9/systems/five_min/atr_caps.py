"""ATR caps · pattern family resolution · time_stops · trail overrides.

D-094 §3.D dual-namespace pattern (Option 3 Superset):
- Legacy keys ("Reactive" / "OFA" / "Flag" / "Double_BT" / "HnS") preserve
  Pkg 1's shipped entry-stop behavior. DO NOT change values without
  Michael lock + D-094 amendment.
- xlsx-aligned keys ("OFA_Reactive" / "OFA_Initiative" / "Pennant" /
  "Wedge" / "Triangle") match Sheet C verbatim. Used by Pkg 3b chandelier
  and future Pkg 5a-c patterns. Future Pkg 1-rev (post-SHADOW) may
  migrate Pkg 1 to xlsx-aligned values.

D-094 §3.A: TRAIL_OVERRIDE_BY_PATTERN bridges Pkg 3a's day-type-only
targets_table with xlsx Sheet A row 14 (OFA Initiative on TDD -> 6R+trail).

D-094 §3.C: PATTERN_TIME_STOPS implements Sheet D row 14 pattern-axis
time_stop. Layer 3 backstop in 3-layer trade management.
"""
from typing import Optional


# === ATR multipliers · single source of truth (D-094 §3.D ripple Option 3) ===

ATR_MULTIPLIERS = {
    # Pkg 1 legacy keys (entry stop · current shipped behavior · DO NOT change)
    "Reactive": 1.0,
    "OFA": 1.5,
    "Flag": 1.5,
    "Double_BT": 2.0,
    "HnS": 2.0,
    # xlsx-aligned keys (Sheet C · Pkg 3b chandelier · future Pkg 5+ patterns)
    "OFA_Reactive": 1.5,
    "OFA_Initiative": 2.0,
    "Pennant": 1.5,
    "Wedge": 2.0,
    "Triangle": 2.0,
}


# === Pattern->family canonical name resolver (D-094 §3.A) ===

def _pattern_to_family(pattern_name: str) -> Optional[str]:
    """Map runtime pattern_name to xlsx family for override + chandelier lookup.

    Runtime pattern_name from five_min detectors as 'REACTIVE' / 'INITIATIVE'.
    xlsx family names are 'OFA_Reactive' / 'OFA_Initiative'.
    """
    name = pattern_name.lower()
    if "initiative" in name:
        return "OFA_Initiative"
    if "reactive" in name:
        return "OFA_Reactive"
    return None


# === Trail overrides (D-094 §3.A · hybrid Option 3) ===

TRAIL_OVERRIDE_BY_PATTERN: dict = {
    ("Trend_DD", "OFA_Initiative"): {
        "t3": "6R+trail",
        "trail_after_t2": True,
        "reason": "Dalton TDD second-leg · Sheet A row 14",
    },
    # Future Pkg 5a-c: add other (day_type, family) entries here
}


# === Pattern-axis time stops (D-094 §3.C · Layer 3 backstop) ===

PATTERN_TIME_STOPS = {
    "Flag":             20,
    "Pennant":          20,
    "OFA_Initiative":   20,
    "OFA_Reactive":     30,
    "Triangle":         30,
    "Wedge":            30,
    "HnS":              30,
    "Double_BT":        30,
    "Wyckoff_Spring":   45,
    "Wyckoff_Upthrust": 45,
}


def compute_time_stop_minutes(
    day_type: str,
    pattern_family: Optional[str],
    *,
    targets_table: dict,
) -> Optional[int]:
    """Layer 3 backstop · first-to-fire wins between day-axis and pattern-axis.

    D-094 §3.C decision: min(day, pattern) honors both spec sources.
    """
    day_stop = targets_table.get(day_type, {}).get("time_stop_minutes")
    pat_stop = PATTERN_TIME_STOPS.get(pattern_family) if pattern_family else None
    candidates = [x for x in (day_stop, pat_stop) if x is not None]
    return min(candidates) if candidates else None


# === Chandelier ATR · continuous Wilder's smoothing (D-094 §3.D Q1 b2) ===

def compute_continuous_atr14(
    yesterday_bars: list,
    today_bars_so_far: list,
) -> Optional[float]:
    """Wilder's ATR-14 with continuous smoothing across yesterday->today seam.

    D-094 §3.D Q1 (b2) decision: a single Wilder ATR-14 series is computed
    over the concatenation `yesterday_bars + today_bars_so_far`. Smoothing
    persists across the overnight seam (no reset at session open).

    Overnight gap is included in the TR computation per Wilder canonical behavior.
    TR for today's first bar = max(today_high - today_low,
                                   abs(today_high - yesterday_last_close),
                                   abs(today_low - yesterday_last_close))
    This is intentional: overnight gaps ARE volatility per Wilder's original
    ATR formulation. ATR may be inflated on gap-up/down mornings; this is by design.
    Do NOT introduce a seam-reset that ignores overnight gaps without explicit
    spec change (see D-094 §3.D Q1).

    Args:
        yesterday_bars: ordered list of bar objects with .high, .low, .close
        today_bars_so_far: ordered list of bar objects from current session

    Returns:
        Wilder's ATR-14 as float, or None if insufficient data (<14 bars total).
    """
    all_bars = list(yesterday_bars) + list(today_bars_so_far)
    if len(all_bars) < 14:
        return None

    trs = []
    for i, bar in enumerate(all_bars):
        h = bar.high if hasattr(bar, "high") else bar.get("high", bar.get("h", 0))
        l = bar.low if hasattr(bar, "low") else bar.get("low", bar.get("l", 0))
        c = bar.close if hasattr(bar, "close") else bar.get("close", bar.get("c", 0))
        if i == 0:
            trs.append(h - l)
        else:
            prev = all_bars[i - 1]
            prev_c = prev.close if hasattr(prev, "close") else prev.get("close", prev.get("c", 0))
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            trs.append(tr)

    atr = sum(trs[:14]) / 14
    for tr in trs[14:]:
        atr = ((atr * 13) + tr) / 14

    return float(atr)
