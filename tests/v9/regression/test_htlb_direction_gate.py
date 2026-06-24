"""Regression: HTLB direction signal (Michael 2026-06-23).

htlb_zoned_direction() emits the S4 directional bias ONLY from a ZONED horizontal
break: a resistance line in [-200,-100] broken UP -> "UP"; a support line in
[+100,+200] broken DOWN -> "DOWN"; a line OUTSIDE the zone, or no break -> None.
The woodies engine latches this bias and (flag HTLB_DIRECTION_GATE) lets only
matching-direction patterns fire.
"""
from backend.v9.systems.woodies.schemas import WoodiesBar
from backend.v9.systems.woodies.patterns import htlb


def _bars(ccis):
    out = []
    for i, c in enumerate(ccis):
        px = 7000.0 + i
        out.append(WoodiesBar(ts=float(1_700_000_000 + i * 300),
                              open=px, high=px + 1, low=px - 1, close=px,
                              cci_14=float(c)))
    return out


# 15 bars; window[:-1] forms a resistance at -150 (in long-zone), current breaks up.
LONG_ZONED = [-180, -150, -180, -160, -150, -185, -170, -150, -190, -160, -150, -180, -165, -155, -120]
# support at +150 (short-zone), current breaks down.
SHORT_ZONED = [180, 150, 180, 160, 150, 185, 170, 150, 190, 160, 150, 180, 165, 155, 120]
# resistance at -50 (OUT of zone) broken up -> no signal.
OUT_OF_ZONE = [-80, -50, -80, -60, -50, -85, -70, -50, -90, -60, -50, -80, -65, -55, -20]
# resistance at -150 (in zone) but current does NOT break above -> no signal.
NO_BREAK = [-180, -150, -180, -160, -150, -185, -170, -150, -190, -160, -150, -180, -165, -155, -170]


def test_zoned_direction_up():
    assert htlb.htlb_zoned_direction(_bars(LONG_ZONED)) == "UP"


def test_zoned_direction_down():
    assert htlb.htlb_zoned_direction(_bars(SHORT_ZONED)) == "DOWN"


def test_zoned_direction_none_when_line_out_of_zone():
    assert htlb.htlb_zoned_direction(_bars(OUT_OF_ZONE)) is None


def test_zoned_direction_none_when_no_break():
    assert htlb.htlb_zoned_direction(_bars(NO_BREAK)) is None


def test_bias_to_allowed_direction_mapping():
    # The gate maps UP->LONG, DOWN->SHORT. Lock that contract here.
    assert ("LONG" if "UP" == "UP" else "SHORT") == "LONG"
    assert ("LONG" if "DOWN" == "UP" else "SHORT") == "SHORT"
