"""T-220 — /api/v9/day_type/state must never pass off the dead engine as a reading.

Root class (CLAUDE.md Rule 1 "honest failure > synthetic value" + "no silent
failures"): backend/v9/systems/day_type/api.py::get_state had

    except Exception:
        pass
    engine = _get_engine()                 # NEVER fed a bar
    state = engine._build_state(zero-bar)  # A1 / UNKNOWN / conf 0.0
    return DayTypeStateResponse(state=state)

which returned a fully-populated, plausible payload from a state machine that
receives no bars, with no marker and no log. Six live consumers read the route
(scripts/fire_drill.py · scripts/morning_briefing.py · scripts/s6_eod_report.py ·
scripts/mems26_preflight.sh · scripts/uat_prompt_4.sh · ChartV5a.tsx) and
fire_drill's `bool(st["day_type"])` check PASSES on the synthetic "UNKNOWN".

Anti-tautological: calls the REAL production route function, not a copy.

if reverted -> RED because: restoring `except Exception: pass` + the unmarked
fallback removes meta.source/meta.degraded, so test_fallback_is_labelled_degraded
and test_db_path_is_labelled_source_db both fail.
"""
import pytest
from unittest.mock import patch


def _meta(resp):
    st = resp.state
    return st.meta if isinstance(st.meta, dict) else {}


def test_fallback_is_labelled_degraded_when_db_read_raises():
    """DB read raising must produce an explicitly DEGRADED, sourced payload."""
    from backend.v9.systems.day_type import api as dt_api

    with patch("backend.v9.db.read.read_one", side_effect=RuntimeError("boom")):
        resp = dt_api.get_state()

    meta = _meta(resp)
    assert meta.get("degraded") is True, meta
    assert meta.get("source") == "dead_engine_fallback", meta
    assert "db_read_failed" in str(meta.get("degraded_reason")), meta


def test_fallback_is_labelled_degraded_when_no_row():
    """No row in v9_day_type_state must also be marked, not silently faked."""
    from backend.v9.systems.day_type import api as dt_api

    with patch("backend.v9.db.read.read_one", return_value=None):
        resp = dt_api.get_state()

    meta = _meta(resp)
    assert meta.get("degraded") is True, meta
    assert meta.get("source") == "dead_engine_fallback", meta
    assert meta.get("degraded_reason") == "no_row_in_v9_day_type_state", meta


def test_db_path_is_labelled_source_db():
    """A real row must be labelled source=v9_day_type_state, degraded=False."""
    from backend.v9.systems.day_type import api as dt_api

    row = {
        "ts": None, "stage": "B2", "day_type": "Neutral_Center",
        "confidence": 0.67, "lock_state": "LOCKED_LOW_CONF",
        "opening_type": "OPEN_DRIVE", "ib_width_class": "EXTREME",
        "behavior": "DEVELOPING",
    }
    with patch("backend.v9.db.read.read_one", return_value=row):
        resp = dt_api.get_state()

    meta = _meta(resp)
    assert meta.get("degraded") is False, meta
    assert meta.get("source") == "v9_day_type_state", meta
    assert resp.state.day_type.value == "Neutral_Center"


def test_real_and_fallback_payloads_are_distinguishable():
    """The whole point: a consumer must be able to tell them apart."""
    from backend.v9.systems.day_type import api as dt_api

    row = {
        "ts": None, "stage": "B2", "day_type": "Neutral_Center",
        "confidence": 0.67, "lock_state": "LOCKED_LOW_CONF",
        "opening_type": "OPEN_DRIVE", "ib_width_class": "EXTREME",
        "behavior": "DEVELOPING",
    }
    with patch("backend.v9.db.read.read_one", return_value=row):
        good = _meta(dt_api.get_state())
    with patch("backend.v9.db.read.read_one", side_effect=RuntimeError("boom")):
        bad = _meta(dt_api.get_state())

    assert good.get("source") != bad.get("source")
    assert good.get("degraded") is not bad.get("degraded")


# ── second state holder: the disconnected wrapper must not build a machine ──

def test_daytype_wrapper_builds_no_second_machine_at_construction():
    """T-220: DayTypeSystem() is registered in the LIVE process
    (backend/v9/app.py::init_event_dispatcher). It must not construct a second
    DayTypeStateMachine next to the canonical app.state.day_type_machine.

    if reverted -> RED because: restoring `self._machine = DayTypeStateMachine()`
    in __init__ makes _machine non-None at construction.
    """
    from backend.v9.systems.wrappers import DayTypeSystem

    sysobj = DayTypeSystem()
    assert sysobj._machine is None, (
        "DayTypeSystem built a second DayTypeStateMachine at construction")
    # and it stays disconnected, so the dispatcher never feeds it
    assert DayTypeSystem.subscribed_streams == []


def test_daytype_wrapper_machine_is_lazy_and_loud(caplog):
    """If the dead path ever comes alive it must announce itself."""
    import logging
    from backend.v9.systems.wrappers import DayTypeSystem

    sysobj = DayTypeSystem()
    with caplog.at_level(logging.WARNING, logger="backend.v9.systems.wrappers"):
        m = sysobj._get_machine()
    assert m is not None
    assert any("SECOND DayTypeStateMachine" in r.message or
               "SECOND DayTypeStateMachine" in r.getMessage()
               for r in caplog.records), [r.getMessage() for r in caplog.records]
