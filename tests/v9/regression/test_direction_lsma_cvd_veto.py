"""Anti-tautological regression tests for DIRECTION_LSMA_VETO (#68).

Tests the PURE helper `lsma_cvd_veto_direction` and its integration through
`compute_direction` with `lsma_veto=True`. Also proves flag-off is identical
to today's engine (the anti-tautology: the flag gates the override, not always-on).

if reverted → RED because: removing lsma_cvd_veto_direction or the short-circuit
in compute_direction would break the truth-table assertions and the
breakout_state=="lsma_cvd_veto" checks.
"""
from backend.v9.systems.direction_context import (
    compute_direction,
    cvd_slope,
    lsma_cvd_veto_direction,
)

IBH, IBL, POC = 110.0, 100.0, 105.0


def _bars(seq):
    """seq of (high, low, close, cumulative_delta).

    NOTE: cumulative_delta is actually PER-BAR delta (ask−bid for that bar),
    not a running cumulative. cvd_slope sums these over the lookback window.
    """
    return [{"high": h, "low": l, "close": c, "cumulative_delta": d} for (h, l, c, d) in seq]


# ── Truth table (6 rows) on the pure helper ──────────────────────────────

def test_lsma_up_cvd_up():
    assert lsma_cvd_veto_direction(+1, +1) == "UP"


def test_lsma_up_cvd_down_vetoed():
    """CVD opposes LSMA-UP → NEUTRAL."""
    assert lsma_cvd_veto_direction(+1, -1) == "NEUTRAL"


def test_lsma_up_cvd_zero():
    """CVD silent → LSMA leads."""
    assert lsma_cvd_veto_direction(+1, 0) == "UP"


def test_lsma_down_cvd_down():
    assert lsma_cvd_veto_direction(-1, -1) == "DOWN"


def test_lsma_down_cvd_up_vetoed():
    """CVD opposes LSMA-DOWN → NEUTRAL."""
    assert lsma_cvd_veto_direction(-1, +1) == "NEUTRAL"


def test_lsma_down_cvd_zero():
    """CVD silent → LSMA leads."""
    assert lsma_cvd_veto_direction(-1, 0) == "DOWN"


# ── Integration through compute_direction (lsma_veto=True) ──────────────

# Fixture: 5 bars with per-bar deltas all positive → net buying → slope +1
_BARS_CVD_UP = _bars([
    (106, 104, 105, 500), (108, 105, 107, 800), (109, 106, 108, 600),
    (110, 107, 109, 700), (111, 108, 110, 900),
])

# Fixture: 5 bars with per-bar deltas all negative → net selling → slope -1
_BARS_CVD_DOWN = _bars([
    (106, 104, 105, -500), (108, 105, 107, -800), (109, 106, 108, -600),
    (107, 104, 106, -700), (106, 103, 105, -900),
])


def test_compute_lsma_up_cvd_aligned():
    r = compute_direction(bars=_BARS_CVD_UP, ib_high=IBH, ib_low=IBL, poc=POC,
                          lsma_side=+1, lsma_veto=True)
    assert r["dir"] == "UP"
    assert r["breakout_state"] == "lsma_cvd_veto"
    assert r["lsma_side"] == +1


def test_compute_lsma_up_cvd_opposes_neutral():
    """CVD falling opposes LSMA UP → NEUTRAL (the veto)."""
    r = compute_direction(bars=_BARS_CVD_DOWN, ib_high=IBH, ib_low=IBL, poc=POC,
                          lsma_side=+1, lsma_veto=True)
    assert r["dir"] == "NEUTRAL"
    assert r["breakout_state"] == "lsma_cvd_veto"


def test_compute_lsma_down_cvd_aligned():
    r = compute_direction(bars=_BARS_CVD_DOWN, ib_high=IBH, ib_low=IBL, poc=POC,
                          lsma_side=-1, lsma_veto=True)
    assert r["dir"] == "DOWN"
    assert r["breakout_state"] == "lsma_cvd_veto"


def test_compute_lsma_down_cvd_opposes_neutral():
    """CVD rising opposes LSMA DOWN → NEUTRAL."""
    r = compute_direction(bars=_BARS_CVD_UP, ib_high=IBH, ib_low=IBL, poc=POC,
                          lsma_side=-1, lsma_veto=True)
    assert r["dir"] == "NEUTRAL"
    assert r["breakout_state"] == "lsma_cvd_veto"


# ── Flag-off == today's engine (anti-tautology) ─────────────────────────

