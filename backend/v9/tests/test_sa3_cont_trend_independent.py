"""SA-3: cont_trend_filter must work independently of DIRECTION_CONTEXT.

Before this fix, CONT_TREND_FILTER was nested inside the DIRECTION_CONTEXT
block. With DIRECTION_CONTEXT=0 (permanent ruling 28.08), the cont_trend_filter
was unreachable — 4 ruled-on flags were dead code.

This test verifies that cont_trend_filter is reachable with DIRECTION_CONTEXT=0
by checking the source code structure (AST-based, not tautological).
"""
import ast
import inspect
import textwrap

import pytest


def test_cont_trend_filter_not_nested_in_direction_context():
    """cont_trend_filter must NOT be inside the DIRECTION_CONTEXT block.

    AST check: find the if-node for CONT_TREND_FILTER and verify it's not
    a child of the if-node for DIRECTION_CONTEXT.
    """
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = textwrap.dedent(inspect.getsource(TradingGateway._route_setup_inner))
    tree = ast.parse(source)

    # Find all if-nodes that check env vars
    def _env_check_name(node):
        """Extract the env var name from an os.getenv(...) call in an if test."""
        if not isinstance(node, ast.If):
            return None
        # Walk the test expression for Call nodes with 'getenv'
        for child in ast.walk(node.test):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Attribute) and func.attr == "getenv":
                    if child.args and isinstance(child.args[0], ast.Constant):
                        return child.args[0].value
        return None

    # Find DIRECTION_CONTEXT and CONT_TREND_FILTER if-nodes with their line numbers
    dc_lines = set()
    ct_lines = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            name = _env_check_name(node)
            if name == "DIRECTION_CONTEXT":
                # Collect all line numbers inside this block
                for child in ast.walk(node):
                    if hasattr(child, "lineno"):
                        dc_lines.add(child.lineno)
            if name == "CONT_TREND_FILTER":
                ct_lines.add(node.lineno)

    # CONT_TREND_FILTER's if-node must NOT be inside DIRECTION_CONTEXT's block
    overlap = ct_lines & dc_lines
    assert not overlap, (
        f"SA-3 REGRESSION: CONT_TREND_FILTER (lines {ct_lines}) is still nested "
        f"inside DIRECTION_CONTEXT (lines {dc_lines}). The cont_trend_filter is "
        f"unreachable when DIRECTION_CONTEXT=0 (permanent ruling 28.08)."
    )


def test_cont_trend_filter_exists_as_top_level_gate():
    """The string 'cont_trend_filter' must appear in _evaluate_gates source."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway._route_setup_inner)
    assert "cont_trend_filter" in source, (
        "cont_trend_filter reference missing from _evaluate_gates"
    )
