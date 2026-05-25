"""CCI flat tighten — RiskRule wrapper (order=2, PRE_TIGHTEN).

Delegates to the frozen layer4 service: backend.v9.services.layer4.cci_flat_tighten
Skip-logs when cci_history is None.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.v9.services.layer4 import cci_flat_tighten
from backend.v9.services.trade_manager.rules.base import (
    PRE_TIGHTEN,
    Layer4Context,
    RiskRule,
    log_skipped_rule,
    register_rule,
)


@register_rule(order=2)
class CCIFlatRule(RiskRule):
    """Wrapper for cci_flat_tighten — skip-logs when cci_history is None."""

    name: str = "CCI_FLAT"
    phase: str = PRE_TIGHTEN

    def evaluate(self, trade: dict, ctx: Layer4Context) -> Optional[Dict[str, Any]]:
        if ctx.cci_history is None:
            log_skipped_rule(self.name, "cci_history=None")
            return None
        return cci_flat_tighten.evaluate(trade, ctx.cci_history)
