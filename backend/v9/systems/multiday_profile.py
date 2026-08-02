"""MULTIDAY_CONTEXT_V1 — 7-day TPO context computed from canonical bars.

Michael's ruling 02.08 (with his Sierra TPO-chart screenshot): "להכניס 7 ימים
אחורה כדי לדעת לפי דלתון סוגי-פתיחה וסוג-יום בצורה מדויקת."

Dalton's opening/day-type reads are defined against the MULTI-DAY balance —
where today opens relative to the recent value/bracket, whether value is
migrating or overlapping — while the system so far looked one day back only.
The audit's 21.07 (−$209: five shorts sold into upward-migrating value) is the
acceptance case: value_migration must read UP there.

ZERO Sierra changes: everything is TPO-counted from the canonical 5-min bars
in v9_bars_5min_woodies (derived analytics from truth bars — allowed; never a
synthesis of missing DLL fields). tpo.json remains canonical for TODAY.

Pure module — no env, no I/O; callers pass per-session bar lists.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

TICK = 0.25
TPO_PERIOD_BARS = 6          # 6 x 5min = one 30-min TPO period (a letter)
VA_PCT = 0.70                # value area = 70% of TPOs around the POC
MIGRATION_MIN_PTS = 4.0      # POC-mid drift below this over the window = FLAT
OVERLAP_BALANCE_MIN = 0.60   # avg pairwise VA overlap >= this = balance regime


def _f(bar: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def session_tpo_profile(bars: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """TPO profile of ONE session from its closed 5-min bars (oldest→newest).
    Counts one TPO per 30-min period per quarter-point touched (exactly what
    the chart's letters do). Returns poc/vah/val/high/low/single-prints."""
    if not bars or len(bars) < TPO_PERIOD_BARS:
        return None
    counts: Dict[float, int] = {}
    n_periods = 0
    for p0 in range(0, len(bars), TPO_PERIOD_BARS):
        period = bars[p0:p0 + TPO_PERIOD_BARS]
        hi = max((_f(b, "h", "high") or float("-inf")) for b in period)
        lo = min((_f(b, "l", "low") or float("inf")) for b in period)
        if hi == float("-inf") or lo == float("inf"):
            continue
        n_periods += 1
        lvl = round(round(lo / TICK) * TICK, 2)
        while lvl <= hi + 1e-9:
            counts[lvl] = counts.get(lvl, 0) + 1
            lvl = round(lvl + TICK, 2)
    if not counts or n_periods == 0:
        return None
    levels = sorted(counts)
    total = sum(counts.values())
    # POC = max count; tie → closest to the middle of the range (Dalton)
    mid = (levels[0] + levels[-1]) / 2
    poc = max(counts, key=lambda p: (counts[p], -abs(p - mid)))
    # value area: expand from POC toward the heavier neighbour until VA_PCT
    va = {poc}
    acc = counts[poc]
    lo_i, hi_i = levels.index(poc), levels.index(poc)
    while acc < VA_PCT * total:
        up = counts.get(levels[hi_i + 1]) if hi_i + 1 < len(levels) else None
        dn = counts.get(levels[lo_i - 1]) if lo_i - 1 >= 0 else None
        if up is None and dn is None:
            break
        if dn is None or (up is not None and up >= dn):
            hi_i += 1
            acc += up
            va.add(levels[hi_i])
        else:
            lo_i -= 1
            acc += dn
            va.add(levels[lo_i])
    singles = [p for p in levels if counts[p] == 1]
    return {
        "poc": poc, "vah": max(va), "val": min(va),
        "high": levels[-1], "low": levels[0],
        "total_tpos": total, "n_periods": n_periods,
        "singles": singles,
        # מייקל 02.08: "מדויק כמו של סיירה" — ההיסטוגרמה המלאה פר-רבע-נקודה,
        # כדי שהפרונט יצייר פרופיל-TPO אמיתי ולא רק קופסת-VA.
        "profile": [[p, counts[p]] for p in levels],
    }


def composite_profile(day_profiles: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Merge day profiles into a composite: range + composite value zone
    (union-weighted by TPO totals is overkill for v1 — the composite VA here
    is the envelope of the per-day VAs, and the composite POC the median of
    daily POCs; honest and stable)."""
    days = [d for d in day_profiles if d]
    if not days:
        return None
    pocs = sorted(d["poc"] for d in days)
    return {
        "range_high": max(d["high"] for d in days),
        "range_low": min(d["low"] for d in days),
        "vah": max(d["vah"] for d in days),
        "val": min(d["val"] for d in days),
        "poc": pocs[len(pocs) // 2],
        "n_days": len(days),
    }


def value_migration(day_profiles: Sequence[Dict[str, Any]],
                    window: int = 5) -> Dict[str, Any]:
    """Direction of value over the last `window` days: linear drift of the
    VA midpoint. UP/DOWN/FLAT + slope (pts/day). The 21.07 acceptance case:
    five days of rising value must read UP."""
    days = [d for d in day_profiles if d][-window:]
    if len(days) < 3:
        return {"direction": None, "slope": None, "n": len(days)}
    mids = [(d["vah"] + d["val"]) / 2 for d in days]
    n = len(mids)
    xbar = (n - 1) / 2
    ybar = sum(mids) / n
    denom = sum((i - xbar) ** 2 for i in range(n))
    slope = sum((i - xbar) * (m - ybar) for i, m in enumerate(mids)) / denom if denom else 0.0
    total_drift = slope * (n - 1)
    if abs(total_drift) < MIGRATION_MIN_PTS:
        direction = "FLAT"
    else:
        direction = "UP" if slope > 0 else "DOWN"
    return {"direction": direction, "slope": round(slope, 2), "n": n}


def va_overlap_pct(day_profiles: Sequence[Dict[str, Any]]) -> Optional[float]:
    """Mean pairwise (consecutive) VA overlap fraction. High = balance
    (overlapping value), low = trend (migrating value)."""
    days = [d for d in day_profiles if d]
    if len(days) < 2:
        return None
    fr = []
    for a, b in zip(days[:-1], days[1:]):
        lo = max(a["val"], b["val"])
        hi = min(a["vah"], b["vah"])
        inter = max(0.0, hi - lo)
        union = max(a["vah"], b["vah"]) - min(a["val"], b["val"])
        fr.append(inter / union if union > 0 else 0.0)
    return round(sum(fr) / len(fr), 2)


def open_location(open_price: float,
                  comp: Dict[str, Any]) -> str:
    """Where today opens relative to the multi-day balance (Dalton R11):
    above_range / above_value / in_value / below_value / below_range."""
    if open_price > comp["range_high"]:
        return "above_range"
    if open_price > comp["vah"]:
        return "above_value"
    if open_price < comp["range_low"]:
        return "below_range"
    if open_price < comp["val"]:
        return "below_value"
    return "in_value"


def build_context(sessions: Sequence[Sequence[Dict[str, Any]]],
                  today_open: Optional[float] = None,
                  suspect_dates: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """One call: `sessions` = list of per-day bar lists (oldest day first,
    excluding today). Returns the full multi-day context. Missing/short days
    are skipped honestly."""
    profiles = [session_tpo_profile(list(s)) for s in sessions]
    kept = [p for p in profiles if p]
    comp = composite_profile(kept[-7:])
    return {
        "days": kept[-7:],
        "composite": comp,
        "value_migration": value_migration(kept),
        "va_overlap_pct": va_overlap_pct(kept[-7:]),
        "open_location": (open_location(today_open, comp)
                          if (today_open is not None and comp) else None),
        "n_days_used": len(kept[-7:]),
        "suspect_dates": list(suspect_dates or []),
    }
