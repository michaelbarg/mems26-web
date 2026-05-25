"""10 tests for the RiskRule registry (base.py)."""
from __future__ import annotations

import pytest

from backend.v9.services.trade_manager.rules.base import (
    PRE_TIGHTEN,
    Layer4Context,
    RiskRule,
    _REGISTRY,
    get_registered_rules,
    register_rule,
    unregister_rule,
)


# ---------------------------------------------------------------------------
# Helper concrete rules used only within this test module
# ---------------------------------------------------------------------------
class _DummyRule(RiskRule):
    name = "_DUMMY_REGISTRY_TEST"
    phase = PRE_TIGHTEN

    def evaluate(self, trade: dict, ctx: Layer4Context):
        return None


class _Dummy2Rule(RiskRule):
    name = "_DUMMY2_REGISTRY_TEST"
    phase = PRE_TIGHTEN

    def evaluate(self, trade: dict, ctx: Layer4Context):
        return None


# ---------------------------------------------------------------------------
# Fixture: isolate registry state per test — snapshot/restore + dummy cleanup
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_dummy_rules():
    """Snapshot registry, remove test-only dummy rules, restore on teardown.

    Uses in-place mutation (_REGISTRY[:]) so that any code holding a direct
    reference to _REGISTRY sees the updated list.
    """
    # Snapshot before cleanup (in-place slice preserves object identity)
    snapshot = list(_REGISTRY)
    # Remove any test-only dummy rules so each test starts from builtins only
    unregister_rule(_DummyRule)
    unregister_rule(_Dummy2Rule)
    # Also remove CustomTightenRule if it leaked from test_future_rule_stub
    try:
        from tests.v9.services.test_trade_manager.test_future_rule_stub import CustomTightenRule
        unregister_rule(CustomTightenRule)
    except ImportError:
        pass
    yield
    # Restore in-place so that references to _REGISTRY remain valid
    _REGISTRY[:] = snapshot


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_register_rule_adds_to_registry():
    """register_rule should add an instance to _REGISTRY."""
    before = len(_REGISTRY)
    register_rule(order=99)(_DummyRule)
    assert len(_REGISTRY) == before + 1


def test_get_registered_rules_sorted_by_order():
    """get_registered_rules() returns instances sorted ascending by order."""
    register_rule(order=200)(_Dummy2Rule)
    register_rule(order=100)(_DummyRule)
    names = [r.name for r in get_registered_rules()]
    idx_dummy = names.index(_DummyRule.name)
    idx_dummy2 = names.index(_Dummy2Rule.name)
    assert idx_dummy < idx_dummy2


def test_register_rule_rejects_non_risrule():
    """register_rule raises TypeError for a plain class that's not a RiskRule subclass."""
    class NotARule:
        pass
    with pytest.raises(TypeError):
        register_rule(order=99)(NotARule)


def test_register_rule_rejects_duplicate_name():
    """register_rule raises ValueError when two rules share the same name."""
    register_rule(order=98)(_DummyRule)

    class _DuplicateRule(RiskRule):
        name = "_DUMMY_REGISTRY_TEST"  # same name as _DummyRule
        phase = PRE_TIGHTEN

        def evaluate(self, trade: dict, ctx: Layer4Context):
            return None

    with pytest.raises(ValueError, match="duplicate"):
        register_rule(order=97)(_DuplicateRule)


def test_unregister_rule_removes_by_class():
    """unregister_rule(cls) removes the entry whose instance is of that class."""
    register_rule(order=99)(_DummyRule)
    names_before = [r.name for r in get_registered_rules()]
    assert _DummyRule.name in names_before

    unregister_rule(_DummyRule)
    names_after = [r.name for r in get_registered_rules()]
    assert _DummyRule.name not in names_after


def test_unregister_rule_noop_when_not_registered():
    """unregister_rule silently no-ops when the class is not in the registry."""
    # _DummyRule is already removed by the autouse fixture
    # calling unregister again must not raise
    unregister_rule(_DummyRule)  # should not raise


def test_registry_is_list_of_tuples():
    """_REGISTRY must be a list of (int, RiskRule) tuples — not a dict."""
    assert isinstance(_REGISTRY, list)
    for item in _REGISTRY:
        assert isinstance(item, tuple)
        order, rule = item
        assert isinstance(order, int)
        assert isinstance(rule, RiskRule)


def test_get_registered_rules_returns_risrule_instances():
    """Every item returned by get_registered_rules() is a RiskRule instance."""
    for rule in get_registered_rules():
        assert isinstance(rule, RiskRule)


def test_five_rules_registered_at_import():
    """After importing the rules package, exactly 5 built-in rules are registered."""
    # Import the package (idempotent after the first time)
    import backend.v9.services.trade_manager.rules  # noqa: F401
    rules = get_registered_rules()
    # At minimum the 5 built-in rules must be present
    assert len(rules) >= 5


def test_builtin_rules_names_and_order():
    """The 5 built-in rules appear in order 1-5 with expected names."""
    import backend.v9.services.trade_manager.rules  # noqa: F401
    rules = get_registered_rules()
    # Only built-ins (no dummy ones registered in this test)
    builtin_names = [r.name for r in rules if not r.name.startswith("_DUMMY")]
    expected = [
        "MFE_PEAK",
        "CCI_FLAT",
        "TCCI_CROSS",
        "SWI",
        "DAY_TYPE_TARGETS",
    ]
    assert builtin_names == expected
