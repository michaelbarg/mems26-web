"""S1_NEUTRAL_PRECEDENCE_V1 — sides==2 must outrank a held single-side acceptance.

N1b root-fix (2026-07-17, docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md RC#2):
with S1_ACCEPTANCE_RECLASS_V1 ON, `classify()` returned Normal_Variation/Trend_Normal
on ANY held accepted break BEFORE ever reaching the sides==2 Neutral check — so a day
that extended BOTH sides but still held one stale acceptance could not be named Neutral
until that acceptance was rejected (live 07-15: the flip to Neutral_Center lagged to
20:46 IL instead of the mechanically-correct ~19:05 IL). Doctrine ruling (06-20):
"נייטרלי = יום מבולגן עם פריצה משני הצדדים" — sides==2 should win. Default OFF,
and a no-op unless S1_ACCEPTANCE_RECLASS_V1 is also on (that's the only branch it guards).
"""
from backend.v9.systems.day_type.daytype_classifier import classify, load_plan

PLAN = load_plan()
LOCKED = 30


def c(**kw):
    kw.setdefault("n_bars", LOCKED)
    return classify(kw, PLAN)


def test_flag_off_acceptance_still_shadows_neutral(monkeypatch):
    """Regression guard: default (flag unset) preserves the EXISTING (if surprising)
    acceptance-reclass-wins behavior — proves this fix is opt-in, not a silent change."""
    monkeypatch.setenv("S1_ACCEPTANCE_RECLASS_V1", "1")
    monkeypatch.delenv("S1_NEUTRAL_PRECEDENCE_V1", raising=False)
    r = c(sides=2, accepted_break="UP", accepted_break_ref="IB", one_tf="UP", close_pos=0.50)
    assert r["day_type"] != "Neutral_Center" and r["day_type"] != "Neutral_Extreme", r
    assert r.get("reclass") is True, r


def test_flag_on_sides_two_wins_over_held_acceptance(monkeypatch):
    """The actual fix: with the flag ON, a two-sided day names Neutral even while
    holding an accepted break in one direction."""
    monkeypatch.setenv("S1_ACCEPTANCE_RECLASS_V1", "1")
    monkeypatch.setenv("S1_NEUTRAL_PRECEDENCE_V1", "1")
    r = c(sides=2, accepted_break="UP", accepted_break_ref="IB", one_tf="UP", close_pos=0.50)
    assert r["day_type"] == "Neutral_Center", r


def test_flag_on_neutral_extreme_variant(monkeypatch):
    monkeypatch.setenv("S1_ACCEPTANCE_RECLASS_V1", "1")
    monkeypatch.setenv("S1_NEUTRAL_PRECEDENCE_V1", "1")
    r = c(sides=2, accepted_break="DOWN", accepted_break_ref="prior_VA", close_pos=0.92)
    assert r["day_type"] == "Neutral_Extreme", r


def test_flag_on_does_not_touch_sides_one_acceptance(monkeypatch):
    """Carve-out is sides==2 only — a one-sided accepted break still reclasses normally."""
    monkeypatch.setenv("S1_ACCEPTANCE_RECLASS_V1", "1")
    monkeypatch.setenv("S1_NEUTRAL_PRECEDENCE_V1", "1")
    r = c(sides=1, accepted_break="UP", accepted_break_ref="IB", one_tf="UP", close_pos=0.80)
    assert r.get("reclass") is True and r["day_type"] in ("Trend_Normal", "Normal_Variation", "Trend_DD"), r


def test_flag_on_no_regression_on_existing_two_sided_fixture_without_acceptance(monkeypatch):
    """T3 (N1B acceptance test): the existing two-sided fixture (no accepted_break present)
    must still produce Neutral_Center with the fix ON — it must strengthen Neutral
    reachability, never weaken it."""
    monkeypatch.setenv("S1_NEUTRAL_PRECEDENCE_V1", "1")
    r = c(sides=2, close_pos=0.50)
    assert r["day_type"] == "Neutral_Center" and r["direction"] == "fade_both", r
