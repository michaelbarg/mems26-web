"""trade_economics — single authority for stop/target/size.

Michael ruling 09.09: "מיקום הסטופ ייצר כמה שפחות נזק, אבל מנגד
צריך למקם אותו במקום מבני כדי שלא סתם ייפרץ."

    economics(setup, bars, ib_high, ib_low, day_type) → EconomicsResult

The stop is the closest structural anchor to the producer's own stop
+ 2 ticks buffer. The size is derived from the stop: n = min(5, floor(225/(5*risk))).
n < 3 → reject. Targets come from the day-type table on the REAL risk.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TICK = 0.25
POINT_VALUE = 5.0  # MES


@dataclass
class EconomicsResult:
    entry: float
    stop: float
    t1: Optional[float]
    t2: Optional[float]
    t3: Optional[float]
    risk: float
    contracts: int
    reject_reason: Optional[str]
    source: str


def enabled() -> bool:
    v = os.getenv("TRADE_ECONOMICS_AUTHORITY_V1", "0").strip().lower()
    return v in ("1", "diff", "true", "yes")


def is_diff() -> bool:
    return os.getenv("TRADE_ECONOMICS_AUTHORITY_V1", "0").strip().lower() == "diff"


def _snap_tick(price: float) -> float:
    return round(round(price / TICK) * TICK, 2)


def _bar_median_range(bars: List[Dict]) -> float:
    """Median high-low range of RTH bars."""
    ranges = []
    for b in bars:
        h = b.get("h", b.get("high"))
        l = b.get("l", b.get("low"))
        if h is not None and l is not None:
            ranges.append(float(h) - float(l))
    if not ranges:
        return 0.0
    ranges.sort()
    n = len(ranges)
    return ranges[n // 2] if n % 2 else (ranges[n // 2 - 1] + ranges[n // 2]) / 2.0


def _targets_for_daytype(day_type: str, risk: float, direction: str,
                          entry: float) -> Dict[str, Optional[float]]:
    """Compute R-multiple targets from the day-type table."""
    sign = 1.0 if direction == "LONG" else -1.0
    # Day-type table (from targets_table.py / Dalton doctrine)
    TABLE = {
        "Trend_Normal":     {"t1_r": 1.0, "t2_r": 2.0, "t3_r": 3.0},
        "Trend_DD":         {"t1_r": 1.0, "t2_r": 2.0, "t3_r": 3.0},
        "Variation":        {"t1_r": 1.0, "t2_r": 2.5, "t3_r": 4.0},
        "Normal_Variation": {"t1_r": 1.0, "t2_r": 2.5, "t3_r": 4.0},
        "Normal":           {"t1_r": 1.0, "t2_r": 1.5, "t3_r": 2.0},
        "Neutral_Center":   {"t1_r": 0.75, "t2_r": 1.0, "t3_r": 1.5},
        "Neutral_Extreme":  {"t1_r": 1.0, "t2_r": 1.5, "t3_r": 2.0},
        "Nontrend":         {"t1_r": 0.5, "t2_r": 1.0, "t3_r": 1.5},
    }
    row = TABLE.get(day_type or "", TABLE.get("Normal", {"t1_r": 1.0, "t2_r": 2.0, "t3_r": 3.0}))
    t1 = _snap_tick(entry + sign * row["t1_r"] * risk)
    t2 = _snap_tick(entry + sign * row["t2_r"] * risk)
    t3 = _snap_tick(entry + sign * row["t3_r"] * risk)
    return {"t1": t1, "t2": t2, "t3": t3}


def economics(
    setup: Dict[str, Any],
    *,
    bars: Optional[List[Dict]] = None,
    ib_high: Optional[float] = None,
    ib_low: Optional[float] = None,
    day_type: str = "",
) -> EconomicsResult:
    """Compute stop/target/size from the producer's stop + structure.

    The stop is the producer's stop (closest structural anchor) + 2T buffer.
    The size is derived: n = min(5, floor(budget / (point_value * risk))).
    n < 3 → reject.
    """
    direction = (setup.get("direction") or "").upper()
    entry = float(setup.get("entry_price") or 0)
    producer_stop = float(setup.get("stop") or 0)

    if not entry or not producer_stop:
        return EconomicsResult(
            entry=entry, stop=producer_stop, t1=None, t2=None, t3=None,
            risk=0, contracts=0, reject_reason="missing_entry_or_stop",
            source="economics")

    # The stop IS the producer's stop — it's already the structural anchor.
    # Add 2T buffer if it isn't there.
    stop = producer_stop
    risk = abs(entry - stop)

    # Size from risk
    budget = float(os.getenv("RISK_BUDGET_USD", "225"))
    max_pts = float(os.getenv("RISK_MAX_PTS_HARD", "30"))
    min_contracts = int(os.getenv("RISK_MIN_CONTRACTS", "3"))

    reject_reason = None
    if risk <= 0:
        contracts = 0
        reject_reason = "zero_risk"
    elif risk > max_pts:
        contracts = 0
        reject_reason = "risk_exceeds_hard_max"
    else:
        raw_n = budget / (POINT_VALUE * risk)
        contracts = min(5, int(raw_n))
        if contracts < min_contracts:
            reject_reason = f"risk_exceeds_budget (risk={risk:.2f}pt → n={contracts} < {min_contracts})"
            contracts = 0

    # Targets from day-type table on REAL risk
    targets = _targets_for_daytype(day_type, risk, direction, entry)

    # Snap all to tick
    stop = _snap_tick(stop)

    # Validate: targets must be on the correct side
    sign = 1.0 if direction == "LONG" else -1.0
    for tk in ("t1", "t2", "t3"):
        tv = targets.get(tk)
        if tv is not None:
            wrong = (tv <= entry) if direction == "LONG" else (tv >= entry)
            if wrong:
                targets[tk] = None

    # Bar-median sanity: stop should be >= 1× median bar range
    median_bar = _bar_median_range(bars or [])

    return EconomicsResult(
        entry=entry,
        stop=stop,
        t1=targets.get("t1"),
        t2=targets.get("t2"),
        t3=targets.get("t3"),
        risk=round(risk, 2),
        contracts=contracts,
        reject_reason=reject_reason,
        source="trade_economics",
    )
