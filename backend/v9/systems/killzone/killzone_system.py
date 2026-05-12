"""System 6 — Killzone Time-Based Observer (STANDALONE).

Does NOT consume bars. Ticks every 30s via asyncio scheduler.
Publishes zone transitions on change.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pytz

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from .definitions import current_killzone, next_killzone

logger = logging.getLogger(__name__)
ET = pytz.timezone('America/New_York')


class KillzoneSystem(BaseV9TradingSystem):
    system_id = 6
    name = "killzone"
    color = "#14b8a6"
    system_type = SystemType.OBSERVING

    def __init__(self):
        self._last_zone_name: Optional[str] = None
        self._last_transition_ts: Optional[str] = None
        self.current_state = {
            "running": False,
            "hydrated": False,
            "current_zone": {},
            "next_zone": {},
            "last_transition_ts": None,
        }

    def subscribed_bar_types(self) -> List[str]:
        return []  # Killzone does NOT consume bars

    def hydrate(self) -> HydrationResult:
        now_et = datetime.now(ET)
        cz = current_killzone(now_et)
        nz = next_killzone(now_et)
        self._last_zone_name = cz["name"]
        self.current_state.update({
            "running": True,
            "hydrated": True,
            "current_zone": cz,
            "next_zone": nz,
        })
        return HydrationResult(
            success=True,
            reached_state=cz["name"],
            confidence=1.0,
            notes=f"Killzone active: {cz['name']} ({cz['edge_class']})",
        )

    def process(self, event: Dict) -> Optional[Dict]:
        return None

    async def process_bar(self, event) -> None:
        pass  # Killzone does not consume bars

    async def tick(self) -> None:
        """Called every 30s by scheduler. Recomputes zone, detects transitions."""
        try:
            now_et = datetime.now(ET)
            cz = current_killzone(now_et)
            nz = next_killzone(now_et)

            # Detect transition
            if cz["name"] != self._last_zone_name:
                logger.info(
                    "[Killzone] Transition: %s -> %s (edge=%s)",
                    self._last_zone_name, cz["name"], cz["edge_class"]
                )
                self._last_zone_name = cz["name"]
                self._last_transition_ts = now_et.isoformat()

            self.current_state.update({
                "current_zone": cz,
                "next_zone": nz,
                "last_transition_ts": self._last_transition_ts,
            })
        except Exception as e:
            logger.error(f"KillzoneSystem.tick error: {e}", exc_info=True)

    def get_current(self) -> dict:
        return dict(self.current_state)
