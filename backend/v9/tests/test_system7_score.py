"""Tests for System-7 confluence scoring (SYSTEM7_SCORE_V1, flag-OFF).

Added by cowork-audit-agent 2026-08-04: b95b13b5 shipped system7_score.py +
gateway wiring with zero tests. These pin the scoring bands, the two IL-time
penalties, the clamp, and the CURRENT honest ceiling (location + delta are
stubs => max 75, sizing 3 unreachable). When cc completes those components,
test_max_reachable_score_while_location_delta_stubbed SHOULD break — that is
the signal to re-review the bands before any replay/enable.
"""
from datetime import datetime, timezone
from types import SimpleNamespace

from backend.v9.systems.system7_score import score

UTC = timezone.utc


def _mc(**kw):
    base = {"day_bias": "NONE", "day_type": "UNKNOWN", "leg_dir": None,
            "opening_conf": 0.0}
    base.update(kw)
    return SimpleNamespace(**base)


def test_bare_setup_scores_base_30_and_blocks():
    r = score(setup={"direction": "LONG", "pattern": "VEGAS"})
    assert r["score"] == 30
    assert r["blocked"] is True and r["sizing"] == 0
    assert r["components"]["base"] == 30


def test_counter_trend_gets_no_day_align():
    r = score(setup={"direction": "SHORT", "pattern": "VEGAS"},
              market_context=_mc(day_bias="UP", day_type="Trend_Up"))
    assert r["components"]["day_align"] == 0


def test_leg_only_scores_45_one_contract():
    r = score(setup={"direction": "LONG", "pattern": "VEGAS"},
              market_context=_mc(leg_dir="UP"))
    assert r["score"] == 45
    assert r["sizing"] == 1 and r["blocked"] is False


def test_day_plus_leg_scores_65_two_contracts():
    r = score(setup={"direction": "LONG", "pattern": "VEGAS"},
              market_context=_mc(day_bias="UP", day_type="Trend_Up", leg_dir="UP"))
    assert r["score"] == 65
    assert r["sizing"] == 2


def test_noon_penalty_applies_in_1830_2030_il_window():
    # 16:00 UTC = 19:00 IL (IDT, UTC+3) — inside the window
    ts = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)
    r = score(setup={"direction": "LONG", "pattern": "VEGAS"},
              market_context=_mc(leg_dir="UP"), bar_ts=ts)
    assert r["components"]["noon_penalty"] == -15
    assert r["score"] == 30  # 45 - 15


def test_late_zlr_penalty_after_2000_il_and_clamp_at_zero():
    # 17:30 UTC = 20:30 IL — late-ZLR AND still inside the noon window:
    # 30 - 15 - 20 = -5 → clamped to 0, blocked.
    ts = datetime(2026, 8, 3, 17, 30, tzinfo=UTC)
    r = score(setup={"direction": "LONG", "pattern": "ZLR_LONG"}, bar_ts=ts)
    assert r["components"]["late_zlr"] == -20
    assert r["components"]["noon_penalty"] == -15
    assert r["score"] == 0 and r["blocked"] is True


def test_non_zlr_pattern_has_no_late_zlr_penalty():
    ts = datetime(2026, 8, 3, 19, 0, tzinfo=UTC)  # 22:00 IL, outside noon window
    r = score(setup={"direction": "LONG", "pattern": "VEGAS"}, bar_ts=ts)
    assert r["components"]["late_zlr"] == 0
    assert r["components"]["noon_penalty"] == 0


def test_max_reachable_score_while_location_delta_stubbed():
    # location + delta are placeholders (always 0) → ceiling is
    # 30 base + 20 day + 15 leg + 10 opening = 75 → sizing 3 (>=85) is
    # UNREACHABLE. If this breaks, the stubs were completed — re-review
    # the bands + this file before replay/enable.
    r = score(setup={"direction": "LONG", "pattern": "VEGAS"},
              market_context=_mc(day_bias="UP", day_type="Trend_Up",
                                 leg_dir="UP", opening_conf=0.9))
    assert r["components"]["location"] == 0
    assert r["components"]["delta"] == 0
    assert r["score"] == 75
    assert r["sizing"] == 2


def test_result_shape():
    r = score(setup={"direction": "LONG", "pattern": "VEGAS"})
    assert set(r) == {"score", "components", "sizing", "blocked", "reason"}
