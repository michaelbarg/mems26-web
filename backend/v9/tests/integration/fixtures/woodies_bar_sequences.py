"""Synthetic bar sequences for Woodies E2E tests (PROMPT 4 · 4.3).

Generates WoodiesBar lists for 5 E2E scenarios.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

from backend.v9.systems.woodies.schemas import WoodiesBar


def generate_trend_blue_sequence(bars=30, base_price=7400.0):
    """Scenario 1: CCI sustained positive (BLUE trend) → ZLR pattern.

    30 bars with CCI > 0, creating BLUE color for strategic gate.
    At least 1 bar exceeds CCI > +200 (Liran Stage-1 requirement per W-6).
    """
    result = []
    for i in range(bars):
        cci = 50 + (i * 2)  # steadily rising CCI above zero
        # Ensure at least 1 bar crosses +200 for Stage-1 validity
        if i == bars - 2:
            cci = max(cci, 210)
        result.append(WoodiesBar(
            ts=1000.0 + i * 1800,
            open=base_price + i * 0.5,
            high=base_price + i * 0.5 + 3,
            low=base_price + i * 0.5 - 2,
            close=base_price + i * 0.5 + 1,
            cci_14=cci,
            cci_6_tcci=cci * 0.9,
            ema_34=base_price + i * 0.3,
            trend_state="BLUE",
        ))
    return result


def generate_trend_red_sequence(bars=30, base_price=7400.0):
    """Scenario 2: CCI sustained negative (RED trend).

    30 bars with CCI < 0, creating RED color.
    """
    result = []
    for i in range(bars):
        cci = -50 - (i * 2)
        result.append(WoodiesBar(
            ts=1000.0 + i * 1800,
            open=base_price - i * 0.5,
            high=base_price - i * 0.5 + 2,
            low=base_price - i * 0.5 - 3,
            close=base_price - i * 0.5 - 1,
            cci_14=cci,
            cci_6_tcci=cci * 0.9,
            ema_34=base_price - i * 0.3,
            trend_state="RED",
        ))
    return result


def generate_color_flip_sequence(bars=20, base_price=7400.0):
    """Scenario 3: Starts BLUE, flips to RED mid-sequence."""
    result = []
    for i in range(bars):
        if i < 10:
            cci = 50 + i * 3  # BLUE first half
            trend = "BLUE"
        else:
            cci = -(i - 9) * 15  # Sharp RED flip
            trend = "RED"
        result.append(WoodiesBar(
            ts=1000.0 + i * 1800,
            open=base_price,
            high=base_price + 3,
            low=base_price - 3,
            close=base_price + (1 if cci > 0 else -1),
            cci_14=cci,
            cci_6_tcci=cci * 0.8,
            trend_state=trend,
        ))
    return result


def generate_news_window_sequence(bars=10, base_price=7400.0):
    """Scenario 4: Normal bars (trade active, news imminent)."""
    return generate_trend_blue_sequence(bars=bars, base_price=base_price)


def generate_eod_sequence(bars=10, base_price=7400.0):
    """Scenario 5: Normal bars (trade active near EOD)."""
    return generate_trend_blue_sequence(bars=bars, base_price=base_price)
