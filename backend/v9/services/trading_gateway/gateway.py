"""W13 Trading Gateway — 3-mode routing layer.

Routes setups from firing systems (1, 2, 4) to three independent layers:
  SHADOW: parallel, no caps, no slot limit — runs ALL setups
  DEMO:   ONE slot, first-wins, Sierra demo account PA-APEX-125218-01
  LIVE:   ONE slot, first-wins + W14 risk caps, Sierra live account APEX-125218-13

Per spec Section 8 pseudo-code:
  1. Always create SHADOW trade (parallel, no blocking)
  2. Check DEMO slot: if empty -> create DEMO trade via W11
  3. Check LIVE slot: if empty -> run W14.check_setup(); if allowed -> create LIVE trade
"""

import logging
import threading
from typing import Any, Dict, List, Optional

from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.risk_validator.validator import RiskValidator
from backend.v9.services.trading_gateway.executors.shadow import ShadowExecutor
from backend.v9.services.trading_gateway.executors.demo import DemoExecutor
from backend.v9.services.trading_gateway.executors.live import LiveExecutor

logger = logging.getLogger(__name__)

# Valid firing systems per SKILL
FIRING_SYSTEMS = frozenset({1, 2, 4})

# Maximum shadow trades kept in memory before oldest are dropped.
# Prevents unbounded growth. Closed shadow trades are in DB regardless.
MAX_SHADOW_HISTORY = 500


class TradingGateway:
    """Routes setups from firing systems to SHADOW/DEMO/LIVE executors.

    SHADOW: parallel, unlimited — every setup gets a shadow trade.
    DEMO:   one slot, first system to fire wins, locked until close.
    LIVE:   one slot, first-wins + W14 risk validation before entry.
    """

    def __init__(
        self,
        trade_manager: TradeManager,
        risk_validator: RiskValidator,
        demo_enabled: bool = True,
        live_enabled: bool = False,
    ):
        self._trade_manager = trade_manager
        self._risk_validator = risk_validator
        self._demo_enabled = demo_enabled
        self._live_enabled = live_enabled

        # Executors
        self._shadow_executor = ShadowExecutor(trade_manager)
        self._demo_executor = DemoExecutor(trade_manager)
        self._live_executor = LiveExecutor(trade_manager, risk_validator)

        # Slot management — thread-safe for concurrent system fires
        self._lock = threading.Lock()
        self._demo_slot: Optional[int] = None  # trade_id or None
        self._live_slot: Optional[int] = None  # trade_id or None

        # Shadow trade history — bounded ring buffer
        self._shadow_trade_ids: List[int] = []

    def route_setup(
        self,
        setup: Dict[str, Any],
        system_id: int,
    ) -> Dict[str, Any]:
        """Route a setup from a firing system to all enabled layers.

        Per spec Section 8:
          1. ALWAYS create SHADOW trade (parallel, no blocking)
          2. Check DEMO slot: if empty -> create via W11; if occupied -> skip
          3. Check LIVE slot: if empty -> W14 check -> create via W11; if occupied -> skip

        Args:
            setup: Trade setup dict (firing_system, direction, stop, t1, t2, t3).
            system_id: The firing system ID (1, 2, or 4).

        Returns:
            Dict with keys:
              shadow_trade_id: int (always present)
              demo_trade_id: int or None
              live_trade_id: int or None
              rejections: list of dicts with mode and reason
        """
        if system_id not in FIRING_SYSTEMS:
            raise ValueError(f"Invalid system_id: {system_id}. Must be one of {sorted(FIRING_SYSTEMS)}")

        result: Dict[str, Any] = {
            "shadow_trade_id": 0,
            "demo_trade_id": None,
            "live_trade_id": None,
            "rejections": [],
        }

        # 1. ALWAYS create SHADOW trade — parallel, no blocking
        shadow_id = self._shadow_executor.execute(setup)
        result["shadow_trade_id"] = shadow_id
        self._record_shadow(shadow_id)

        # 2. Check DEMO slot
        if self._demo_enabled:
            with self._lock:
                if self._demo_slot is None:
                    demo_id = self._demo_executor.execute(setup)
                    self._demo_slot = demo_id
                    result["demo_trade_id"] = demo_id
                else:
                    result["rejections"].append({
                        "mode": "demo",
                        "reason": f"DEMO slot occupied by trade {self._demo_slot}",
                    })
                    logger.info(
                        "DEMO rejected for sys=%d: slot occupied by trade %d",
                        system_id, self._demo_slot,
                    )

        # 3. Check LIVE slot
        if self._live_enabled:
            with self._lock:
                if self._live_slot is None:
                    allowed, trade_id, reason = self._live_executor.execute(setup)
                    if allowed:
                        self._live_slot = trade_id
                        result["live_trade_id"] = trade_id
                    else:
                        result["rejections"].append({
                            "mode": "live",
                            "reason": reason,
                        })
                else:
                    result["rejections"].append({
                        "mode": "live",
                        "reason": f"LIVE slot occupied by trade {self._live_slot}",
                    })
                    logger.info(
                        "LIVE rejected for sys=%d: slot occupied by trade %d",
                        system_id, self._live_slot,
                    )

        logger.info(
            "route_setup complete: sys=%d shadow=%d demo=%s live=%s rejections=%d",
            system_id,
            result["shadow_trade_id"],
            result["demo_trade_id"],
            result["live_trade_id"],
            len(result["rejections"]),
        )
        return result

    def get_slot_status(self) -> Dict[str, Any]:
        """Return current slot status for DEMO and LIVE.

        Returns:
            Dict with demo and live slot info:
              demo: {occupied: bool, trade_id: int or None}
              live: {occupied: bool, trade_id: int or None}
        """
        with self._lock:
            return {
                "demo": {
                    "occupied": self._demo_slot is not None,
                    "trade_id": self._demo_slot,
                },
                "live": {
                    "occupied": self._live_slot is not None,
                    "trade_id": self._live_slot,
                },
            }

    def release_slot(self, mode: str, trade_id: int) -> bool:
        """Release a slot when a trade closes.

        Called by trade lifecycle events (W11 on_trade_close callback).

        Args:
            mode: "demo" or "live".
            trade_id: The trade ID occupying the slot.

        Returns:
            True if slot was released, False if trade_id did not match.
        """
        if mode not in ("demo", "live"):
            raise ValueError(f"Invalid mode for slot release: {mode}. Must be 'demo' or 'live'")

        with self._lock:
            if mode == "demo":
                if self._demo_slot == trade_id:
                    self._demo_slot = None
                    logger.info("DEMO slot released: trade %d", trade_id)
                    return True
                logger.warning(
                    "DEMO slot release mismatch: expected %s, got %d",
                    self._demo_slot, trade_id,
                )
                return False
            else:  # live
                if self._live_slot == trade_id:
                    self._live_slot = None
                    logger.info("LIVE slot released: trade %d", trade_id)
                    return True
                logger.warning(
                    "LIVE slot release mismatch: expected %s, got %d",
                    self._live_slot, trade_id,
                )
                return False

    def _record_shadow(self, trade_id: int) -> None:
        """Track shadow trade ID — bounded to prevent unbounded growth."""
        self._shadow_trade_ids.append(trade_id)
        if len(self._shadow_trade_ids) > MAX_SHADOW_HISTORY:
            # Drop oldest entries
            self._shadow_trade_ids = self._shadow_trade_ids[-MAX_SHADOW_HISTORY:]
