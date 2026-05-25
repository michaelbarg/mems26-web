"""3 tests for custom RiskRule registration — extensibility contract."""
from __future__ import annotations

from backend.v9.services.trade_manager.rules.base import (
    PRE_TIGHTEN,
    Layer4Context,
    RiskRule,
    get_registered_rules,
    register_rule,
    unregister_rule,
)


# ---------------------------------------------------------------------------
# Custom rule used across tests — NOT registered at module level
# ---------------------------------------------------------------------------
class CustomTightenRule(RiskRule):
    name = "_CUSTOM_FUTURE_STUB"
    phase = PRE_TIGHTEN

    def evaluate(self, trade: dict, ctx: Layer4Context):
        stop = trade.get("stop", 0)
        return {
            "action": "TIGHTEN_STOP",
            "rule": self.name,
            "new_stop": stop + 1.0,
        }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_register_custom_rule():
    """A third-party rule can be registered and retrieved via get_registered_rules()."""
    try:
        register_rule(order=50)(CustomTightenRule)
        names = [r.name for r in get_registered_rules()]
        assert "_CUSTOM_FUTURE_STUB" in names
    finally:
        unregister_rule(CustomTightenRule)


def test_custom_rule_participates_in_registry_loop():
    """Custom rule's evaluate() is reachable through get_registered_rules() iteration."""
    try:
        register_rule(order=50)(CustomTightenRule)
        trade_dict = {"direction": "LONG", "stop": 5000.0}
        ctx = Layer4Context()
        results = []
        for rule in get_registered_rules():
            if rule.name == "_CUSTOM_FUTURE_STUB":
                result = rule.evaluate(trade_dict, ctx)
                results.append(result)
        assert len(results) == 1
        assert results[0]["action"] == "TIGHTEN_STOP"
        assert results[0]["new_stop"] == 5001.0
    finally:
        unregister_rule(CustomTightenRule)


def test_unregister_custom_rule_is_idempotent():
    """unregister_rule(CustomTightenRule) can be called multiple times without error."""
    register_rule(order=50)(CustomTightenRule)
    unregister_rule(CustomTightenRule)
    # second call must not raise
    unregister_rule(CustomTightenRule)
    names = [r.name for r in get_registered_rules()]
    assert "_CUSTOM_FUTURE_STUB" not in names
