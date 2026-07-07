"""Regression: EOD auto-flatten at RTH close (Michael 2026-07-07).

Guards docs/handoff/CC_POSTTRADE_SYSTEM6_2026-07-07.md P1.1 — B2EodCheck evaluates
CLOSE_ALL at >=15:59 ET but nothing consumed it. BarLevelDetector._eod_flatten wires
B2 -> the existing CANCEL op, flag-gated EOD_FLATTEN_V1 (default OFF):
  * OFF -> no flatten (inert),
  * ON + CLOSE_ALL -> one CANCEL per demo/live trade, shadow skipped, idempotent,
  * I-62: sends CANCEL and does NOT mark the trade CLOSED (FillPoller closes it on the
    Sierra flat fill — marking flat before Sierra confirms is the orphan I-62 forbids).
"""
import types
import pytest

import backend.v9.services.sierra_command as sc
import backend.v9.systems.woodies.stages.b2_eod_check as b2mod
from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


class _StubTM:
    def _get_sierra_order_id(self, trade):
        return getattr(trade, "_oid", None)


def _trade(i, mode, oid=None):
    return types.SimpleNamespace(id=i, mode=mode, _oid=oid)


@pytest.fixture
def cancels(monkeypatch):
    calls = []
    monkeypatch.setattr(sc, "write_cancel", lambda **kw: calls.append(kw) or {})
    return calls


@pytest.fixture
def force_close_all(monkeypatch):
    monkeypatch.setattr(b2mod.B2EodCheck, "evaluate",
                        lambda self, current_time_et: b2mod.B2Output(True, "CLOSE_ALL"))


def test_off_is_inert(cancels, force_close_all, monkeypatch):
    monkeypatch.delenv("EOD_FLATTEN_V1", raising=False)
    BarLevelDetector(_StubTM())._eod_flatten([_trade(1, "live")])
    assert cancels == []


def test_on_flattens_demo_live_only(cancels, force_close_all, monkeypatch):
    monkeypatch.setenv("EOD_FLATTEN_V1", "1")
    det = BarLevelDetector(_StubTM())
    det._eod_flatten([_trade(1, "live", 111), _trade(2, "demo", 222), _trade(3, "shadow")])
    assert len(cancels) == 2
    assert {c["mode"] for c in cancels} == {"live", "demo"}
    assert any(c["order_id"] == 111 for c in cancels)  # sierra order id threaded through


def test_idempotent_across_bars(cancels, force_close_all, monkeypatch):
    monkeypatch.setenv("EOD_FLATTEN_V1", "1")
    det = BarLevelDetector(_StubTM())
    active = [_trade(1, "live", 111)]
    det._eod_flatten(active)
    det._eod_flatten(active)          # next bar — must NOT re-send CANCEL
    assert len(cancels) == 1


def test_hold_before_close_does_nothing(cancels, monkeypatch):
    monkeypatch.setenv("EOD_FLATTEN_V1", "1")
    monkeypatch.setattr(b2mod.B2EodCheck, "evaluate",
                        lambda self, current_time_et: b2mod.B2Output(False, "HOLD"))
    BarLevelDetector(_StubTM())._eod_flatten([_trade(1, "live")])
    assert cancels == []
