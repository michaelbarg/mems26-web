"""Top-level conftest — re-export DB fixtures for cross-directory access.

The api/ test directory needs fixtures defined in tests/v9/db/conftest.py.
Importing them here makes them discoverable by pytest without using the
deprecated pytest_plugins mechanism in non-top-level conftest files.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

# N12: pytest must never write into the LIVE central ops log — System6/feed
# scenarios would land fake CRITICAL ALERT lines in docs/reports/OPS_LOG_*.md.
# scripts/ops_log.log_event honors this and becomes a silent no-op.
os.environ.setdefault("OPS_LOG_DISABLE", "1")

# ── 🔴 SIGNALS ISOLATION (2026-07-28) — the same class of bug as N12, but this
# one placed REAL ORDERS on Michael's LIVE account.
#
# `trade_command.json` is a live wire: the Sierra DLL polls it and submits
# whatever it finds. Its path comes from MEMS26_SIGNALS_DIR, which defaulted to
# the real ~/SierraChart_Data/v9_export — so any test that reached a genuine
# command writer fired an order at the broker. Evidence (07-28): trade_result.json
# held ORDER_SUBMITTED parent_id=9737 stamped 09:03:37, exactly when the suite was
# run, with no matching row in v9_trades; Sierra's activity log for the day
# carries six "Order reject — Insufficient Account Value (NLV) for margin"
# entries. The account being under-margined is the only reason none of them
# filled. Michael saw it from the outside: "המערכת מנסה לשלוח הוראות כל הזמן".
#
# Set at MODULE level, not in a fixture: fill_poller and friends resolve these
# paths at IMPORT time, which happens after conftest is loaded but before any
# fixture runs. A test that genuinely needs a signals dir should still create
# its own tmp_path — this is the floor, not a substitute.
_TEST_SIGNALS_DIR = Path(tempfile.mkdtemp(prefix="mems26_test_signals_"))
os.environ["MEMS26_SIGNALS_DIR"] = str(_TEST_SIGNALS_DIR)
os.environ["V9_EXPORT_DIR"] = str(_TEST_SIGNALS_DIR)
os.environ["TRADE_FILLS_PATH"] = str(_TEST_SIGNALS_DIR / "trade_fills.json")

# The live path, kept only so the guard below can prove we never touched it.
_LIVE_COMMAND_FILE = Path(os.path.expanduser(
    "~/SierraChart_Data/v9_export/trade_command.json"))
_LIVE_COMMAND_MTIME = (
    _LIVE_COMMAND_FILE.stat().st_mtime if _LIVE_COMMAND_FILE.exists() else None)


@pytest.fixture(autouse=True)
def _never_touch_the_live_command_file():
    """Fail loudly if a test wrote to the real command file.

    Redirecting the env is the fix; this is the alarm that tells us if some code
    path hard-codes the live path and slips past it. An order sent to the broker
    from a test run must never again be something we discover from the outside."""
    yield
    if _LIVE_COMMAND_FILE.exists():
        now = _LIVE_COMMAND_FILE.stat().st_mtime
        if _LIVE_COMMAND_MTIME is None or now != _LIVE_COMMAND_MTIME:
            pytest.fail(
                f"TEST WROTE TO THE LIVE COMMAND FILE {_LIVE_COMMAND_FILE} — "
                "the Sierra DLL polls this file and submits real orders. "
                "Use the MEMS26_SIGNALS_DIR redirect or a tmp_path.")

# Re-export; pytest picks up fixtures by name from any conftest in the path.
from tests.v9.db.conftest import db, client, BRIDGE_HEADERS  # noqa: F401

# NOTE: setup_db is NOT re-exported here because it's autouse=True in
# tests/v9/db/conftest.py — re-exporting an autouse fixture at root level
# would apply it to ALL tests, including unit tests that don't use a DB.


@pytest.fixture(autouse=True)
def _ensure_event_loop():
    """Ensure an asyncio event loop exists for tests using get_event_loop().

    Python 3.10+ removed the implicit loop creation in the main thread.
    Tests that use asyncio.get_event_loop().run_until_complete() break
    after another test calls asyncio.run() (which creates + closes a loop).
    This fixture guarantees a fresh loop is available for every test.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield
    # Don't close — let subsequent tests reuse it


@pytest.fixture(autouse=True)
def _isolate_gateway_decisions(tmp_path, monkeypatch):
    """A3: Redirect gateway_decisions.jsonl to tmp_path for EVERY test.

    Without this, 8% of the decision feed is test-fixture phantom data
    (same class as backend/v9/tests/conftest.py — extended to root).
    Sets MEMS26_TEST_MODE=1 so any code path can bail out of production
    side effects.
    """
    decisions_file = str(tmp_path / "gateway_decisions.jsonl")
    monkeypatch.setenv("GATEWAY_DECISIONS_PATH", decisions_file)
    monkeypatch.setenv("MEMS26_TEST_MODE", "1")
    monkeypatch.delenv("GATEWAY_DECISIONS_HYDRATE", raising=False)
