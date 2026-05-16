"""Demo executor — Sierra demo account, ONE slot, first-wins.

Routes to Sierra demo account PA-APEX-125218-01.
Uses W11 TradeManager for lifecycle. No risk caps.
"""

import logging
from typing import Any, Dict

from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.sierra_command import command_from_setup

logger = logging.getLogger(__name__)

# Sierra demo account identifier
SIERRA_DEMO_ACCOUNT = "PA-APEX-125218-01"


class DemoExecutor:
    """Executes setups in DEMO mode — Sierra demo, one slot.

    Creates trade via W11 TradeManager with mode='demo'.
    Caller (TradingGateway) manages slot locking.
    """

    def __init__(self, trade_manager: TradeManager):
        self._trade_manager = trade_manager

    def execute(self, setup: Dict[str, Any]) -> int:
        """Create a demo trade via W11 TradeManager.

        Args:
            setup: Trade setup dict from firing system.

        Returns:
            trade_id: The ID of the created demo trade.
        """
        trade_id = self._trade_manager.accept_setup(setup, mode="demo")
        command_from_setup(
            setup,
            trade_id=str(trade_id),
            account=SIERRA_DEMO_ACCOUNT,
            mode="demo",
        )
        logger.info(
            "DEMO trade %d created: sys=%d dir=%s account=%s",
            trade_id,
            setup["firing_system"],
            setup["direction"],
            SIERRA_DEMO_ACCOUNT,
        )
        return trade_id
