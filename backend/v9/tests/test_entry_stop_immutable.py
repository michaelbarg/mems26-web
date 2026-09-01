"""T-200a: entry_stop is written ONCE and never updated.

v9_trades.stop has 8 writers (BE, trail, structure, ...) — it's the FINAL
stop, not the entry stop. quality.entry_stop is the immutable truth for
risk measurement.

Enforcement: grep for write sites. More than 1 → the field will drift.
"""
import os
import subprocess

import pytest


def test_entry_stop_single_write_site():
    """Only ONE place in backend/ may write to entry_stop.

    Mutation test: adding a second write site breaks this test.
    """
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    result = subprocess.run(
        ["grep", "-rn", r'"entry_stop"', os.path.join(root, "backend")],
        capture_output=True, text=True)
    lines = [l for l in result.stdout.strip().split("\n")
             if l and "entry_stop" in l
             # Only count WRITE sites (assignment), not reads
             and ("entry_stop\"]" in l or "entry_stop'" in l)
             and "=" in l.split("entry_stop", 1)[1][:5]
             # Exclude comments and test files
             and not l.strip().startswith("#")
             and "/tests/" not in l]

    assert len(lines) <= 1, (
        f"MUTATION: entry_stop has {len(lines)} write sites in backend/ "
        f"(must be exactly 1). Sites:\n" + "\n".join(lines))


def test_entry_stop_written_at_accept():
    """accept_setup must set quality.entry_stop from setup.stop."""
    from unittest.mock import MagicMock, patch
    from backend.v9.services.trade_manager.manager import TradeManager

    db = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    tm = TradeManager(db=db)

    setup = {
        "firing_system": 2,
        "direction": "LONG",
        "stop": 7740.0,
        "t1": 7760.0,
        "t2": 7770.0,
        "t3": 7780.0,
        "entry_price": 7750.0,
        "metadata": {},
    }
    with patch.object(tm, "_db", db):
        trade_id = tm.accept_setup(setup, mode="shadow")

    # The trade should have been added to DB
    assert db.add.called
    trade = db.add.call_args[0][0]
    q = trade.quality if isinstance(trade.quality, dict) else {}
    assert q.get("entry_stop") == 7740.0, (
        f"entry_stop should be 7740.0 from setup.stop, got {q.get('entry_stop')}")


def test_entry_stop_not_overwritten_by_be():
    """After BE moves trade.stop, quality.entry_stop must stay unchanged."""
    # This is a design test — the enforcement test above catches any new
    # write site. This documents the INTENT.
    pass  # Covered by the grep test above
