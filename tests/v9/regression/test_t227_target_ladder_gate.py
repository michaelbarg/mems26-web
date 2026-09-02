"""T-227 — the target ladder must be sane, and a violation must be LOUD.

Production evidence, 2026-09-02: `v9_trades` row #953 (LONG) closed carrying

    t1=7672.50   t2=7686.75   t3=7684.75

— t2 above t3 on a LONG, a ladder no planner can produce. Its shadow twin #952,
fired the same second at the same price, holds the real plan t2=7679.25. The
7686.75 is a Sierra FILL price that `on_target_hit` wrote into the plan column.
Nothing logged a thing; meanwhile System6 spent the afternoon emitting
`AUTO-CORRECT target_divergence_t1/t2/t3 -> rejected` against the books' own row.

Two guarantees:
  1. the planned ladder is preserved before the first fill overwrites it;
  2. an impossible ladder is reported at ERROR with the offending pair named.

The check is a DETECTOR, never a gate: it must not raise, and it must not be
able to interfere with managing a live position.
"""
import logging
from types import SimpleNamespace

import pytest

from backend.v9.services.trade_manager.manager import TradeManager


def _tm():
    return TradeManager.__new__(TradeManager)


def _mk(direction="LONG", **kw):
    t = SimpleNamespace(id=953, direction=direction, quality={},
                        t1=None, t2=None, t3=None, t4=None)
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def test_real_953_ladder_is_reported_as_invalid(caplog):
    t = _mk(t1=7672.50, t2=7686.75, t3=7684.75)
    with caplog.at_level(logging.ERROR):
        ok = _tm()._check_target_ladder_sane(t, "T2-fill")
    assert ok is False
    assert "TARGET_LADDER_INVALID" in caplog.text
    assert "t2=7686.75" in caplog.text and "t3=7684.75" in caplog.text
    assert any(r.levelno >= logging.ERROR for r in caplog.records), \
        "must be ERROR — a debug line is what let #953 through"


def test_planned_long_ladder_is_sane(caplog):
    """#952, the shadow twin: the same fire with the plan intact."""
    t = _mk(t1=7672.50, t2=7679.25, t3=7684.75)
    with caplog.at_level(logging.ERROR):
        assert _tm()._check_target_ladder_sane(t) is True
    assert caplog.text == ""


def test_short_ladder_must_descend(caplog):
    t = _mk(direction="SHORT", t1=7670.75, t2=7665.50, t3=7660.00)
    assert _tm()._check_target_ladder_sane(t) is True
    # the same numbers on a SHORT the wrong way round
    bad = _mk(direction="SHORT", t1=7660.00, t2=7665.50, t3=7670.75)
    with caplog.at_level(logging.ERROR):
        assert _tm()._check_target_ladder_sane(bad) is False
    assert "TARGET_LADDER_INVALID" in caplog.text


@pytest.mark.parametrize("trade", [
    _mk(t1=7672.50),                      # a single target cannot be unordered
    _mk(),                                # nothing planned yet
    _mk(t1=7672.50, t2=None, t3=7684.75),  # gaps are skipped, not guessed
])
def test_incomplete_ladders_are_not_false_alarms(trade):
    assert _tm()._check_target_ladder_sane(trade) is True


def test_detector_never_raises():
    """A broken trade object must not be able to kill live management."""
    class Explodes:
        direction = "LONG"
        quality = {}

        def __getattr__(self, name):
            raise RuntimeError("boom")

    assert _tm()._check_target_ladder_sane(Explodes()) is True


def test_plan_is_preserved_before_the_overwrite():
    tm = _tm()
    t = _mk(t1=7672.50, t2=7679.25, t3=7684.75)
    tm._preserve_planned_targets(t)
    # simulate what on_target_hit does next
    t.t2 = 7686.75
    tm._preserve_planned_targets(t)          # second call must be a no-op
    assert t.quality["planned_targets"] == {
        "t1": 7672.50, "t2": 7679.25, "t3": 7684.75, "t4": None}


def test_plan_snapshot_skipped_when_nothing_planned():
    t = _mk()
    _tm()._preserve_planned_targets(t)
    assert "planned_targets" not in t.quality
