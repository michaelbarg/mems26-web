"""Daily P&L grouping from the Sierra activity journal (Michael 2026-07-28)."""
import json

from backend.v9.services.daily_pnl import group_daily


def _ln(**kw):
    return json.dumps(kw)


def test_groups_by_et_day_and_sums():
    lines = [
        _ln(type="CLOSED_TRADE_PNL", pnl=-23.75, ts="2026-07-27T17:20:00+00:00"),
        _ln(type="CLOSED_TRADE_PNL", pnl=10.0, ts="2026-07-27T19:00:00+00:00"),
        _ln(type="POSITION_CHANGE", new_qty=0, ts="2026-07-27T19:00:00+00:00"),
        _ln(type="CLOSED_TRADE_PNL", pnl=2.5, ts="2026-07-28T13:00:00+00:00"),
    ]
    d = group_daily(lines)
    assert d["2026-07-27"]["pnl"] == -13.75
    assert d["2026-07-27"]["closes"] == 2
    assert d["2026-07-27"]["wins"] == 1 and d["2026-07-27"]["losses"] == 1
    assert d["2026-07-28"]["pnl"] == 2.5


def test_et_day_boundary_not_utc():
    """23:30 UTC = 19:30 ET same day; 03:30 UTC = 23:30 ET PREVIOUS day."""
    lines = [
        _ln(type="CLOSED_TRADE_PNL", pnl=1.0, ts="2026-07-28T03:30:00+00:00"),
    ]
    d = group_daily(lines)
    assert "2026-07-27" in d and "2026-07-28" not in d


def test_missing_ts_goes_to_unknown_never_guessed():
    d = group_daily([_ln(type="CLOSED_TRADE_PNL", pnl=-5.0)])
    assert d["unknown"]["closes"] == 1


def test_garbage_lines_and_null_pnl_skipped():
    d = group_daily(["not json", _ln(type="CLOSED_TRADE_PNL", pnl=None,
                                     ts="2026-07-27T17:00:00+00:00")])
    assert d == {}


def test_biggest_win_loss_tracked():
    lines = [
        _ln(type="CLOSED_TRADE_PNL", pnl=-90.0, ts="2026-07-27T17:00:00+00:00"),
        _ln(type="CLOSED_TRADE_PNL", pnl=-23.75, ts="2026-07-27T17:10:00+00:00"),
        _ln(type="CLOSED_TRADE_PNL", pnl=427.5, ts="2026-07-27T18:00:00+00:00"),
    ]
    d = group_daily(lines)["2026-07-27"]
    assert d["biggest_loss"] == -90.0 and d["biggest_win"] == 427.5
