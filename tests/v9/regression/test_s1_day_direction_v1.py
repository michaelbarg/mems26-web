# -*- coding: utf-8 -*-
"""S1_DAY_DIRECTION_V1 — get_live_expansion must read the app that actually runs.

Root cause (cowork 2026-08-25): `get_live_expansion()` resolved
`backend.v9.app.app`, a DIFFERENT FastAPI object from the one the process runs.
The sole writer of `last_cls_result` is `backend/main.py:674` on
`backend.main.app`. So priority-1 of the gateway `day_direction` chain
(`trading_gateway.py:1234-1239`) was permanently dead and day_direction always
fell through to the LSMA `get_live_dir_bias`.

THE TEST THAT WOULD HAVE CAUGHT IT (the one missing today): write the classifier
result to the REAL app — `backend.main.app` — exactly as main.py does, and assert
the function reports it. A flag-ON run against a dead source returns None and
fails here; that is the whole point.
"""
import importlib

import pytest

from backend.v9.services.trade_context import get_live_expansion


@pytest.fixture
def real_app_state():
    """The app object `backend/main.py` actually writes to, cleaned up after."""
    main = importlib.import_module("backend.main")
    prev = getattr(main.app.state, "last_cls_result", None)
    yield main.app.state
    main.app.state.last_cls_result = prev


@pytest.fixture
def legacy_app_state():
    """The stale object the pre-fix code read (`backend.v9.app`)."""
    v9app = importlib.import_module("backend.v9.app")
    prev = getattr(v9app.app.state, "last_cls_result", None)
    yield v9app.app.state
    v9app.app.state.last_cls_result = prev


# --------------------------------------------------------------------------
# 1. THE REGRESSION: flag ON must read the LIVE source.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("direction,ref", [("DOWN", "IB_LOW"), ("UP", "PDH")])
def test_flag_on_reads_the_running_app(monkeypatch, real_app_state, direction, ref):
    """Fails loudly if the source is dead — today's actual defect."""
    monkeypatch.setenv("S1_DAY_DIRECTION_V1", "1")
    real_app_state.last_cls_result = {
        "accepted_break": direction,
        "accepted_break_ref": ref,
    }

    got = get_live_expansion()

    assert got is not None, (
        "get_live_expansion() returned None while backend.main.app.state."
        "last_cls_result held an accepted_break — the source is dead again."
    )
    assert got["dir"] == direction
    assert got["ref"] == ref


def test_flag_on_falls_back_to_break_dir(monkeypatch, real_app_state):
    """`break_dir` is the documented secondary key."""
    monkeypatch.setenv("S1_DAY_DIRECTION_V1", "1")
    real_app_state.last_cls_result = {"break_dir": "UP", "reclass_ref": "VAH"}
    assert get_live_expansion() == {"dir": "UP", "ref": "VAH"}


def test_flag_on_is_honest_when_no_break(monkeypatch, real_app_state):
    """No accepted expansion → honest None (Rule 1), never a synthesised guess."""
    monkeypatch.setenv("S1_DAY_DIRECTION_V1", "1")
    real_app_state.last_cls_result = {"day_type": "Normal_Variation"}
    assert get_live_expansion() is None


def test_flag_on_ignores_garbage_direction(monkeypatch, real_app_state):
    monkeypatch.setenv("S1_DAY_DIRECTION_V1", "1")
    real_app_state.last_cls_result = {"accepted_break": "SIDEWAYS"}
    assert get_live_expansion() is None


def test_no_confidence_leaks_into_the_result(monkeypatch, real_app_state):
    """Michael ruling: Dalton is binary — no confidence percentages, any stage."""
    monkeypatch.setenv("S1_DAY_DIRECTION_V1", "1")
    real_app_state.last_cls_result = {
        "accepted_break": "DOWN",
        "accepted_break_ref": "IB_LOW",
        "confidence": 0.73,
        "confidence_raw": 0.61,
    }
    got = get_live_expansion()
    assert set(got.keys()) == {"dir", "ref"}
    assert not any("conf" in k for k in got)


# --------------------------------------------------------------------------
# 2. FLAG OFF: byte-identical to today.
# --------------------------------------------------------------------------

def test_flag_off_is_identical_to_today(monkeypatch, real_app_state, legacy_app_state):
    """OFF ignores the live source entirely — the pre-fix (dead) behaviour."""
    monkeypatch.delenv("S1_DAY_DIRECTION_V1", raising=False)
    real_app_state.last_cls_result = {
        "accepted_break": "DOWN", "accepted_break_ref": "IB_LOW",
    }
    legacy_app_state.last_cls_result = None

    assert get_live_expansion() is None, (
        "flag OFF must not change behaviour — it read the live app anyway."
    )


def test_flag_off_still_reads_the_legacy_object(monkeypatch, legacy_app_state):
    """OFF path is preserved exactly: if anything ever wrote there, it is read."""
    monkeypatch.delenv("S1_DAY_DIRECTION_V1", raising=False)
    legacy_app_state.last_cls_result = {
        "accepted_break": "UP", "accepted_break_ref": "PDH",
    }
    assert get_live_expansion() == {"dir": "UP", "ref": "PDH"}


@pytest.mark.parametrize("val", ["0", "false", "no", "off", ""])
def test_falsey_flag_values_stay_off(monkeypatch, real_app_state, legacy_app_state, val):
    monkeypatch.setenv("S1_DAY_DIRECTION_V1", val)
    real_app_state.last_cls_result = {"accepted_break": "DOWN"}
    legacy_app_state.last_cls_result = None
    assert get_live_expansion() is None


@pytest.mark.parametrize("val", ["1", "true", "yes", "on", "TRUE", " 1 "])
def test_truthy_flag_values_turn_it_on(monkeypatch, real_app_state, val):
    monkeypatch.setenv("S1_DAY_DIRECTION_V1", val)
    real_app_state.last_cls_result = {"accepted_break": "DOWN", "accepted_break_ref": "IB_LOW"}
    assert get_live_expansion() == {"dir": "DOWN", "ref": "IB_LOW"}


# --------------------------------------------------------------------------
# 3. FAIL-SAFE: any error → None → existing chain continues.
# --------------------------------------------------------------------------

def test_import_failure_is_fail_safe(monkeypatch):
    """A broken import must yield None, never propagate into the gateway."""
    monkeypatch.setenv("S1_DAY_DIRECTION_V1", "1")
    import importlib as _il

    def _boom(name, *a, **kw):
        raise ImportError("simulated")

    monkeypatch.setattr(_il, "import_module", _boom)
    assert get_live_expansion() is None


def test_non_dict_result_is_fail_safe(monkeypatch, real_app_state):
    monkeypatch.setenv("S1_DAY_DIRECTION_V1", "1")
    real_app_state.last_cls_result = "not-a-dict"
    assert get_live_expansion() is None