def test_flag_off_identical_to_existing_engine():
    """lsma_veto=False → the LSMA override is NOT applied; same result as
    calling without the params at all. This is the anti-tautological proof:
    if reverted (lsma_veto always False), ALL these tests still pass, but the
    truth-table / breakout_state tests above go RED.

    if reverted → RED because: the truth-table tests assert
    breakout_state=='lsma_cvd_veto' which only appears when lsma_veto=True.
    """
    for bars in [_BARS_CVD_UP, _BARS_CVD_DOWN]:
        baseline = compute_direction(bars=bars, ib_high=IBH, ib_low=IBL, poc=POC)
        with_flag_off = compute_direction(bars=bars, ib_high=IBH, ib_low=IBL, poc=POC,
                                          lsma_side=+1, lsma_veto=False)
        assert baseline["dir"] == with_flag_off["dir"], (
            "flag-off must match baseline: %s vs %s" % (baseline, with_flag_off))
        assert baseline["breakout_state"] == with_flag_off["breakout_state"]


def test_flag_off_lsma_none_passthrough():
    """lsma_side=None (LSMA missing) with lsma_veto=True → fail-safe,
    falls through to the existing engine (not NEUTRAL from the override)."""
    baseline = compute_direction(bars=_BARS_CVD_UP, ib_high=IBH, ib_low=IBL, poc=POC)
    with_none = compute_direction(bars=_BARS_CVD_UP, ib_high=IBH, ib_low=IBL, poc=POC,
                                  lsma_side=None, lsma_veto=True)
    assert baseline["dir"] == with_none["dir"]
    assert with_none["breakout_state"] != "lsma_cvd_veto"


# ── CVD per-bar delta semantics (Fix #5, 2026-06-24) ────────────────────

def test_cvd_slope_all_positive_deltas_is_up():
    """On a buying day every per-bar delta is positive → cvd_slope = +1.
    The old formula (cum[-1] - cum[-1-3]) would have given noise/wrong sign
    because it compared two arbitrary per-bar values.

    if reverted → RED because: reverting to sign(a-b) with per-bar data
    yields sign(900-600)=+1 by luck here, but the GHOST test below fails.
    """
    # Real-world pattern: buying day, all deltas positive (3773, 3423, 3629, 7013)
    bars = _bars([
        (105, 103, 104, 3773), (106, 104, 105, 3423),
        (107, 105, 106, 3629), (108, 106, 107, 7013),
    ])
    assert cvd_slope(bars, lookback=3) == +1


def test_cvd_slope_all_negative_deltas_is_down():
    """All per-bar deltas negative → cvd_slope = -1."""
    bars = _bars([
        (107, 105, 106, -2000), (106, 104, 105, -1500),
        (105, 103, 104, -3000), (104, 102, 103, -2500),
    ])
    assert cvd_slope(bars, lookback=3) == -1


def test_ghost_0940_counter_trend_blocked():
    """GHOST-09:40 regression: on 2026-06-24 the engine read NEUTRAL (spurious
    veto) because the old cvd_slope compared per-bar deltas as if cumulative,
    yielding -1 on a buying day (1992 < 4662). The counter-trend GHOST SHORT
    slipped through. With the fix, sum of positive deltas → +1 → LONG direction
    → blocks the short.

    if reverted → RED because: reverting cvd_slope to sign(a-b) makes the
    slope = sign(1992-4662) = -1, so the engine reads DOWN/NEUTRAL instead of UP.
    """
    # Approximate 06-24 bars around 09:40 CT: price rising, all per-bar deltas positive
    # (buying pressure). The old formula saw 1992 < 4662 three bars ago → "selling".
    bars = _bars([
        (7442, 7438, 7440, 4662), (7448, 7440, 7445, 3423),
        (7455, 7445, 7452, 3629), (7462, 7450, 7460, 1992),
    ])
    # New: sum(4662+3423+3629) for lookback=3 = 11714 > 0 → +1
    assert cvd_slope(bars, lookback=3) == +1, "buying day must yield +1 slope"

    # With LSMA UP + CVD +1 → direction = UP → blocks a counter-trend SHORT
    r = compute_direction(bars=bars, ib_high=7470.0, ib_low=7440.0, poc=7455.0,
                          lsma_side=+1, lsma_veto=True)
    assert r["dir"] == "UP", "GHOST-09:40: engine must read UP (LONG), not NEUTRAL"
    assert r["breakout_state"] == "lsma_cvd_veto"
