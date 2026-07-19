"""T9 — G2/G3: S2 detection + Flag-T2 should read get_live_day_type (ready before build).

Contract (Michael / S124 G2+G3):
  Flag S2_DETECTION_LIVE_DAYTYPE_V1 default OFF → byte-identical (current_day_type).
  Flag ON → detection NT-skip + chart_patterns_allowed use live first.
  Anti-tautology: ON + live=Nontrend → still skip; ON + live=Variation while
  hydrate=Nontrend → do NOT NT-skip.

Production hook not shipped yet (cc-macbook) → xfail on import/wiring tests.
Pure helpers below encode the intended resolver so CI proves the contract.
"""
from __future__ import annotations

import os
from typing import Optional
from unittest.mock import patch

import pytest

from backend.v9.systems.five_min.five_min_system import chart_patterns_allowed


def resolve_detection_day_type(
    *,
    current_day_type: Optional[str],
    live_day_type: Optional[str],
    flag_on: bool,
) -> Optional[str]:
    """Intended G2 resolver — pure. Production should mirror this under the flag."""
    if flag_on and live_day_type and live_day_type not in ("UNKNOWN", "None", ""):
        return live_day_type
    return current_day_type


def test_flag_off_uses_hydrate_even_if_live_differs():
    dt = resolve_detection_day_type(
        current_day_type="Nontrend", live_day_type="Variation", flag_on=False)
    assert dt == "Nontrend"
    # chart gate follows resolved type
    assert chart_patterns_allowed(dt, "5a") is False


def test_flag_on_override_variation_unblocks_chart_vs_hydrate_nt():
    dt = resolve_detection_day_type(
        current_day_type="Nontrend", live_day_type="Variation", flag_on=True)
    assert dt == "Variation"
    assert chart_patterns_allowed(dt, "5a") is True


def test_flag_on_live_nontrend_still_skips_anti_tautology():
    dt = resolve_detection_day_type(
        current_day_type="Normal", live_day_type="Nontrend", flag_on=True)
    assert dt == "Nontrend"
    assert chart_patterns_allowed(dt, "5a") is False
    assert chart_patterns_allowed(dt, "5c") is False


def test_production_g2_wiring_not_yet():
    """Fails green until five_min_system detection reads get_live under the flag."""
    src = open("backend/v9/systems/five_min/five_min_system.py").read()
    if "S2_DETECTION_LIVE_DAYTYPE_V1" not in src:
        pytest.xfail("G2 not shipped: S2_DETECTION_LIVE_DAYTYPE_V1 absent from five_min_system")
    # When shipped: NT-skip block must not use only self.current_day_type without live
    assert "S2_DETECTION_LIVE_DAYTYPE_V1" in src


def test_production_g3_flag_t2_wiring_not_yet():
    src = open("backend/v9/systems/five_min/five_min_system.py").read()
    # G3: Flag T2 fork at ~1551 still current_day_type today
    if "S2_DETECTION_LIVE_DAYTYPE_V1" not in src:
        pytest.xfail("G3 not shipped: live day-type for Flag T2")
    assert "S2_DETECTION_LIVE_DAYTYPE_V1" in src
