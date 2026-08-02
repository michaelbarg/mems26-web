"""MULTIDAY_CONTEXT_V1 — 7-day TPO context (plan 02.08)."""
from backend.v9.systems.multiday_profile import (
    session_tpo_profile, composite_profile, value_migration,
    va_overlap_pct, open_location, build_context)


def _day(center, rng=10.0, bars=78):
    out = []
    for i in range(bars):
        # gentle rotation around center
        off = ((i % 12) - 6) / 6.0 * rng / 2
        o = center + off
        out.append({"o": o, "h": o + 1.0, "l": o - 1.0, "c": o + 0.25})
    return out


def test_session_profile_basic():
    p = session_tpo_profile(_day(7450))
    assert p is not None
    assert p["val"] <= p["poc"] <= p["vah"]
    assert p["low"] <= p["val"] and p["vah"] <= p["high"]
    assert abs(p["poc"] - 7450) < 5


def test_migration_up_detected():
    days = [session_tpo_profile(_day(7400 + 6 * i)) for i in range(5)]
    m = value_migration(days)
    assert m["direction"] == "UP" and m["slope"] > 0


def test_migration_flat_when_overlapping():
    days = [session_tpo_profile(_day(7450)) for _ in range(5)]
    assert value_migration(days)["direction"] == "FLAT"


def test_overlap_high_in_balance_low_in_trend():
    bal = [session_tpo_profile(_day(7450)) for _ in range(4)]
    trend = [session_tpo_profile(_day(7400 + 25 * i)) for i in range(4)]
    assert va_overlap_pct(bal) > 0.8
    assert va_overlap_pct(trend) < 0.3


def test_open_location_bands():
    comp = {"range_high": 7480, "range_low": 7420, "vah": 7465, "val": 7435}
    assert open_location(7490, comp) == "above_range"
    assert open_location(7470, comp) == "above_value"
    assert open_location(7450, comp) == "in_value"
    assert open_location(7430, comp) == "below_value"
    assert open_location(7410, comp) == "below_range"


def test_build_context_end_to_end():
    sessions = [_day(7400 + 6 * i) for i in range(7)]
    ctx = build_context(sessions, today_open=7455)
    assert ctx["n_days_used"] == 7
    assert ctx["composite"] is not None
    assert ctx["value_migration"]["direction"] == "UP"
    assert ctx["open_location"] in ("above_range", "above_value", "in_value")


def test_short_sessions_skipped_honestly():
    ctx = build_context([[{"o": 1, "h": 1, "l": 1, "c": 1}]], today_open=None)
    assert ctx["n_days_used"] == 0 and ctx["composite"] is None
