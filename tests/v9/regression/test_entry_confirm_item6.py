"""Item-6 — S4_ENTRY_CONFIRM_V1: confirm bar + CVD + fresh-extreme guard."""
import random

from backend.v9.systems.entry_confirm import entry_confirmed, at_fresh_extreme


def _bar(o, c, h=None, l=None):
    return {"o": o, "c": c, "h": h if h is not None else max(o, c),
            "l": l if l is not None else min(o, c)}


# --- entry_confirmed ---
def test_long_bullish_bar_confirms():
    ok, _ = entry_confirmed(direction="LONG", bars=[_bar(7500, 7504)])
    assert ok


def test_long_bearish_bar_rejected():
    ok, reason = entry_confirmed(direction="LONG", bars=[_bar(7504, 7500)])
    assert not ok and "confirm" in reason


def test_short_bearish_bar_confirms():
    ok, _ = entry_confirmed(direction="SHORT", bars=[_bar(7504, 7500)])
    assert ok


def test_cvd_alignment_required_when_flagged():
    # bullish bar but CVD sell-dominant → rejected when require_cvd
    ok, reason = entry_confirmed(direction="LONG", bars=[_bar(7500, 7504)],
                                 cvd_pos=0.2, require_cvd=True)
    assert not ok and "CVD" in reason
    ok2, _ = entry_confirmed(direction="LONG", bars=[_bar(7500, 7504)],
                             cvd_pos=0.8, require_cvd=True)
    assert ok2


def test_no_bars_fails_safe():
    ok, _ = entry_confirmed(direction="LONG", bars=[])
    assert not ok


# --- at_fresh_extreme (item-10 guard) ---
def test_long_at_fresh_high_flagged():
    """The 08:45 fixture: buying the top of the drive."""
    bars = [_bar(7580, 7585, h=7590), _bar(7585, 7588, h=7594)]
    assert at_fresh_extreme(direction="LONG", entry_price=7594.0, bars=bars) is True


def test_long_pullback_entry_not_flagged():
    bars = [_bar(7580, 7585, h=7594), _bar(7585, 7582, h=7588)]
    assert at_fresh_extreme(direction="LONG", entry_price=7580.0, bars=bars) is False


def test_short_at_fresh_low_flagged():
    bars = [_bar(7500, 7495, l=7492), _bar(7495, 7490, l=7486)]
    assert at_fresh_extreme(direction="SHORT", entry_price=7486.0, bars=bars) is True


def test_too_few_bars_fails_safe():
    assert at_fresh_extreme(direction="LONG", entry_price=7594.0,
                            bars=[_bar(7590, 7594)]) is False


# --- property/fuzz: a confirmed entry is NEVER a wrong-direction bar ---
def test_confirm_never_accepts_wrong_direction_fuzz():
    rnd = random.Random(46)
    for _ in range(2000):
        direction = rnd.choice(["LONG", "SHORT"])
        o = round(rnd.uniform(7400, 7700), 2)
        c = round(o + rnd.uniform(-8, 8), 2)
        ok, _ = entry_confirmed(direction=direction, bars=[_bar(o, c)])
        if ok:
            if direction == "LONG":
                assert c > o
            else:
                assert c < o
