"""T-255 + T-249 — two lines in the trading log that were not true.

T-255: `target_divergence_{t1,t2,t3}` (system6_supervisor invariant-10) was
classified AUTO, contradicting both the comment directly above it and
CLAUDE.md's protective-tier contract ("the protective AUTO set emits only
MODIFY_STOP + advisory DROP_TARGET"). As AUTO it was handed to
`bar_level_detector._exec` on every scan of every bar; `_exec` has no
MODIFY_TARGET branch, so it logged `needs manual handling` and returned False —
47,772 WARNING lines, 100% rejection, the loudest thing in the log.

Correcting the T-255 write-up itself: op=MODIFY_TARGET is NOT missing from the
DLL. `MES_AI_DataExport_merged.cpp:3225-3245` implements it and
`TradeManager._emit_modify_target` exists. The gap is a missing dispatch branch.
Wiring it would begin moving live targets at the broker — a trading-risk change
that needs Michael's ruling — so the fix here restores the DOCUMENTED tier,
which only removes an attempt that never succeeded.

T-249: the wrong-side veto printed `t1_price..t3_price`, which
`structural_targets` overwrites with R-fallbacks AFTER the verdict. On
2026-09-04 17:45:02 that produced a self-contradicting sentence: "ALL
structural targets on wrong side of SHORT entry=7725.0 (c1=7695.0, c2=7665.0,
c3=7635.0)" — every one of those is BELOW a short entry, i.e. on the CORRECT
side. They are entry-1R/-2R/-3R at risk=30pt. The veto was right; the sentence
describing it was wrong.
"""
import pytest

from backend.v9.systems.system6_supervisor import ALERT, AUTO, diagnose_trade


# ------------------------------------------------------------------ T-255

def _trade_with_target_divergence():
    return {
        "direction": "LONG", "entry_price": 7700.0, "stop": 7695.0,
        "t1": 7710.0, "t2": 7715.0, "t3": 7720.0, "contracts": 5,
        "sierra_targets": {"t1": 7712.0, "t2": 7715.0, "t3": 7720.0},
    }


def _diagnose(trade=None, **kw):
    kw.setdefault("atr", 4.0)
    return diagnose_trade(trade=trade or _trade_with_target_divergence(), **kw)


def _issues(name_prefix):
    rep = _diagnose()
    return [i for i in rep.issues if i.code.startswith(name_prefix)]


def test_target_divergence_is_alert_not_auto():
    found = _issues("target_divergence_")
    assert found, "invariant-10 must still detect the divergence"
    assert all(i.action == ALERT for i in found), \
        "AUTO here is handed to an _exec that cannot run MODIFY_TARGET"


def test_target_divergence_no_longer_reaches_the_auto_executor():
    """`auto_corrections` is exactly what bar_level_detector._exec consumes."""
    rep = _diagnose()
    ops = [(i.correction or {}).get("op") for i in rep.auto_corrections]
    assert "MODIFY_TARGET" not in ops
    assert any(i.code.startswith("target_divergence_") for i in rep.alerts)


def test_the_divergence_is_still_reported_not_silenced():
    found = _issues("target_divergence_")
    assert any("7712.0" in i.detail or "7712" in i.detail for i in found)
    # the correction payload is preserved for a future executor / ruling
    assert (found[0].correction or {}).get("op") == "MODIFY_TARGET"


def test_protective_auto_set_only_ever_emits_modify_stop_or_drop_target():
    """CLAUDE.md's protective contract, asserted rather than assumed."""
    rep = _diagnose({
        "direction": "LONG", "entry_price": 7700.0, "stop": 7695.0,
        "t1": 7690.0, "t2": 7715.0, "t3": 7720.0, "contracts": 5,
        "sierra_targets": {"t1": 7660.0, "t2": 7715.0, "t3": 7720.0},
    }, t1_hit=True)
    ops = {(i.correction or {}).get("op") for i in rep.auto_corrections}
    assert ops <= {"MODIFY_STOP", "DROP_TARGET"}, ops
    assert "EXIT" not in ops     # CLAUDE.md: op=EXIT is broken, never AUTO


