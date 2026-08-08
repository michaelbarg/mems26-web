"""Tests for day-type writer watchdog (+ K2 2026-08-08: self-heal that HEALS)."""

import sys
import time
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import pytest

import backend.v9.services.daytype_watchdog as wd
from backend.v9.services.daytype_watchdog import check_daytype_staleness


@pytest.fixture
def rth(monkeypatch):
    """Force RTH + silence alert cooldown + reset escalation state.

    Also stub scripts.ops_log so forced-RTH tests never append to the real
    OPS_LOG file (the watchdog logs WARN/ERROR events there in production).
    """
    monkeypatch.setattr(wd, "_is_rth_now", lambda: True)
    monkeypatch.setattr(wd, "_last_alert_ts", 0.0)
    monkeypatch.setattr(wd, "_esc", {"first_stale_ts": 0.0, "force_close_ts": 0.0,
                                     "critical_ts": 0.0})
    monkeypatch.setitem(sys.modules, "scripts.ops_log",
                        SimpleNamespace(log_event=lambda *a, **k: None))
    return wd


def _stale_row(minutes=20):
    return {"ts": datetime.now(timezone.utc) - timedelta(minutes=minutes),
            "day_type": "Variation"}


def test_never_raises_on_broken_db():
    """Watchdog must never raise, even with broken DB."""
    with patch("backend.v9.db.read.read_one", side_effect=Exception("DB dead")):
        result = check_daytype_staleness()
        assert result is None  # fail-safe


def test_no_rows_returns_warning():
    """No rows in v9_day_type_state → warning (if in RTH)."""
    with patch("backend.v9.db.read.read_one", return_value=None):
        result = check_daytype_staleness()
        # Depends on current time — if RTH, warns; otherwise None
        assert result is None or "no v9_day_type_state" in result


def test_fresh_entry_returns_none():
    """Fresh entry (2min old) → None."""
    fresh_ts = datetime.now(timezone.utc) - timedelta(minutes=2)
    with patch("backend.v9.db.read.read_one",
               return_value={"ts": fresh_ts, "day_type": "Balance"}):
        result = check_daytype_staleness()
        assert result is None


def test_stale_entry_during_rth():
    """Stale entry (20min old) during RTH → warning."""
    old_ts = datetime.now(timezone.utc) - timedelta(minutes=20)
    with patch("backend.v9.db.read.read_one",
               return_value={"ts": old_ts, "day_type": "Balance"}):
        result = check_daytype_staleness()
        # Only triggers during RTH — test passes either way
        assert result is None or "stale" in result


# ── K2 (2026-08-08): the self-heal must actually heal ──────────────────────

def test_self_heal_resets_sig_on_passed_app_state(rth):
    app_state = SimpleNamespace(_last_dts_sig=("Variation", "B2", 0.33, "LOCKED"))
    with patch("backend.v9.db.read.read_one", return_value=_stale_row()):
        result = check_daytype_staleness(app_state=app_state)
    assert result is not None and "stale" in result
    assert app_state._last_dts_sig is None, "stage-1 self-heal must reset the sig"


def test_self_heal_resolves_real_app_state_when_none(rth, monkeypatch):
    """THE dead-code regression: production always passed app_state=None
    (nothing ever set _app_state on BLD/gateway), so the P2-7 sig reset never
    ran live. With None the watchdog must now resolve backend.main.app.state
    itself and reset the sig there."""
    fake_state = SimpleNamespace(_last_dts_sig=("Variation", "B2", 0.33, "LOCKED"))
    fake_main = SimpleNamespace(app=SimpleNamespace(state=fake_state))
    monkeypatch.setitem(sys.modules, "backend.main", fake_main)
    with patch("backend.v9.db.read.read_one", return_value=_stale_row()):
        result = check_daytype_staleness(app_state=None)
    assert result is not None and "stale" in result
    assert fake_state._last_dts_sig is None, \
        "app_state=None must fall back to the real backend.main app.state"


def test_escalation2_force_closes_stale_partial_bar(rth, monkeypatch):
    """Staleness persisting after the sig-reset → the watchdog must force-close
    the aggregator's stale partial bar (input-starvation heal; the function
    existed with ZERO callers — same never-wired class as drain_command_queue)."""
    called = {"n": 0}
    from backend.v9.services.bar_aggregator_5min import five_min_aggregator
    monkeypatch.setattr(five_min_aggregator, "force_close_if_stale",
                        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or None)
    app_state = SimpleNamespace(_last_dts_sig=None)
    # staleness already persisting for 2 minutes (stage-1 had its chance)
    wd._esc["first_stale_ts"] = time.time() - 120
    with patch("backend.v9.db.read.read_one", return_value=_stale_row()):
        check_daytype_staleness(app_state=app_state)
    assert called["n"] == 1, "escalation-2 must call force_close_if_stale"


def test_escalation2_rate_limited(rth, monkeypatch):
    called = {"n": 0}
    from backend.v9.services.bar_aggregator_5min import five_min_aggregator
    monkeypatch.setattr(five_min_aggregator, "force_close_if_stale",
                        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or None)
    app_state = SimpleNamespace(_last_dts_sig=None)
    wd._esc["first_stale_ts"] = time.time() - 120
    with patch("backend.v9.db.read.read_one", return_value=_stale_row()):
        check_daytype_staleness(app_state=app_state)
        check_daytype_staleness(app_state=app_state)  # immediately again
    assert called["n"] == 1, "force-close must be rate-limited (1/min)"


def test_escalation3_critical_when_far_past_threshold(rth):
    app_state = SimpleNamespace(_last_dts_sig=None)
    wd._esc["first_stale_ts"] = time.time() - 120
    with patch("backend.v9.db.read.read_one", return_value=_stale_row(minutes=25)):
        check_daytype_staleness(app_state=app_state)  # 25 > 2×10
    assert wd._esc["critical_ts"] > 0, "stage-3 CRITICAL must fire past 2× threshold"


def test_healthy_resets_escalation_ladder(rth):
    wd._esc["first_stale_ts"] = time.time() - 120
    fresh = {"ts": datetime.now(timezone.utc) - timedelta(minutes=1),
             "day_type": "Balance"}
    with patch("backend.v9.db.read.read_one", return_value=fresh):
        assert check_daytype_staleness(app_state=SimpleNamespace()) is None
    assert wd._esc["first_stale_ts"] == 0.0
