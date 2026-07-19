"""D0 direction-authority map — pure expected rules (xfail until D1 wires production).

Spec: docs/handoff/DIRECTION_AUTHORITY_MAP_2026-07-19.md
Anti-tautology: each allow case has a mirrored block case (flip side / mig / family).

When D1 lands, replace `_d0_allowed` import with the real gateway helper and
remove the xfail marker on `test_production_hook_not_yet`.
"""
from __future__ import annotations

from typing import Optional, Tuple

import pytest

# ── Pure D0 reference (spec mirror — NOT production) ─────────────────────────

_ROTATION = frozenset({"Normal", "Variation", "Neutral_Center", "Neutral_Extreme"})
_TREND = frozenset({"Trend_Normal", "Trend_DD"})
_SKIP = frozenset({"Nontrend", "Nonconviction"})


def d0_allowed(
    *,
    day_type: str,
    family: str,  # CONT | REV
    direction: str,  # LONG | SHORT
    zone: str,  # near_val|below_value|mid|near_vah|above_value
    poc_side: str,  # below_poc | above_poc | at_poc
    poc_mig: str,  # UP | DOWN | FLAT | None
    expansion_dir: Optional[str] = None,  # UP | DOWN | None (Variation)
    trend_dir: Optional[str] = None,  # UP | DOWN | None (Trend_*)
) -> Tuple[bool, str]:
    """Return (allow, reason) per signed D0 map. Fail-open only when inputs missing
    is a *production* rule; this reference requires explicit inputs for tests."""
    d = direction.upper()
    fam = family.upper()
    mig = (poc_mig or "").upper() or "FLAT"

    if day_type in _SKIP:
        return False, f"{day_type}: SKIP"

    if day_type in _TREND:
        if fam == "REV":
            return False, "Trend: REV blocked"
        want = "LONG" if (trend_dir or "").upper() == "UP" else "SHORT"
        if d != want:
            return False, f"Trend: CONT must be with trend ({want})"
        return True, "Trend: CONT with trend (POC not a gate)"

    if day_type == "Variation":
        if fam == "CONT":
            if not expansion_dir:
                return True, "Variation CONT: no expansion signal (fail-open ref)"
            want = "LONG" if expansion_dir.upper() == "UP" else "SHORT"
            if d != want:
                return False, "Variation CONT against expansion"
            return True, "Variation CONT with expansion"
        # REV — edges after acceptance (simplified: correct fade edge)
        if d == "LONG" and zone in ("near_val", "below_value"):
            return True, "Variation REV at floor"
        if d == "SHORT" and zone in ("near_vah", "above_value"):
            return True, "Variation REV at ceiling"
        return False, "Variation REV wrong edge"

    if day_type in ("Neutral_Center", "Neutral_Extreme"):
        if fam == "CONT":
            return False, "Neutral: CONT blocked (balanced)"
        if d == "LONG" and zone in ("near_val", "below_value"):
            return True, "Neutral REV floor"
        if d == "SHORT" and zone in ("near_vah", "above_value"):
            return True, "Neutral REV ceiling"
        return False, "Neutral REV wrong edge"

    if day_type == "Normal":
        # #372 trap (rotation): CONT long above POC / short below POC
        if fam == "CONT":
            if poc_side == "above_poc" and d == "LONG":
                return False, "Normal CONT LONG above POC (#372)"
            if poc_side == "below_poc" and d == "SHORT":
                return False, "Normal CONT SHORT below POC (#372)"
            if mig == "FLAT":
                return False, "Normal CONT blocked when POC FLAT (REV-only)"
            if d == "LONG" and mig == "UP" and poc_side == "below_poc":
                return True, "Normal CONT LONG below POC + mig UP"
            if d == "SHORT" and mig == "DOWN" and poc_side == "above_poc":
                return True, "Normal CONT SHORT above POC + mig DOWN"
            return False, "Normal CONT needs mig aligned + correct POC side"
        # REV at edges
        if d == "LONG" and zone in ("near_val", "below_value"):
            return True, "Normal REV floor"
        if d == "SHORT" and zone in ("near_vah", "above_value"):
            return True, "Normal REV ceiling"
        return False, "Normal REV wrong edge"

    return True, f"unknown day_type={day_type} (fail-open ref)"


