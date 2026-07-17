"""Top-level conftest — re-export DB fixtures for cross-directory access.

The api/ test directory needs fixtures defined in tests/v9/db/conftest.py.
Importing them here makes them discoverable by pytest without using the
deprecated pytest_plugins mechanism in non-top-level conftest files.
"""

import asyncio
import os

import pytest

# N12: pytest must never write into the LIVE central ops log — System6/feed
# scenarios would land fake CRITICAL ALERT lines in docs/reports/OPS_LOG_*.md.
# scripts/ops_log.log_event honors this and becomes a silent no-op.
os.environ.setdefault("OPS_LOG_DISABLE", "1")

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
