"""Regression test conftest — isolate backend.main from leaking live state.

Root cause (cowork round-3, 2026-07-22): when the backend is running on the
same machine, `sys.modules["backend.main"]` holds the LIVE app with a real
`day_type_machine` (e.g. Trend_Normal). Tests that call `get_live_day_type()`
hit this live module BEFORE falling back to their mock — so all 12 day-type
tests see "Trend_Normal" instead of their expected mock values.

Fix: autouse fixture removes backend.main from sys.modules before each test,
and also clears the antiflap state that persists between tests.
"""

import sys
import pytest


@pytest.fixture(autouse=True)
def _isolate_backend_main():
    """Remove backend.main from sys.modules so get_live_day_type falls back to
    the test's own mock (importlib.import_module path), not the live process."""
    saved = sys.modules.pop("backend.main", None)
    # Also clear the antiflap mutable state that persists cross-test
    try:
        from backend.v9.services.trade_context import _ANTIFLAP_STATE
        _ANTIFLAP_STATE.update({"stable": None, "pending": None, "since": 0.0})
    except Exception:
        pass
    yield
    # Restore if it was there (don't permanently remove for other test suites)
    if saved is not None:
        sys.modules["backend.main"] = saved
