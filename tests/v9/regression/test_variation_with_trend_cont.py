"""W4 — VARIATION_WITH_TREND_CONT_V1: with-trend continuation on directional Variation (2026-07-25).

Live incident (07-24): Variation-UP day, REACTIVE LONG @7478 was BLOCKED "not at VAL
(above_value)" while a counter-trend SHORT went live. The fix allows with-trend
continuation entries on directional Variation days using session-extreme distance for
chase detection (IB-scaled), not value-location.

Tests (anti-tautological — real fixtures from 07-24):
1. Today's miss: REACTIVE LONG @7478 on Variation-UP → ALLOW when flag ON; SKIP when OFF
2. Chasing: REACTIVE LONG @7487 (dist 2.5 < 6) → SKIP even with flag ON
3. Counter-trend: SHORT on Variation-UP → falls to location-fade (ruling #3)
4. Trend days unchanged: Trend_Normal behavior byte-identical
5. OFF = byte-identical: flag unset → every case returns today's verdict
6. IB-scaled chase threshold: max(6, 0.25 * ib_width)
"""
import os
import pytest


@pytest.fixture(autouse=True)
def _enable_playbook_and_prereqs(monkeypatch):
    """Enable the playbook + prerequisite flags for all tests."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "1")
    monkeypatch.setenv("RESPONSIVE_WITH_DAY_TREND_V1", "1")
    monkeypatch.setenv("NEVERFADE_TREND_ONLY_V1", "1")
    # Reset the cached config so tests don't interfere
    from backend.v9.systems.daytype_playbook import reset_cache
    reset_cache()
    yield
    reset_cache()


# Real levels from 07-24 live session
LEVELS_0724 = {
    "vah": 7465.0, "val": 7445.0, "ib_width": 20.0,
    "day_high": 7489.5, "day_low": 7431.25,
}


# ── Test 1: Today's miss — REACTIVE LONG @7478 on Variation-UP → ALLOW ──────

def test_variation_up_with_trend_long_allowed(monkeypatch):
    """The 07-24 miss: REACTIVE LONG @7478 on Variation-UP should be ALLOWED."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="LONG",
        day_direction="UP", location="above_value", entry_price=7478.0,
        levels=LEVELS_0724, variation_phase="EXPANSION",
    )
    assert d.allow, f"Expected ALLOW but got SKIP: {d.reason}"


def test_variation_up_with_trend_long_blocked_when_off(monkeypatch):
    """Flag OFF → the same entry is SKIP (today's behavior, byte-identical)."""
    monkeypatch.delenv("VARIATION_WITH_TREND_CONT_V1", raising=False)
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="LONG",
        day_direction="UP", location="above_value", entry_price=7478.0,
        levels=LEVELS_0724,
    )
    assert not d.allow, f"Expected SKIP but got ALLOW: {d.reason}"
    assert "not at VAL" in d.reason or "above_value" in d.reason


# ── Test 2: Chasing — LONG @7487 (dist=2.5 < 6) → SKIP ─────────────────────

def test_variation_up_chasing_blocked(monkeypatch):
    """Entry too close to day_high (7489.5 - 7487 = 2.5 < 6) → SKIP even with flag ON."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="LONG",
        day_direction="UP", location="above_value", entry_price=7487.0,
        variation_phase="EXPANSION",
        levels=LEVELS_0724,
    )
    assert not d.allow, f"Expected SKIP (chasing) but got ALLOW: {d.reason}"
    assert "chasing" in d.reason.lower()


# ── Test 3: Counter-trend on Variation → location-fade (ruling #3) ───────────

def test_variation_up_counter_trend_short_at_vah_allowed(monkeypatch):
    """Counter-trend SHORT at VAH on Variation-UP → ALLOW (location fade works)."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="SHORT",
        day_direction="UP", location="near_vah", entry_price=7465.0,
        levels=LEVELS_0724,
    )
    assert d.allow, f"Expected ALLOW (counter at VAH) but got SKIP: {d.reason}"


def test_variation_up_counter_trend_short_at_mid_blocked(monkeypatch):
    """Counter-trend SHORT NOT at VAH on Variation-UP → SKIP."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="SHORT",
        day_direction="UP", location="mid_value", entry_price=7455.0,
        levels=LEVELS_0724,
    )
    assert not d.allow, f"Expected SKIP (counter not at edge) but got ALLOW: {d.reason}"


# ── Test 4: Trend days unchanged ─────────────────────────────────────────────

def test_trend_day_with_trend_still_works(monkeypatch):
    """On Trend_Normal, with-trend LONG on UP-day → ALLOW (not affected by W4)."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Trend_Normal", direction="LONG",
        day_direction="UP", location="mid_value", entry_price=7460.0,
        levels=LEVELS_0724,
    )
    assert d.allow, f"Expected ALLOW on Trend day but got SKIP: {d.reason}"


