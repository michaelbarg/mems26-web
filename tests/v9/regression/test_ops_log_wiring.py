"""N12 regression — ops_log wiring must NEVER break the consumers it logs for.

The central ops log (scripts/ops_log.py) is imported by trading-critical code
(feed_watchdog gate, System6 supervisor). The import is GUARDED: when
scripts.ops_log is missing/unimportable, each consumer must fall back to a
no-op log_event and keep working exactly as before.

if reverted → RED because: replacing the guarded import with a bare
`from scripts.ops_log import log_event` raises at import time when ops_log is
absent — killing the feed gate / supervisor with it.
"""
import importlib
import sys


def _import_with_ops_log_blocked(monkeypatch, module_name):
    """Force `from scripts.ops_log import ...` to raise, then fresh-import module.

    Returns (fresh_module, original_module). The caller MUST restore the
    original into sys.modules afterwards — other test files hold references
    into the original object and `unittest.mock.patch` resolves it by name.
    """
    # None in sys.modules → "import of scripts.ops_log halted" (ImportError)
    monkeypatch.setitem(sys.modules, "scripts.ops_log", None)
    orig = sys.modules.pop(module_name, None)
    return importlib.import_module(module_name), orig


def _restore(module_name, orig):
    if orig is not None:
        sys.modules[module_name] = orig
    else:
        sys.modules.pop(module_name, None)


def test_feed_watchdog_imports_when_ops_log_missing(monkeypatch):
    name = "backend.v9.services.feed_watchdog"
    mod, orig = _import_with_ops_log_blocked(monkeypatch, name)
    try:
        # the no-op fallback is in place (real log_event returns True)
        assert mod.log_event("feed_watchdog", "CRITICAL", "test") is False
        # the gate itself still behaves: flag OFF → always alive
        monkeypatch.delenv("FEED_WATCHDOG", raising=False)
        assert mod.is_feed_alive() == (True, None)
    finally:
        _restore(name, orig)


def test_system6_supervisor_imports_when_ops_log_missing(monkeypatch):
    name = "backend.v9.systems.system6_supervisor"
    mod, orig = _import_with_ops_log_blocked(monkeypatch, name)
    try:
        assert mod.log_event("system6", "WARN", "test") is False
        # diagnosis still works untouched (pure function, no logging inside)
        rep = mod.diagnose_trade(
            trade={"direction": "LONG", "entry_price": 100.0, "stop": 99.0,
                   "t1": 101.0, "contracts": 3},
            atr=2.0)
        assert rep is not None and rep.healthy
    finally:
        _restore(name, orig)


def test_real_ops_log_still_importable():
    """Sanity: the real module exists and log_event is callable (no write here)."""
    ol = importlib.import_module("scripts.ops_log")
    assert callable(ol.log_event)
