"""LiveExecutor — real order execution stub.

LIVE mode: single slot, strict risk checks required.
Currently a stub — logs intent but does not connect to Sierra live account.
Full implementation deferred to post-DEMO validation.
"""

import logging

logger = logging.getLogger(__name__)


class LiveExecutor:
    """Execute a live trade: log intent, no Sierra connection yet."""

    def execute(self, trade: dict) -> dict:
        """Mark trade as live-executed (stub)."""
        trade["execution_status"] = "LIVE_STUB"
        logger.warning("[LiveExecutor] STUB: %s %s entry=%.2f — NOT sent to Sierra live",
                        trade["direction"],
                        trade.get("classification", ""),
                        trade.get("entry_price", 0))
        return trade
