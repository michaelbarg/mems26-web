"""Tests for the day-type playbook decision engine.

Anti-tautological: every test calls the production decide() which reads the REAL
config/daytype_playbook.yaml. Reverting a YAML cell flips the matching test RED
(noted per case), so the test proves the config drives behavior — not a copy.
"""
import pytest

from backend.v9.systems import daytype_playbook as P


@pytest.fixture(autouse=True)
def _reset():
    P.reset_cache()
    yield
    P.reset_cache()


def _on(mp):
    mp.setenv("DAYTYPE_PLAYBOOK", "1")
    P.reset_cache()


def _off(mp):
    mp.delenv("DAYTYPE_PLAYBOOK", raising=False)
    P.reset_cache()


def test_off_is_noop(monkeypatch):
    # GATE OFF → FULL for everything (zero change to current firing).
    _off(monkeypatch)
    d = P.decide("HFE_SHORT", "Trend_Normal", "SHORT", "RED")
    assert d.verdict == "FULL" and d.allow


def test_hfe_skip_on_trend(monkeypatch):
    # spec: HFE on a trend day = SKIP.  if reverted (YAML HFE.Trend_Normal->FULL) → RED
    _on(monkeypatch)
    d = P.decide("HFE_SHORT", "Trend_Normal", "SHORT", "RED")
    assert d.verdict == "SKIP" and not d.allow


def test_reactive_counter_trend_skip(monkeypatch):
    # REACTIVE short on an UP trend (trend_state BLUE) = counter-trend → SKIP.
    _on(monkeypatch)
    d = P.decide("REACTIVE_SHORT", "Trend_Normal", "SHORT", "BLUE")
    assert d.verdict == "SKIP"


def test_reactive_with_trend_ok(monkeypatch):
    # REACTIVE long on an UP trend = with-trend → allowed (FULL).
    _on(monkeypatch)
    d = P.decide("REACTIVE_LONG", "Trend_Normal", "LONG", "BLUE")
    assert d.verdict == "FULL" and d.allow


def test_reduced_sizes_down(monkeypatch):
    # Ruling 2026-08-12 (playbook inversion, CC_WORKORDER F4): ZLR is REDUCED
    # on Variation (was FULL) and SKIP on Normal (was REDUCED). REDUCED must
    # still size down to 2. If reverted (ZLR.Variation->FULL) → RED.
    _on(monkeypatch)
    d = P.decide("ZLR_LONG", "Variation", "LONG", "GRAY")
    assert d.verdict == "REDUCED" and d.contracts == 2


def test_zlr_skip_on_normal_ruling_2026_08_12(monkeypatch):
    # Ruling 2026-08-12: ZLR on Normal = SKIP (live −$270 / 39%, 65% of volume).
    _on(monkeypatch)
    d = P.decide("ZLR_LONG", "Normal", "LONG", "GRAY")
    assert d.verdict == "SKIP" and not d.allow


def test_unknown_pattern_fails_open(monkeypatch):
    # fail-open: an unmapped pattern is never blocked.
    _on(monkeypatch)
    d = P.decide("MYSTERY", "Trend_Normal", "LONG", "BLUE")
    assert d.verdict == "FULL"


def test_nontrend_skips_all(monkeypatch):
    _on(monkeypatch)
    assert P.decide("ZLR_LONG", "Nontrend", "LONG", "GRAY").verdict == "SKIP"


# ── K5: EXCESS counter-entry exception tests ────────────────────────────────

def test_expansion_counter_fade_blocked_without_excess_flag(monkeypatch):
    """Counter-trend fade during Variation EXPANSION is blocked (base case)."""
    _on(monkeypatch)
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    monkeypatch.delenv("DAYTYPE_POSITION_GATE", raising=False)
    monkeypatch.delenv("EXCESS_COUNTER_ENTRY_V1", raising=False)
    d = P.decide(
        "REACTIVE_SHORT", "Variation", "SHORT", "BLUE",
        day_direction="UP", variation_phase="EXPANSION",
        entry_price=7781.5,
        levels={"day_high": 7786.75, "day_low": 7743.25, "ib_width": 37.25},
    )
    assert d.verdict == "SKIP"
    assert "counter-trend fade" in d.reason.lower() or "rebalance" in d.reason.lower()


def test_expansion_counter_fade_exempt_with_excess(monkeypatch):
    """K5: EXCESS at the edge → counter-trend fade is ALLOWED during EXPANSION."""
    from unittest.mock import patch
    from backend.v9.systems.extremes_quality import ExtremeQuality, SessionExtremes

    _on(monkeypatch)
    monkeypatch.setenv("VARIATION_WITH_TREND_CONT_V1", "1")
    monkeypatch.delenv("DAYTYPE_POSITION_GATE", raising=False)
    monkeypatch.setenv("EXCESS_COUNTER_ENTRY_V1", "1")

    # Mock session bars: 10 bars of a Variation-up session
    _bars = [
        {"open": 7757, "high": 7760, "low": 7755, "close": 7759},
        {"open": 7759, "high": 7765, "low": 7758, "close": 7764},
        {"open": 7764, "high": 7770, "low": 7750, "close": 7752},
        {"open": 7752, "high": 7770, "low": 7743, "close": 7765},
        {"open": 7765, "high": 7780, "low": 7764, "close": 7778},
        {"open": 7778, "high": 7780, "low": 7770, "close": 7775},
        {"open": 7775, "high": 7782, "low": 7774, "close": 7780},
        {"open": 7780, "high": 7786, "low": 7778, "close": 7782},
        {"open": 7782, "high": 7787, "low": 7780, "close": 7783},
        {"open": 7783, "high": 7786, "low": 7781, "close": 7781},
    ]

    excess_high = ExtremeQuality("EXCESS", 7786.75, 5.0, 1, "tail rejection")
    neutral_low = ExtremeQuality("NEUTRAL", 7743.25, 1.0, 1, "normal")
    extremes = SessionExtremes(
        high=excess_high, low=neutral_low,
        session_high=7786.75, session_low=7743.25, n_bars=10)

    def _mock_read(sql, params):
        return _bars

    with patch("backend.v9.db.read.read_all", side_effect=_mock_read):
        with patch(
            "backend.v9.systems.extremes_quality.classify_session_extremes",
            return_value=extremes
        ):
            d = P.decide(
                "REACTIVE_SHORT", "Variation", "SHORT", "BLUE",
                day_direction="UP", variation_phase="EXPANSION",
                entry_price=7785.0,  # within 2pt of EXCESS at 7786.75
                levels={"day_high": 7786.75, "day_low": 7743.25, "ib_width": 37.25},
            )
    # With EXCESS at the edge, the counter-trend fade should be allowed
    assert d.verdict != "SKIP" or "excess" in d.reason.lower(), (
        f"K5: EXCESS counter-entry should exempt the EXPANSION fade block: {d}"
    )
