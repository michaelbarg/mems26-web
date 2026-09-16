"""T-392: Tests for the draft decision tree v2 — loader, evaluator, safety.

Verifies:
  - All rows in the draft YAML load successfully
  - validate_expr accepts each condition (no unsafe AST nodes)
  - evaluate returns correct decision for sample vectors
  - 15.09 19:10 GHOST SHORT: tree says 'allow' (deliberate diff from current)
  - Row with Call node is rejected
"""
import pytest

from backend.v9.services.dalton_tree import evaluate, load_tree, invalidate_cache
from backend.v9.services.dalton_playbook import validate_expr


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure each test gets a fresh tree load."""
    invalidate_cache()
    yield
    invalidate_cache()


class TestTreeLoad:
    """All rows in the draft YAML load and pass validation."""

    def test_loads_non_empty(self):
        tree = load_tree()
        assert len(tree) > 0, "tree should have at least one rule"

    def test_all_rows_have_required_keys(self):
        tree = load_tree()
        for rule in tree:
            assert "id" in rule, f"rule missing id: {rule}"
            assert "condition" in rule, f"rule {rule['id']} missing condition"
            assert "decision" in rule, f"rule {rule['id']} missing decision"
            assert "source" in rule, f"rule {rule['id']} missing source"

    def test_all_expr_conditions_validate(self):
        """Every expr: condition passes the safe AST whitelist."""
        tree = load_tree()
        for rule in tree:
            cond = rule.get("condition", "")
            if cond.startswith("expr:"):
                expr_str = cond[5:].strip()
                # Should not raise — validates against safe AST nodes
                validate_expr(expr_str)

    def test_all_ids_unique(self):
        tree = load_tree()
        ids = [r["id"] for r in tree]
        assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"


class TestEvaluate:
    """evaluate() returns correct decisions for sample vectors."""

    def test_t319b_blocks_long_from_mid_value(self):
        """Phase C, Normal day, LONG from mid_value -> blocked."""
        tree = load_tree()
        vector = {
            "day_type": "Normal",
            "phase": "C",
            "zone": "mid_value",
            "direction": "LONG",
        }
        setup = {"direction": "LONG", "classification": "REACTIVE"}
        result = evaluate(tree, vector, setup)
        assert result["decision"] == "block"
        assert result["row"] == "t319b_normal_location_long"

    def test_t319b_allows_long_from_near_val(self):
        """Phase C, Normal day, LONG from near_val -> no block from t319b."""
        tree = load_tree()
        vector = {
            "day_type": "Normal",
            "phase": "C",
            "zone": "near_val",
            "direction": "LONG",
        }
        setup = {"direction": "LONG", "classification": "REACTIVE"}
        result = evaluate(tree, vector, setup)
        # near_val is in the allowed set for LONG, so t319b should NOT match
        assert result["row"] != "t319b_normal_location_long"

    def test_t319b_blocks_short_from_mid_value(self):
        """Phase C, Normal day, SHORT from mid_value -> blocked."""
        tree = load_tree()
        vector = {
            "day_type": "Normal",
            "phase": "C",
            "zone": "mid_value",
            "direction": "SHORT",
        }
        setup = {"direction": "SHORT", "classification": "REACTIVE"}
        result = evaluate(tree, vector, setup)
        assert result["decision"] == "block"
        assert result["row"] == "t319b_normal_location_short"

    def test_t367_blocks_variation_mid_value_no_extension(self):
        """Variation + mid_value + no extension -> blocked by t367 Rule B."""
        tree = load_tree()
        vector = {
            "day_type": "Variation",
            "phase": "C",
            "zone": "mid_value",
            "direction": "SHORT",
            "extension": "none",
        }
        setup = {"direction": "SHORT", "classification": "BREAK"}
        result = evaluate(tree, vector, setup)
        assert result["decision"] == "block"
        assert result["row"] == "t367_rule_b_midvalue_block"

    def test_t367_allows_variation_extension_not_mid(self):
        """Variation + extension + not mid_value -> allowed by t367 Rule A."""
        tree = load_tree()
        vector = {
            "day_type": "Variation",
            "phase": "C",
            "zone": "below_value",
            "direction": "SHORT",
            "extension": "down",
        }
        setup = {"direction": "SHORT", "classification": "BREAK"}
        result = evaluate(tree, vector, setup)
        assert result["decision"] == "allow"
        assert result["row"] == "t367_rule_a_extension_allow"

    def test_no_match_returns_stand_down(self):
        """Vector that matches no rule -> stand_down."""
        tree = load_tree()
        vector = {
            "day_type": "Unknown_Type_XYZ",
            "phase": "D",
            "zone": "unknown_zone",
            "direction": "LONG",
        }
        setup = {"direction": "LONG"}
        result = evaluate(tree, vector, setup)
        assert result["decision"] == "stand_down"
        assert result["row"] == "no_match"


class TestGhostShort:
    """15.09 19:10 GHOST SHORT: tree v2 says 'allow' — deliberate diff.

    The current code blocks this via variation_mid_value (T-367 Rule B).
    The tree v2 intent is to allow entries WITH the extension even from
    mid_value when going with the trend.  In the tree, Rule A
    (extension_allow) fires BEFORE Rule B (midvalue_block) when
    extension != 'none'.
    """

    def test_ghost_short_tree_allows(self):
        """15.09 19:10 SHORT from mid_value WITH extension -> tree says allow.

        Current code blocks this via variation_mid_value (T-367 Rule B).
        Tree v2 deliberately allows it: Rule A (extension_allow) is ordered
        before Rule B (midvalue_block) and matches mid_value entries when
        extension is present.  This IS the designed divergence.
        """
        tree = load_tree()
        vector = {
            "day_type": "Variation",
            "phase": "C",
            "zone": "mid_value",
            "direction": "SHORT",
            "extension": "down",
            "extension_pts": 4.5,
        }
        setup = {
            "direction": "SHORT",
            "classification": "BREAK",
            "entry_kind": "BREAK",
        }
        result = evaluate(tree, vector, setup)
        assert result["decision"] == "allow", (
            f"GHOST SHORT should be 'allow' per T-392 spec, got '{result['decision']}' "
            f"from row '{result['row']}' — this is the deliberate diff from current code"
        )
        assert result["row"] == "t367_rule_a_extension_allow"


class TestUnsafeRejected:
    """Row with Call node is rejected by the safe evaluator."""

    def test_call_node_rejected(self):
        """A rule with a function call in its condition is rejected."""
        evil_tree = [{
            "id": "evil_call",
            "condition": "expr: print('pwned')",
            "decision": "allow",
            "source": "test",
            "measured": "UNMEASURED",
        }]
        setup = {"direction": "LONG"}
        vector = {"zone": "mid_value"}
        result = evaluate(evil_tree, vector, setup)
        # Call node fails validate_expr -> _match_condition returns False -> no match
        assert result["decision"] == "stand_down"
        assert result["row"] == "no_match"

    def test_call_node_in_validate_expr(self):
        """validate_expr directly rejects Call nodes."""
        with pytest.raises(ValueError, match="unsafe"):
            validate_expr("print('pwned')")
