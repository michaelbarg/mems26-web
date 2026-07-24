"""OPEN-FIRE v1 (OPENING_FIRE_V1) — 60-min window + PULLBACK-CONT entry.

Anti-tautological: the PULLBACK-CONT fixture is the REAL 07-23 RTH opening
(v9_bars_5min_woodies, 16:30-17:30 IL) — the session that rallied to 7486.5
(16:40) then rejected down, which the existing DRIVE/TD/ORR/EXTREME_REJECT
triggers all MISS. Michael's ruling AC (07-23): catch the SHORT after the 7486
rejection (~7466-7470). revert→RED: delete the PULLBACK-CONT block and
test_pullback_cont_catches_0723_short / test_revert_red_guard go red.

OFF (enable_pullback=False, the default) must be byte-identical to the 30-min
SHADOW spec — proven by test_off_is_byte_identical.
"""
import pytest

from backend.v9.systems.opening_entry import (
    build_opening_setup, evaluate_opening_entry)


def B(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


# ── REAL 07-23 RTH opening bars (source: v9_bars_5min_woodies, IL times) ──
BARS_0723 = [
    B(7453.5, 7474.5, 7444.75, 7473.75),    # 16:30  bar1 (OR)
    B(7473.75, 7479.25, 7468.75, 7474.75),  # 16:35  bar2  close>OR-high → drove_up
    B(7474.75, 7486.5, 7474.25, 7478.75),   # 16:40  bar3  peak 7486.5
    B(7478.75, 7480.75, 7462.0, 7464.25),   # 16:45  bar4  rejection close 7464.25
    B(7464.0, 7470.0, 7457.5, 7469.5),      # 16:50  bar5
    B(7469.75, 7473.0, 7453.0, 7455.75),    # 16:55  bar6
    B(7455.75, 7466.5, 7455.75, 7463.75),   # 17:00  bar7  (beyond old 30-min window)
    B(7463.5, 7469.75, 7448.75, 7453.75),   # 17:05  bar8
]


def test_pullback_cont_catches_0723_short():
    """Michael 07-23 AC: after the 7486.5 rejection, PULLBACK-CONT fires a SHORT
    at bar 4 (16:45) close 7464.25, stop behind 7486.5 + 16T, T1 = 1.5R."""
    bars = BARS_0723[:4]  # through 16:45
    t = evaluate_opening_entry(bars, enable_pullback=True)
    assert t is not None, "PULLBACK-CONT must fire on the 07-23 rejection"
    assert t["type"] == "PULLBACK_CONT"
    assert t["direction"] == "SHORT"
    assert t["entry"] == 7464.25
    assert t["extreme"] == 7486.5
    s = build_opening_setup(t, bars, shadow_only=False)
    assert s["classification"] == "OPENING_PULLBACK_CONT"
    assert s["stop"] == 7486.5 + 4.0           # peak + 16T (16 * 0.25)
    risk = s["stop"] - s["entry_price"]
    assert s["t1"] == pytest.approx(s["entry_price"] - 1.5 * risk)  # 1.5R short
    assert s["firing_system"] == 2


def test_revert_red_guard():
    """Explicit revert→RED: ON has the 07-23 short, OFF does not — so deleting
    the PULLBACK-CONT block turns the catch test red."""
    on = evaluate_opening_entry(BARS_0723[:4], enable_pullback=True)
    off = evaluate_opening_entry(BARS_0723[:4], enable_pullback=False)
    assert on and on["type"] == "PULLBACK_CONT"
    assert not (off and off.get("type") == "PULLBACK_CONT")


def test_off_is_byte_identical():
    """Default args (OFF) == explicit OFF, and existing triggers are unchanged:
    PULLBACK-CONT never appears with the flag off, and the narrow-OR DRIVE still
    fires exactly as before."""
    for n in range(2, 7):
        r_default = evaluate_opening_entry(BARS_0723[:n])
        r_off = evaluate_opening_entry(
            BARS_0723[:n], window_last_bar=6, enable_pullback=False)
        assert r_default == r_off
        assert not (r_default and r_default.get("type") == "PULLBACK_CONT")
    # a known pre-existing DRIVE must still fire identically under OFF
    drive_bars = [B(7530.0, 7533.0, 7528.25, 7531.0),
                  B(7531.0, 7536.0, 7530.5, 7535.0)]
    assert (evaluate_opening_entry(drive_bars)
            == evaluate_opening_entry(drive_bars, window_last_bar=6,
                                      enable_pullback=False))
    assert evaluate_opening_entry(drive_bars)["type"] == "DRIVE"


def test_pullback_not_premature_at_bar3():
    """At bar 3 the retrace off the 7486.5 peak is only 7.75pt (<33% of the 33pt
    rally) → no entry yet (waits for the real rejection at bar 4)."""
    t = evaluate_opening_entry(BARS_0723[:3], enable_pullback=True)
    assert not (t and t["type"] == "PULLBACK_CONT")


def test_bias_filter_blocks_counter_seed():
    """Opening-seed safety filter: a LONG bias blocks the 07-23 SHORT candidate
    (never fade a with-bias move); the agreeing SHORT bias still fires."""
    t_long = evaluate_opening_entry(BARS_0723[:4], enable_pullback=True, bias="LONG")
    assert not (t_long and t_long["type"] == "PULLBACK_CONT")
    t_short = evaluate_opening_entry(BARS_0723[:4], enable_pullback=True, bias="SHORT")
    assert t_short and t_short["type"] == "PULLBACK_CONT" and t_short["direction"] == "SHORT"


# ── window fixture: a rejection that completes only at bar 7 (needs 60-min) ──
WINDOW_FIX = [
    B(7500, 7505, 7495, 7503),   # bar1 OR (open 7500)
    B(7503, 7512, 7502, 7510),   # bar2 rally, close > OR-high → drove_up
    B(7510, 7515, 7508, 7513),   # bar3 peak 7515
    B(7513, 7514, 7509, 7511),   # bar4
    B(7511, 7513, 7508, 7510),   # bar5
    B(7510, 7512, 7506, 7509),   # bar6  (OFF window ends here)
    B(7509, 7510, 7501, 7503),   # bar7  rejection: close<open & <prior, still > session-open (no ORR)
]


def test_window_capped_off_extended_on():
    """OFF caps at bar 6 (30 min) → n=7 vetoed to None; ON (window 12) lifts the
    veto and the bar-7 rejection fires PULLBACK-CONT SHORT."""
    assert evaluate_opening_entry(WINDOW_FIX) is None          # OFF: n=7 > 6
    r = evaluate_opening_entry(WINDOW_FIX, window_last_bar=12, enable_pullback=True)
    assert r and r["type"] == "PULLBACK_CONT" and r["direction"] == "SHORT"
    assert r["extreme"] == 7515


def test_long_pullback_symmetric():
    """Symmetric LONG: a down-dip off the open that retraces ≥33% up with a
    bullish rejection bar → LONG, stop behind the trough."""
    bars = [
        B(7500.0, 7502.0, 7490.0, 7492.0),   # bar1 OR (open 7500)
        B(7492.0, 7493.0, 7480.0, 7482.0),   # bar2 drive down (close < OR-low 7490)
        B(7482.0, 7484.0, 7478.0, 7479.0),   # bar3 trough 7478
        B(7479.0, 7491.0, 7479.0, 7490.0),   # bar4 rejection UP (close>open & >prior)
    ]
    t = evaluate_opening_entry(bars, enable_pullback=True)
    assert t and t["type"] == "PULLBACK_CONT" and t["direction"] == "LONG"
    assert t["extreme"] == 7478.0
    s = build_opening_setup(t, bars, shadow_only=False)
    assert s["stop"] == 7478.0 - 4.0           # trough − 16T
    risk = s["entry_price"] - s["stop"]
    assert s["t1"] == pytest.approx(s["entry_price"] + 1.5 * risk)  # 1.5R long


def test_one_pullback_per_session():
    """PULLBACK-CONT fires at most once (tracked in `already_fired`)."""
    assert evaluate_opening_entry(BARS_0723[:4], {"PULLBACK_CONT"},
                                  enable_pullback=True) is None
