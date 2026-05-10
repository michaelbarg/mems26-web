"""W12 quality scoring dimensions for V9 trades.

Each dimension returns 0.0-1.0. compute_grade() aggregates
dimensions into a letter grade (A/B/C/D).

ANALYTICAL only — does NOT gate trades.
"""

from datetime import time
from typing import Any, Dict, Optional


# ── Killzone quality mapping (ET hours) ──────────────────────────
# Maps zone quality tier to timing score.
# HIGH zones = best entries, full score.
# Based on backend/v9/systems/killzone/zones.py definitions.

_KILLZONE_TIERS = [
    # (start_et, end_et, quality_score)
    (time(5, 0), time(9, 30), 0.2),     # PRE_MARKET — LOW
    (time(9, 30), time(9, 45), 0.5),     # NY_OPEN_VOLATILITY — MEDIUM
    (time(9, 45), time(10, 30), 1.0),    # NY_OPEN_IB — HIGH
    (time(10, 30), time(11, 30), 1.0),   # NY_PRIME — HIGH
    (time(11, 30), time(12, 0), 0.5),    # PRE_LUNCH — MEDIUM
    (time(12, 0), time(13, 0), 0.2),     # LUNCH — LOW
    (time(13, 0), time(14, 0), 0.5),     # PM_RECOVERY — MEDIUM
    (time(14, 0), time(15, 0), 1.0),     # PM_PRIME — HIGH
    (time(15, 0), time(15, 45), 0.5),    # CLOSE_APPROACH — MEDIUM
    (time(15, 45), time(16, 0), 0.2),    # CLOSE_FINAL — LOW
]

# After-hours (16:00-05:00) gets 0.0
_AFTER_HOURS_SCORE = 0.0


def timing_quality(entry_hour: int, entry_minute: int) -> float:
    """Score based on whether entry happened during a high-quality killzone.

    Args:
        entry_hour: Hour in ET (0-23).
        entry_minute: Minute in ET (0-59).

    Returns:
        0.0-1.0 score. HIGH killzones = 1.0, LOW = 0.2, OFF = 0.0.
    """
    entry_time = time(entry_hour, entry_minute)

    for start, end, score in _KILLZONE_TIERS:
        if start <= entry_time < end:
            return score

    # Outside all defined tiers (after-hours)
    return _AFTER_HOURS_SCORE


def execution_quality(
    entry_price: float,
    expected_price: Optional[float],
    stop_price: float,
) -> float:
    """Score based on slippage vs expected entry price.

    Slippage measured as fraction of risk (entry-to-stop distance).
    Zero slippage = 1.0, slippage >= risk = 0.0.

    Args:
        entry_price: Actual fill price.
        expected_price: Signal price at entry time. If None, returns 1.0
            (no expected price means no slippage measurable).
        stop_price: Stop loss price for risk distance calculation.

    Returns:
        0.0-1.0 score.
    """
    if expected_price is None:
        return 1.0

    risk_distance = abs(expected_price - stop_price)
    if risk_distance == 0.0:
        return 1.0

    slippage = abs(entry_price - expected_price)
    slippage_ratio = slippage / risk_distance

    # Linear decay: 0 slippage = 1.0, slippage >= risk = 0.0
    score = max(0.0, 1.0 - slippage_ratio)
    return round(score, 4)


def outcome_quality(outcome: str, exit_reason: Optional[str]) -> float:
    """Score based on trade outcome.

    WIN with full target (T3) = 1.0.
    WIN with partial = 0.75.
    BE = 0.5.
    LOSS at full stop = 0.0.

    Args:
        outcome: "WIN", "LOSS", or "BE".
        exit_reason: How the trade exited (T3_HIT, STOP_HIT, manual, etc.).

    Returns:
        0.0-1.0 score.
    """
    if outcome == "WIN":
        if exit_reason == "T3_HIT":
            return 1.0
        return 0.75
    elif outcome == "BE":
        return 0.5
    elif outcome == "LOSS":
        return 0.0
    # Unknown outcome — should not happen on completed trades
    return 0.0


def context_quality(cross_context: Optional[Dict[str, Any]]) -> float:
    """Score based on cross-system agreement at entry time.

    Reads the cross_context JSON field from V9Trade.
    Each system's stance is scored: bullish/bearish agreement = 1.0,
    neutral = 0.5, disagreement = 0.0.

    Args:
        cross_context: Dict like {"sys2": "bullish", "sys4": "neutral"}.

    Returns:
        0.0-1.0 average score across observer systems.
    """
    if not cross_context:
        return 0.5  # No context recorded = neutral score

    stance_scores = {
        "bullish": 1.0,
        "bearish": 1.0,
        "neutral": 0.5,
    }

    scores = []
    for _sys_key, stance in cross_context.items():
        if isinstance(stance, str):
            scores.append(stance_scores.get(stance.lower(), 0.0))
        elif isinstance(stance, dict):
            # Nested context: {"direction": "bullish", ...}
            direction = stance.get("direction", "")
            scores.append(stance_scores.get(str(direction).lower(), 0.0))

    if not scores:
        return 0.5

    return round(sum(scores) / len(scores), 4)


# ── Grade computation ────────────────────────────────────────────

# Dimension weights for weighted average
_WEIGHTS = {
    "timing": 0.20,
    "execution": 0.25,
    "outcome": 0.35,
    "context": 0.20,
}


def compute_grade(dimensions: Dict[str, float]) -> str:
    """Compute letter grade from dimension scores.

    Weighted average:
        A >= 0.8, B >= 0.6, C >= 0.4, D < 0.4

    Args:
        dimensions: Dict with keys timing, execution, outcome, context.
            Each value 0.0-1.0.

    Returns:
        'A', 'B', 'C', or 'D'.
    """
    weighted_sum = 0.0
    total_weight = 0.0

    for dim_name, weight in _WEIGHTS.items():
        if dim_name in dimensions:
            weighted_sum += dimensions[dim_name] * weight
            total_weight += weight

    if total_weight == 0.0:
        return "D"

    avg = weighted_sum / total_weight

    if avg >= 0.8:
        return "A"
    elif avg >= 0.6:
        return "B"
    elif avg >= 0.4:
        return "C"
    else:
        return "D"
