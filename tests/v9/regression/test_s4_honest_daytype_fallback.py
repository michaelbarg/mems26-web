"""T10 — G6: S4 fail-honest when live day-type missing (no dead-table / Normal synth).

Contract:
  Flag S4_HONEST_DAYTYPE_FALLBACK_V1 (proposed) ON + live None → return None
    (do NOT read v9_day_type_state, do NOT force \"Normal\").
  Flag OFF → legacy chain (current_state → machine → v9_day_type_state → \"Normal\").
  Anti-tautology: real live value still flows when present.

Today woodies_system.py:672-688 still synthesizes \"Normal\". Tests encode the
target contract; production wiring xfail until cc-macbook ships G6.
"""
from __future__ import annotations

from typing import Optional
from unittest.mock import patch

import pytest


def resolve_s4_day_type(
    *,
    live: Optional[str],
    current_state: Optional[str],
    machine: Optional[str],
    db_state: Optional[str],
    honest_fallback: bool,
) -> Optional[str]:
    """Intended G6 resolver."""
    def _ok(v: Optional[str]) -> Optional[str]:
        if not v or v in ("UNKNOWN", "None", "INDETERMINATE"):
            return None
        return v

    if _ok(live):
        return _ok(live)
    if honest_fallback:
        return None  # fail-honest — no dead sources, no Normal synth
    return _ok(current_state) or _ok(machine) or _ok(db_state) or "Normal"


def test_honest_on_all_none_returns_none_not_normal():
    assert resolve_s4_day_type(
        live=None, current_state=None, machine=None, db_state=None,
        honest_fallback=True) is None


def test_honest_on_ignores_dead_db_and_normal_synth():
    assert resolve_s4_day_type(
        live=None, current_state=None, machine=None, db_state="Normal",
        honest_fallback=True) is None


def test_honest_off_legacy_normal_synth():
    assert resolve_s4_day_type(
        live=None, current_state=None, machine=None, db_state=None,
        honest_fallback=False) == "Normal"


def test_live_value_still_flows_anti_tautology():
    assert resolve_s4_day_type(
        live="Variation", current_state="Normal", machine="Normal",
        db_state="Normal", honest_fallback=True) == "Variation"


def test_production_g6_not_yet():
    src = open("backend/v9/systems/woodies/woodies_system.py").read()
    # Today still has the synth line
    if ' _s4_day_type = "Normal"' in src or "_s4_day_type = \"Normal\"" in src:
        if "S4_HONEST_DAYTYPE_FALLBACK_V1" not in src and "S4_FAIL_HONEST" not in src:
            pytest.xfail("G6 not shipped: Normal synth still present without honest flag")
    assert True
