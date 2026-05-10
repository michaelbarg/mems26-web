"""Shadow executor — paper-only, no Sierra orders, no caps, no slot limit.

Logs every setup to DB with mode='shadow'. Runs ALL setups from ALL
firing systems in parallel. No blocking, no rejection.
"""

import logging
from typing import Any, Dict

from backend.v9.services.trade_manager.manager import TradeManager

logger = logging.getLogger(__name__)


class ShadowExecutor:
    """Executes setups in SHADOW mode — paper-only, parallel, unlimited.

    No Sierra orders. No caps. No slot management.
    Every firing system's setup gets a shadow trade.
    """

    def __init__(self, trade_manager: TradeManager):
        self._trade_manager = trade_manager

    def execute(self, setup: Dict[str, Any]) -> int:
        """Create a shadow trade via W11 TradeManager.

        Args:
            setup: Trade setup dict from firing system.

        Returns:
            trade_id: The ID of the created shadow trade.
        """
        trade_id = self._trade_manager.accept_setup(setup, mode="shadow")
        logger.info(
            "SHADOW trade %d created: sys=%d dir=%s",
            trade_id,
            setup["firing_system"],
            setup["direction"],
        )
        return trade_id
