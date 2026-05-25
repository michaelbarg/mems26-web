"""Day type targets verify — RiskRule wrapper (order=5, POST_TIGHTEN).

Delegates to the frozen layer4 service:
    backend.v9.services.layer4.day_type_targets_verify
Skip-logs when current_day_type is None.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.v9.services.layer4 import day_type_targets_verify
from backend.v9.services.trade_manager.rules.base import (
    POST_TIGHTEN,
    Layer4Context,
    RiskRule,
    log_skipped_rule,
    register_rule,
)


@register_rule(order=5)
class DayTypeTargetsVerifyRule(RiskRule):
    """Wrapper for day_type_targets_verify — POST_TIGHTEN phase, skip-logs on None."""

    name: str = "DAY_TYPE_TARGETS"
    phase: str = POST_TIGHTEN

    def evaluate(self, trade: dict, ctx: Layer4Context) -> Optional[Dict[str, Any]]:
        if ctx.current_day_type is None:
            log_skipped_rule(self.name, "current_day_type=None")
            return None
        return day_type_targets_verify.evaluate(trade, ctx.current_day_type)
