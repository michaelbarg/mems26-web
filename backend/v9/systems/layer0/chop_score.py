"""ChopScoreComputer — 6 indicators per Constitution V3 Layer 0.

Reads from existing systems to compute:
  1. vegas_flips_60m — count of bull/bear flips in last 60min
  2. cci_zl_crossings_30m — CCI14 zero-line crossings in last 30min
  3. poc_migration_stuck — true if POC hasn't moved >0.5pt for >5min 🟡 default
  4. ib_breakouts_recent — bars exceeding IB-H or IB-L in last 30min 🟡 default
  5. range_atr_ratio — current range / ATR14 🟡 default
  6. poc_vwap_distance — abs(poc_vol - vwap) in pts

Composite score: weighted blend 🟡 default weights, to-calibrate-in-SHADOW.
"""

import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger("mems26.layer0.chop_score")

API = "http://localhost:8000"
# 🟡 default thresholds — to-calibrate-in-SHADOW
POC_STUCK_MINUTES = 5
ATR_PERIOD = 14
IB_BREAKOUT_WINDOW_MIN = 30
# 🟡 default composite weights
WEIGHTS = {
    "vegas_flips_60m": 0.15,
    "cci_zl_crossings_30m": 0.20,
    "poc_migration_stuck": 0.15,
    "ib_breakouts_recent": 0.15,
    "range_atr_ratio": 0.20,
    "poc_vwap_distance": 0.15,
}


def _fetch_json(endpoint: str, default=None):
    try:
        r = requests.get(f"{API}{endpoint}", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return default


def compute_vegas_flips_60m() -> int:
    """Count bull/bear trend flips in TPO sessions over last 60min."""
    data = _fetch_json("/api/v9/woodies/signals", {"entries": []})
    entries = data.get("entries", [])
    if not entries:
        return 0
    # Count direction changes in recent signals
    flips = 0
    prev_dir = None
    for e in entries[-30:]:
        d = e.get("direction", "")
        if d and d != prev_dir:
            if prev_dir is not None:
                flips += 1
            prev_dir = d
    return flips


def compute_cci_zl_crossings_30m() -> int:
    """Count CCI14 zero-line crossings in last 30min."""
    data = _fetch_json("/api/v9/woodies/signals", {"entries": []})
    entries = data.get("entries", [])
    crossings = 0
    prev_cci = None
    for e in entries[-15:]:
        cci = e.get("cci_14")
        if cci is not None and prev_cci is not None:
            if (prev_cci < 0 and cci >= 0) or (prev_cci >= 0 and cci < 0):
                crossings += 1
        prev_cci = cci
    return crossings


def compute_poc_migration_stuck() -> bool:
    """True if POC hasn't moved >0.5pt in recent polls."""
    tpo = _fetch_json("/api/v9/tpo/current", {})
    migration = tpo.get("poc_migration")
    if isinstance(migration, dict):
        return migration.get("direction") == "STUCK"
    if isinstance(migration, str):
        return migration == "STUCK"
    return False


def compute_ib_breakouts_recent() -> int:
    """Count bars that exceeded IB-H or IB-L recently. 🟡 default window: 30min."""
    tpo = _fetch_json("/api/v9/tpo/current", {})
    ib_h = tpo.get("ib_high")
    ib_l = tpo.get("ib_low")
    if ib_h is None or ib_l is None:
        return 0
    # Check recent bars against IB
    bars = _fetch_json("/api/v9/chart/bars5min?limit=6", [])
    if not isinstance(bars, list):
        return 0
    count = 0
    for b in bars:
        if b.get("h", 0) > ib_h or b.get("l", float("inf")) < ib_l:
            count += 1
    return count


def compute_range_atr_ratio() -> float:
    """Current session range / ATR14. 🟡 default ATR period: 14."""
    bars = _fetch_json("/api/v9/chart/bars5min?limit=14", [])
    if not isinstance(bars, list) or len(bars) < 2:
        return 1.0
    ranges = [b.get("h", 0) - b.get("l", 0) for b in bars]
    atr = sum(ranges) / len(ranges) if ranges else 1.0
    current_range = ranges[-1] if ranges else 0
    return round(current_range / atr, 3) if atr > 0 else 1.0


def compute_poc_vwap_distance() -> float:
    """abs(POC - VWAP) in points."""
    tpo = _fetch_json("/api/v9/tpo/current", {})
    poc = tpo.get("poc")
    # VWAP not directly available yet — use VAH/VAL midpoint as proxy 🟡
    vah = tpo.get("vah")
    val = tpo.get("val")
    if poc is None:
        return 0.0
    if vah is not None and val is not None:
        vwap_proxy = (vah + val) / 2
        return round(abs(poc - vwap_proxy), 2)
    return 0.0


def compute_composite(indicators: dict) -> float:
    """Weighted composite score 0-100. 🟡 default weights."""
    score = 0.0
    # Normalize each to 0-1 range
    # vegas_flips: more = choppier. Cap at 10.
    score += min(indicators.get("vegas_flips_60m", 0) / 10, 1.0) * WEIGHTS["vegas_flips_60m"]
    # cci crossings: more = choppier. Cap at 8.
    score += min(indicators.get("cci_zl_crossings_30m", 0) / 8, 1.0) * WEIGHTS["cci_zl_crossings_30m"]
    # poc stuck: binary
    score += (1.0 if indicators.get("poc_migration_stuck") else 0.0) * WEIGHTS["poc_migration_stuck"]
    # ib breakouts: more = trending. Invert for chop.
    ib = indicators.get("ib_breakouts_recent", 0)
    score += max(0, 1.0 - ib / 4) * WEIGHTS["ib_breakouts_recent"]
    # range/atr: < 0.8 = chop, > 1.2 = trending
    ratio = indicators.get("range_atr_ratio", 1.0)
    score += max(0, 1.0 - ratio) * WEIGHTS["range_atr_ratio"] if ratio < 1.2 else 0
    # poc-vwap distance: small = chop
    dist = indicators.get("poc_vwap_distance", 0)
    score += max(0, 1.0 - dist / 5) * WEIGHTS["poc_vwap_distance"]

    return round(score * 100, 1)


def classify_state(chop_score: float) -> str:
    """4-state classifier per Constitution V3 D-044.

    >=75 → SEARCHING (high chop — no directional signal)
    50-74 → RESPECTING (mid chop — levels holding)
    25-49 → EXPANDING (low chop — range expanding, trending)
    <25  → FOUND (clean directional move)
    """
    if chop_score >= 75:
        return "SEARCHING"
    elif chop_score >= 50:
        return "RESPECTING"
    elif chop_score >= 25:
        return "EXPANDING"
    else:
        return "FOUND"


def get_chop_score() -> dict:
    """Compute all 6 indicators + composite score + 4-state."""
    indicators = {
        "vegas_flips_60m": compute_vegas_flips_60m(),
        "cci_zl_crossings_30m": compute_cci_zl_crossings_30m(),
        "poc_migration_stuck": compute_poc_migration_stuck(),
        "ib_breakouts_recent": compute_ib_breakouts_recent(),
        "range_atr_ratio": compute_range_atr_ratio(),
        "poc_vwap_distance": compute_poc_vwap_distance(),
    }
    score = compute_composite(indicators)
    return {
        "chop_score": score,
        "state": classify_state(score),
        "indicators": indicators,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
