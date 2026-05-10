"""W15 Active Trade Manager — real-time monitoring of open trades.

Watches FILLED and PARTIAL trades, computes unrealized PnL,
emits proximity alerts, triggers Smart BE on T1 hit.
"""

from .monitor import ActiveTradeMonitor
from .alerts import AlertEmitter

__all__ = [
    "ActiveTradeMonitor",
    "AlertEmitter",
]