def test_trend_day_counter_trend_still_blocked(monkeypatch):
    """On Trend_Normal, counter-trend SHORT on UP-day → SKIP (never fade)."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Trend_Normal", direction="SHORT",
        day_direction="UP", location="mid_value", entry_price=7460.0,
        levels=LEVELS_0724,
    )
    assert not d.allow, f"Expected SKIP (counter on Trend) but got ALLOW: {d.reason}"


# ── Test 5: OFF = byte-identical ─────────────────────────────────────────────
# (covered by test_variation_up_with_trend_long_blocked_when_off above)


# ── Test 6: IB-scaled chase threshold ────────────────────────────────────────

def test_ib_scaled_chase_threshold(monkeypatch):
    """With wide IB (40pt), threshold = max(6, 0.25*40) = 10. Entry at dist=8 → SKIP."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    wide_levels = {
        "vah": 7460.0, "val": 7420.0, "ib_width": 40.0,
        "day_high": 7500.0, "day_low": 7410.0,
    }
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="LONG",
        day_direction="UP", location="above_value", entry_price=7493.0,
        variation_phase="EXPANSION",
        levels=wide_levels,
    )
    # dist = 7500 - 7493 = 7 < max(6, 0.25*40) = 10 → SKIP (chasing)
    assert not d.allow, f"Expected SKIP (IB-scaled chase) but got ALLOW: {d.reason}"


def test_ib_scaled_chase_not_chasing(monkeypatch):
    """With wide IB (40pt), threshold=10. Entry at dist=15 → ALLOW."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    wide_levels = {
        "vah": 7460.0, "val": 7420.0, "ib_width": 40.0,
        "day_high": 7500.0, "day_low": 7410.0,
    }
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="LONG",
        day_direction="UP", location="above_value", entry_price=7485.0,
        variation_phase="EXPANSION",
        levels=wide_levels,
    )
    # dist = 7500 - 7485 = 15 >= 10 → ALLOW (not chasing)
    assert d.allow, f"Expected ALLOW but got SKIP: {d.reason}"


# ── Test: SHORT with-trend on Variation-DOWN ─────────────────────────────────

def test_variation_down_with_trend_short_allowed(monkeypatch):
    """Symmetric: SHORT on Variation-DOWN → ALLOW as continuation."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    down_levels = {
        "vah": 7465.0, "val": 7445.0, "ib_width": 20.0,
        "day_high": 7480.0, "day_low": 7420.0,
    }
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="SHORT",
        day_direction="DOWN", location="below_value", entry_price=7435.0,
        variation_phase="EXPANSION",
        levels=down_levels,
    )
    # dist = 7435 - 7420 = 15 >= 6 → ALLOW
    assert d.allow, f"Expected ALLOW but got SKIP: {d.reason}"


# ── A1 (AMENDMENT 07-25): variation_phase gating — CONT only in EXPANSION ────

def test_phase_rebalanced_cont_denied_falls_to_fade(monkeypatch):
    """REBALANCED: with-trend CONT above value is DENIED (extension over) —
    the same call that ALLOWs in EXPANSION returns SKIP 'not at VAL'."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="LONG",
        day_direction="UP", location="above_value", entry_price=7478.0,
        levels=LEVELS_0724, variation_phase="REBALANCED",
    )
    assert not d.allow, f"Expected SKIP in REBALANCED but got ALLOW: {d.reason}"


def test_phase_unknown_is_todays_behavior(monkeypatch):
    """Phase None (unknown) → fail-safe to today's location-only behavior."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="LONG",
        day_direction="UP", location="above_value", entry_price=7478.0,
        levels=LEVELS_0724,
    )
    assert not d.allow


def test_phase_expansion_counter_trend_fade_skipped(monkeypatch):
    """During EXPANSION, fading the new edge (counter-trend SHORT at VAH on an
    UP expansion) is SKIPPED — fade only after rebalance."""
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    from backend.v9.systems.daytype_playbook import decide
    d = decide(
        pattern="REACTIVE", day_type="Variation", direction="SHORT",
        day_direction="UP", location="near_vah", entry_price=7465.0,
        levels=LEVELS_0724, variation_phase="EXPANSION",
    )
    assert not d.allow
    assert "rebalance" in d.reason.lower() or "EXPANSION" in d.reason
