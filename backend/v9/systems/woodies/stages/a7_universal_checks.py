"""Stage A7 — Universal Pre-Entry Checks (PROMPT 3 · 3.3).

Purpose: Final non-Woodies-specific safety checks before entry execution.
Reference: Decision Tree V1 § Section 4 · A7
Type: Woodies Core (independent decision)
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# D-001: stop distance limits
STOP_MIN_PT = 3.0
STOP_MAX_PT = 8.0

# Daily loss cap
DAILY_LOSS_CAP_USD = 200.0

# News window buffer
NEWS_WINDOW_MINUTES = 5

# Minimum time before EOD to allow new entry
MIN_EOD_DISTANCE_MINUTES = 60


@dataclass
class A7Output:
    """A7 stage output."""
    entry_approved: bool
    skip_reason: Optional[str]  # reason enum if not approved


class A7UniversalChecks:
    """Stage A7 — Universal Pre-Entry Checks.

    Runs safety checks before entry execution:
      - news_window_check (±5min)
      - cool_down_active (30min after stop)
      - daily_loss_cap_hit ($200)
      - stop_within_3_to_8_pts (D-001 cap)
      - bridge_status == healthy
      - eod_distance > 60min

    Terminal states:
      SKIP — universal block (with reason)
      BUY (LONG) — if direction == LONG and all pass
      SELL (SHORT) — if direction == SHORT and all pass
    """

    def evaluate(
        self,
        direction: str,
        news_calendar: Optional[dict] = None,
        cool_down_state: bool = False,
        daily_pnl: float = 0.0,
        proposed_stop_pts: float = 5.0,
        bridge_health: bool = True,
        time_to_eod_minutes: float = 120.0,
    ) -> A7Output:
        """Evaluate universal checks per Decision Tree V1 § A7.

        All checks must pass. Any failure → SKIP with reason.
        """
        # Check 1: news window
        if news_calendar:
            minutes_to_news = news_calendar.get("minutes_to_next_tier1", 999)
            if abs(minutes_to_news) <= NEWS_WINDOW_MINUTES:
                return A7Output(entry_approved=False, skip_reason="NEWS_WINDOW")

        # Check 2: cool-down active
        if cool_down_state:
            return A7Output(entry_approved=False, skip_reason="COOL_DOWN_ACTIVE")

        # Check 3: daily loss cap
        if daily_pnl <= -DAILY_LOSS_CAP_USD:
            return A7Output(entry_approved=False, skip_reason="DAILY_LOSS_CAP")

        # Check 4: stop distance (D-001)
        if proposed_stop_pts < STOP_MIN_PT or proposed_stop_pts > STOP_MAX_PT:
            return A7Output(entry_approved=False, skip_reason="STOP_OUT_OF_RANGE")

        # Check 5: bridge health
        if not bridge_health:
            return A7Output(entry_approved=False, skip_reason="BRIDGE_UNHEALTHY")

        # Check 6: EOD distance
        if time_to_eod_minutes < MIN_EOD_DISTANCE_MINUTES:
            return A7Output(entry_approved=False, skip_reason="TOO_CLOSE_TO_EOD")

        # All checks passed
        return A7Output(entry_approved=True, skip_reason=None)
