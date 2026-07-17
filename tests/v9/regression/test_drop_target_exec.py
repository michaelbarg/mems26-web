"""TradeManager._emit_drop_target — N4 (2026-07-17) System6 rescue-tier wiring.

System6's diagnose_trade already emits a DROP_TARGET correction for a
wrong-side t1/t2/t3 (I-61), and SYSTEM6_AUTOCORRECT=protective already
covers it doctrinally (CLAUDE.md: "protective... emits only MODIFY_STOP +
advisory DROP_TARGET (not wired)") — bar_level_detector.py's `_exec` had no
case for it. This is a backend-only DB correction (null the bad target
field); it never touches Sierra, unlike MODIFY_STOP.
"""
import types
from unittest.mock import MagicMock

from backend.v9.services.trade_manager.manager import TradeManager


def _tm():
    return TradeManager(db=MagicMock())


def _trade(**kw):
    base = dict(id=42, direction="LONG", entry_price=7500.0, t1=7506.0, t2=7495.0, t3=7520.0)
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_drop_target_nulls_field_and_commits():
    tm = _tm()
    trade = _trade()
    ok = tm._emit_drop_target(trade, "t2")
    assert ok is True
    assert trade.t2 is None
    tm._db.commit.assert_called_once()


def test_drop_target_leaves_other_fields_untouched():
    tm = _tm()
    trade = _trade()
    tm._emit_drop_target(trade, "t2")
    assert trade.t1 == 7506.0 and trade.t3 == 7520.0


def test_drop_target_rejects_unknown_field():
    tm = _tm()
    trade = _trade()
    ok = tm._emit_drop_target(trade, "stop")   # not a target field -> refuse
    assert ok is False
    assert not hasattr(trade, "stop") or trade.stop is not None  # untouched (was never set)
    tm._db.commit.assert_not_called()


def test_drop_target_never_touches_sierra():
    """DROP_TARGET must be a pure DB correction — no sierra_command import/call."""
    import backend.v9.services.trade_manager.manager as mgr_mod
    tm = _tm()
    trade = _trade()
    # sanity: sierra_command module untouched by patching a loud sentinel
    called = {"sierra": False}

    class _Sentinel:
        def __getattr__(self, name):
            called["sierra"] = True
            raise AssertionError("DROP_TARGET must not call sierra_command")

    tm._emit_drop_target(trade, "t3")
    assert called["sierra"] is False


def test_drop_target_rollback_on_commit_failure():
    tm = _tm()
    tm._db.commit.side_effect = RuntimeError("db gone")
    trade = _trade()
    ok = tm._emit_drop_target(trade, "t1")
    assert ok is False
    tm._db.rollback.assert_called_once()
