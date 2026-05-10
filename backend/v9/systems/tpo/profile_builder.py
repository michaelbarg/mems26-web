"""TPO Profile Builder — Stages A-C of MEMS26_TPO_TREE_V2.

Builds and maintains the TPO map as price data arrives.
Each 30-min period gets a letter (A-M, 13 slots for RTH 09:30-16:00).

Flow:
  1. init_profile()  — Stage A: create empty map
  2. add_price()     — Stage C: add price to current letter
  3. advance_letter() — Stage C1: move to next letter on 30-min boundary
  4. lock_ib()       — Stage C3: lock IB at 10:30

TPO map key format: price quantized to tick_size (0.25).
"""

from typing import Dict, Optional
from .schemas import (
    TPOLevel, TPOConfig, TPOProfile, InitialBalance,
    IBWidth, SessionState,
)
from . import levels as calc

# RTH letters: A=09:30, B=10:00, ... M=15:30 (13 periods)
LETTERS = "ABCDEFGHIJKLM"
MAX_LETTERS = len(LETTERS)


def _price_key(price: float, tick_size: float) -> str:
    """Quantize price to tick grid and return string key."""
    quantized = round(round(price / tick_size) * tick_size, 4)
    return f"{quantized:.4f}"


def init_profile(config: Optional[TPOConfig] = None) -> TPOProfile:
    """Stage A: Initialize empty TPO profile for new session."""
    return TPOProfile(
        session_state=SessionState.BUILDING,
        current_letter="A",
        letter_count=0,
        levels={},
    )


def add_price(
    profile: TPOProfile,
    price: float,
    config: TPOConfig,
) -> TPOProfile:
    """Stage C: Add a price tick to the current TPO letter.

    - Assigns price to current letter at quantized level
    - Updates session high/low
    - Updates IB if in A/B period and not locked
    """
    key = _price_key(price, config.tick_size)
    letter = profile.current_letter

    # Add to TPO map
    if key not in profile.levels:
        profile.levels[key] = TPOLevel(price=float(key))

    level = profile.levels[key]
    if letter not in level.letters:
        level.letters.append(letter)

    # Update session extremes
    if profile.session_high is None or price > profile.session_high:
        profile.session_high = price
    if profile.session_low is None or price < profile.session_low:
        profile.session_low = price

    # Update IB if in A/B period and not locked
    if not profile.ib.locked and letter in ("A", "B"):
        if profile.ib.high is None or price > profile.ib.high:
            profile.ib.high = price
        if profile.ib.low is None or price < profile.ib.low:
            profile.ib.low = price
        if profile.ib.high is not None and profile.ib.low is not None:
            profile.ib.width = profile.ib.high - profile.ib.low

    return profile


def advance_letter(
    profile: TPOProfile,
    config: TPOConfig,
) -> TPOProfile:
    """Stage C1: Advance to next TPO letter on 30-min boundary.

    Also triggers POC migration tracking (C6).
    """
    idx = LETTERS.index(profile.current_letter) if profile.current_letter in LETTERS else -1
    if idx < MAX_LETTERS - 1:
        profile.current_letter = LETTERS[idx + 1]
        profile.letter_count = idx + 2  # 1-based count

    # Track POC migration per letter (C6)
    poc_price, _ = calc.compute_poc(profile.levels)
    if poc_price is not None:
        profile.poc_migration.history.append(poc_price)
        _update_poc_migration(profile, poc_price, config)

    return profile


def lock_ib(
    profile: TPOProfile,
    config: TPOConfig,
) -> TPOProfile:
    """Stage C3: Lock IB at 10:30 ET and classify width."""
    profile.ib.locked = True
    w = profile.ib.width or 0.0
    if w < config.ib_width_narrow_max:
        profile.ib.classification = IBWidth.NARROW
    elif w > config.ib_width_wide_min:
        profile.ib.classification = IBWidth.WIDE
    else:
        profile.ib.classification = IBWidth.MEDIUM
    return profile


def refresh_levels(
    profile: TPOProfile,
    config: TPOConfig,
) -> TPOProfile:
    """Recompute all derived levels from current TPO map.

    Called after add_price or advance_letter.
    Covers Stages C4-C7.
    """
    # POC (SG1)
    poc_price, poc_count = calc.compute_poc(profile.levels)
    profile.poc = poc_price
    profile.poc_vol = poc_count

    # VAH/VAL (SG2/SG3)
    vah, val = calc.compute_value_area(profile.levels, poc_price, config)
    profile.vah = vah
    profile.val = val

    # C4: Single prints
    profile.single_prints = calc.compute_single_prints(profile.levels, config)

    # C5: Tails
    buy_tail, sell_tail = calc.compute_tails(
        profile.levels, profile.session_low, profile.session_high, config
    )
    profile.buying_tail_count = buy_tail
    profile.selling_tail_count = sell_tail

    # D3: HVN/LVN
    hvn, lvn = calc.compute_hvn_lvn(profile.levels, config)
    profile.hvn_prices = hvn
    profile.lvn_prices = lvn

    return profile


def _update_poc_migration(
    profile: TPOProfile,
    poc_price: float,
    config: TPOConfig,
) -> None:
    """Stage C6: Track POC migration velocity and stuck status."""
    hist = profile.poc_migration.history
    if len(hist) < 2:
        profile.poc_migration.velocity = 0.0
        profile.poc_migration.stuck_count = 1
        return

    # Velocity = average movement per letter
    deltas = [abs(hist[i] - hist[i - 1]) for i in range(1, len(hist))]
    profile.poc_migration.velocity = sum(deltas) / len(deltas) if deltas else 0.0

    # Stuck: consecutive letters at same price (within threshold)
    stuck = 1
    for i in range(len(hist) - 1, 0, -1):
        if abs(hist[i] - hist[i - 1]) <= config.poc_migration_threshold:
            stuck += 1
        else:
            break
    profile.poc_migration.stuck_count = stuck

    # Distance from open
    if profile.opening.open_price is not None:
        profile.poc_migration.distance_from_open = abs(
            poc_price - profile.opening.open_price
        )
