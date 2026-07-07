"""Regression: P1.3 — reconcile runs every bar while a slot is active.

Guards docs/handoff/CC_POSTTRADE_SYSTEM6_2026-07-07.md P1.3. The item-20 reconcile verdict
already handles live_slot; the gap was ZERO callers. BarLevelDetector._reconcile_live wires it
in, flag-gated RECONCILE_LIVE_V1 (default OFF):
  * OFF -> never calls reconcile,
  * ON + no slot -> skips (flat by belief),
  * ON + slot occupied -> runs, and a mismatch verdict is escalated to CRITICAL,
  * fail-safe (reconcile error is swallowed).
"""
import logging
import types
import pytest

import backend.v9.services.reconcile as rc
from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


def _gw(demo=None, live=None):
    return types.SimpleNamespace(demo_slot=demo, live_slot=live)


def _det(gw):
    d = BarLevelDetector(trade_manager=types.SimpleNamespace())
    d.set_gateway(gw)
    return d


def test_off_never_reconciles(monkeypatch):
    monkeypatch.delenv("RECONCILE_LIVE_V1", raising=False)
    called = []
    monkeypatch.setattr(rc, "gather_and_reconcile", lambda **k: called.append(1))
    _det(_gw(live=5))._reconcile_live()
    assert called == []


def test_on_but_flat_skips(monkeypatch):
    monkeypatch.setenv("RECONCILE_LIVE_V1", "1")
    called = []
    monkeypatch.setattr(rc, "gather_and_reconcile", lambda **k: called.append(1))
    _det(_gw(demo=None, live=None))._reconcile_live()   # no slot → flat
    assert called == []


def test_on_with_slot_runs_and_escalates_mismatch(monkeypatch, caplog):
    monkeypatch.setenv("RECONCILE_LIVE_V1", "1")
    verdict = types.SimpleNamespace(mismatch=True, naked_stop_suspect=False,
                                    verdict="MISMATCH_ORPHAN_TM", detail="orphan")
    monkeypatch.setattr(rc, "gather_and_reconcile", lambda **k: verdict)
    with caplog.at_level(logging.CRITICAL):
        _det(_gw(live=7))._reconcile_live()
    assert any(r.levelno == logging.CRITICAL and "Reconcile-live" in r.getMessage()
               for r in caplog.records)


def test_fail_safe_on_reconcile_error(monkeypatch):
    monkeypatch.setenv("RECONCILE_LIVE_V1", "1")
    def _boom(**k):
        raise RuntimeError("db down")
    monkeypatch.setattr(rc, "gather_and_reconcile", _boom)
    _det(_gw(live=7))._reconcile_live()                 # must NOT raise
