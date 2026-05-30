"""Top-level conftest — re-export DB fixtures for cross-directory access.

The api/ test directory needs fixtures defined in tests/v9/db/conftest.py.
Importing them here makes them discoverable by pytest without using the
deprecated pytest_plugins mechanism in non-top-level conftest files.
"""

# Re-export; pytest picks up fixtures by name from any conftest in the path.
from tests.v9.db.conftest import db, client, BRIDGE_HEADERS  # noqa: F401

# NOTE: setup_db is NOT re-exported here because it's autouse=True in
# tests/v9/db/conftest.py — re-exporting an autouse fixture at root level
# would apply it to ALL tests, including unit tests that don't use a DB.
