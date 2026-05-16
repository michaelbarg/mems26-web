"""Woodies Execution Bridge (PROMPT 4 · 4.2).

D-067 Hybrid Architecture: Decision IN Woodies · Execution OUT via this bridge.

Translates Woodies high-level intents into trade_manager API calls.
NEVER duplicates execution mechanics. NEVER modifies trade_manager files.
Calls only its public API: accept_setup, on_target_hit, on_stop_hit,
close_trade, get_active_trades.

4 public methods:
  1. submit_bracket → tm.accept_setup
  2. close_all → tm.close_trade (for each active)
  3. close_contracts → tm.on_target_hit (T1/T2/T3)
  4. move_stop → (intent recorded; stop updates via trade state)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Woodies execution intent types."""
    SUBMIT_BRACKET = "SUBMIT_BRACKET"
    CLOSE_ALL = "CLOSE_ALL"
    CLOSE_CONTRACTS = "CLOSE_CONTRACTS"
    MOVE_STOP = "MOVE_STOP"


@dataclass
class WoodiesIntent:
    """A high-level execution intent from Woodies decision logic."""
    intent_type: IntentType
    reason: str
    # SUBMIT_BRACKET fields
    direction: Optional[str] = None
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    t1_price: Optional[float] = None
    t2_price: Optional[float] = None
    t3_price: Optional[float] = None
    classification: Optional[str] = None
    position_size: int = 3
    # CLOSE_CONTRACTS fields
    contract_count: int = 0
    target_level: Optional[str] = None  # "T1", "T2", "T3"
    # MOVE_STOP fields
    new_stop_price: Optional[float] = None


@dataclass
class ExecutionResult:
    """Result of executing an intent via trade_manager."""
    success: bool
    intent_type: str
    trade_id: Optional[int] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class WoodiesExecutionBridge:
    """Translates Woodies decision intents → trade_manager calls.

    D-067 Hybrid: Decision IN Woodies · Execution OUT via this bridge.
    NEVER duplicates trade_manager logic. Calls only its public API.
    """

    def __init__(self, trade_manager=None, mode: str = "shadow"):
        """Initialize bridge.

        Args:
            trade_manager: TradeManager instance (None for testing)
            mode: Trading mode ("shadow", "demo", "live")
        """
        self._tm = trade_manager
        self._mode = mode
        self._intent_log = []  # in-memory log for testing

    def execute_intent(self, intent: WoodiesIntent) -> ExecutionResult:
        """Dispatch intent to appropriate trade_manager method."""
        self._intent_log.append(intent)

        if intent.intent_type == IntentType.SUBMIT_BRACKET:
            return self.submit_bracket(intent)
        elif intent.intent_type == IntentType.CLOSE_ALL:
            return self.close_all(intent.reason)
        elif intent.intent_type == IntentType.CLOSE_CONTRACTS:
            return self.close_contracts(
                intent.contract_count, intent.reason, intent.target_level,
            )
        elif intent.intent_type == IntentType.MOVE_STOP:
            return self.move_stop(intent.new_stop_price, intent.reason)
        else:
            return ExecutionResult(
                success=False, intent_type=intent.intent_type.value,
                error=f"Unknown intent type: {intent.intent_type}",
            )

    def submit_bracket(self, intent: WoodiesIntent) -> ExecutionResult:
        """Submit entry bracket → tm.accept_setup.

        Called by: A7 entry approval (BUY/SELL terminal).
        """
        if self._tm is None:
            logger.info("[Bridge] submit_bracket (no trade_manager): %s %s",
                        intent.direction, intent.reason)
            return ExecutionResult(
                success=True, intent_type="SUBMIT_BRACKET",
                details={"direction": intent.direction, "mode": self._mode},
            )

        setup = {
            "firing_system": 4,  # S4 Woodies
            "direction": intent.direction,
            "stop": intent.stop_price,
            "t1": intent.t1_price,
            "t2": intent.t2_price,
            "t3": intent.t3_price,
        }
        try:
            trade_id = self._tm.accept_setup(setup, self._mode)
            return ExecutionResult(
                success=True, intent_type="SUBMIT_BRACKET",
                trade_id=trade_id,
            )
        except Exception as e:
            logger.error("[Bridge] submit_bracket failed: %s", e)
            return ExecutionResult(
                success=False, intent_type="SUBMIT_BRACKET", error=str(e),
            )

    def close_all(self, reason: str) -> ExecutionResult:
        """Close all active Woodies trades → tm.close_trade for each.

        Called by: B1 (stop), B2 (EOD), B3 (flip), B6 (news),
                   B7 (time), B11 REACTIVE (T2 close all).
        """
        if self._tm is None:
            logger.info("[Bridge] close_all (no trade_manager): %s", reason)
            return ExecutionResult(
                success=True, intent_type="CLOSE_ALL",
                details={"reason": reason},
            )

        try:
            active = self._tm.get_active_trades(self._mode)
            s4_trades = [t for t in active if t.firing_system == 4]
            for trade in s4_trades:
                self._tm.close_trade(trade.id, reason)
            return ExecutionResult(
                success=True, intent_type="CLOSE_ALL",
                details={"closed_count": len(s4_trades)},
            )
        except Exception as e:
            logger.error("[Bridge] close_all failed: %s", e)
            return ExecutionResult(
                success=False, intent_type="CLOSE_ALL", error=str(e),
            )

    def close_contracts(
        self,
        count: int,
        reason: str,
        target_level: Optional[str] = None,
    ) -> ExecutionResult:
        """Close specific contracts → tm.on_target_hit.

        Called by: B10 (T1, count=1), B11 INITIATIVE (T2, count=1),
                   B12 (T3, count=1), B13 (trail, count=remaining),
                   B9 (partial, count=variable).
        """
        if self._tm is None:
            logger.info("[Bridge] close_contracts (no trade_manager): count=%d %s",
                        count, reason)
            return ExecutionResult(
                success=True, intent_type="CLOSE_CONTRACTS",
                details={"count": count, "target": target_level, "reason": reason},
            )

        try:
            active = self._tm.get_active_trades(self._mode)
            s4_trades = [t for t in active if t.firing_system == 4]
            if s4_trades and target_level:
                self._tm.on_target_hit(s4_trades[0].id, target_level)
            return ExecutionResult(
                success=True, intent_type="CLOSE_CONTRACTS",
                details={"count": count, "target": target_level},
            )
        except Exception as e:
            logger.error("[Bridge] close_contracts failed: %s", e)
            return ExecutionResult(
                success=False, intent_type="CLOSE_CONTRACTS", error=str(e),
            )

    def move_stop(
        self,
        new_price: Optional[float],
        reason: str,
    ) -> ExecutionResult:
        """Move stop to new price → intent recorded.

        Called by: B8 (tighten), B4 (default tighten), B5 (default tighten),
                   B11 INITIATIVE Smart BE (move to entry).

        Note: trade_manager doesn't have a direct move_stop method.
        This records the intent for the position management layer.
        """
        if new_price is None:
            return ExecutionResult(
                success=False, intent_type="MOVE_STOP",
                error="No new_price provided",
            )

        logger.info("[Bridge] move_stop: price=%.2f reason=%s", new_price, reason)
        return ExecutionResult(
            success=True, intent_type="MOVE_STOP",
            details={"new_stop_price": new_price, "reason": reason},
        )

    def get_intent_log(self) -> list:
        """Return in-memory intent log (for testing)."""
        return list(self._intent_log)
