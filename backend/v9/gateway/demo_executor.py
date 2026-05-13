"""DemoExecutor — simulated execution stub.

DEMO mode: single slot, one trade at a time.
Currently a stub — logs intent but does not connect to Sierra demo account.
Full implementation deferred to post-SHADOW activation.
"""

import logging

logger = logging.getLogger(__name__)


class DemoExecutor:
    """Execute a demo trade: log intent, no Sierra connection yet."""

    def execute(self, trade: dict) -> dict:
        """Mark trade as demo-executed (stub)."""
        trade["execution_status"] = "DEMO_STUB"
        logger.info("[DemoExecutor] STUB: %s %s entry=%.2f — not sent to Sierra demo",
                     trade["direction"],
                     trade.get("classification", ""),
                     trade.get("entry_price", 0))
        return trade
