"""Live executor — Sierra live account, ONE slot, W14 risk checks first.

Routes to Sierra live account APEX-125218-13.
Runs W14 RiskValidator.check_setup() BEFORE creating trade.
Uses W11 TradeManager for lifecycle.
"""

import logging
from typing import Any, Dict, Tuple

from backend.v9.services.risk_validator.validator import (
    AccountState,
    RiskValidator,
)
from backend.v9.services.trade_manager.manager import TradeManager

logger = logging.getLogger(__name__)

# Sierra live account identifier
SIERRA_LIVE_ACCOUNT = "APEX-125218-13"


class LiveExecutor:
    """Executes setups in LIVE mode — Sierra live, risk-gated.

    Runs W14 risk checks before creating trade via W11.
    Caller (TradingGateway) manages slot locking.
    """

    def __init__(
        self,
        trade_manager: TradeManager,
        risk_validator: RiskValidator,
    ):
        self._trade_manager = trade_manager
        self._risk_validator = risk_validator

    def execute(
        self,
        setup: Dict[str, Any],
    ) -> Tuple[bool, int, str]:
        """Run W14 risk check, then create live trade if allowed.

        Args:
            setup: Trade setup dict from firing system.

        Returns:
            (allowed, trade_id_or_zero, rejection_reason_or_empty):
                allowed=True: trade created, trade_id set, reason empty.
                allowed=False: trade_id=0, reason explains rejection.
        """
        account_state = AccountState(mode="LIVE")

        allowed, rejection_reason = self._risk_validator.check_setup(
            setup, account_state
        )

        if not allowed:
            logger.warning(
                "LIVE rejected: sys=%d dir=%s reason=%s",
                setup["firing_system"],
                setup["direction"],
                rejection_reason,
            )
            return False, 0, rejection_reason or "rejected"

        trade_id = self._trade_manager.accept_setup(setup, mode="live")
        logger.info(
            "LIVE trade %d created: sys=%d dir=%s account=%s",
            trade_id,
            setup["firing_system"],
            setup["direction"],
            SIERRA_LIVE_ACCOUNT,
        )
        return True, trade_id, ""
