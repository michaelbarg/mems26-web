"""LEG_RIDE_V1 — leg detection (Michael's screenshot ruling 2026-07-31)."""
from backend.v9.systems.leg_state import detect_leg


def _r(h, l, c, lsma, cci):
    return {"high": h, "low": l, "close": c, "lsma_value": lsma, "cci_14": cci}


def _up_leg_rows():
    # stair-steps riding a rising LSMA, CCI positive — the screenshot
    return [
        _r(7496, 7490, 7495, 7489.0, 40),
        _r(7499, 7493, 7498, 7490.5, 55),
        _r(7502, 7496, 7501, 7492.5, 70),
        _r(7505, 7499, 7504, 7495.0, 85),
        _r(7508, 7502, 7507, 7498.0, 90),
        _r(7511, 7505, 7510, 7501.5, 95),
    ]


def test_up_leg_detected():
    leg, age, why = detect_leg(_up_leg_rows())
    assert leg == "UP", why
    assert age >= 2


def test_down_leg_detected():
    rows = [_r(2*7500-r["high"]+0, 2*7500-r["low"], 2*7500-r["close"],
               2*7500-r["lsma_value"], -r["cci_14"]) for r in _up_leg_rows()]
    # mirror: swap high/low ordering
    rows = [{"high": r["low"] if r["low"]>r["high"] else r["high"],
             "low": r["high"] if r["low"]>r["high"] else r["low"],
             "close": r["close"], "lsma_value": r["lsma_value"],
             "cci_14": r["cci_14"]} for r in rows]
    leg, _, why = detect_leg(rows)
    assert leg == "DOWN", why


def test_no_leg_when_lsma_flat():
    rows = _up_leg_rows()
    for r in rows:
        r["lsma_value"] = 7495.0
    assert detect_leg(rows)[0] is None


def test_leg_dies_when_close_loses_lsma():
    rows = _up_leg_rows()
    rows[-1]["close"] = rows[-1]["lsma_value"] - 4.0  # beyond the 2.5pt kiss-tolerance
    assert detect_leg(rows)[0] is None


def test_cci_tolerates_single_zlr_dip():
    rows = _up_leg_rows()
    rows[-2]["cci_14"] = -12   # the momentary zero-line dip = the ZLR itself
    leg, _, why = detect_leg(rows)
    assert leg == "UP", why


def test_cci_two_crossings_kills_leg():
    rows = _up_leg_rows()
    rows[-2]["cci_14"] = -12
    rows[-3]["cci_14"] = -8
    assert detect_leg(rows)[0] is None


def test_missing_canonical_lsma_honest_none():
    rows = _up_leg_rows()
    rows[-1]["lsma_value"] = None
    leg, _, why = detect_leg(rows)
    assert leg is None and "Rule 1" in why
