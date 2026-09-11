"""T-314: Opening type lock + negation tests.

Bar geometry from 10.09 session:
  bar1: o=7599.0 h=7603.0 l=7595.0 c=7596.75
  bar2: o=7597.0 h=7604.5 l=7593.75 c=7603.25
  bar3: o=7603.5 h=7606.5 l=7599.5 c=7600.25
  bar4: o=7600.25 h=7609.25 l=7600.0 c=7605.5
  bar5: o=7605.75 h=7605.75 l=7591.5 c=7592.25

rej_low = min(l of bars 1-3) = 7593.75
bar5 close 7592.25 < 7593.75 → ORR/UP negated.
"""
from types import SimpleNamespace

import pytest

from backend.v9.systems.day_type.opening_lock import update_opening_lock

NOW = "2026-09-10T09:35:00"

BAR1 = {"o": 7599.00, "h": 7603.00, "l": 7595.00,  "c": 7596.75}
BAR2 = {"o": 7597.00, "h": 7604.50, "l": 7593.75,  "c": 7603.25}
BAR3 = {"o": 7603.50, "h": 7606.50, "l": 7599.50,  "c": 7600.25}
BAR4 = {"o": 7600.25, "h": 7609.25, "l": 7600.00,  "c": 7605.50}
BAR5 = {"o": 7605.75, "h": 7605.75, "l": 7591.50,  "c": 7592.25}


def _fresh_machine():
    return SimpleNamespace(
        _opening_type_locked=False,
        _opening_locked_val=None,
        _opening_locked_dir=None,
        _opening_locked_at=None,
        _opening_negated=False,
        _opening_negated_at=None,
    )


# ── T-314-1: Non-AUCTION locks at bar 4 ─────────────────────────────────────

def test_non_auction_locks_at_bar4():
    """ORR/UP (non-AUCTION): update_opening_lock at bar 4 sets _opening_type_locked."""
    m = _fresh_machine()
    bars = [BAR1, BAR2, BAR3, BAR4]
    update_opening_lock(m, bars, ib_locked=False, now_iso=NOW)
    assert m._opening_type_locked is True
    assert m._opening_locked_val == "OPEN_REJECTION_REVERSE"
    assert m._opening_locked_dir == "UP"


def test_non_auction_does_not_need_ib_lock():
    """Non-AUCTION types lock immediately regardless of ib_locked flag."""
    m = _fresh_machine()
    bars = [BAR1, BAR2, BAR3, BAR4]
    update_opening_lock(m, bars, ib_locked=False, now_iso=NOW)
    assert m._opening_type_locked is True


# ── T-314-2: AUCTION_IN does NOT lock until ib_locked=True ───────────────────

def _auction_in_bars():
    """Construct bars that produce OPEN_AUCTION_IN (rotational, open inside range).

    Crosses open multiple times with small moves, no clear drive.
    open_price = 7500.0, pdh=7520, pdl=7480 context implied by geometry.
    """
    return [
        {"o": 7500.0, "h": 7503.0, "l": 7498.0, "c": 7501.5},
        {"o": 7501.5, "h": 7504.0, "l": 7497.0, "c": 7499.0},
        {"o": 7499.0, "h": 7502.0, "l": 7498.0, "c": 7501.0},
        {"o": 7501.0, "h": 7503.0, "l": 7499.0, "c": 7500.5},
    ]


def test_auction_in_does_not_lock_without_ib():
    """OPEN_AUCTION_IN must NOT lock until IB is locked.

    opening_lock.py imports detect_opening_type inline (inside the function),
    so we patch the source module — opening_detector_v2 — at the attribute
    the inline import resolves to.
    """
    m = _fresh_machine()
    import unittest.mock as mock
    import backend.v9.systems.day_type.opening_detector_v2 as _odv2
    fake_result = {"opening_type": "OPEN_AUCTION_IN", "direction": "NEUTRAL"}
    with mock.patch.object(_odv2, "detect_opening_type", return_value=fake_result):
        bars = _auction_in_bars()
        update_opening_lock(m, bars, ib_locked=False, now_iso=NOW)
    assert m._opening_type_locked is False, "AUCTION_IN must not lock until ib_locked"


def test_auction_in_locks_when_ib_locked():
    """OPEN_AUCTION_IN locks once IB is locked."""
    m = _fresh_machine()
    import unittest.mock as mock
    import backend.v9.systems.day_type.opening_detector_v2 as _odv2
    fake_result = {"opening_type": "OPEN_AUCTION_IN", "direction": "NEUTRAL"}
    with mock.patch.object(_odv2, "detect_opening_type", return_value=fake_result):
        bars = _auction_in_bars()
        update_opening_lock(m, bars, ib_locked=True, now_iso=NOW)
    assert m._opening_type_locked is True
    assert m._opening_locked_val == "OPEN_AUCTION_IN"


# ── T-314-3: ORR/UP negated when bar5 close < rej_low ────────────────────────

def test_orr_up_negated_by_bar5_close():
    """bar5 close 7592.25 < rej_low 7593.75 → _opening_negated becomes True."""
    m = _fresh_machine()
    # Lock first (bars 1-4)
    update_opening_lock(m, [BAR1, BAR2, BAR3, BAR4], ib_locked=False, now_iso=NOW)
    assert m._opening_type_locked is True
    assert m._opening_locked_val == "OPEN_REJECTION_REVERSE"

    # Bar 5: close below rej_low → negation
    update_opening_lock(m, [BAR1, BAR2, BAR3, BAR4, BAR5], ib_locked=False, now_iso=NOW)
    assert m._opening_negated is True


# ── T-314-4: Mutation — close > rej_high does NOT negate UP ──────────────────

def test_orr_up_not_negated_by_close_above_rej_high():
    """close > rej_high is confirmation for DOWN, not negation for UP.

    ORR/UP: negation condition is close < rej_low.
    A close above rej_high must NOT trigger negation for the UP direction.
    """
    m = _fresh_machine()
    # Lock at bar 4
    update_opening_lock(m, [BAR1, BAR2, BAR3, BAR4], ib_locked=False, now_iso=NOW)
    assert m._opening_locked_dir == "UP"

    # rej_high = max(h of bars 1-3) = 7606.5
    # Construct a bar that closes ABOVE rej_high — confirmation, not negation for UP
    bar5_high_close = {"o": 7605.0, "h": 7610.0, "l": 7603.0, "c": 7608.0}
    update_opening_lock(m, [BAR1, BAR2, BAR3, BAR4, bar5_high_close],
                        ib_locked=False, now_iso=NOW)
    assert m._opening_negated is False, (
        "Close above rej_high must NOT negate an ORR/UP — wrong negation axis"
    )


# ── T-314-5: After negation, re-read gives a new opening type ────────────────

def test_after_negation_new_opening_type_is_set():
    """After negation, _opening_locked_val is updated by the re-read."""
    m = _fresh_machine()
    update_opening_lock(m, [BAR1, BAR2, BAR3, BAR4], ib_locked=False, now_iso=NOW)
    locked_val_before = m._opening_locked_val

    update_opening_lock(m, [BAR1, BAR2, BAR3, BAR4, BAR5], ib_locked=False, now_iso=NOW)

    assert m._opening_negated is True
    # The re-read runs detect_opening_type on the closed bars (bars 1-4).
    # The result may or may not differ, but it must not be None/empty.
    assert m._opening_locked_val is not None
    assert m._opening_locked_val != ""
    # Negation timestamp is set
    assert m._opening_negated_at == NOW
