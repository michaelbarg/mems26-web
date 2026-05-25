"""SWI tighten — RiskRule wrapper (order=4, PRE_TIGHTEN).

Delegates to the frozen layer4 service: backend.v9.services.layer4.swi_tighten
Skip-logs when swi is None.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.v9.services.layer4 import swi_tighten
from backend.v9.services.trade_manager.rules.base import (
    PRE_TIGHTEN,
    Layer4Context,
    RiskRule,
    log_skipped_rule,
    register_rule,
)


@register_rule(order=4)
class SWITightenRule(RiskRule):
    """Wrapper for swi_tighten — skip-logs when swi is None."""

    name: str = "SWI"
    phase: str = PRE_TIGHTEN

    def evaluate(self, trade: dict, ctx: Layer4Context) -> Optional[Dict[str, Any]]:
        if ctx.swi is None:
            log_skipped_rule(self.name, "swi=None")
            return None
        return swi_tighten.evaluate(trade, ctx.swi)
