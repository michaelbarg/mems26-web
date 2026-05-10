"""W11 Trade Manager — trade lifecycle: entry -> bracket -> exit.

NOT a decision maker. Receives setup objects from firing systems,
manages state transitions, emits events. Each firing system makes
its own entry decision independently.
"""

from .manager import TradeManager
from .state_machine import TradeStateMachine, TradeState, InvalidTransition
from .events import TradeEventEmitter

__all__ = [
    "TradeManager",
    "TradeStateMachine",
    "TradeState",
    "InvalidTransition",
    "TradeEventEmitter",
]
