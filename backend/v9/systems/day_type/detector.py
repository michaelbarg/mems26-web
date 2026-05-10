"""Day Type Engine — helper / detection functions."""

from __future__ import annotations
from typing import List, Optional, Tuple

from .schemas import (
    BarInput, OpeningType, IBWidth, Behavior, DayType,
    FailedExtensionType, RangeCategory,
)

# ── IB Width Classification ─────────────────────────────────────────────

IB_NARROW_THRESHOLD = 15.0   # points
IB_WIDE_THRESHOLD = 20.0     # points


def classify_ib_width(ib_range_pt: float) -> IBWidth:
    """Classify IB range into NARROW / MEDIUM / WIDE."""
    if ib_range_pt < IB_NARROW_THRESHOLD:
        return IBWidth.NARROW
    elif ib_range_pt <= IB_WIDE_THRESHOLD:
        return IBWidth.MEDIUM
    else:
        return IBWidth.WIDE


# ── Opening Type Detection ───────────────────────────────────────────────

def detect_opening_type(bars: List[BarInput]) -> Tuple[OpeningType, str, float]:
    """Detect opening type from the first few bars after open.

    Returns (opening_type, drive_direction, confidence).

    Logic (simplified from Dalton):
    - OPEN_DRIVE: first 3 bars all move in same direction, no overlap
    - OPEN_TEST_DRIVE: initial move, pullback test, then drive
    - OPEN_REJECTION_REVERSE: initial move, then full reversal
    - OPEN_AUCTION_IN/OUT: rotational, no clear direction
    """
    if not bars or len(bars) < 2:
        return OpeningType.UNKNOWN, "NEUTRAL", 0.0

    first = bars[0]
    # Determine if opening is inside or outside prior day range
    is_outside = False
    if first.pd_high is not None and first.pd_low is not None:
        is_outside = first.open > first.pd_high or first.open < first.pd_low

    # Calculate net move from open through available bars
    opens = [b.open for b in bars]
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]

    net_move = closes[-1] - opens[0]
    total_range = max(highs) - min(lows)
    if total_range == 0:
        return OpeningType.OPEN_AUCTION_IN, "NEUTRAL", 0.3

    directional_ratio = abs(net_move) / total_range

    # Check for drive: strong directional move
    all_up = all(b.close >= b.open for b in bars)
    all_down = all(b.close <= b.open for b in bars)

    if directional_ratio >= 0.7 and (all_up or all_down):
        direction = "UP" if net_move > 0 else "DOWN"
        return OpeningType.OPEN_DRIVE, direction, min(0.9, directional_ratio)

    # Check for test-drive: pullback then continuation
    if len(bars) >= 3:
        first_move = closes[0] - opens[0]
        pullback = closes[1] - closes[0]
        continuation = closes[2] - closes[1]

        if first_move != 0 and pullback != 0:
            pullback_ratio = abs(pullback / first_move)
            same_dir = (first_move > 0 and continuation > 0) or (first_move < 0 and continuation < 0)
            opposite_pull = (first_move > 0 and pullback < 0) or (first_move < 0 and pullback > 0)

            if same_dir and opposite_pull and 0.2 <= pullback_ratio <= 0.6:
                direction = "UP" if first_move > 0 else "DOWN"
                return OpeningType.OPEN_TEST_DRIVE, direction, 0.7

    # Check for rejection-reverse: move then reversal
    if len(bars) >= 3:
        first_move = closes[0] - opens[0]
        last_move = closes[-1] - opens[0]

        if first_move != 0 and abs(last_move) > 0:
            reversed_dir = (first_move > 0 and last_move < 0) or (first_move < 0 and last_move > 0)
            if reversed_dir and abs(last_move) >= abs(first_move) * 0.5:
                direction = "UP" if last_move > 0 else "DOWN"
                return OpeningType.OPEN_REJECTION_REVERSE, direction, 0.65

    # Auction: rotational
    if is_outside:
        direction = "UP" if net_move > 0 else ("DOWN" if net_move < 0 else "NEUTRAL")
        return OpeningType.OPEN_AUCTION_OUT, direction, 0.5
    else:
        return OpeningType.OPEN_AUCTION_IN, "NEUTRAL", 0.4


# ── Behavior Detection ──────────────────────────────────────────────────

