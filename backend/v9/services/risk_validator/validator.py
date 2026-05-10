"""W14 Risk Validator — enforces LIVE mode risk caps.

Per 3-Mode Trading Spec V3 Section 5:
- SHADOW and DEMO modes: always allowed, no caps.
- LIVE mode: strict gating in this order:
  1. Time filter (no new trades after 14:30 ET)
  2. News window (FOMC/CPI/NFP +/-10 min)
  3. Daily loss cap ($250)
  4. Max trades/day (5)
  5. Consecutive losses (2 -> STOP DAY)
  6. Position size (max 2 contracts)
  7. Manual override (required for size > standard)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional, Tuple

import pytz

from backend.v9.services.risk_validator.news_calendar import is_in_news_window

ET = pytz.timezone("US/Eastern")

# --- LIVE mode caps (spec Section 5) ---
DAILY_LOSS_CAP_USD = 250.0
MAX_TRADES_PER_DAY = 5
MAX_POSITION_SIZE = 2
CUTOFF_TIME_ET = time(14, 30)
CONSECUTIVE_LOSS_LIMIT = 2
STANDARD_SIZE = 1  # contracts; size > standard requires manual override


@dataclass
class AccountState:
    """Snapshot of account state passed into check_setup."""

    mode: str  # "SHADOW", "DEMO", "LIVE"
    requested_size: int = 1  # contracts requested for this setup
    manual_override: bool = False  # True if operator approved non-standard size


@dataclass
class RiskValidator:
    """Validates trade setups against LIVE mode risk caps.

    SHADOW and DEMO modes bypass all checks.
    LIVE mode runs checks in spec-defined gating order.
    """

    daily_trades_count: int = 0
    daily_loss_usd: float = 0.0
    consecutive_losses: int = 0
    _stopped_for_day: bool = False
    _trade_results: dict = field(default_factory=dict)

    def check_setup(
        self,
        setup: dict,
        account_state: AccountState,
        now_et: datetime | None = None,
    ) -> tuple[bool, str | None]:
        """Run all risk checks against a proposed setup.

        Args:
            setup: Trade setup dict (must contain at least 'system_id', 'direction').
            account_state: Current account state including mode.
            now_et: Current time in ET (injected for testing). If None, uses wall clock.

        Returns:
            (allowed, rejection_reason) — allowed=True means trade can proceed.
            SHADOW and DEMO always return (True, None).
        """
        mode = account_state.mode.upper()

        # SHADOW and DEMO bypass all risk checks
        if mode in ("SHADOW", "DEMO"):
            return True, None

        if mode != "LIVE":
            return False, f"Unknown mode: {mode}"

        if now_et is None:
            now_et = datetime.now(ET)

        # --- Gating order per spec Section 5 ---

        # 1. Time filter
        if now_et.time() >= CUTOFF_TIME_ET:
            return False, f"After {CUTOFF_TIME_ET.strftime('%H:%M')} ET cutoff"

        # 2. News window
        blocked, event_desc = is_in_news_window(now_et)
        if blocked:
            return False, f"News block: {event_desc}"

        # 3. Daily loss cap
        if self.daily_loss_usd >= DAILY_LOSS_CAP_USD:
            return False, f"Daily loss cap reached: ${self.daily_loss_usd:.2f} >= ${DAILY_LOSS_CAP_USD:.2f}"

        # 4. Max trades/day
        if self.daily_trades_count >= MAX_TRADES_PER_DAY:
            return False, f"Max trades/day reached: {self.daily_trades_count} >= {MAX_TRADES_PER_DAY}"

        # 5. Consecutive losses -> STOP DAY
        if self._stopped_for_day:
            return False, f"Day stopped: {self.consecutive_losses} consecutive losses"
        if self.consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
            self._stopped_for_day = True
            return False, f"Consecutive loss limit: {self.consecutive_losses} >= {CONSECUTIVE_LOSS_LIMIT}"

        # 6. Position size
        requested_size = account_state.requested_size
        if requested_size > MAX_POSITION_SIZE:
            return False, f"Size {requested_size} exceeds max {MAX_POSITION_SIZE} contracts"

        # 7. Manual override required for non-standard size
        if requested_size > STANDARD_SIZE and not account_state.manual_override:
            return False, f"Size {requested_size} > standard ({STANDARD_SIZE}): manual override required"

        return True, None

    def record_trade_result(self, trade_id: str, pnl_usd: float) -> None:
        """Record a completed trade result and update daily state.

        Args:
            trade_id: Unique trade identifier.
            pnl_usd: Realized PnL in USD (negative = loss).
        """
        self._trade_results[trade_id] = pnl_usd
        self.daily_trades_count += 1

        if pnl_usd < 0:
            self.daily_loss_usd += abs(pnl_usd)
            self.consecutive_losses += 1
            if self.consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
                self._stopped_for_day = True
        else:
            self.consecutive_losses = 0

    def daily_reset(self) -> None:
        """Reset all daily counters. Called at midnight ET."""
        self.daily_trades_count = 0
        self.daily_loss_usd = 0.0
        self.consecutive_losses = 0
        self._stopped_for_day = False
        self._trade_results.clear()
