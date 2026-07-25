"""MANUAL_POSITION_GUARD_V1 — alert-only naked-stop watch on Michael's MANUAL
position (Michael ruling 2026-07-25 "התראה-בלבד").

A MANUAL position (ownership-aware branch) with no working protective stop for
>= grace seconds → CRITICAL + phone push. ALERT-ONLY: never places/modifies
orders — the 12:20 ownership ruling ("לא-לרפא") stays fully intact.
"""
import time

import pytest

import backend.v9.services.sierra_position_reconciler as rec


# ── _has_protective_stop (pure) ──────────────────────────────────────────────

def test_long_with_sell_stop_below_avg_is_protected():
    orders = [{"id": 1, "type": 2, "bs": 2, "price": 7431.5, "qty": 6}]
    assert rec._has_protective_stop(6, orders, 7460.75) is True


def test_long_with_only_target_above_avg_is_naked():
    orders = [{"id": 1, "type": 1, "bs": 2, "price": 7504.0, "qty": 6}]
    assert rec._has_protective_stop(6, orders, 7460.75) is False


def test_short_with_buy_stop_above_avg_is_protected():
    orders = [{"id": 1, "type": 3, "bs": 1, "price": 7459.5, "qty": 6}]
    assert rec._has_protective_stop(-6, orders, 7459.75) is True


def test_short_with_only_buy_target_below_is_naked():
    orders = [{"id": 1, "type": 1, "bs": 1, "price": 7450.5, "qty": 6}]
    assert rec._has_protective_stop(-6, orders, 7459.75) is False


def test_no_orders_is_naked():
    assert rec._has_protective_stop(4, [], 7460.0) is False
    assert rec._has_protective_stop(4, None, 7460.0) is False


def test_missing_avg_is_unknown_not_naked():
    """Typeless orders + avg missing → None (honest unknown, no alert) — Rule 1.
    Typed orders decide by type alone (price/avg-agnostic)."""
    typeless = [{"id": 1, "bs": 2, "price": 7431.5, "qty": 6}]
    assert rec._has_protective_stop(6, typeless, None) is None
    typed = [{"id": 1, "type": 2, "bs": 2, "price": 7431.5, "qty": 6}]
    assert rec._has_protective_stop(6, typed, None) is True


def test_locked_profit_stop_beyond_avg_is_protected():
    """Real 07-24 case: short -6 avg 7459.75 with buy STOP @7459.5 (locked
    profit, below avg) — type-based detection must call it PROTECTED."""
    orders = [{"id": 9577, "type": 3, "bs": 1, "price": 7459.5, "qty": 6}]
    assert rec._has_protective_stop(-6, orders, 7459.75) is True


# ── _manual_position_guard (episode logic) ───────────────────────────────────

@pytest.fixture
def _guard_env(monkeypatch):
    monkeypatch.setenv("MANUAL_POSITION_GUARD_V1", "1")
    monkeypatch.setenv("MANUAL_GUARD_GRACE_S", "0.01")
    monkeypatch.setenv("MANUAL_GUARD_REALERT_S", "300")
    rec._manual_guard["first_naked_ts"] = None
    rec._manual_guard["last_alert_ts"] = 0.0
    pushed = []
    import backend.v9.services.phone_alert as pa
    monkeypatch.setattr(pa, "push", lambda *a, **k: pushed.append(a), raising=False)
    yield pushed
    rec._manual_guard["first_naked_ts"] = None
    rec._manual_guard["last_alert_ts"] = 0.0


def test_naked_manual_alerts_after_grace(_guard_env, monkeypatch):
    monkeypatch.setattr(rec, "_sierra_state_orders", lambda: [])
    monkeypatch.setattr(rec, "_sierra_state_avg_price", lambda: 7460.0)
    assert rec._manual_position_guard(4) is None      # 1st sighting arms episode
    time.sleep(0.02)                                   # pass the grace
    alert = rec._manual_position_guard(4)              # 2nd sighting alerts
    assert alert and "NAKED" in alert and "alert-only" in alert
    assert len(_guard_env) == 1                        # phone push fired


def test_protected_manual_never_alerts(_guard_env, monkeypatch):
    monkeypatch.setattr(rec, "_sierra_state_orders",
                        lambda: [{"bs": 2, "price": 7431.5, "type": 2}])
    monkeypatch.setattr(rec, "_sierra_state_avg_price", lambda: 7460.0)
    assert rec._manual_position_guard(4) is None
    time.sleep(0.02)
    assert rec._manual_position_guard(4) is None
    assert len(_guard_env) == 0


def test_flag_off_is_silent(monkeypatch):
    monkeypatch.delenv("MANUAL_POSITION_GUARD_V1", raising=False)
    monkeypatch.setattr(rec, "_sierra_state_orders", lambda: [])
    monkeypatch.setattr(rec, "_sierra_state_avg_price", lambda: 7460.0)
    assert rec._manual_position_guard(4) is None


def test_realert_throttled(_guard_env, monkeypatch):
    monkeypatch.setattr(rec, "_sierra_state_orders", lambda: [])
    monkeypatch.setattr(rec, "_sierra_state_avg_price", lambda: 7460.0)
    rec._manual_position_guard(4)
    time.sleep(0.02)
    assert rec._manual_position_guard(4) is not None   # first alert
    assert rec._manual_position_guard(4) is None       # throttled (300s)
    assert len(_guard_env) == 1


def test_stop_added_resets_episode(_guard_env, monkeypatch):
    monkeypatch.setattr(rec, "_sierra_state_orders", lambda: [])
    monkeypatch.setattr(rec, "_sierra_state_avg_price", lambda: 7460.0)
    rec._manual_position_guard(4)                      # armed
    monkeypatch.setattr(rec, "_sierra_state_orders",
                        lambda: [{"bs": 2, "price": 7431.5, "type": 2}])
    assert rec._manual_position_guard(4) is None       # protected → reset
    assert rec._manual_guard["first_naked_ts"] is None
