"""TCCI cross exit — RiskRule wrapper (order=3, PRE_TIGHTEN).

Delegates to the frozen layer4 service: backend.v9.services.layer4.tcci_cross_exit
No skip log — the layer4 service handles None direction_change_event gracefully.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.v9.services.layer4 import tcci_cross_exit
from backend.v9.services.trade_manager.rules.base import (
    PRE_TIGHTEN,
    Layer4Context,
    RiskRule,
    register_rule,
)


@register_rule(order=3)
class TCCIExitRule(RiskRule):
    """Wrapper for tcci_cross_exit — layer4 handles None internally."""

    name: str = "TCCI_CROSS"
    phase: str = PRE_TIGHTEN

    def evaluate(self, trade: dict, ctx: Layer4Context) -> Optional[Dict[str, Any]]:
        return tcci_cross_exit.evaluate(trade, ctx.direction_change_event)
