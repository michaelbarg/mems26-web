"""Regression: _det_buf/_s2_det_dt must be assigned BEFORE first use (T-118 find, 2026-08-28).

Bug class: VA_FADE (:~1884) and FAILED_BREAK (:~1917) consumed _det_buf/_s2_det_dt
that were only assigned ~400 lines later in the same method. Python scoping made
them locals => UnboundLocalError on every first-hour bar, swallowed by the blocks'
try/except => both detectors silently dead (FAILED_BREAK shadow measured nothing).

This test parses the source with ast and asserts, per function, that the first
assignment line of each name precedes its first non-assignment use line.
"""
import ast
import os

SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..",
    "backend", "v9", "systems", "five_min", "five_min_system.py",
)

NAMES = ("_det_buf", "_s2_det_dt")


def _first_assign_and_use(func: ast.AST, name: str):
    first_assign = None
    first_use = None
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id == name:
            if isinstance(node.ctx, ast.Store):
                if first_assign is None or node.lineno < first_assign:
                    first_assign = node.lineno
            elif isinstance(node.ctx, ast.Load):
                if first_use is None or node.lineno < first_use:
                    first_use = node.lineno
    return first_assign, first_use


def test_det_buf_assigned_before_use():
    with open(os.path.abspath(SRC), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    checked = 0
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for name in NAMES:
            first_assign, first_use = _first_assign_and_use(func, name)
            if first_use is None:
                continue  # name not consumed in this function
            checked += 1
            assert first_assign is not None, (
                f"{name} used at line {first_use} in {func.name} but never assigned"
            )
            assert first_assign < first_use, (
                f"{name} first assigned at line {first_assign} but first used at "
                f"line {first_use} in {func.name} — assign-before-use ordering "
                f"broken (UnboundLocalError class, T-118 2026-08-28)"
            )
    assert checked >= 2, "expected at least one consumer of each hoisted name"
