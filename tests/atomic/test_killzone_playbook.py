"""W4-epsilon -- Per-zone playbook preferences per V3 Layer 2"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from backend.v9.systems.killzone.zone_playbook import (
    get_zone_preferences, is_pattern_preferred, is_pattern_avoided,
    get_quality_modifier,
)


def test_ny_open_prefers_initiative():
    prefs = get_zone_preferences("NY_OPEN")
    assert prefs is not None
    assert "INITIATIVE" in prefs["preferred_patterns"]
    assert "BREAKOUT" in prefs["preferred_patterns"]
    assert prefs["quality_modifier"] >= 0
    assert "reasoning_notes" in prefs


def test_asia_only_reactive():
    prefs = get_zone_preferences("ASIA")
    assert prefs is not None
    assert "REACTIVE" in prefs["preferred_patterns"]
    assert "INITIATIVE" not in prefs["preferred_patterns"]
    assert prefs["quality_modifier"] < 0


def test_midday_avoids_initiative():
    prefs = get_zone_preferences("MIDDAY")
    assert "INITIATIVE" in prefs["avoid_patterns"]
    assert "BREAKOUT" in prefs["avoid_patterns"]
    assert prefs["sizing_cap"] == "HALF"
    assert prefs["quality_modifier"] < -0.1


def test_ny_pm_allows_initiative():
    prefs = get_zone_preferences("NY_PM")
    assert "INITIATIVE" in prefs["preferred_patterns"]
    assert prefs["quality_modifier"] > 0


def test_closed_blocks_all():
    prefs = get_zone_preferences("CLOSED")
    assert prefs["sizing_cap"] == "REJECT"
    assert prefs["quality_modifier"] == -1.0
    assert len(prefs["preferred_patterns"]) == 0


def test_weekend_blocks_all():
    prefs = get_zone_preferences("WEEKEND")
    assert prefs["sizing_cap"] == "REJECT"
    assert prefs["quality_modifier"] == -1.0


def test_unknown_zone_returns_none():
    prefs = get_zone_preferences("MARS")
    assert prefs is None


def test_is_pattern_preferred():
    assert is_pattern_preferred("NY_OPEN", "INITIATIVE") is True
    assert is_pattern_preferred("ASIA", "INITIATIVE") is False
    assert is_pattern_preferred("ASIA", "REACTIVE") is True


def test_is_pattern_avoided():
    assert is_pattern_avoided("MIDDAY", "INITIATIVE") is True
    assert is_pattern_avoided("NY_OPEN", "INITIATIVE") is False
    assert is_pattern_avoided("UNKNOWN_ZONE", "REACTIVE") is True


def test_quality_modifier_range():
    for zone in ["ASIA", "LONDON", "NY_PREMARKET", "NY_OPEN", "MIDDAY", "NY_PM", "POST_MARKET"]:
        mod = get_quality_modifier(zone)
        assert -1.0 <= mod <= 1.0, f"{zone} modifier {mod} out of range"


def test_all_zones_have_reasoning_notes():
    for zone in ["ASIA", "LONDON", "NY_PREMARKET", "NY_OPEN", "MIDDAY",
                 "NY_PM", "POST_MARKET", "CLOSED", "WEEKEND"]:
        prefs = get_zone_preferences(zone)
        assert prefs is not None, f"{zone} missing"
        assert "reasoning_notes" in prefs and len(prefs["reasoning_notes"]) > 0, \
            f"{zone} missing reasoning_notes"
