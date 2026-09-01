# -*- coding: utf-8 -*-
"""OPENING_PATTERN_SKIP_V1 — the temporary hold on the losing opening patterns.

Michael 2026-09-01 14:05, approving the scoped reading of *"לא נאפשר מסחר עד
שיתוקן"*: hold the opening patterns that lost, let the rest of the day trade.

Scoped by PATTERN, never by hour — Michael 2026-08-20: *"אתה לא מגביל שעות
בשום אופן"*. An hour gate would have been the obvious implementation and is
forbidden; that is why this reads a pattern list.

What the tests pin down:
  * unset ⇒ the block cannot fire (byte-identical behaviour)
  * only the named patterns are dropped — a neighbour like OPENING_TEST_DRIVE
    that shares a prefix must survive
  * the DRIVE flag CC built is untouched and still works on its own

The expiry condition is the point. This is a SAFETY hold with unequal evidence
behind it — DRIVE n=6/0 wins, ORR n=3/1 win, PULLBACK_CONT n=1 — and Michael's
standing rule is that a losing pattern gets fixed, not cancelled. The list must
be emptied once the opening ATR seed and the ENTRY_LOCATION_QUALITY wiring land.
`test_the_hold_is_recorded_as_temporary` fails if the code stops saying so,
because a hold that loses its expiry note becomes a silent kill — exactly what
happened to FAMIR and VEGAS (T-195).
"""
from __future__ import annotations

import os
import re

import pytest

MOD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))),
    "backend", "v9", "systems", "five_min", "five_min_system.py")


def _skip_block() -> str:
    """The comment + code of the skip gate.

    Anchored on the assignment, not on the first mention of the flag name: the
    first mention is inside the comment block, and a window centred there
    reaches back into unrelated code and stops short of the predicate.
    """
    src = open(MOD, encoding="utf-8").read()
    i = src.index('_ops_raw = os.getenv("OPENING_PATTERN_SKIP_V1"')
    start = src.rindex("# OPENING_PATTERN_SKIP_V1", 0, i)
    end = src.index("if _trig:", i)
    return src[start:end]


def _decide(trig_type, env_value):
    """The gate's logic, mirrored exactly as written in five_min_system.

    A behavioural test would need a full FiveMinSystem with bars, a gateway and
    an opening window — that harness does not exist, and inventing one would
    test the harness. So the predicate is mirrored here and
    `test_the_mirror_matches_the_source` fails if the source stops matching it.
    Returns True when the trigger SURVIVES.
    """
    raw = env_value or ""
    if not raw.strip():
        return True
    names = {p.strip().upper() for p in raw.split(",") if p.strip()}
    return (trig_type or "").upper() not in names


LIVE_LIST = "OPENING_ORR,OPENING_PULLBACK_CONT"


# ── the hold itself ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("pattern,survives", [
    ("OPENING_ORR", False),            # n=3, 1W-2L, −$120
    ("OPENING_PULLBACK_CONT", False),  # n=1, −$216
    ("OPENING_TEST_DRIVE", True),      # never ruled on — must keep firing
    ("OPENING_DRIVE", True),           # held by CC's own flag, not this one
    ("ZLR", True),                     # not an opening pattern at all
])
def test_only_the_named_patterns_are_held(pattern, survives):
    assert _decide(pattern, LIVE_LIST) is survives


def test_unset_holds_nothing():
    """Flag OFF ⇒ byte-identical. The hold must be opt-in, in both directions."""
    for p in ("OPENING_ORR", "OPENING_PULLBACK_CONT", "OPENING_DRIVE", "ZLR"):
        assert _decide(p, "") is True
        assert _decide(p, "   ") is True


def test_a_prefix_is_not_a_match():
    """MUTATION GUARD. `startswith` instead of an exact set lookup would hold
    OPENING_ORR_FADE and anything else sharing the prefix — a wider kill than
    was ruled, and invisible in the log line."""
    assert _decide("OPENING_ORR_FADE", LIVE_LIST) is True
    assert _decide("OPENING_PULLBACK_CONT_X", LIVE_LIST) is True


def test_whitespace_and_case_do_not_change_the_hold():
    for raw in ("opening_orr", " OPENING_ORR ", "OPENING_ORR,", ",OPENING_ORR"):
        assert _decide("OPENING_ORR", raw) is False
        assert _decide("OPENING_TEST_DRIVE", raw) is True


# ── the gate must stay pattern-scoped, never hour-scoped ─────────────────────

def test_the_hold_is_not_implemented_as_an_hour_gate():
    """Michael 2026-08-20: 'אתה לא מגביל שעות בשום אופן'. An hour window is the
    obvious way to write this and is forbidden."""
    blk = _skip_block()
    for forbidden in ("hour", "datetime.now", "time()", "RTH_OPEN", "minute"):
        assert forbidden not in blk.replace("# ", ""), (
            f"the skip block references {forbidden!r} — this hold is scoped by "
            "pattern, never by clock")


# ── the source must keep matching the mirror ─────────────────────────────────

def test_the_mirror_matches_the_source():
    blk = _skip_block()
    assert 'os.getenv("OPENING_PATTERN_SKIP_V1", "")' in blk
    assert ".split(\",\")" in blk
    assert ".upper()" in blk
    # exact membership, not a prefix or substring test
    assert re.search(r'\.upper\(\)\s+in\s+_ops', blk), (
        "membership is no longer an exact set lookup — see "
        "test_a_prefix_is_not_a_match for why that widens the kill")


def test_the_drive_flag_is_untouched():
    """CC's OPENING_DRIVE_SKIP_V1 must keep working on its own — this flag is
    additive, so removing it cannot resurrect DRIVE."""
    src = open(MOD, encoding="utf-8").read()
    assert 'os.getenv("OPENING_DRIVE_SKIP_V1", "0")' in src
    assert '_trig.get("type") == "OPENING_DRIVE"' in src


def test_the_hold_is_recorded_as_temporary():
    """The expiry condition must survive in the code.

    FAMIR and VEGAS (T-195) were switched off on evidence and simply stayed off,
    against the standing rule that a losing pattern is fixed rather than
    cancelled. The difference between a hold and a silent kill is whether the
    condition for lifting it is written down where the next reader will see it.
    """
    blk = _skip_block()
    assert "temporary" in blk.lower() or "זמני" in blk
    assert "ENTRY_LOCATION_QUALITY" in blk, (
        "the lifting condition is gone — without it this hold becomes a "
        "permanent kill nobody decided on")
    assert "n=1" in blk, (
        "the unequal evidence behind the three patterns is no longer recorded")
