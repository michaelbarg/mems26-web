"""T-391: safe expression evaluator for _match_condition expr: conditions.

Tests cover every operator, None handling, injection rejection, and
backward compatibility with existing playbook YAML conditions.
"""

import pytest
from backend.v9.services.dalton_playbook import (
    _match_condition, validate_expr, _eval_safe_expr,
)


class TestLegacyConditions:
    """Existing condition forms still work (backward compat)."""

    def test_default(self):
        assert _match_condition("default", "OPEN_DRIVE", "Normal") is True

    def test_opening_type_eq(self):
        assert _match_condition("opening_type == OPEN_DRIVE", "OPEN_DRIVE", "Normal") is True
        assert _match_condition("opening_type == OPEN_DRIVE", "OPEN_AUCTION_IN", "Normal") is False

    def test_opening_type_in(self):
        assert _match_condition("opening_type in [OPEN_DRIVE, OPEN_TEST_DRIVE]",
                                "OPEN_DRIVE", "Normal") is True
        assert _match_condition("opening_type in [OPEN_DRIVE, OPEN_TEST_DRIVE]",
                                "OPEN_AUCTION_IN", "Normal") is False

    def test_day_type_eq(self):
        assert _match_condition("day_type == Normal", "OPEN_DRIVE", "Normal") is True
        assert _match_condition("day_type == Variation", "OPEN_DRIVE", "Normal") is False

    def test_day_type_in(self):
        assert _match_condition("day_type in [Normal, Variation]",
                                "OPEN_DRIVE", "Variation") is True

    def test_unknown_legacy(self):
        assert _match_condition("something_else == foo", "X", "Y") is False


class TestExprConditions:
    """New expr: form."""

    def test_simple_eq(self):
        assert _match_condition(
            "expr: zone == 'below_value'", "X", "Y",
            vector={"zone": "below_value"}) is True

    def test_simple_neq(self):
        assert _match_condition(
            "expr: zone != 'mid_value'", "X", "Y",
            vector={"zone": "below_value"}) is True

    def test_and(self):
        assert _match_condition(
            "expr: extension == 'down' and zone != 'mid_value'", "X", "Y",
            vector={"extension": "down", "zone": "below_value"}) is True
        assert _match_condition(
            "expr: extension == 'down' and zone != 'mid_value'", "X", "Y",
            vector={"extension": "down", "zone": "mid_value"}) is False

    def test_or(self):
        assert _match_condition(
            "expr: zone == 'near_val' or zone == 'below_value'", "X", "Y",
            vector={"zone": "below_value"}) is True

    def test_not(self):
        assert _match_condition(
            "expr: not ib_locked", "X", "Y",
            vector={"ib_locked": False}) is True
        assert _match_condition(
            "expr: not ib_locked", "X", "Y",
            vector={"ib_locked": True}) is False

    def test_in_list(self):
        assert _match_condition(
            "expr: day_type in ['Variation', 'Normal_Variation']", "X", "Variation",
            vector={}) is True
        assert _match_condition(
            "expr: day_type in ['Variation', 'Normal_Variation']", "X", "Normal",
            vector={}) is False

    def test_not_in(self):
        assert _match_condition(
            "expr: zone not in ['mid_value', 'near_vah']", "X", "Y",
            vector={"zone": "below_value"}) is True

    def test_numeric_comparison(self):
        assert _match_condition(
            "expr: bars_since_low >= 2", "X", "Y",
            vector={"bars_since_low": 5}) is True
        assert _match_condition(
            "expr: bars_since_low >= 2", "X", "Y",
            vector={"bars_since_low": 1}) is False

    def test_lt_gt(self):
        assert _match_condition(
            "expr: extension_pts > 5.0", "X", "Y",
            vector={"extension_pts": 8.0}) is True
        assert _match_condition(
            "expr: extension_pts < 3.0", "X", "Y",
            vector={"extension_pts": 8.0}) is False

    def test_nested_parens(self):
        assert _match_condition(
            "expr: (zone == 'below_value' or zone == 'near_val') and extension == 'down'",
            "X", "Y",
            vector={"zone": "below_value", "extension": "down"}) is True

    def test_opening_type_in_expr(self):
        """opening_type and day_type accessible from expr namespace."""
        assert _match_condition(
            "expr: opening_type == 'OPEN_DRIVE' and day_type == 'Normal'",
            "OPEN_DRIVE", "Normal", vector={}) is True

    def test_none_value_returns_false(self):
        """None field in comparison → False (fail-closed for rule)."""
        assert _match_condition(
            "expr: zone == 'below_value'", "X", "Y",
            vector={"zone": None}) is False

    def test_unknown_name_returns_false(self):
        """Unknown variable name → False."""
        assert _match_condition(
            "expr: nonexistent_field == 'x'", "X", "Y",
            vector={}) is False

    def test_no_vector_returns_false(self):
        """No vector passed → still works for opening_type/day_type."""
        assert _match_condition(
            "expr: day_type == 'Normal'", "X", "Normal") is True
        # But vector field → False
        assert _match_condition(
            "expr: zone == 'x'", "X", "Y") is False


class TestInjectionRejected:
    """Unsafe AST nodes rejected at validation time."""

    def test_import(self):
        with pytest.raises(ValueError, match="unsafe"):
            validate_expr("__import__('os')")

    def test_dunder_class(self):
        with pytest.raises(ValueError, match="unsafe"):
            validate_expr("x.__class__")

    def test_function_call(self):
        with pytest.raises(ValueError, match="unsafe"):
            validate_expr("f()")

    def test_subscript(self):
        with pytest.raises(ValueError, match="unsafe"):
            validate_expr("a[0]")

    def test_lambda(self):
        with pytest.raises(ValueError, match="unsafe"):
            validate_expr("lambda: 1")

    def test_getattr(self):
        with pytest.raises(ValueError, match="unsafe"):
            validate_expr("x.y")

    def test_invalid_syntax(self):
        with pytest.raises(ValueError, match="invalid"):
            validate_expr("if True: pass")


class TestComplexExpressions:
    """More complex real-world-like expressions."""

    def test_variation_extension_zone(self):
        """Example from the order: Variation + extension down + zone + bars."""
        expr = ("expr: day_type in ['Variation','Normal_Variation'] "
                "and extension == 'down' and zone != 'mid_value' "
                "and bars_since_low >= 2")
        assert _match_condition(expr, "X", "Variation", vector={
            "extension": "down", "zone": "below_value", "bars_since_low": 5,
        }) is True
        # mid_value blocked
        assert _match_condition(expr, "X", "Variation", vector={
            "extension": "down", "zone": "mid_value", "bars_since_low": 5,
        }) is False
        # wrong day_type
        assert _match_condition(expr, "X", "Normal", vector={
            "extension": "down", "zone": "below_value", "bars_since_low": 5,
        }) is False
