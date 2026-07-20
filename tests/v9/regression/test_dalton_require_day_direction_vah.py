"""Dalton Alignment — SHORT @ VAH on Variation-down despite CCI BLUE.

Real case 2026-07-20 ~12:11 ET: price 7532 > VAH 7527.5 (ceiling), day =
Variation-DOWN (Michael override). Correct trade = responsive SHORT at VAH.
Blocked by require_with_trend(trend_state=BLUE bounce).

Dalton rule (§3): require_with_trend = against DAY DIRECTION, not momentary
CCI/trend_state. Responsive fade allowed at value extreme IN day direction
(SHORT near VAH on Variation-down / LONG near VAL on Variation-up).

Flag REQUIRE_WITH_TREND_DAY_DIRECTION_V1 (default OFF):
  ON  → SHORT@VAH + BLUE = verdict ≠ SKIP
  OFF → legacy SKIP on BLUE (byte-identical)
"""
from __future__ import annotations

import pytest

from backend.v9.systems.daytype_playbook import decide

# Live-day levels (VAH from Dalton handoff)
_LEVELS = {"vah": 7527.5, "val": 7490.0, "ib_width": 40.0}
_ENTRY_AT_VAH = 7532.0  # above VAH → above_value / near ceiling


def allow_responsive_fade(
    *,
    day_type: str,
    day_dir: str,  # UP | DOWN — expansion / day direction
    direction: str,  # LONG | SHORT
    location: str,  # at_VAH | at_VAL | mid | other
    trend_state: str | None = None,
) -> bool:
    """Pure Dalton contract (no playbook YAML)."""
    dt = (day_type or "").strip()
    if not dt.startswith(("Variation", "Trend", "Normal_Variation")):
        return True  # non-directional: leave to other gates
    ddir = (day_dir or "").upper()
    want = (direction or "").upper()
    loc = (location or "").lower()
    # With-day-direction continuation always allowed
    if (ddir == "DOWN" and want == "SHORT") or (ddir == "UP" and want == "LONG"):
        return True
    # Responsive fade: opposite-of-bounce OK only at value extreme in day direction
    if ddir == "DOWN" and want == "SHORT" and loc in ("at_vah", "vah"):
        return True
    if ddir == "UP" and want == "LONG" and loc in ("at_val", "val"):
        return True
    # Counter-day at wrong location blocked regardless of CCI color
    return False


def test_contract_short_at_vah_variation_down_allows_blue_bounce():
    """The live miss: Variation-down + SHORT@VAH + BLUE must be ALLOWED."""
    assert allow_responsive_fade(
        day_type="Variation",
        day_dir="DOWN",
        direction="SHORT",
        location="at_VAH",
        trend_state="BLUE",
    ) is True


def test_contract_long_at_vah_variation_down_blocked():
    """LONG into Variation-down ceiling is counter-day — blocked."""
    assert allow_responsive_fade(
        day_type="Variation",
        day_dir="DOWN",
        direction="LONG",
        location="at_VAH",
        trend_state="BLUE",
    ) is False


def test_contract_short_mid_range_variation_down_allowed_as_with_day():
    """SHORT with day direction allowed even mid-range (CONT path)."""
    assert allow_responsive_fade(
        day_type="Variation",
        day_dir="DOWN",
        direction="SHORT",
        location="mid",
        trend_state="BLUE",
    ) is True


def test_flag_off_still_skips_blue_short_byte_identical(monkeypatch):
    """OFF → legacy: decide(REACTIVE, Variation, SHORT, BLUE) → SKIP."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    monkeypatch.delenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", raising=False)
    d = decide("REACTIVE", "Variation", "SHORT", trend_state="BLUE")
    assert d.verdict == "SKIP", f"OFF must stay SKIP on BLUE; got {d}"


def test_flag_on_short_at_vah_blue_not_skip(monkeypatch):
    """ON → live miss fixed: SHORT@VAH + BLUE → verdict ≠ SKIP."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    monkeypatch.setenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "1")
    d = decide(
        "REACTIVE", "Variation", "SHORT",
        trend_state="BLUE",
        day_direction="DOWN",
        location="at_VAH",
    )
    assert d.verdict != "SKIP", f"expected allow under ON; got {d}"
    assert d.verdict in ("FULL", "REDUCED")


def test_flag_on_short_at_vah_via_entry_levels(monkeypatch):
    """ON → entry above VAH derives location; BLUE ignored."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    monkeypatch.setenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "1")
    d = decide(
        "REACTIVE", "Variation", "SHORT",
        trend_state="BLUE",
        day_direction="DOWN",
        entry_price=_ENTRY_AT_VAH,
        levels=_LEVELS,
    )
    assert d.verdict != "SKIP", f"got {d}"


def test_flag_on_long_at_vah_still_skip(monkeypatch):
    """ON → LONG at VAH (wrong location for fade) → SKIP."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    monkeypatch.setenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "1")
    d = decide(
        "REACTIVE", "Variation", "LONG",
        trend_state="BLUE",
        day_direction="DOWN",
        location="at_VAH",
    )
    assert d.verdict == "SKIP", f"LONG@VAH must SKIP; got {d}"


def test_flag_on_hns_short_at_vah_allows_blue(monkeypatch):
    """HNS is responsive-REV — same location rule as REACTIVE."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    monkeypatch.setenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "1")
    d = decide(
        "HNS_TOP", "Variation", "SHORT",
        trend_state="BLUE",
        day_direction="DOWN",
        location="near_vah",
    )
    assert d.verdict != "SKIP", f"got {d}"


def test_flag_on_confluence_uses_day_direction_not_blue(monkeypatch):
    """Non-responsive require_with_trend: day_dir DOWN + SHORT passes despite BLUE."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    monkeypatch.setenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "1")
    d = decide(
        "CONFLUENCE_RI_ZLR", "Variation", "SHORT",
        trend_state="BLUE",
        day_direction="DOWN",
    )
    assert d.verdict != "SKIP", f"with-day SHORT must pass; got {d}"
    d_bad = decide(
        "CONFLUENCE_RI_ZLR", "Variation", "LONG",
        trend_state="BLUE",
        day_direction="DOWN",
    )
    assert d_bad.verdict == "SKIP", f"counter-day LONG must SKIP; got {d_bad}"


def test_flag_off_ignores_day_direction_kwargs(monkeypatch):
    """OFF + day_direction/location kwargs must not change legacy SKIP on BLUE."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    monkeypatch.setenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "0")
    d = decide(
        "REACTIVE", "Variation", "SHORT",
        trend_state="BLUE",
        day_direction="DOWN",
        location="at_VAH",
    )
    assert d.verdict == "SKIP", f"kwargs must be ignored when OFF; got {d}"


def test_playbook_red_short_on_variation_still_full(monkeypatch):
    """With-color path: SHORT + RED on Variation remains FULL (flag OFF)."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    monkeypatch.delenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", raising=False)
    d = decide("REACTIVE", "Variation", "SHORT", trend_state="RED")
    assert d.verdict in ("FULL", "REDUCED")
