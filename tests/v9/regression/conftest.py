"""Regression test conftest — isolate backend.main from leaking live state.

Root cause (cowork round-3, 2026-07-22): when the backend is running on the
same machine, `sys.modules["backend.main"]` holds the LIVE app with a real
`day_type_machine` (e.g. Trend_Normal). Tests that call `get_live_day_type()`
hit this live module BEFORE falling back to their mock — so all 12 day-type
tests see "Trend_Normal" instead of their expected mock values.

Fix: autouse fixture removes backend.main from sys.modules before each test,
and also clears the antiflap state that persists between tests.

SECOND leak (cowork round-4, 2026-07-22 night): importing `backend.main`
(3 tests in this suite do) runs env_loader, which floods os.environ with ALL
~150 production .env flags (e.g. DAYTYPE_PATTERN_AWARE_V1=1) for the REST of
the pytest process — flipping daytype_position_gate into its pattern-aware
branch, changing gate order (cont_trend vs rr), etc. sys.modules cleanup can't
undo os.environ. Fix: snapshot os.environ before each test and restore it
after — every test runs with the environment it started the process with.
"""

import os
import sys
import pytest

# Baseline environment captured at CONFTEST IMPORT TIME — i.e. BEFORE pytest
# collects (imports) the test modules. Three test modules import backend.main
# at module level, which runs env_loader and floods os.environ with ~150
# production flags DURING COLLECTION — before any fixture runs. Snapshotting
# inside a fixture would therefore preserve the already-polluted env. This
# module-level capture is the only point that precedes the flood.
_BASELINE_ENV = dict(os.environ)


def _restore_baseline():
    """Reset os.environ to the pre-collection baseline, preserving pytest's
    own runtime keys (PYTEST_*) — pytest pops PYTEST_CURRENT_TEST at teardown
    and KeyErrors if we wiped it."""
    pytest_keys = {k: v for k, v in os.environ.items() if k.startswith("PYTEST_")}
    os.environ.clear()
    os.environ.update(_BASELINE_ENV)
    os.environ.update(pytest_keys)


@pytest.fixture(autouse=True)
def _isolate_env():
    """Restore the pre-collection baseline environment around EVERY test —
    kills the env_loader flood (production .env flags leaking into tests).
    monkeypatch.setenv within a test still works (applied after this fixture,
    undone by monkeypatch before our restore)."""
    _restore_baseline()
    yield
    _restore_baseline()


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