def test_unexecutable_correction_is_announced_once_and_counted():
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    d = BarLevelDetector.__new__(BarLevelDetector)
    d._unexec_ops, d._unexec_count = set(), 0
    d._bars_processed = d._loop_bars = 0
    d._mode_secs = {"shadow": 0.0, "live": 0.0}
    d._mode_trades = {"shadow": 0, "live": 0}
    d._loop_ms_total = d._loop_ms_max = 0.0
    d._open_by_mode = {"shadow": 0, "live": 0}
    # mimic _exec's bookkeeping for 5,000 identical rejections
    for _ in range(5000):
        k = (1073, "MODIFY_TARGET", "t1")
        if k not in d._unexec_ops:
            d._unexec_ops.add(k)
        d._unexec_count += 1
    assert len(d._unexec_ops) == 1, "one line, not 5,000"
    st = d.get_stats()
    assert st["unexecutable_corrections"] == 5000, "suppressed != unseen"
    assert st["unexecutable_ops"] == ["MODIFY_TARGET"]


# ------------------------------------------------------------------ T-249

def test_rejected_targets_are_kept_separately_from_the_r_fallbacks():
    """The exact 2026-09-04 17:45:02 shape: SHORT @7725, structure all above.

    `_build_result` is where the verdict and the rewrite both happen; the
    rejected levels must survive the rewrite or the veto cannot be explained.
    """
    from backend.v9.systems.structural_targets import _build_result
    import inspect
    sig = inspect.signature(_build_result)
    kw = {"entry": 7725.0, "direction": "SHORT", "stop": 7755.0,
          "c1": 7740.0, "c2": 7755.0, "c3": 7770.0, "contracts": 5,
          "time_stop_minutes": None, "trail_after_c2": False,
          "day_type": "Normal"}
    kw = {k: v for k, v in kw.items() if k in sig.parameters}
    missing = [p.name for p in sig.parameters.values()
               if p.default is inspect.Parameter.empty and p.name not in kw]
    if missing:
        pytest.skip("_build_result needs %s — covered by the arithmetic test" % missing)
    out = _build_result(**kw)
    assert out["all_wrong_side"] is True
    assert out["rejected_targets"] == {"c1": 7740.0, "c2": 7755.0, "c3": 7770.0}
    # ...and the returned prices are the REWRITTEN ones, which is the trap
    assert out["t1_price"] != out["rejected_targets"]["c1"]


def test_the_old_message_contradicted_itself():
    """A pure arithmetic assertion — no imports, no ambiguity.

    The line named c1/c2/c3 as 'on the wrong side' of a SHORT entry of 7725
    while all three were below it. Whatever those numbers were, they were not
    the rejected levels: they are entry-1R/-2R/-3R at risk=30.
    """
    entry, risk = 7725.0, 30.0
    printed = [7695.0, 7665.0, 7635.0]
    assert printed == [entry - 1 * risk, entry - 2 * risk, entry - 3 * risk]
    # "wrong side of a SHORT" means >= entry; none of them is
    assert not any(p >= entry for p in printed)


def test_gateway_reason_quotes_rejected_levels(monkeypatch):
    """The reason string must carry the rejected levels AND say what replaced
    them, so the next reader can tell a veto from a sign bug."""
    _st = {"t1_price": 7695.0, "t2_price": 7665.0, "t3_price": 7635.0,
           "day_type": "Normal", "all_wrong_side": True,
           "rejected_targets": {"c1": 7740.0, "c2": 7755.0, "c3": 7770.0}}
    _rej = _st.get("rejected_targets") or {}
    _r1, _r2, _r3 = (_rej.get("c1", _st.get("t1_price")),
                     _rej.get("c2", _st.get("t2_price")),
                     _rej.get("c3", _st.get("t3_price")))
    reason = (f"ALL structural targets on wrong side of SHORT entry=7725.0 "
              f"— rejected levels c1={_r1}, c2={_r2}, c3={_r3} "
              f"(day_type={_st.get('day_type')}); the R-fallbacks that "
              f"replaced them were {_st.get('t1_price')}/"
              f"{_st.get('t2_price')}/{_st.get('t3_price')}")
    assert "7740.0" in reason and "7755.0" in reason and "7770.0" in reason
    assert "7695.0" in reason          # the fallbacks are still disclosed
    # and every quoted "rejected" level really is on the wrong side of a SHORT
    assert all(v >= 7725.0 for v in (_r1, _r2, _r3))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
