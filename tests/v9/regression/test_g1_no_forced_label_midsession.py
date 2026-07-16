"""Michael URGENT root-fix (2026-07-16 ~19:15 IDT, live directive).

classify_replay's `final` is computed with is_eod=True — on a PARTIAL day it
forces a terminal label (the "Neutral_Center" that wrongly fed playbook /
location gates mid-session and clamped #28's ladder). The extract_g1 fallback
is now gated by _g1_replay_fallback_ok(): allowed ONLY outside the live
session (ET hour >= 16 or < 9). Mid-session with live-None → day_type stays
None (gates fail-OPEN on unclassified, never fail-WRONG on invented labels).
"""
from unittest import mock

import backend.v9.services.trade_context as tc


def _ctx():
    return {"systems": {"day_type_machine": {}, "woodies_system": {}, "tpo_system": {}}}


def test_midsession_live_none_stays_none(monkeypatch):
    monkeypatch.setenv("S1_NEW_CLASSIFIER", "1")
    monkeypatch.setattr(tc, "get_live_day_type", lambda: None)
    monkeypatch.setattr(tc, "_g1_replay_fallback_ok", lambda: False)  # mid-session
    # prove classify_replay is NOT consulted mid-session
    called = {"n": 0}
    monkeypatch.setitem(tc._NC_CACHE, "date", None)
    with mock.patch(
        "backend.v9.api.v9.daytype_classify_routes.classify_replay",
        side_effect=lambda *a, **k: called.__setitem__("n", called["n"] + 1) or {},
    ):
        g1 = tc.extract_g1_entry_context(_ctx())
    assert g1.get("day_type_at_entry") is None
    assert called["n"] == 0, "classify_replay must not run mid-session"


def test_postclose_fallback_allowed(monkeypatch):
    monkeypatch.setenv("S1_NEW_CLASSIFIER", "1")
    monkeypatch.setattr(tc, "get_live_day_type", lambda: None)
    monkeypatch.setattr(tc, "_g1_replay_fallback_ok", lambda: True)  # post-close
    monkeypatch.setitem(tc._NC_CACHE, "date", None)
    with mock.patch(
        "backend.v9.api.v9.daytype_classify_routes.classify_replay",
        return_value={"final": {"day_type": "Normal_Variation"}},
    ):
        g1 = tc.extract_g1_entry_context(_ctx())
    assert g1.get("day_type_at_entry") == "Variation"  # mapped, allowed after close


def test_location_gate_day_type_none_allows():
    """location_gate with day_type=None must fail-OPEN (allow)."""
    from backend.v9.systems.location_gate import decide_location
    allow, reason = decide_location(
        family="CONT", direction="LONG", day_type=None, entry_price=7600.0,
        levels={"vah": 7617.0, "val": 7593.0, "poc": 7603.0,
                "ib": (7601.25, 7626.25)},
        expansion=None,
    )
    assert allow, f"None day_type must not location-block (got: {reason})"
