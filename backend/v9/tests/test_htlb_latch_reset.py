"""HTLB latch reset on a new RTH session — HTLB_LATCH_RESET_V1 (default OFF).

Bug (audit-confirmed 2026-07-14): WoodiesSystem._htlb_dir_bias is a zoned-HTLB
direction latch (init in __init__, latched in the HTLB direction gate in
process_bar). It is instance state that is updated only on a NEW zoned HTLB and
is NEVER cleared on a new session/day. Because hydrate() reloads prior bars, a
stale overnight bias silently blocks EVERY opposite-direction S4 fire at the next
session open until a fresh zoned HTLB flips it.

Fix: HTLB_LATCH_RESET_V1=1 clears the latch (to its neutral None) at the first
RTH bar of a new ET session — mirroring the day-type engine's session_date guard.
Default OFF keeps today's behaviour byte-for-byte.

This test proves:
  (a) flag OFF -> a day-1 bias PERSISTS into day-2's first RTH bar (today's bug)
  (b) flag ON  -> the bias is CLEARED at day-2's first RTH bar, so an
                  opposite-direction setup is no longer blocked by the gate.
Plus two fail-safe edge cases (same-session no-reset, overnight bar no-reset).
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend.v9.systems.woodies.woodies_system import WoodiesSystem

_ET = ZoneInfo("America/New_York")


def _rth_ts(y, m, d, hh=10, mm=0):
    """UTC unix seconds for an ET wall-clock time (10:00 ET is inside RTH)."""
    return datetime(y, m, d, hh, mm, tzinfo=_ET).timestamp()


# Day-1 and day-2 first RTH bars (10:00 ET), plus a day-2 overnight bar (02:00 ET).
DAY1_RTH = _rth_ts(2026, 7, 13)
DAY2_RTH = _rth_ts(2026, 7, 14)
DAY2_OVERNIGHT = _rth_ts(2026, 7, 14, 2, 0)  # 02:00 ET — NOT an RTH bar


def _htlb_direction_gate(bias, patterns):
    """Faithful mirror of the HTLB direction gate in process_bar:

        if flag("HTLB_DIRECTION_GATE") and self._htlb_dir_bias:
            _allowed = "LONG" if self._htlb_dir_bias == "UP" else "SHORT"
            patterns = [p for p in patterns if p.direction == _allowed]

    A latched bias keeps only same-direction patterns; no bias keeps them all.
    """
    if bias:
        allowed = "LONG" if bias == "UP" else "SHORT"
        return [p for p in patterns if p["direction"] == allowed]
    return patterns


@pytest.fixture
def sys_with_day1_bias():
    """A WoodiesSystem that latched an UP (LONG) bias during day 1."""
    s = WoodiesSystem()
    s._htlb_dir_bias = "UP"                 # day-1 zoned HTLB latched a LONG bias
    s._htlb_session_date = "2026-07-13"     # session the latch belongs to
    return s


def test_flag_off_bias_persists_into_next_session(monkeypatch, sys_with_day1_bias):
    """(a) Flag OFF: the day-1 bias survives day-2's first RTH bar (today's bug)."""
    monkeypatch.delenv("HTLB_LATCH_RESET_V1", raising=False)  # unset == default OFF
    s = sys_with_day1_bias

    s._maybe_reset_htlb_latch(DAY2_RTH)

    assert s._htlb_dir_bias == "UP", "OFF must not clear the latch (behaviour unchanged)"

    # And the gate still blocks the opposite (SHORT) setup at the open — the bug.
    short_setup = [{"pattern_id": "GB100", "direction": "SHORT"}]
    assert _htlb_direction_gate(s._htlb_dir_bias, short_setup) == [], \
        "stale UP bias still blocks the opposite SHORT fire when the flag is OFF"


def test_flag_on_clears_bias_at_new_session_open(monkeypatch, sys_with_day1_bias):
    """(b) Flag ON: the bias is cleared at day-2's first RTH bar → SHORT unblocked."""
    monkeypatch.setenv("HTLB_LATCH_RESET_V1", "1")
    s = sys_with_day1_bias

    s._maybe_reset_htlb_latch(DAY2_RTH)

    assert s._htlb_dir_bias is None, "ON must clear the stale latch at the new session open"
    assert s._htlb_session_date == "2026-07-14", "session date advances to the new day"

    # The opposite-direction (SHORT) setup now survives the gate — bug fixed.
    short_setup = [{"pattern_id": "GB100", "direction": "SHORT"}]
    assert _htlb_direction_gate(s._htlb_dir_bias, short_setup) == short_setup, \
        "with the latch cleared, the opposite SHORT fire is no longer blocked"


def test_flag_on_same_session_does_not_reset(monkeypatch):
    """ON but same ET date: a later intraday bar must NOT wipe a fresh latch."""
    monkeypatch.setenv("HTLB_LATCH_RESET_V1", "1")
    s = WoodiesSystem()

    # First RTH bar of day 2 establishes the session key (bias starts neutral).
    s._maybe_reset_htlb_latch(DAY2_RTH)
    assert s._htlb_session_date == "2026-07-14"
    assert s._htlb_dir_bias is None

    s._htlb_dir_bias = "DOWN"  # a fresh intraday zoned HTLB latches SHORT bias
    # A later same-session RTH bar (11:00 ET) must leave the fresh latch intact.
    s._maybe_reset_htlb_latch(_rth_ts(2026, 7, 14, 11, 0))
    assert s._htlb_dir_bias == "DOWN", "same-session bars must not reset the latch"


def test_flag_on_overnight_bar_does_not_open_session(monkeypatch, sys_with_day1_bias):
    """ON but a non-RTH (overnight) bar must NOT reset — only RTH opens a session."""
    monkeypatch.setenv("HTLB_LATCH_RESET_V1", "1")
    s = sys_with_day1_bias

    s._maybe_reset_htlb_latch(DAY2_OVERNIGHT)  # 02:00 ET — not an RTH bar

    assert s._htlb_dir_bias == "UP", "an overnight bar must not clear the latch"
    assert s._htlb_session_date == "2026-07-13", \
        "an overnight bar must not advance the session date"
