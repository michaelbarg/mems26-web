"""T-622 NORMAL_DAY_RUNNER_OTHER_SIDE_V1 (Michael 21.10 — fixes that follow the Normal day; his 11.09 doctrine "to the
POC, or as long as it continues, to the other side"): a runner on a Normal day ends at the other side of the IB.

20.10: OPENING_ORR LONG 7729.00 (16:50) — T1 17:00, T2 17:15, the runner held the one slot to 18:10. IB 7710.25–7786.00;
the 17:25 bar touched 7786.00 (closed 7785.00), the 17:30 bar probed 7791.50 and closed 7779.25 back inside.
"""
import os
import types
from unittest.mock import patch

from backend.v9.services import normal_day_runner as ndr

IB_BARS = [  # 20.10 16:30–17:25 (h, l, c)
    (7727.0, 7718.5, 7723.25), (7731.0, 7720.0, 7725.5), (7726.25, 7711.25, 7713.0), (7731.25, 7710.25, 7729.0),
    (7737.75, 7726.75, 7732.5), (7748.25, 7732.5, 7748.0), (7752.75, 7743.25, 7747.5), (7758.0, 7745.0, 7755.75),
    (7760.5, 7753.25, 7759.5), (7768.0, 7758.75, 7766.25), (7776.75, 7765.25, 7775.25), (7786.0, 7772.5, 7785.0),
]
B1730 = (7791.5, 7777.5, 7779.25)


def _bars(extra=()):
    return [{"h": h, "l": l, "c": c} for h, l, c in list(IB_BARS) + list(extra)]


def _env(**kv):
    base = {k: v for k, v in os.environ.items() if k != "NORMAL_DAY_RUNNER_OTHER_SIDE_V1"}
    base.update(kv)
    return patch.dict(os.environ, base, clear=True)


def test_ib_of_needs_twelve_closed_bars():
    assert ndr.ib_of(_bars()[:11]) is None
    assert ndr.ib_of(_bars()) == (7786.0, 7710.25)
    assert ndr.ib_of([types.SimpleNamespace(h=h, l=l, c=c) for h, l, c in IB_BARS]) == (7786.0, 7710.25)


def test_2010_the_17_25_touch_and_the_17_30_probe():
    # the 17:25 bar reached the IB high and closed inside ⇒ one tick under the close
    assert ndr.runner_stop("LONG", "Normal", 7786.0, 7710.25, 7786.0, 7772.5, 7785.0, 7729.25) == 7784.75
    # the 17:30 probe closed back inside at 7779.25 ⇒ 7779.00
    assert ndr.runner_stop("LONG", "Normal", 7786.0, 7710.25, *B1730, 7729.25) == 7779.0
    # a close BEYOND the edge ⇒ one tick inside the edge (out only if it comes back in)
    assert ndr.runner_stop("LONG", "Normal", 7786.0, 7710.25, 7795.0, 7787.0, 7794.0, 7729.25) == 7785.75


def test_no_change_cases():
    assert ndr.runner_stop("LONG", "Variation", 7786.0, 7710.25, *B1730, 7729.25) is None     # not a Normal day
    assert ndr.runner_stop("LONG", "Normal", 7786.0, 7710.25, 7781.5, 7776.25, 7778.5, 7729.25) is None  # not reached
    assert ndr.runner_stop("LONG", "Normal", 7786.0, 7710.25, *B1730, 7780.0) is None         # would not tighten
    assert ndr.runner_stop("FLAT", "Normal", 7786.0, 7710.25, *B1730, 7729.25) is None
    assert ndr.runner_stop("LONG", "Normal", None, 7710.25, *B1730, 7729.25) is None


def test_short_mirror():
    assert ndr.runner_stop("SHORT", "Normal", 7786.0, 7710.25, 7720.0, 7709.0, 7712.0, 7760.0) == 7712.25
    assert ndr.runner_stop("SHORT", "Normal", 7786.0, 7710.25, 7712.0, 7700.0, 7701.0, 7760.0) == 7710.5
    assert ndr.runner_stop("SHORT", "Normal", 7786.0, 7710.25, 7720.0, 7711.0, 7712.0, 7760.0) is None


def test_flag_default_off():
    with _env():
        assert ndr.enabled() is False
    with _env(NORMAL_DAY_RUNNER_OTHER_SIDE_V1="1"):
        assert ndr.enabled() is True


def _fake_trade(**kw):
    t = types.SimpleNamespace(id=3544, entry_price=7729.0, direction="LONG", stop=7729.25,
                              t1_hit_ts="2026-10-20T14:00:00Z", cross_context=[], quality={})
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def _run_manager(trade, day_type, bars):
    from backend.v9.services.trade_manager.manager import TradeManager
    calls = {"log": [], "emit": []}
    tm = types.SimpleNamespace(_log_management=lambda tid, act, payload: calls["log"].append((tid, act, payload)),
                               _emit_modify_stop=lambda tr, s: calls["emit"].append(s))
    with patch("backend.v9.services.trade_context.get_live_day_type", lambda: day_type), \
            patch("backend.v9.services.trade_context.get_closed_rth_bars_today", lambda: bars):
        moved = TradeManager.apply_normal_day_runner(tm, trade)
    return moved, calls


def test_manager_off_is_inert():
    t = _fake_trade()
    with _env():
        moved, calls = _run_manager(t, "Normal", _bars([B1730]))
    assert moved is False and calls == {"log": [], "emit": []} and t.stop == 7729.25


def test_manager_moves_the_runner_stop_with_modify_stop():
    t = _fake_trade()
    with _env(NORMAL_DAY_RUNNER_OTHER_SIDE_V1="1"):
        moved, calls = _run_manager(t, "Normal", _bars([B1730]))
    assert moved is True and t.stop == 7779.0 and calls["emit"] == [7779.0]
    assert calls["log"][0][1] == "NORMAL_DAY_RUNNER" and t.cross_context[-1]["to"] == 7779.0


def test_manager_before_t1_or_not_normal_or_ib_forming():
    with _env(NORMAL_DAY_RUNNER_OTHER_SIDE_V1="1"):
        assert _run_manager(_fake_trade(t1_hit_ts=None), "Normal", _bars([B1730]))[0] is False
        assert _run_manager(_fake_trade(), "Variation", _bars([B1730]))[0] is False
        assert _run_manager(_fake_trade(), "Normal", _bars()[:10])[0] is False


def test_wiring_is_flag_gated_after_the_trail():
    src = open("backend/v9/services/trade_manager/bar_level_detector.py", encoding="utf-8").read()
    i = src.index('getenv("NORMAL_DAY_RUNNER_OTHER_SIDE_V1", "0")')
    j = src.index("stop = trade.stop  # refresh after potential trail update")
    k = src.index('if trade.t1_hit_ts is not None and trade.state != "CLOSED":')
    assert k < i < j and "self._tm.apply_normal_day_runner(trade)" in src[i:j]
