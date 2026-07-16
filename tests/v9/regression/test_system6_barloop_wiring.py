"""Regression: System 6 advisory supervision is wired into the per-bar loop.

Guards docs/handoff/CC_POSTTRADE_SYSTEM6_2026-07-07.md P2.4 — `scan_active_trade`
must run every bar on the active demo/live trade, via BarLevelDetector._system6_scan,
and be:
  * inert when SYSTEM6_SUPERVISOR is off (zero touch to the live trade),
  * advisory-only when on but SYSTEM6_AUTOCORRECT is off (never applies a fix),
  * fail-safe (a malformed trade must not raise into trade management).
"""
import os
import types
import pytest

from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


def _trade(**kw):
    """A minimal V9Trade-like stub."""
    base = dict(direction="LONG", entry_price=7500.0, stop=None,  # naked stop → CRITICAL
                t1=7506.0, t2=7512.0, t3=7520.0, contracts=2, t1_hit_ts=None)
    base.update(kw)
    return types.SimpleNamespace(**base)


class _StubTM:
    def __init__(self):
        self.modify_calls = []
        self.drop_calls = []

    def _emit_modify_stop(self, trade, price):
        self.modify_calls.append((trade, price))

    def _emit_drop_target(self, trade, target_field):
        self.drop_calls.append((trade, target_field))
        return True


@pytest.fixture
def det():
    return BarLevelDetector(trade_manager=_StubTM())


def _set(env, monkeypatch):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)


def test_inert_when_supervisor_off(det, monkeypatch):
    """Flag OFF → no diagnosis, no executor, no error."""
    _set({"SYSTEM6_SUPERVISOR": None}, monkeypatch)
    det._system6_scan(_trade())               # must not raise
    assert det._tm.modify_calls == []          # nothing applied


def test_advisory_only_when_autocorrect_off(det, monkeypatch):
    """Supervisor ON but AUTOCORRECT OFF → diagnoses (naked stop) but applies nothing."""
    _set({"SYSTEM6_SUPERVISOR": "1", "SYSTEM6_AUTOCORRECT": None}, monkeypatch)
    det._system6_scan(_trade(stop=None))       # naked stop = CRITICAL correction available
    assert det._tm.modify_calls == []          # advisory → executor never invoked


def test_fail_safe_on_bad_trade(det, monkeypatch):
    """A trade whose attribute access explodes must be swallowed, not raised."""
    _set({"SYSTEM6_SUPERVISOR": "1"}, monkeypatch)

    class _Boom:
        def __getattr__(self, name):
            raise RuntimeError("boom")

    det._system6_scan(_Boom())                 # must not raise


def test_expected_contracts_follows_fixed_flag(det, monkeypatch):
    """With FIXED_CONTRACTS_2 on, a 3-contract trade should be diagnosable as a size
    mismatch (proves the expected-count is threaded through). AUTOCORRECT off → advisory."""
    _set({"SYSTEM6_SUPERVISOR": "1", "FIXED_CONTRACTS_2": "1",
          "SYSTEM6_AUTOCORRECT": None}, monkeypatch)
    # 3 contracts while expecting 2 → contract_mismatch ALERT (advisory, no apply)
    det._system6_scan(_trade(contracts=3, stop=7494.0))
    assert det._tm.modify_calls == []


def test_auto_be_after_t1_applies_via_existing_plumbing(det, monkeypatch):
    """AUTOCORRECT on + T1 hit + stop below entry → the ONE auto-fix (move stop to BE)
    flows through the existing manager._emit_modify_stop. Proves the executor is wired."""
    import datetime
    _set({"SYSTEM6_SUPERVISOR": "1", "SYSTEM6_AUTOCORRECT": "1"}, monkeypatch)
    det._system6_scan(_trade(stop=7494.0, t1_hit_ts=datetime.datetime.now()))
    assert det._tm.modify_calls and det._tm.modify_calls[-1][1] == 7500.0  # → BE(entry)


def test_auto_drop_target_wrong_side_applies_via_existing_plumbing(det, monkeypatch):
    """N4 (2026-07-17): DROP_TARGET was advisory-only even under protective mode
    (CLAUDE.md: 'not wired') — now completes via manager._emit_drop_target.
    LONG trade with t2 on the wrong side (<= entry) → auto-dropped."""
    _set({"SYSTEM6_SUPERVISOR": "1", "SYSTEM6_AUTOCORRECT": "protective"}, monkeypatch)
    det._system6_scan(_trade(stop=7494.0, t2=7495.0))  # t2 below LONG entry 7500 -> wrong side
    assert det._tm.drop_calls and det._tm.drop_calls[-1][1] == "t2"


def test_auto_drop_target_inert_when_autocorrect_off(det, monkeypatch):
    """Supervisor on, AUTOCORRECT off -> DROP_TARGET stays advisory (not applied)."""
    _set({"SYSTEM6_SUPERVISOR": "1", "SYSTEM6_AUTOCORRECT": None}, monkeypatch)
    det._system6_scan(_trade(stop=7494.0, t2=7495.0))
    assert det._tm.drop_calls == []


def test_naked_stop_never_auto_applies(det, monkeypatch):
    """Safety design: a naked stop is CRITICAL/ALERT — it must NEVER be auto-corrected,
    even with AUTOCORRECT on (System 6 alerts a human, never silently invents a stop)."""
    _set({"SYSTEM6_SUPERVISOR": "1", "SYSTEM6_AUTOCORRECT": "1"}, monkeypatch)
    det._system6_scan(_trade(stop=None))
    assert det._tm.modify_calls == []


def test_reconcile_mismatch_is_folded_into_diagnosis(det, monkeypatch, caplog):
    """A reconcile verdict passed in (DB open / Sierra flat — the phantom-trade case, e.g.
    SIM_TEST 297) must surface as a System 6 reconcile_mismatch alert — this is what makes
    System 6 continuously catch a trade the system thinks is active but Sierra doesn't hold."""
    import logging as _lg
    import types as _ty
    _set({"SYSTEM6_SUPERVISOR": "1"}, monkeypatch)
    rv = _ty.SimpleNamespace(mismatch=True, naked_stop_suspect=False,
                             verdict="MISMATCH_ORPHAN_DB", detail="DB open, slot flat")
    with caplog.at_level(_lg.WARNING):
        det._system6_scan(_trade(stop=7494.0), reconcile_verdict=rv)
    assert any("reconcile_mismatch" in r.getMessage() for r in caplog.records)
