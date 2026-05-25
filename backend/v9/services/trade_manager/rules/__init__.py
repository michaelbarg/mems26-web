"""RiskRule registry public API — S2_TRADEMGR_HOOKS_V1 §2.6.

Importing this package auto-registers the 5 built-in rules in order 1-5.
"""
from backend.v9.services.trade_manager.rules.base import (
    Layer4Context,
    PRE_TIGHTEN,
    POST_TIGHTEN,
    RiskRule,
    _REGISTRY,
    _skip_limiter,
    get_registered_rules,
    log_skipped_rule,
    register_rule,
    unregister_rule,
)

# Auto-import the 5 built-in wrappers so they self-register on package load.
# Import ORDER matters — matches D-094 §3.B.3 evaluation order.
from backend.v9.services.trade_manager.rules import mfe_peak       # noqa: F401  order=1
from backend.v9.services.trade_manager.rules import cci_flat        # noqa: F401  order=2
from backend.v9.services.trade_manager.rules import tcci_cross      # noqa: F401  order=3
from backend.v9.services.trade_manager.rules import swi             # noqa: F401  order=4
from backend.v9.services.trade_manager.rules import day_type_targets  # noqa: F401  order=5

__all__ = [
    "Layer4Context",
    "PRE_TIGHTEN",
    "POST_TIGHTEN",
    "RiskRule",
    "get_registered_rules",
    "log_skipped_rule",
    "register_rule",
    "unregister_rule",
    "_REGISTRY",
    "_skip_limiter",
]
