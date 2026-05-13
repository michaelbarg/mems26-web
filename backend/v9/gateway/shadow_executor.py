"""ShadowExecutor — persists trade record only, no Sierra order.

SHADOW mode is always active and unlimited. Every setup from any firing system
gets a shadow trade recorded for post-session analysis.
"""

import logging

logger = logging.getLogger(__name__)


class ShadowExecutor:
    """Execute a shadow trade: persist to DB, no real order."""

    def execute(self, trade: dict) -> dict:
        """Mark trade as shadow-executed. Persistence handled by TradingGateway."""
        trade["execution_status"] = "SHADOW_RECORDED"
        logger.info("[ShadowExecutor] recorded: %s %s entry=%.2f",
                     trade["direction"],
                     trade.get("classification", ""),
                     trade.get("entry_price", 0))
        return trade
