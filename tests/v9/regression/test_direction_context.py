"""Anti-tautological tests for the dynamic direction-context model (#68).

Each case asserts that DIRECTION depends on CVD + breakout-state (not just price
geometry): flipping CVD flips/voids the call. The 06-11 "failed-low → reversal"
is the headline case Michael taught.

NOTE (2026-06-24): cumulative_delta is actually PER-BAR delta (ask−bid for that
bar), not a running cumulative. cvd_slope = sign(Σ delta over last N bars).
Fixtures use per-bar deltas accordingly.
"""
from backend.v9.systems.direction_context import compute_direction

IBH, IBL, POC = 110.0, 100.0, 105.0


def _bars(seq):
    # seq of (high, low, close, cumulative_delta) — cumulative_delta = per-bar delta
    return [{"high": h, "low": l, "close": c, "cumulative_delta": d} for (h, l, c, d) in seq]


def test_accepted_up_go_with():
    # All per-bar deltas positive → sum > 0 → cs >= 0 → accepted_up
    b = _bars([(106, 104, 105, 100), (108, 105, 107, 200), (111, 107, 110, 300),
               (113, 109, 112, 400), (116, 112, 115, 500)])
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)
    assert r["dir"] == "UP" and r["breakout_state"] == "accepted_up", r


def test_accepted_down_go_with():
    # All per-bar deltas negative → sum < 0 → cs <= 0 → accepted_down
    b = _bars([(104, 102, 103, -100), (101, 98, 99, -200), (99, 95, 96, -300),
               (97, 93, 94, -400), (95, 91, 92, -500)])
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)
    assert r["dir"] == "DOWN" and r["breakout_state"] == "accepted_down", r


def test_failed_low_reversal_0611():
    # Poked below IBL (low 97 < 100) then back inside (close 104).
    # Per-bar deltas: selling early then strong buying on reversal → sum of last 3 > 0
    b = _bars([(104, 102, 103, -500), (102, 98, 99, -800), (101, 97, 98, -300),
               (103, 99, 101, 600), (105, 101, 104, 1200)])
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)
    assert r["dir"] == "UP" and r["breakout_state"] == "failed_low", r


def test_failed_high_fade():
    # Poked above IBH (high 113 > 110) then back inside (close 107).
    # Per-bar deltas: buying early then selling on fade → sum of last 3 < 0
    b = _bars([(108, 105, 107, 500), (112, 108, 111, 400), (113, 109, 109, -200),
               (110, 106, 108, -600), (109, 105, 107, -800)])
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)
    assert r["dir"] == "DOWN" and r["breakout_state"] == "failed_up", r


def test_balance_above_value_cvd_down():
    # Wide-enough range; price above POC. Per-bar deltas: net negative over last 3 → cs < 0
    b = _bars([(102, 101, 101, 300), (105, 102, 104, 200), (108, 104, 107, -100),
               (107, 105, 106, -400), (109, 106, 108, -600)])
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)
    assert r["dir"] == "DOWN" and r["breakout_state"] == "balance", r


def test_balance_below_value_cvd_up():
    # Wide-enough range; price below POC. Per-bar deltas: net positive over last 3 → cs > 0
    b = _bars([(108, 107, 108, -300), (106, 103, 104, -200), (104, 101, 102, 100),
               (105, 102, 103, 400), (103, 101, 102, 600)])
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)
    assert r["dir"] == "UP" and r["breakout_state"] == "balance", r


def test_no_ib_is_neutral():
    b = _bars([(105, 103, 104, 100), (106, 104, 105, 200)])
    r = compute_direction(bars=b, ib_high=None, ib_low=None, poc=None)
    assert r["dir"] == "NEUTRAL" and r["breakout_state"] == "forming", r


def test_revert_failed_low_with_cvd_down_is_not_up():
    # SAME failed-low price geometry, but per-bar deltas net negative → cs < 0 → not reversal UP
    b = _bars([(104, 102, 103, 100), (102, 98, 99, 200), (101, 97, 98, -300),
               (103, 99, 101, -600), (105, 101, 104, -800)])
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)
    assert r["dir"] != "UP", r  # CVD flipped → direction is not the bullish reversal


def test_chop_narrow_range_stand_aside():
    # last 8 bars stuck in a ~3-pt band; IB width = 10 → 3 < 0.55*10 → chop → no fade
    # Per-bar deltas mixed/small → doesn't matter, chop triggers on range
    b = _bars([(106, 104, 105, 50), (106, 103, 104, 80), (105, 104, 105, -60),
               (106, 104, 105, 30), (105, 103, 104, -20), (106, 104, 105, 40),
               (105, 104, 105, 10), (106, 103, 104, -30)])
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)
    assert r["dir"] == "NEUTRAL" and r["breakout_state"] == "chop", r


def test_accepted_breakout_overrides_chop():
    # a real accepted breakout up is NOT chop (conviction)
    b = _bars([(106, 104, 105, 100), (108, 105, 107, 200), (111, 107, 110, 300),
               (113, 109, 112, 400), (116, 112, 115, 500)])
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)
    assert r["breakout_state"] == "accepted_up", r


def test_trend_day_down_pullback_stays_down():
    # 06-16 case: broke below IBL, pulled back inside with CVD up (reversal buying).
    # WITHOUT day_type → failed_low→reversal UP; WITH Trend → stays DOWN.
    b = _bars([(106, 104, 105, -500), (102, 98, 99, -800), (101, 97, 98, -300),
               (103, 99, 101, 600), (105, 101, 104, 1200)])
    assert compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)["dir"] == "UP"
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC, day_type="Trend_DD")
    assert r["dir"] == "DOWN" and r["breakout_state"] == "trend_with", r


def test_trend_day_up_pullback_stays_up():
    # Mirror: broke above IBH, pulled back inside with CVD down (fade selling).
    # WITHOUT = failed_up fade DOWN; WITH Trend → stays UP.
    b = _bars([(108, 106, 107, 500), (112, 108, 111, 400), (113, 109, 109, -200),
               (110, 106, 108, -600), (109, 105, 107, -800)])
    assert compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC)["dir"] == "DOWN"
    r = compute_direction(bars=b, ib_high=IBH, ib_low=IBL, poc=POC, day_type="Trend_Normal")
    assert r["dir"] == "UP" and r["breakout_state"] == "trend_with", r
