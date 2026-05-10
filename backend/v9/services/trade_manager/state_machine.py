"""Trade state machine — explicit transitions, invalid ones raise.

States: PENDING -> FILLED -> PARTIAL -> CLOSED
"""

from enum import Enum
from typing import Dict, FrozenSet


class TradeState(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CLOSED = "CLOSED"


class InvalidTransition(Exception):
    """Raised when a state transition is not allowed."""

    def __init__(self, from_state: TradeState, to_state: TradeState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition: {from_state.value} -> {to_state.value}"
        )


# Explicit transition table — anything not listed here is invalid
_VALID_TRANSITIONS: Dict[TradeState, FrozenSet[TradeState]] = {
    TradeState.PENDING: frozenset({TradeState.FILLED, TradeState.CLOSED}),
    TradeState.FILLED: frozenset({TradeState.PARTIAL, TradeState.CLOSED}),
    TradeState.PARTIAL: frozenset({TradeState.CLOSED}),
    TradeState.CLOSED: frozenset(),
}


class TradeStateMachine:
    """Manages state transitions for a single trade."""

    __slots__ = ("_state",)

    def __init__(self, initial: TradeState = TradeState.PENDING):
        self._state = initial

    @property
    def state(self) -> TradeState:
        return self._state

    def transition(self, to_state: TradeState) -> TradeState:
        """Transition to a new state. Raises InvalidTransition if not allowed."""
        if to_state not in _VALID_TRANSITIONS[self._state]:
            raise InvalidTransition(self._state, to_state)
        prev = self._state
        self._state = to_state
        return prev

    def can_transition(self, to_state: TradeState) -> bool:
        """Check if a transition is valid without performing it."""
        return to_state in _VALID_TRANSITIONS[self._state]

    @property
    def is_terminal(self) -> bool:
        return self._state == TradeState.CLOSED
