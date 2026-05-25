"""MFE Peak tighten — RiskRule wrapper (order=1, PRE_TIGHTEN).

Delegates to the frozen layer4 service: backend.v9.services.layer4.mfe_peak_tighten
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.v9.services.layer4 import mfe_peak_tighten
from backend.v9.services.trade_manager.rules.base import (
    PRE_TIGHTEN,
    Layer4Context,
    RiskRule,
    register_rule,
)


@register_rule(order=1)
class MFETightenRule(RiskRule):
    """Wrapper for mfe_peak_tighten — no skip log (always runs)."""

    name: str = "MFE_PEAK"
    phase: str = PRE_TIGHTEN

    def evaluate(self, trade: dict, ctx: Layer4Context) -> Optional[Dict[str, Any]]:
        return mfe_peak_tighten.evaluate(trade)
