"""RESPONSIVE_WITH_DAY_TREND_V1 — the 07-23 live miss + its fix.

Live 2026-07-23: a RED (LSMA) down-session; RTH opened after a big overnight
down-leg and chopped mid-value. The responsive (REACTIVE) family was gated by
LOCATION ONLY, blind to the held down-trend:
  • with-trend SHORT @ 7456.5 (mid_value)  → BLOCKED ("not at VAH")   ← the miss
  • counter-trend LONG @ 7469.75 (mid_value → would be allowed at VAL) ← wrong-way

Doctrine (Dalton): on a trend day you SELL the rally and NEVER fade the trend.
With RESPONSIVE_WITH_DAY_TREND_V1=1 and a known day_direction (accepted-break
expansion, or the held-LSMA dir_bias fallback):
  • counter-trend (LONG on DOWN / SHORT on UP) → SKIP (never fade)
  • with-trend  (SHORT on DOWN / LONG on UP) → ALLOW off the value-edge, EXCEPT
    chasing the far extreme (SHORT@below_value / LONG@above_value) → SKIP.

Flag OFF → location-only, byte-identical to the prior behavior.
"""
from __future__ import annotations

import pytest

from backend.v9.systems.daytype_playbook import decide, reset_cache

# Today's live geometry: VAH/VAL from a value that sits ABOVE the RTH chop, so a
# 7456.5 short reads as mid_value (the exact block that happened).
_LEVELS = {"vah": 7472.0, "val": 7450.0, "ib_width": 12.0}
_SHORT_MID = 7456.5     # the with-trend SHORT that was blocked "not at VAH"
_LONG_MID = 7469.75     # the counter-trend LONG generated at the pullback high
_SHORT_LOW = 7444.5     # a SHORT chasing the day low (below_value)


def _clean(monkeypatch):
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    reset_cache()


# ── with flag ON ───────────────────────────────────────────────────────────

def test_with_trend_short_allowed_off_edge_on_down_day(monkeypatch):
    """THE FIX: a with-trend SHORT mid-value on a DOWN day is allowed (continuation),
    no longer blocked for 'not at VAH'."""
    _clean(monkeypatch)
    monkeypatch.setenv("RESPONSIVE_WITH_DAY_TREND_V1", "1")
    d = decide(
        pattern="REACTIVE_SHORT", day_type="Variation", direction="SHORT",
        day_direction="DOWN", entry_price=_SHORT_MID, levels=_LEVELS,
    )
    assert d.allow, f"with-trend SHORT should be allowed, got SKIP: {d.reason}"


def test_counter_trend_long_blocked_on_down_day(monkeypatch):
    """A counter-trend LONG on a DOWN day is SKIPped even at a value edge —
    never fade the trend (buy-the-dip is forbidden)."""
    _clean(monkeypatch)
    monkeypatch.setenv("RESPONSIVE_WITH_DAY_TREND_V1", "1")
    d = decide(
        pattern="REACTIVE_LONG", day_type="Variation", direction="LONG",
        day_direction="DOWN", entry_price=_LONG_MID, levels=_LEVELS,
    )
    assert not d.allow
    assert "counter-trend" in d.reason.lower()


def test_with_trend_short_chasing_low_blocked(monkeypatch):
    """A with-trend SHORT that is CHASING the low (below_value) is SKIPped —
    'enter from a pullback, not the low' (Michael 'מנקודה גבוהה')."""
    _clean(monkeypatch)
    monkeypatch.setenv("RESPONSIVE_WITH_DAY_TREND_V1", "1")
    d = decide(
        pattern="REACTIVE_SHORT", day_type="Variation", direction="SHORT",
        day_direction="DOWN", entry_price=_SHORT_LOW, levels=_LEVELS,
    )
    assert not d.allow
    assert "chasing" in d.reason.lower()


