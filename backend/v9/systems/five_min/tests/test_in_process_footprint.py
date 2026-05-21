"""P31-02b — FiveMinSystem.process_bar must read Footprint state in-process,
not via HTTP self-call to localhost:8000.

Background (docs/handoff/P31_TASK_BOARD.md §6.1):
  Synthetic firing UAT 2026-05-21 14:13 found process_bar consistently took
  ~8 seconds per bar. Source review located the root cause: 5-9 synchronous
  `requests.get('http://localhost:8000/api/v9/footprint/current', timeout=2)`
  and `/api/v9/tpo/current` self-calls per bar. Each call hits the FastAPI
  loop on localhost, costing ~900ms × ~9 ≈ 8s steady state.

P31-02b fix: FiveMinSystem.set_footprint_system(fp) lets backend.main inject
  the live FootprintSystem at startup. The helpers _get_cot/amt/belly_from_
  footprint and _footprint_state then read in-process (<1ms) instead of
  HTTP. Legacy HTTP fallback preserved for instances created without the
  setter (tests / pre-wire).

These tests pin the new behaviour:
  1. With injection: process_bar must NOT call requests.get for cot/amt/belly.
  2. _footprint_state returns the injected dict verbatim.
  3. The legacy fallback still works when no injection (no regression).
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from backend.v9.systems.five_min.five_min_system import FiveMinSystem


def _reactive_long_bars():
    return [
        {"o": 5250, "h": 5250, "l": 5247, "c": 5247.5, "v": 1000},
        {"o": 5248, "h": 5248, "l": 5247, "c": 5247.75, "v": 80},
        {"o": 5247.25, "h": 5249, "l": 5247.25, "c": 5248.75, "v": 800},
        {"o": 5248.5, "h": 5250, "l": 5248.5, "c": 5249.75, "v": 700},
    ]


def _make_sys() -> FiveMinSystem:
    sys = FiveMinSystem()
    sys._hydrated = True
    sys.current_state = {"last_reasoning_notes": ""}
    sys.last_pattern = None
    sys.last_classification = None
    sys.last_confluence = 0
    sys.opening_type = None
    return sys


def _mock_footprint(state: Dict[str, Any]) -> MagicMock:
    fp = MagicMock()
    fp.get_current.return_value = state
    return fp


def test_footprint_state_uses_injected_system_no_http():
    """When set_footprint_system is called, _footprint_state must NOT use requests."""
    sys = _make_sys()
    sys.set_footprint_system(_mock_footprint({"cot": 150.0, "amt": 100.0, "belly_ratio_dominant": True}))

    with patch("requests.get", side_effect=AssertionError("HTTP call must not happen when injected")):
        state = sys._footprint_state()

    assert state == {"cot": 150.0, "amt": 100.0, "belly_ratio_dominant": True}


def test_get_cot_from_footprint_uses_injected_system_no_http():
    sys = _make_sys()
    sys.set_footprint_system(_mock_footprint({"cot": 42.0}))

    with patch("requests.get", side_effect=AssertionError("HTTP call must not happen when injected")):
        assert sys._get_cot_from_footprint() == 42.0


def test_get_amt_from_footprint_uses_injected_system_no_http():
    sys = _make_sys()
    sys.set_footprint_system(_mock_footprint({"amt": 33.5}))

    with patch("requests.get", side_effect=AssertionError("HTTP call must not happen when injected")):
        assert sys._get_amt_from_footprint() == 33.5


def test_get_belly_from_footprint_uses_injected_system_no_http():
    sys = _make_sys()
    sys.set_footprint_system(_mock_footprint({"belly_ratio_dominant": True}))

    with patch("requests.get", side_effect=AssertionError("HTTP call must not happen when injected")):
        assert sys._get_belly_from_footprint() is True


def test_get_belly_returns_none_when_value_missing_in_injected_state():
    """belly_ratio_dominant=None must surface as None (not False) — explicit per §6.7."""
    sys = _make_sys()
    sys.set_footprint_system(_mock_footprint({"cot": 1.0, "amt": 1.0}))  # no belly key

    assert sys._get_belly_from_footprint() is None


def test_footprint_state_returns_empty_when_injected_get_current_raises():
    """Defensive: a crash in get_current must not propagate."""
    sys = _make_sys()
    fp = MagicMock()
    fp.get_current.side_effect = RuntimeError("simulated failure")
    sys.set_footprint_system(fp)

    assert sys._footprint_state() == {}


def test_legacy_path_no_injection_falls_back_to_requests():
    """Without set_footprint_system, the legacy HTTP fallback must still work."""
    sys = _make_sys()  # no injection
    fake_resp = MagicMock()
    fake_resp.ok = True
    fake_resp.json.return_value = {"cot": 7.0, "amt": 3.0}

    with patch("requests.get", return_value=fake_resp) as mock_get:
        state = sys._footprint_state()

    assert state == {"cot": 7.0, "amt": 3.0}
    assert mock_get.called, "legacy fallback must call requests.get when no injection"


def test_process_bar_with_injected_footprint_makes_no_http_calls():
    """Full process_bar with a 4-bar Reactive LONG buffer + injected footprint
    must NOT make any HTTP calls (proves the 8s SLOW root cause is fixed when wire-up active).
    """
    sys = _make_sys()
    sys.set_footprint_system(_mock_footprint({
        "cot": 150.0,
        "amt": 100.0,
        "belly_ratio_dominant": True,
    }))
    sys._bar_buffer = _reactive_long_bars()[:-1]

    with patch("requests.get", side_effect=AssertionError(
        "process_bar made an HTTP self-call — P31-02b regression"
    )):
        # Patch out the gateway and DB persist so this test stays unit-scoped.
        with patch("backend.v9.systems.five_min.five_min_system.emit_t1_setup",
                   return_value=MagicMock(pattern_name="REACTIVE_LONG",
                                          direction="LONG",
                                          confidence=80,
                                          entry_price=5249.75,
                                          stop_price=5246.5,
                                          t1_price=5253.0,
                                          t2_price=5256.25,
                                          sizing_contracts=1)), \
             patch("backend.v9.db.session.SessionLocal", return_value=MagicMock()), \
             patch.object(FiveMinSystem, "_compute_location_vs_poc", return_value="far"):
            # _compute_location_vs_poc is also a self-call site (TPO file/HTTP);
            # we stub it here so this test focuses purely on the footprint path.
            asyncio.run(sys.process_bar(_reactive_long_bars()[-1]))


def test_compute_location_vs_poc_prefers_sierra_file_over_http():
    """_compute_location_vs_poc must prefer the in-process Sierra file loader
    over a HTTP call to /api/v9/tpo/current (saves ~500ms per call)."""
    sys = _make_sys()

    with patch("backend.v9.api.v9.tpo_routes._load_sierra_tpo",
               return_value={"poc": 5250.0}) as mock_load, \
         patch("requests.get", side_effect=AssertionError(
             "HTTP fallback must not run when _load_sierra_tpo succeeds"
         )):
        loc = sys._compute_location_vs_poc({"h": 5250.5, "l": 5249.5})

    assert loc == "at"
    assert mock_load.called
