"""Mutation test: STRUCTURE_EXIT wiring exists in bar_level_detector.

This test verifies that `_maybe_structure_exit` is CALLED from the on_bar
loop. Removing the call must fail this test — that's the mutation contract.
"""
import ast
import inspect

import pytest


def test_structure_exit_called_from_on_bar():
    """The on_bar method must contain a call to _maybe_structure_exit.

    AST-based: survives refactors (rename-safe as long as the method name
    stays). Fails if the call is removed, commented out, or moved behind
    an always-false guard.
    """
    import textwrap
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    source = textwrap.dedent(inspect.getsource(BarLevelDetector.on_bar))
    tree = ast.parse(source)
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "_maybe_structure_exit":
                calls.append(func.attr)
    assert len(calls) >= 1, (
        "MUTATION FAIL: _maybe_structure_exit is not called from on_bar. "
        "The structure exit system is orphaned — no trade will ever exit "
        "on a structural failure. Restore the call."
    )


def test_structure_exit_method_exists():
    """BarLevelDetector must have the _maybe_structure_exit method."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    assert hasattr(BarLevelDetector, "_maybe_structure_exit"), (
        "MUTATION FAIL: _maybe_structure_exit method missing from BarLevelDetector"
    )


def test_structure_exit_imports_from_module():
    """The wiring must import from the pure-function module."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    source = inspect.getsource(BarLevelDetector._maybe_structure_exit)
    assert "should_exit_on_failbreak" in source, (
        "MUTATION FAIL: _maybe_structure_exit does not reference "
        "should_exit_on_failbreak from structure_exit.py"
    )
    assert "should_exit_on_double_top" in source, (
        "MUTATION FAIL: _maybe_structure_exit does not reference "
        "should_exit_on_double_top from structure_exit.py"
    )
