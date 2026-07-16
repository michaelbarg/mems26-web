"""S1_IB_SANITY_V1 — Sierra-IB sanity check against first-12-bar extremes.

N1a/N1b root-fix (2026-07-17, dev+cc-imac night task). The Sierra-exported IB
can be a stale pre-open snapshot that never re-bases to the true 09:30 ET
cash-session first hour — proven on 2026-07-15
(docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md RC#1): exported
7591.75-7619.0 vs the true first-12-bars 7601.25-7626.25 (off 7.25/9.5pt),
which fed a phantom UP side and forced a false Neutral mid-session while the
real day was a clean Variation-DOWN leg.

Flag S1_IB_SANITY_V1 (default OFF) sanity-checks the passed Sierra
ib_high/ib_low against the bars' own first-12-bar extremes once >=12 RTH
bars exist, and falls back to the bars-derived IB when inconsistent. This is
validation of already-ingested bars (Rule-1-compatible — the no-Sierra bars
fallback already exists at relative_features.py:219-225), not a new source.
"""
from backend.v9.systems.day_type.classifier_core import classify_session


def _bars12(highs, lows):
    """12 synthetic 5-min RTH bars from parallel high/low lists (len must be 12)."""
    assert len(highs) == len(lows) == 12
    return [
        {"o": lows[i], "h": highs[i], "l": lows[i], "c": (highs[i] + lows[i]) / 2, "v": 1000}
        for i in range(12)
    ]


def _real_07_15_first_hour():
    """Extremes match the TRUE 07-15 first-hour IB: 7601.25-7626.25
    (N1B section 0a: 09:30-10:29 ET bars). Interior values are plausible
    fills; only the extremes are asserted on by these tests.
    """
    highs = [7615, 7621.75, 7626.25, 7620, 7615, 7610, 7608, 7606, 7605, 7607, 7609, 7611]
    lows = [7605, 7612.25, 7618.75, 7608, 7603, 7601.25, 7602, 7603, 7602.5, 7604, 7605, 7606]
    return _bars12(highs, lows)


def test_flag_off_byte_identical_even_when_sierra_ib_wrong(monkeypatch):
    monkeypatch.delenv("S1_IB_SANITY_V1", raising=False)
    bars = _real_07_15_first_hour()
    # the stale pre-open IB actually exported on 07-15 (N1B RC#1)
    result = classify_session(bars=bars, ib_high=7619.0, ib_low=7591.75)
    assert result["ib_source"] == "sierra_tpo"
    assert result["measured"]["ib_width"] == round(7619.0 - 7591.75, 2)


def test_flag_on_falls_back_when_sierra_ib_inconsistent(monkeypatch):
    monkeypatch.setenv("S1_IB_SANITY_V1", "1")
    bars = _real_07_15_first_hour()
    result = classify_session(bars=bars, ib_high=7619.0, ib_low=7591.75)
    assert result["ib_source"] == "bars_fallback_sierra_inconsistent"
    # corrected width is the true ~25.0pt IB, not the stale 27.25pt
    assert result["measured"]["ib_width"] == round(7626.25 - 7601.25, 2)


def test_flag_on_noop_when_sierra_ib_consistent(monkeypatch):
    monkeypatch.setenv("S1_IB_SANITY_V1", "1")
    bars = _real_07_15_first_hour()
    # within 2 ticks/2pt of the bars' own extremes -> no override (T4, sanity-guard no-op)
    result = classify_session(bars=bars, ib_high=7626.5, ib_low=7601.0)
    assert result["ib_source"] == "sierra_tpo"


def test_flag_on_noop_with_fewer_than_12_bars(monkeypatch):
    monkeypatch.setenv("S1_IB_SANITY_V1", "1")
    bars = _real_07_15_first_hour()[:6]
    result = classify_session(bars=bars, ib_high=7619.0, ib_low=7591.75)
    assert result["ib_source"] == "sierra_tpo"  # can't sanity-check without the full hour


def test_flag_string_zero_is_off(monkeypatch):
    monkeypatch.setenv("S1_IB_SANITY_V1", "0")
    bars = _real_07_15_first_hour()
    result = classify_session(bars=bars, ib_high=7619.0, ib_low=7591.75)
    assert result["ib_source"] == "sierra_tpo"
