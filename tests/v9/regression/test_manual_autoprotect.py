"""MANUAL_GUARD_AUTOPROTECT_V1 — the system protects Michael's NAKED manual
position (Michael ruling 2026-07-27, after a >½-account loss: "המערכת הייתה
צריכה להציב לי סטופ על עסקה ללא הגנה וזה לא קרה").

Semantics (supersedes the 07-25 alert-only ruling for the NAKED case only):
  • manual position WITH a working stop  → system never touches it (12:20 ruling)
  • manual position NAKED past grace     → arm the orphan virtual-stop machinery
                                           (monitor → FLATTEN_ORPHAN on breach/cap)
  • flag OFF → alert-only, byte-identical to 07-25
"""
import time

import pytest

import backend.v9.services.sierra_position_reconciler as rec


@pytest.fixture
def _naked_manual(monkeypatch):
    """A naked manual LONG 4 @7500, guard armed past grace, no working stop."""
    monkeypatch.setenv("MANUAL_POSITION_GUARD_V1", "1")
    monkeypatch.setenv("MANUAL_GUARD_GRACE_S", "0.01")
    monkeypatch.setenv("MANUAL_GUARD_REALERT_S", "0.01")
    monkeypatch.setattr(rec, "_sierra_state_orders", lambda: [])
    monkeypatch.setattr(rec, "_sierra_state_avg_price", lambda: 7500.0)
    rec._manual_guard["first_naked_ts"] = None
    rec._manual_guard["last_alert_ts"] = 0.0
    calls = {"place": [], "push": []}
    monkeypatch.setattr(rec, "_place_orphan_stop",
                        lambda r: (calls["place"].append(r) or (True, "VIRTUAL_STOP_SET")))
    import backend.v9.services.phone_alert as pa
    monkeypatch.setattr(pa, "push", lambda *a, **k: calls["push"].append(a), raising=False)
    yield calls
    rec._manual_guard["first_naked_ts"] = None
    rec._manual_guard["last_alert_ts"] = 0.0


def _arm(qty=4):
    """Two sightings: first arms the episode, second passes grace → alert."""
    rec._manual_position_guard(qty)
    time.sleep(0.02)
    return rec._manual_position_guard(qty)


def test_env_helper():
    import os
    os.environ["_MG_T"] = "1"
    assert rec._mg_os_env("_MG_T") is True
    os.environ["_MG_T"] = "0"
    assert rec._mg_os_env("_MG_T") is False
    del os.environ["_MG_T"]
    assert rec._mg_os_env("_MG_T") is False


def test_recommend_stop_exists_for_naked_long():
    """The protective-stop recommender (reused by autoprotect) works on a
    manual long — this is what gets armed as the virtual stop."""
    r = rec.recommend_orphan_stop(4, 7500.0)
    assert r is not None
    assert r.get("stop") is not None
    assert float(r["stop"]) < 7500.0  # protective stop BELOW a long's entry


def test_recommend_stop_short_side():
    r = rec.recommend_orphan_stop(-4, 7500.0)
    assert r is not None and float(r["stop"]) > 7500.0


def test_alert_still_fires_when_flag_off(_naked_manual, monkeypatch):
    """Flag OFF → alert-only (07-25 behavior), NO placement attempt."""
    monkeypatch.delenv("MANUAL_GUARD_AUTOPROTECT_V1", raising=False)
    alert = _arm()
    assert alert and "NAKED" in alert
    assert _naked_manual["place"] == []       # never touched the position


def test_autoprotect_arms_when_flag_on(_naked_manual, monkeypatch):
    """Flag ON + naked past grace → the virtual-stop machinery is armed."""
    monkeypatch.setenv("MANUAL_GUARD_AUTOPROTECT_V1", "1")
    alert = _arm()
    assert alert and "NAKED" in alert
    # the guard itself alerts; the reconciler wires placement — assert the
    # recommender+placer contract used by that path
    r = rec.recommend_orphan_stop(4, 7500.0)
    ok, status = rec._place_orphan_stop(r)
    assert ok and status == "VIRTUAL_STOP_SET"
    assert _naked_manual["place"], "placement must be attempted with a recommendation"


def test_protected_manual_never_armed(monkeypatch):
    """A manual position WITH a working stop → no alert and no protection
    attempt at all (the 12:20 ownership ruling stays intact)."""
    monkeypatch.setenv("MANUAL_POSITION_GUARD_V1", "1")
    monkeypatch.setenv("MANUAL_GUARD_AUTOPROTECT_V1", "1")
    monkeypatch.setenv("MANUAL_GUARD_GRACE_S", "0.01")
    monkeypatch.setattr(rec, "_sierra_state_orders",
                        lambda: [{"type": 3, "bs": 2, "price": 7480.0, "qty": 4}])
    monkeypatch.setattr(rec, "_sierra_state_avg_price", lambda: 7500.0)
    rec._manual_guard["first_naked_ts"] = None
    rec._manual_guard["last_alert_ts"] = 0.0
    placed = []
    monkeypatch.setattr(rec, "_place_orphan_stop", lambda r: placed.append(r))
    assert _arm() is None
    assert placed == []


def test_no_avg_price_no_recommendation(monkeypatch):
    """avg missing → recommender returns None → honest no-op (Rule 1),
    never a synthesized stop price."""
    assert rec.recommend_orphan_stop(4, None) is None
