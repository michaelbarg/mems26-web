"""STRUCTURE_EXIT_REALIZE_V1: lock profit on failed break after T1 (Michael 02.09).

#942 anchor: failed break at 17:52, trade had T1 banked. Instead of FLATTEN
(account-wide), MODIFY_STOP on each open leg to bar_close ∓ 1 tick.
Pre-T1: no action (don't realize a loss on signal).
"""
import ast
import inspect
import os
import textwrap

import pytest


def test_realize_flag_in_structure_exit():
    """The STRUCTURE_EXIT_REALIZE_V1 flag must be checked in _maybe_structure_exit."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    source = textwrap.dedent(inspect.getsource(BarLevelDetector._maybe_structure_exit))
    assert "STRUCTURE_EXIT_REALIZE_V1" in source, (
        "MUTATION: STRUCTURE_EXIT_REALIZE_V1 not in _maybe_structure_exit")


def test_realize_does_not_flatten():
    """The realize path must NOT contain write_flatten_account."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    source = inspect.getsource(BarLevelDetector._maybe_structure_exit)
    # Find the REALIZE block
    start = source.find("STRUCTURE_EXIT_REALIZE_V1")
    assert start > 0
    # The block between REALIZE check and the elif
    realize_block = source[start:start + 800]
    # FLATTEN must NOT be in the realize path — it's account-wide
    assert "write_flatten_account" not in realize_block.split("elif")[0], (
        "MUTATION: REALIZE path contains FLATTEN — must use per-leg MODIFY_STOP only")


def test_realize_uses_target_order_key():
    """The realize path must use _target_order_key (T0-aware)."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    source = inspect.getsource(BarLevelDetector._maybe_structure_exit)
    start = source.find("STRUCTURE_EXIT_REALIZE_V1")
    realize_block = source[start:start + 2500]
    assert "_target_order_key" in realize_block, (
        "REALIZE must use _target_order_key for T0-aware order mapping")


def test_flag_off_byte_identical():
    """STRUCTURE_EXIT_REALIZE_V1=0 → the old FLATTEN path is reached."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    source = inspect.getsource(BarLevelDetector._maybe_structure_exit)
    # When realize is OFF, the elif chain falls through to FLATTEN
    assert "elif _se_a_mode != \"shadow\"" in source, (
        "Flag OFF must fall through to the original FLATTEN/tighten behavior")
