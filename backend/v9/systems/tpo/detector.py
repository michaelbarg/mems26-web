"""TPO Detector — Stages D-E of MEMS26_TPO_TREE_V2.

Stage D: Profile shape classification (8 shapes).
Stage E: Intent signals + OTF clarity inference.

Profile shapes (per Dalton / Mind Over Markets):
  D           — Normal Day: symmetric, POC mid
  WIDE_D      — Variation Day: spread out
  COMPACT_D   — Non-trend: tight range
  P           — Buy day: POC in upper third
  b           — Sell day: POC in lower third
  DOUBLE_DIST — Two distinct POC clusters
  THIN        — Trend day: narrow, elongated
  NEUTRAL     — Both extensions (upper + lower)
"""

from datetime import datetime
from typing import Optional
from .schemas import (
    TPOProfile, TPOConfig, ProfileShape, MigrationPattern,
    Intent, OTFClarity,
)


def classify_shape(
    profile: TPOProfile,
    config: TPOConfig,
    current_time: Optional[datetime] = None,
) -> TPOProfile:
    """Stage D1/D2: Classify profile shape from TPO distribution.

    Rules (simplified from spec, in priority order):
    1. THIN: range < IB width * 0.5 AND elongated (many letters, few per level)
    2. DOUBLE_DIST: two distinct POC clusters
    3. P: POC in upper 1/3 of range
    4. b: POC in lower 1/3 of range
    5. NEUTRAL: extensions both above and below IB
    6. WIDE_D: range > IB width * 2
    7. COMPACT_D: range < IB width * 1.2
    8. D: default (symmetric, POC near mid)
    """
    if not profile.levels or profile.poc is None:
        return profile

    sh = profile.session_high
    sl = profile.session_low
    if sh is None or sl is None or sh == sl:
        return profile

    total_range = sh - sl
    poc = profile.poc
    ib_width = profile.ib.width or total_range

    # Relative POC position: 0.0 = bottom, 1.0 = top
    poc_position = (poc - sl) / total_range

    # Average TPO count per level
    counts = [lvl.count for lvl in profile.levels.values()]
    avg_count = sum(counts) / len(counts) if counts else 0
    max_count = max(counts) if counts else 0

    # Check for double distribution (two peaks)
    is_double = _detect_double_distribution(profile, config)

    # Classify
    if avg_count <= 1.5 and len(profile.levels) > 8:
        shape = ProfileShape.THIN
        confidence = min(0.9, 0.6 + (1.5 - avg_count) * 0.3)
    elif is_double:
        shape = ProfileShape.DOUBLE_DIST
        confidence = 0.75
    elif poc_position > 0.67:
        shape = ProfileShape.P
        confidence = 0.5 + (poc_position - 0.67) * 1.5
    elif poc_position < 0.33:
        shape = ProfileShape.b
        confidence = 0.5 + (0.33 - poc_position) * 1.5
    elif _has_both_extensions(profile):
        shape = ProfileShape.NEUTRAL
        confidence = 0.7
    elif total_range > ib_width * 2:
        shape = ProfileShape.WIDE_D
        confidence = 0.7
    elif total_range < ib_width * 1.2:
        shape = ProfileShape.COMPACT_D
        confidence = 0.7
    else:
        shape = ProfileShape.D
        confidence = 0.8

    profile.shape = shape
    profile.shape_confidence = min(confidence, 1.0)

    return profile


def detect_intent(
    profile: TPOProfile,
    config: TPOConfig,
) -> TPOProfile:
    """Stage E1: Detect buyer/seller intent from tails and responsive activity."""
    buy_tail = profile.buying_tail_count >= config.tail_min_letters
    sell_tail = profile.selling_tail_count >= config.tail_min_letters

    if buy_tail and not sell_tail:
        profile.intent = Intent.BUYER
    elif sell_tail and not buy_tail:
        profile.intent = Intent.SELLER
    else:
        profile.intent = Intent.NONE

    return profile


def detect_migration_pattern(
    profile: TPOProfile,
    config: TPOConfig,
) -> TPOProfile:
    """Stage E2: Classify POC migration pattern."""
    hist = profile.poc_migration.history
    if len(hist) < 3:
        profile.migration_pattern = MigrationPattern.ROTATIONAL
        return profile

    # Net movement
    net = hist[-1] - hist[0]
    total_movement = sum(abs(hist[i] - hist[i - 1]) for i in range(1, len(hist)))
    avg_step = total_movement / (len(hist) - 1) if len(hist) > 1 else 0

    stuck = profile.poc_migration.stuck_count >= config.poc_stuck_letters

    if stuck:
        profile.migration_pattern = MigrationPattern.STUCK
    elif abs(net) > config.poc_migration_threshold * 3 and avg_step > config.poc_migration_threshold:
        profile.migration_pattern = MigrationPattern.ACCEPTED
    elif abs(net) < config.poc_migration_threshold and total_movement > config.poc_migration_threshold * 2:
        profile.migration_pattern = MigrationPattern.ROTATIONAL
    elif abs(net) > config.poc_migration_threshold and avg_step < config.poc_migration_threshold * 0.5:
        profile.migration_pattern = MigrationPattern.FAILED
    else:
        profile.migration_pattern = MigrationPattern.ROTATIONAL

    profile.poc_migration.pattern = profile.migration_pattern
    return profile


def infer_otf_clarity(
    profile: TPOProfile,
    config: TPOConfig,
) -> TPOProfile:
    """Stage E3: OTF Clarity inference from tails.

    Logic (from spec):
      buying_tail AND selling_tail → BOTH_CLEAR (all trades OK)
      selling_tail only           → SELLERS_CLEAR (LONG only)
      buying_tail only            → BUYERS_CLEAR (SHORT only)
      neither                     → UNCLEAR (no trades allowed)
    """
    buy_tail = profile.buying_tail_count >= config.tail_min_letters
    sell_tail = profile.selling_tail_count >= config.tail_min_letters

    if buy_tail and sell_tail:
        profile.otf_clarity = OTFClarity.BOTH_CLEAR
    elif sell_tail:
        profile.otf_clarity = OTFClarity.SELLERS_CLEAR
    elif buy_tail:
        profile.otf_clarity = OTFClarity.BUYERS_CLEAR
    else:
        profile.otf_clarity = OTFClarity.UNCLEAR

    return profile


def _detect_double_distribution(
    profile: TPOProfile,
    config: TPOConfig,
) -> bool:
    """Check for double distribution — two distinct high-volume clusters
    separated by a low-volume zone (LVN)."""
    if len(profile.levels) < 6:
        return False

    sorted_levels = sorted(profile.levels.values(), key=lambda x: x.price)
    counts = [lvl.count for lvl in sorted_levels]
    if not counts:
        return False

    avg = sum(counts) / len(counts)

    # Find valleys: consecutive levels below average
    in_valley = False
    valley_found = False
    peak_before = False

    for c in counts:
        if c >= avg * 1.3:
            if in_valley:
                valley_found = True
                break
            peak_before = True
        elif c < avg * 0.7 and peak_before:
            in_valley = True

    return valley_found


def _has_both_extensions(profile: TPOProfile) -> bool:
    """Check if profile extends both above and below IB."""
    if not profile.ib.locked or profile.ib.high is None or profile.ib.low is None:
        return False
    if profile.session_high is None or profile.session_low is None:
        return False

    above = profile.session_high > profile.ib.high
    below = profile.session_low < profile.ib.low
    return above and below
