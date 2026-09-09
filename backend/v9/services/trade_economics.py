"""trade_economics — single authority for stop/target/size.

Michael ruling 09.09: "מיקום הסטופ ייצר כמה שפחות נזק, אבל מנגד
צריך למקם אותו במקום מבני כדי שלא סתם ייפרץ."

    economics(setup, intent, cross_context, bars) → EconomicsResult

Stops from structural anchors via intent.stop_rule.
Targets from day-type table + structural levels via intent.target_rule.
Size derived: n = min(5, floor(225/(5×risk))), n<3 → reject.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TICK = 0.25
POINT_VALUE = 5.0  # MES
STOP_OFFSET_TICKS = 16  # 16T = 4pt buffer


def enabled() -> bool:
    v = os.getenv("TRADE_ECONOMICS_AUTHORITY_V1", "0").strip().lower()
    return v in ("1", "diff", "true", "yes")


def is_diff() -> bool:
    return os.getenv("TRADE_ECONOMICS_AUTHORITY_V1", "0").strip().lower() == "diff"


def _snap(price: float) -> float:
    return round(round(price / TICK) * TICK, 2)


@dataclass
class EconomicsResult:
    entry: float
    stop: Optional[float]
    t1: Optional[float]
    t2: Optional[float]
    t3: Optional[float]
    risk: float
    contracts: int
    reject_reason: Optional[str]
    stop_rule: Optional[str]
    target_rule: Optional[str]
    source: str = "trade_economics"


def _resolve_stop(
    setup: Dict, stop_rule: Optional[str], entry: float, direction: str,
    cross_context: Optional[Dict] = None,
) -> Optional[float]:
    """Resolve stop from intent.stop_rule to a price level."""
    if not stop_rule:
        return None
    sign = 1.0 if direction == "LONG" else -1.0
    offset = STOP_OFFSET_TICKS * TICK  # 4pt
    cc = cross_context or {}
    tpo = cc.get("tpo_system") if isinstance(cc, dict) else {}
    if not isinstance(tpo, dict):
        tpo = {}
    meta = setup.get("metadata") if isinstance(setup.get("metadata"), dict) else {}

    anchor = None

    if stop_rule == "BEYOND_OPEN":
        # Session open price
        _open = meta.get("session_open") or tpo.get("session_open")
        if _open:
            anchor = float(_open)

    elif stop_rule == "BEYOND_REJECTED_EXTREME":
        # The extreme of the rejection bar / producer's initial stop
        _si = meta.get("stop_initial") or setup.get("stop")
        if _si:
            anchor = float(_si)

    elif stop_rule == "BEYOND_FAILED_SIDE":
        # IB edge that was tested and failed
        if direction == "LONG":
            anchor = float(tpo["ib_low"]) if tpo.get("ib_low") else None
        else:
            anchor = float(tpo["ib_high"]) if tpo.get("ib_high") else None

    elif stop_rule == "BEYOND_LEG_EXTREME":
        # Leg extreme from the producer
        _sa = setup.get("stop_anchor") or meta.get("stop_anchor")
        if _sa:
            anchor = float(_sa)
        else:
            # Fallback: producer's stop
            _ps = setup.get("stop")
            if _ps:
                anchor = float(_ps)

    elif stop_rule == "BEYOND_IB_EDGE":
        if direction == "LONG":
            anchor = float(tpo["ib_low"]) if tpo.get("ib_low") else None
        else:
            anchor = float(tpo["ib_high"]) if tpo.get("ib_high") else None

    if anchor is None:
        return None

    # Stop = anchor + offset in the stop direction (away from entry)
    stop = anchor - sign * offset if direction == "LONG" else anchor + abs(sign) * offset
    # For LONG: stop is BELOW entry, anchor is below entry, stop = anchor - offset
    # For SHORT: stop is ABOVE entry, anchor is above entry, stop = anchor + offset
    if direction == "LONG":
        stop = _snap(anchor - offset)
    else:
        stop = _snap(anchor + offset)

    return stop


def _resolve_targets(
    target_rule: Optional[str], entry: float, risk: float, direction: str,
    day_type: str, cross_context: Optional[Dict] = None,
) -> Dict[str, Optional[float]]:
    """Resolve targets from intent.target_rule."""
    sign = 1.0 if direction == "LONG" else -1.0
    cc = cross_context or {}
    tpo = cc.get("tpo_system") if isinstance(cc, dict) else {}
    if not isinstance(tpo, dict):
        tpo = {}

    if target_rule == "POC":
        poc = tpo.get("poc")
        if poc:
            t1 = _snap(float(poc))
            t2 = _snap(entry + sign * 2.0 * risk)
            t3 = _snap(entry + sign * 3.0 * risk)
            return {"t1": t1, "t2": t2, "t3": t3}

    elif target_rule == "OPPOSITE_EDGE":
        vah = tpo.get("vah")
        val = tpo.get("val")
        ibh = tpo.get("ib_high")
        ibl = tpo.get("ib_low")
        if direction == "LONG":
            t1 = _snap(float(vah)) if vah else (_snap(float(ibh)) if ibh else None)
        else:
            t1 = _snap(float(val)) if val else (_snap(float(ibl)) if ibl else None)
        t2 = _snap(entry + sign * 2.0 * risk) if risk > 0 else None
        t3 = _snap(entry + sign * 3.0 * risk) if risk > 0 else None
        return {"t1": t1, "t2": t2, "t3": t3}

    elif target_rule == "CENTER":
        ibh = tpo.get("ib_high")
        ibl = tpo.get("ib_low")
        if ibh and ibl:
            t1 = _snap((float(ibh) + float(ibl)) / 2.0)
            t2 = _snap(entry + sign * 2.0 * risk) if risk > 0 else None
            return {"t1": t1, "t2": t2, "t3": None}
        return {"t1": None, "t2": None, "t3": None}

    elif target_rule == "MEASURED_MOVE":
        ibh = tpo.get("ib_high")
        ibl = tpo.get("ib_low")
        if ibh and ibl:
            ib_range = float(ibh) - float(ibl)
            if direction == "LONG":
                t1 = _snap(float(ibh) + ib_range)
            else:
                t1 = _snap(float(ibl) - ib_range)
            t2 = _snap(entry + sign * 2.0 * risk) if risk > 0 else None
            t3 = _snap(entry + sign * 3.0 * risk) if risk > 0 else None
            return {"t1": t1, "t2": t2, "t3": t3}

    # S1_TABLE or fallback: R-multiple from day-type
    TABLE = {
        "Trend_Normal":     {"t1_r": 1.0, "t2_r": 2.0, "t3_r": 3.0},
        "Trend_DD":         {"t1_r": 1.0, "t2_r": 2.0, "t3_r": 3.0},
        "Variation":        {"t1_r": 1.0, "t2_r": 2.5, "t3_r": 4.0},
        "Normal_Variation": {"t1_r": 1.0, "t2_r": 2.5, "t3_r": 4.0},
        "Normal":           {"t1_r": 1.0, "t2_r": 1.5, "t3_r": 2.0},
        "Neutral_Center":   {"t1_r": 0.75, "t2_r": 1.0, "t3_r": 1.5},
        "Neutral_Extreme":  {"t1_r": 1.0, "t2_r": 1.5, "t3_r": 2.0},
    }
    row = TABLE.get(day_type, {"t1_r": 1.0, "t2_r": 2.0, "t3_r": 3.0})
    if risk <= 0:
        return {"t1": None, "t2": None, "t3": None}
    return {
        "t1": _snap(entry + sign * row["t1_r"] * risk),
        "t2": _snap(entry + sign * row["t2_r"] * risk),
        "t3": _snap(entry + sign * row["t3_r"] * risk),
    }


def economics(
    setup: Dict[str, Any],
    *,
    intent_stop_rule: Optional[str] = None,
    intent_target_rule: Optional[str] = None,
    day_type: str = "",
    cross_context: Optional[Dict] = None,
    bars: Optional[List[Dict]] = None,
) -> EconomicsResult:
    """Compute stop/target/size from structural anchors."""
    direction = (setup.get("direction") or "").upper()
    entry = float(setup.get("entry_price") or 0)

    if not entry:
        return EconomicsResult(
            entry=entry, stop=None, t1=None, t2=None, t3=None,
            risk=0, contracts=0, reject_reason="missing_entry",
            stop_rule=intent_stop_rule, target_rule=intent_target_rule)

    # Resolve stop from structural anchor
    stop = _resolve_stop(setup, intent_stop_rule, entry, direction, cross_context)

    if stop is None:
        return EconomicsResult(
            entry=entry, stop=None, t1=None, t2=None, t3=None,
            risk=0, contracts=0, reject_reason="no_anchor",
            stop_rule=intent_stop_rule, target_rule=intent_target_rule)

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
        reject_reason = f"risk_exceeds_hard_max ({risk:.2f}pt > {max_pts})"
    else:
        raw_n = budget / (POINT_VALUE * risk)
        contracts = min(5, int(raw_n))
        if contracts < min_contracts:
            reject_reason = f"risk_exceeds_budget (risk={risk:.2f}pt → n={contracts} < {min_contracts})"
            contracts = 0

    # Targets from rule
    targets = _resolve_targets(
        intent_target_rule, entry, risk, direction, day_type, cross_context)

    # Validate: targets must be on correct side
    for tk in ("t1", "t2", "t3"):
        tv = targets.get(tk)
        if tv is not None:
            wrong = (tv <= entry) if direction == "LONG" else (tv >= entry)
            if wrong:
                targets[tk] = None

    return EconomicsResult(
        entry=entry, stop=stop,
        t1=targets.get("t1"), t2=targets.get("t2"), t3=targets.get("t3"),
        risk=round(risk, 2), contracts=contracts,
        reject_reason=reject_reason,
        stop_rule=intent_stop_rule, target_rule=intent_target_rule)