def detect_behavior(
    extensions_up: int,
    extensions_down: int,
    returned_to_range: bool,
    range_ratio: float,
) -> Behavior:
    """Detect mid-day behavior from extension/range data.

    Args:
        extensions_up: count of extensions above IB high
        extensions_down: count of extensions below IB low
        returned_to_range: whether price returned after extending
        range_ratio: current range / ATR
    """
    if returned_to_range and (extensions_up > 0 or extensions_down > 0):
        return Behavior.FAILED_EXTENSION

    if range_ratio < 0.7:
        return Behavior.COMPRESSED

    if extensions_up > 0 and extensions_down == 0:
        return Behavior.TRENDING_UP

    if extensions_down > 0 and extensions_up == 0:
        return Behavior.TRENDING_DOWN

    return Behavior.DEVELOPING


# ── Failed Extension Detection ──────────────────────────────────────────

def detect_failed_extension(
    extensions_up: int,
    extensions_down: int,
    returned_to_range: bool,
    current_price: float,
    ib_high: float,
    ib_low: float,
) -> FailedExtensionType:
    """Detect failed extension type.

    A 'strong failed' occurs when price extends beyond IB, then returns
    fully inside. 'Double failed' means both sides failed.
    """
    if not returned_to_range:
        return FailedExtensionType.NONE

    in_range = ib_low <= current_price <= ib_high

    failed_up = extensions_up > 0 and in_range
    failed_down = extensions_down > 0 and in_range

    if failed_up and failed_down:
        return FailedExtensionType.DOUBLE_FAILED
    elif failed_up:
        return FailedExtensionType.STRONG_FAILED_UP
    elif failed_down:
        return FailedExtensionType.STRONG_FAILED_DOWN

    return FailedExtensionType.NONE


# ── Range / ATR Comparison ──────────────────────────────────────────────

def classify_range(current_range: float, atr: float) -> RangeCategory:
    """Classify current range relative to ATR."""
    if atr <= 0:
        return RangeCategory.NORMAL

    ratio = current_range / atr

    if ratio < 0.7:
        return RangeCategory.COMPRESSED
    elif ratio <= 1.3:
        return RangeCategory.NORMAL
    elif ratio < 2.0:
        return RangeCategory.EXPANDED
    else:
        return RangeCategory.EXTREME


# ── Confidence Calculation ───────────────────────────────────────────────

def calculate_confidence(
    vote_history: list,
    behavior_agrees: bool,
    range_aligned: bool,
) -> float:
    """Calculate confidence score for the current day-type vote.

    Components:
    - Vote stability: how many consecutive same votes (max +0.40)
    - Behavior agreement: does mid-day behavior match vote? (+0.30)
    - Range alignment: does range/ATR category fit? (+0.20)
    - Base: minimum confidence (+0.10)

    Returns 0.0-1.0.
    """
    if not vote_history:
        return 0.1

    # Base
    conf = 0.10

    # Vote stability: count consecutive same votes from end
    last_type = vote_history[-1]
    consecutive = 0
    for v in reversed(vote_history):
        if v == last_type:
            consecutive += 1
        else:
            break

    stability_score = min(consecutive / 5.0, 1.0) * 0.40
    conf += stability_score

    # Behavior agreement
    if behavior_agrees:
        conf += 0.30

    # Range alignment
    if range_aligned:
        conf += 0.20

    return min(conf, 1.0)


# ── Re-eval Triggers ────────────────────────────────────────────────────

def check_reeval_triggers(
    locked_day_type: DayType,
    range_ratio: float,
    move_in_30min: Optional[float] = None,
    atr: Optional[float] = None,
    failed_extension_after_lock: bool = False,
    expected_range_exceeded: bool = False,
) -> Tuple[bool, str]:
    """Check if a re-evaluation is needed after lock.

    Returns (should_reeval, reason).

    Triggers:
    1. Extreme move >3 ATR in <30 min
    2. Failed extension after lock
    3. Range exceeded for day type
    """
    # Trigger 1: extreme move
    if move_in_30min is not None and atr is not None and atr > 0:
        if abs(move_in_30min) > 3.0 * atr:
            return True, "extreme_move_3atr"

    # Trigger 2: failed extension after lock
    if failed_extension_after_lock:
        return True, "failed_extension_post_lock"

    # Trigger 3: beyond expected range
    if expected_range_exceeded:
        return True, "range_exceeded_for_type"

    return False, ""