def test_up_day_symmetric(monkeypatch):
    """Symmetric: on an UP day the with-trend LONG mid-value is allowed and the
    counter-trend SHORT is blocked."""
    _clean(monkeypatch)
    monkeypatch.setenv("RESPONSIVE_WITH_DAY_TREND_V1", "1")
    up_levels = {"vah": 7472.0, "val": 7450.0, "ib_width": 12.0}
    long_ok = decide(pattern="REACTIVE_LONG", day_type="Variation", direction="LONG",
                     day_direction="UP", entry_price=7458.0, levels=up_levels)
    short_bad = decide(pattern="REACTIVE_SHORT", day_type="Variation", direction="SHORT",
                       day_direction="UP", entry_price=7458.0, levels=up_levels)
    assert long_ok.allow, long_ok.reason
    assert not short_bad.allow and "counter-trend" in short_bad.reason.lower()


# ── flag OFF = byte-identical location-only behavior ────────────────────────

def test_flag_off_short_mid_still_blocked_by_location(monkeypatch):
    """Flag OFF → the old location-only rule: a SHORT mid-value is blocked
    'not at VAH' regardless of day_direction (byte-identical)."""
    _clean(monkeypatch)
    monkeypatch.delenv("RESPONSIVE_WITH_DAY_TREND_V1", raising=False)
    d = decide(
        pattern="REACTIVE_SHORT", day_type="Variation", direction="SHORT",
        day_direction="DOWN", entry_price=_SHORT_MID, levels=_LEVELS,
    )
    assert not d.allow
    assert "not at VAH" in d.reason


def test_flag_on_but_no_day_direction_falls_back_to_location(monkeypatch):
    """Flag ON but day_direction unknown (None) → location-only path unchanged."""
    _clean(monkeypatch)
    monkeypatch.setenv("RESPONSIVE_WITH_DAY_TREND_V1", "1")
    d = decide(
        pattern="REACTIVE_SHORT", day_type="Variation", direction="SHORT",
        day_direction=None, entry_price=_SHORT_MID, levels=_LEVELS,
    )
    assert not d.allow
    assert "not at VAH" in d.reason


# ── NEVERFADE_TREND_ONLY_V1 (Michael ruling #3, 07-23) ──

def test_trend_only_variation_allows_low_long(monkeypatch):
    """Ruling #3: on Variation the never-fade rule is OFF — the 07-23 18:50
    REACTIVE_LONG @7433.25 near the low (blocked live) must now pass to the
    location path and be ALLOWED at the VAL-side edge."""
    _clean(monkeypatch)
    monkeypatch.setenv("RESPONSIVE_WITH_DAY_TREND_V1", "1")
    monkeypatch.setenv("NEVERFADE_TREND_ONLY_V1", "1")
    d = decide(pattern="REACTIVE_LONG", day_type="Variation", direction="LONG",
               day_direction="DOWN", entry_price=7451.0,
               levels={"vah": 7472.0, "val": 7450.0, "ib_width": 12.0})
    assert d.allow, f"Variation low-long must pass location path: {d.reason}"


def test_trend_only_trend_day_still_blocks(monkeypatch):
    """On a canonical Trend day the never-fade rule still applies."""
    _clean(monkeypatch)
    monkeypatch.setenv("RESPONSIVE_WITH_DAY_TREND_V1", "1")
    monkeypatch.setenv("NEVERFADE_TREND_ONLY_V1", "1")
    d = decide(pattern="REACTIVE_LONG", day_type="Trend_Normal", direction="LONG",
               day_direction="DOWN", entry_price=7451.0,
               levels={"vah": 7472.0, "val": 7450.0, "ib_width": 12.0})
    assert not d.allow and "counter-trend" in d.reason.lower()


def test_trend_only_flag_off_byte_identical(monkeypatch):
    """New flag OFF → Variation counter-trend still blocked (yesterday's behavior)."""
    _clean(monkeypatch)
    monkeypatch.setenv("RESPONSIVE_WITH_DAY_TREND_V1", "1")
    monkeypatch.delenv("NEVERFADE_TREND_ONLY_V1", raising=False)
    d = decide(pattern="REACTIVE_LONG", day_type="Variation", direction="LONG",
               day_direction="DOWN", entry_price=7451.0,
               levels={"vah": 7472.0, "val": 7450.0, "ib_width": 12.0})
    assert not d.allow and "counter-trend" in d.reason.lower()
