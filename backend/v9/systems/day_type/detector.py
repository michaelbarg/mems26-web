"""Day Type Engine — helper / detection functions."""

from __future__ import annotations
from typing import List, Optional, Tuple

from .schemas import (
    BarInput, OpeningType, IBWidth, Behavior, DayType,
    FailedExtensionType, RangeCategory,
)

# ── IB Width Classification ─────────────────────────────────────────────


def classify_ib_width(
    ib_range_pt: float,
    narrow_max: float = 15.0,
    medium_max: float = 25.0,
) -> IBWidth:
    """Classify IB range into NARROW / MEDIUM / WIDE.

    Args:
        ib_range_pt: IB range in points
        narrow_max: max width for NARROW (default 15.0 per spec)
        medium_max: max width for MEDIUM (default 25.0 per spec)
    """
    if ib_range_pt < narrow_max:
        return IBWidth.NARROW
    elif ib_range_pt <= medium_max:
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
        return OpeningType.OPEN_DRIVE, direction, 0.95

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


# ── CVD-Based Opening Detection (E2E 2/2 · flag S1_CVD_OPENING · shadow only) ──

from backend.v9.shared.atr import S1_CVD_OPENING  # noqa: E402

# Priors — to be calibrated during soak
_DRIVE_PE_THRESHOLD = 0.65       # PE_30 > 0.65 for DRIVE
_DRIVE_RANGE_EXP_MIN = 1.0      # range expansion > 1.0 for DRIVE
_AUCTION_NET_CVD_RATIO = 0.15   # |net_CVD|/total_vol < 0.15 for AUCTION
_AUCTION_PE_MAX = 0.25           # PE < 0.25 for AUCTION
_REJECTION_CVD_FLIP = True       # CVD sign flip required for REJECTION

# Gap classification tiers: gap/ATR14_daily
_GAP_TINY_MAX = 0.25
_GAP_SMALL_MAX = 0.50
_GAP_MEDIUM_MAX = 1.0


def classify_gap_atr(gap_size: float, atr_daily: Optional[float]) -> str:
    """Classify gap as Tiny/Small/Medium/Large relative to daily ATR.

    Returns gap tier string. Uses absolute fallback when ATR unavailable.
    """
    if atr_daily is None or atr_daily <= 0:
        # Fallback: absolute classification
        ag = abs(gap_size)
        if ag < 3.0:
            return "TINY"
        elif ag < 6.0:
            return "SMALL"
        elif ag < 12.0:
            return "MEDIUM"
        return "LARGE"

    ratio = abs(gap_size) / atr_daily
    if ratio < _GAP_TINY_MAX:
        return "TINY"
    elif ratio < _GAP_SMALL_MAX:
        return "SMALL"
    elif ratio < _GAP_MEDIUM_MAX:
        return "MEDIUM"
    return "LARGE"


def _compute_pe(deltas: List[float]) -> Optional[float]:
    """Participation Efficiency: net_CVD / sum(|delta|). None if no data."""
    if not deltas:
        return None
    total_abs = sum(abs(d) for d in deltas)
    if total_abs == 0:
        return None
    net = sum(deltas)
    return net / total_abs


def _detect_divergence(price_direction: float, cvd_direction: float) -> bool:
    """Price and CVD moving in opposite directions."""
    if price_direction == 0 or cvd_direction == 0:
        return False
    return (price_direction > 0) != (cvd_direction > 0)


def detect_opening_type_cvd(
    bars: List[BarInput],
    footprint_deltas: Optional[List[float]] = None,
    atr_daily: Optional[float] = None,
) -> Tuple[OpeningType, str, float, dict]:
    """CVD-enhanced opening type detection (two-stage model).

    When S1_CVD_OPENING is OFF, delegates to original detect_opening_type
    and returns empty shadow dict.

    When ON, computes PE/DE/divergence from footprint deltas and produces
    a shadow label alongside the original result.

    Args:
        bars: opening bars (BarInput list)
        footprint_deltas: per-bar delta values from v9_bars_footprint.delta,
                         reset-aware within session. None = no CVD data.
        atr_daily: ATR14 daily for gap classification. None = use absolute.

    Returns:
        (opening_type, direction, confidence, shadow_dict)
        shadow_dict contains CVD metrics when flag ON, empty when OFF.
    """
    # Original detection (always runs — this is the live path)
    original_ot, original_dir, original_conf = detect_opening_type(bars)

    if not S1_CVD_OPENING or footprint_deltas is None or len(footprint_deltas) < 2:
        return original_ot, original_dir, original_conf, {}

    # --- Shadow path: CVD analysis (flag ON, does NOT replace live result) ---
    pe = _compute_pe(footprint_deltas)
    net_cvd = sum(footprint_deltas) if footprint_deltas else 0.0
    total_vol = sum(abs(d) for d in footprint_deltas) if footprint_deltas else 0.0
    net_cvd_ratio = abs(net_cvd) / total_vol if total_vol > 0 else 0.0

    # Price direction from bars
    if bars:
        price_move = bars[-1].close - bars[0].open
    else:
        price_move = 0.0

    cvd_sign_flip = False
    if len(footprint_deltas) >= 3:
        first_half = sum(footprint_deltas[:len(footprint_deltas) // 2])
        second_half = sum(footprint_deltas[len(footprint_deltas) // 2:])
        cvd_sign_flip = (first_half > 0) != (second_half > 0)

    divergence = _detect_divergence(price_move, net_cvd)

    # Compute range expansion
    if bars:
        total_range = max(b.high for b in bars) - min(b.low for b in bars)
    else:
        total_range = 0.0

    # Shadow label
    shadow_label = "UNKNOWN"
    shadow_conf = 0.0

    if pe is not None and pe > _DRIVE_PE_THRESHOLD and total_range > 0 and not divergence:
        shadow_label = "DRIVE"
        shadow_conf = min(0.95, 0.7 + pe * 0.3)
    elif net_cvd_ratio < _AUCTION_NET_CVD_RATIO and (pe is None or abs(pe) < _AUCTION_PE_MAX):
        shadow_label = "AUCTION"
        shadow_conf = 0.5
    elif cvd_sign_flip and divergence:
        shadow_label = "REJECTION_REVERSE"
        shadow_conf = 0.6

    # Gap classification (separate dimension)
    gap_size = None
    gap_tier = None
    if bars and bars[0].pd_close is not None:
        gap_size = bars[0].open - bars[0].pd_close
        gap_tier = classify_gap_atr(gap_size, atr_daily)

    shadow = {
        "cvd_pe": round(pe, 4) if pe is not None else None,
        "cvd_net": round(net_cvd, 2),
        "cvd_net_ratio": round(net_cvd_ratio, 4),
        "cvd_sign_flip": cvd_sign_flip,
        "cvd_divergence": divergence,
        "shadow_label": shadow_label,
        "shadow_confidence": round(shadow_conf, 3),
        "gap_size": round(gap_size, 2) if gap_size is not None else None,
        "gap_tier": gap_tier,
        "original_label": original_ot.value,
        "original_confidence": round(original_conf, 3),
    }

    # Return original result (live path unchanged) + shadow for logging
    return original_ot, original_dir, original_conf, shadow


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
    news_event: bool = False,
) -> Tuple[bool, str]:
    """Check if a re-evaluation is needed after lock.

    Returns (should_reeval, reason).

    Triggers:
    1. Extreme move >3 ATR in <30 min
    2. Failed extension after lock
    3. Range exceeded for day type
    """
    # Trigger 1: scheduled news event after lock (FOMC/NFP/CPI)
    if news_event:
        return True, "news_event"

    # Trigger 2: extreme move
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