# ── Anti-tautology cases ─────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "kwargs,expect",
    [
        # Normal CONT allow
        (dict(day_type="Normal", family="CONT", direction="LONG", zone="near_val",
              poc_side="below_poc", poc_mig="UP"), True),
        # mirror block: same but above POC
        (dict(day_type="Normal", family="CONT", direction="LONG", zone="near_vah",
              poc_side="above_poc", poc_mig="UP"), False),
        # FLAT → REV only
        (dict(day_type="Normal", family="CONT", direction="LONG", zone="near_val",
              poc_side="below_poc", poc_mig="FLAT"), False),
        # Normal REV ceiling
        (dict(day_type="Normal", family="REV", direction="SHORT", zone="near_vah",
              poc_side="above_poc", poc_mig="FLAT"), True),
        # mirror: REV long at ceiling blocked
        (dict(day_type="Normal", family="REV", direction="LONG", zone="near_vah",
              poc_side="above_poc", poc_mig="FLAT"), False),
        # Trend CONT with trend
        (dict(day_type="Trend_Normal", family="CONT", direction="LONG", zone="mid",
              poc_side="above_poc", poc_mig="UP", trend_dir="UP"), True),
        # Trend CONT against + POC above still OK only if with trend — against blocked
        (dict(day_type="Trend_Normal", family="CONT", direction="SHORT", zone="mid",
              poc_side="above_poc", poc_mig="DOWN", trend_dir="UP"), False),
        # Trend REV blocked even at edge
        (dict(day_type="Trend_Normal", family="REV", direction="SHORT", zone="near_vah",
              poc_side="above_poc", poc_mig="FLAT", trend_dir="UP"), False),
        # Neutral CONT blocked
        (dict(day_type="Neutral_Center", family="CONT", direction="LONG", zone="near_val",
              poc_side="below_poc", poc_mig="UP"), False),
        # Nontrend SKIP
        (dict(day_type="Nontrend", family="CONT", direction="LONG", zone="near_val",
              poc_side="below_poc", poc_mig="UP"), False),
        # Variation CONT with expansion
        (dict(day_type="Variation", family="CONT", direction="LONG", zone="above_value",
              poc_side="above_poc", poc_mig="UP", expansion_dir="UP"), True),
        # Variation CONT against expansion
        (dict(day_type="Variation", family="CONT", direction="SHORT", zone="above_value",
              poc_side="above_poc", poc_mig="DOWN", expansion_dir="UP"), False),
    ],
)
def test_d0_reference_map_anti_tautology(kwargs, expect):
    allow, reason = d0_allowed(**kwargs)
    assert allow is expect, reason


def test_production_hook_not_yet():
    """D1 will export allowed_direction / extend daytype_position_gate.decide.
    Until then this stays xfail so CI stays green while the suite is ready."""
    try:
        from backend.v9.systems.daytype_position_gate import allowed_direction  # type: ignore
    except ImportError:
        pytest.xfail("D1 not shipped: allowed_direction missing")
    else:
        # When D1 lands, pin one Normal CONT trap case to production
        ok, _ = allowed_direction(
            day_type="Normal", family="CONT", direction="LONG",
            zone="near_vah", poc_side="above_poc", poc_mig="UP",
        )
        assert ok is False


# ── T11: pin existing daytype_position_gate (POC-level) + xfail migration ────

def test_t11_position_gate_blocks_cont_long_above_poc_when_on(monkeypatch):
    """Existing gate already enforces #372-class POC side when DAYTYPE_POSITION_GATE=1."""
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "1")
    monkeypatch.setenv("DAYTYPE_PATTERN_AWARE_V1", "0")  # isolate POC path
    from backend.v9.systems.daytype_position_gate import decide
    ok, reason = decide(
        pattern="ZLR",
        direction="LONG",
        day_type="Normal",
        entry_price=7610.0,
        tpo_ctx={"poc": 7600.0, "vah": 7620.0, "val": 7580.0},
    )
    assert ok is False, reason
    assert "POC" in reason or "above" in reason.lower()


def test_t11_position_gate_allows_cont_long_below_poc_when_on(monkeypatch):
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "1")
    monkeypatch.setenv("DAYTYPE_PATTERN_AWARE_V1", "0")
    from backend.v9.systems.daytype_position_gate import decide
    ok, reason = decide(
        pattern="ZLR",
        direction="LONG",
        day_type="Normal",
        entry_price=7590.0,
        tpo_ctx={"poc": 7600.0, "vah": 7620.0, "val": 7580.0},
    )
    assert ok is True, reason


def test_t11_trend_poc_not_a_gate_allows_long_above_poc(monkeypatch):
    """D0: Trend → POC not a direction gate; WITH IB break only."""
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "1")
    monkeypatch.setenv("DAYTYPE_PATTERN_AWARE_V1", "0")
    from backend.v9.systems.daytype_position_gate import decide
    ok, reason = decide(
        pattern="ZLR",
        direction="LONG",
        day_type="Trend_Normal",
        entry_price=7610.0,
        tpo_ctx={
            "poc": 7600.0, "vah": 7620.0, "val": 7580.0,
            "ib_high": 7595.0, "ib_low": 7580.0,
            "session_high": 7615.0, "session_low": 7585.0,
        },
    )
    assert ok is True, reason


def test_t11_poc_migration_not_yet_in_gate():
    src = open("backend/v9/systems/daytype_position_gate.py").read()
    if "poc_mig" not in src and "poc_migration" not in src and "mig" not in src.lower():
        pytest.xfail("D1 POC-migration input not yet wired into daytype_position_gate")
    assert "poc_mig" in src or "poc_migration" in src
