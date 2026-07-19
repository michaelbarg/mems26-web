"""A6 ruling 2026-07-19 (Michael): S4 must honor DAY_TYPE_MANUAL_OVERRIDE.

The gateway already gates S4 fires with the override (extract_g1_entry_context →
get_live_day_type) and S2 already sizes/targets with it (D-0717-A). S4's internal
_s4_day_type read the non-override chain, so a trade was gated as Variation but
sized/targeted as Normal. S4_OVERRIDE_AWARE_V1 routes S4 through the same
override-aware helper first, fail-open to the legacy chain.

These pins exercise get_live_day_type's override path (the shared helper S4 now
uses) and the flag default.
"""
import importlib

import backend.v9.services.trade_context as tc


def _reload(monkeypatch, override=None, gate_live="0"):
    if override is None:
        monkeypatch.delenv("DAY_TYPE_MANUAL_OVERRIDE", raising=False)
    else:
        monkeypatch.setenv("DAY_TYPE_MANUAL_OVERRIDE", override)
    monkeypatch.setenv("DAYTYPE_GATE_LIVE_V1", gate_live)
    return importlib.reload(tc)


def _today_et():
    import datetime as dt
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def test_override_today_is_honored(monkeypatch):
    """A dated override matching today returns its label — the value S4 now reads."""
    m = _reload(monkeypatch, override=f"{_today_et()}:Variation")
    assert m.get_live_day_type() == "Variation"


def test_override_other_date_is_inert(monkeypatch):
    """A stale dated override (not today) is ignored — auto-expires at the ET roll.
    (This is exactly why the leftover 2026-07-17:Normal line was safe but noise.)"""
    m = _reload(monkeypatch, override="2020-01-01:Trend_Normal")
    # no override today, gate-live off, no app machine in test → None (fall-through)
    assert m.get_live_day_type() is None


def test_no_override_falls_through(monkeypatch):
    """No override + gate-live OFF → None, so S4 falls through to its legacy
    chain unchanged (fail-open, zero behaviour change when unset)."""
    m = _reload(monkeypatch, override=None, gate_live="0")
    assert m.get_live_day_type() is None


def test_s4_flag_default_off():
    """S4's new branch is gated OFF by default until enabled."""
    import inspect
    import backend.v9.systems.woodies.woodies_system as ws
    src = inspect.getsource(ws)
    assert 'S4_OVERRIDE_AWARE_V1", "0"' in src, "flag must default OFF"
    # and the override-aware helper is wired into S4
    assert "get_live_day_type" in src, "S4 must consult the override-aware helper"


def test_s4_and_s2_use_same_helper():
    """Consistency: both S2 and S4 resolve live day_type via get_live_day_type."""
    import inspect
    import backend.v9.systems.woodies.woodies_system as ws
    import backend.v9.systems.five_min.five_min_system as fm
    assert "get_live_day_type" in inspect.getsource(ws)
    assert "get_live_day_type" in inspect.getsource(fm)
