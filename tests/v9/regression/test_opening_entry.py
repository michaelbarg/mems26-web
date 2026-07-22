"""Opening-entry triggers (07-22, SHADOW phase) — revised rules pinned to the
31-session historical-validation findings:
  • wide-OR drives were noise (06-12: 51pt R, lost) → DRIVE only on narrow OR.
  • bar-1-wick 'weak' TEST_DRIVE fired 84% of days at −0.35R avg → excursion
    must come from bar 2 onward, ≥ 50% of OR.
  • ORR was the only >50%-to-+1R trigger but must SUPERSEDE a drive entry.
  • AUCTION days must produce NO entry.
"""
import pytest

from backend.v9.systems.opening_entry import (
    OR_NARROW_MAX_PTS, build_opening_setup, evaluate_opening_entry)


def B(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


# bar1: narrow OR 4.75pt (the historical winner's class)
NARROW_B1 = B(7530.0, 7533.0, 7528.25, 7531.0)
# bar1: wide OR 20pt (the 06-12 noise class)
WIDE_B1 = B(7530.0, 7542.0, 7522.0, 7531.0)


def test_narrow_or_drive_long_fires():
    bars = [NARROW_B1, B(7531.0, 7536.0, 7530.5, 7535.0)]  # close > OR high 7533
    t = evaluate_opening_entry(bars)
    assert t and t["type"] == "DRIVE" and t["direction"] == "LONG"
    assert t["or_width"] <= OR_NARROW_MAX_PTS


def test_wide_or_drive_does_not_fire():
    bars = [WIDE_B1, B(7531.0, 7545.0, 7530.0, 7544.0)]  # close > OR high but OR=20pt
    assert evaluate_opening_entry(bars) is None


def test_bar1_wick_does_not_arm_test_drive():
    """The 'weak' artifact: bar-1's own wick was the only excursion. Bar 2
    closing on the other side of the open must NOT fire."""
    b1 = B(7530.0, 7538.0, 7526.0, 7531.0)  # big wick both ways, OR 12pt
    bars = [b1, B(7531.0, 7532.0, 7527.0, 7528.0)]  # bar2 closes below open
    assert evaluate_opening_entry(bars) is None


def test_real_test_drive_fires_on_reclaim():
    """Excursion ≥50% of OR from bar 2, no drive-close, then close back
    through the open → entry on the reclaim side."""
    b1 = B(7530.0, 7534.0, 7526.0, 7529.0)          # OR 8pt → need ≥4pt excursion
    b2 = B(7529.0, 7535.5, 7528.5, 7532.0)          # up-excursion 5.5 > 4, close < OR high 7534? 7532<7534 ✓ no drive
    b3 = B(7532.0, 7532.5, 7527.0, 7528.5)          # closes back through open 7530 → SHORT
    t = evaluate_opening_entry([b1, b2, b3])
    assert t and t["type"] == "TEST_DRIVE" and t["direction"] == "SHORT"


def test_orr_supersedes_drive():
    """Drive-close up (bar2), then bar4 closes back below the OPEN → ORR SHORT,
    even though DRIVE already fired (supersede)."""
    b1 = NARROW_B1                                   # open 7530, OR high 7533
    b2 = B(7531.0, 7536.0, 7530.5, 7535.0)          # drive-close up (DRIVE fired)
    fired = set()
    t1 = evaluate_opening_entry([b1, b2], fired)
    assert t1 and t1["type"] == "DRIVE"
    fired.add("DRIVE")
    b3 = B(7535.0, 7535.5, 7530.0, 7531.5)
    b4 = B(7531.5, 7532.0, 7526.0, 7528.0)          # close < open 7530 → reversal
    t2 = evaluate_opening_entry([b1, b2, b3, b4], fired)
    assert t2 and t2["type"] == "ORR" and t2["direction"] == "SHORT"
    assert t2["reverses"] == "UP_DRIVE"
    fired.add("ORR")
    # only one ORR
    assert evaluate_opening_entry([b1, b2, b3, b4], fired) is None


def test_auction_rotation_no_entry():
    """Rotation inside the OR through bar 6 → honest None (the historical spec
    claimed a tradable open 31/31 days — must be possible to decline)."""
    b1 = B(7530.0, 7536.0, 7524.0, 7530.5)  # OR 12pt
    rot = [B(7530.5, 7533.0, 7527.5, 7529.5), B(7529.5, 7532.0, 7527.0, 7531.0),
           B(7531.0, 7534.0, 7528.0, 7530.0), B(7530.0, 7533.5, 7527.5, 7531.5),
           B(7531.5, 7533.0, 7528.5, 7529.0)]
    for n in range(2, 7):
        assert evaluate_opening_entry([b1] + rot[:n - 1]) is None


def test_one_initiating_entry_per_session():
    bars = [NARROW_B1, B(7531.0, 7536.0, 7530.5, 7535.0)]
    assert evaluate_opening_entry(bars, {"DRIVE"}) is None
    assert evaluate_opening_entry(bars, {"TEST_DRIVE"}) is None


def test_build_setup_shadow_structure_stop_and_1r():
    bars = [NARROW_B1, B(7531.0, 7536.0, 7530.5, 7535.0)]
    t = evaluate_opening_entry(bars)
    s = build_opening_setup(t, bars, shadow_only=True)
    assert s["metadata"]["shadow_only"] is True
    assert s["classification"] == "OPENING_DRIVE"
    # stop behind session low 7528.25 − 6T = 7526.75
    assert s["stop"] == 7526.75
    # T1 = +1R (bank)
    risk = s["entry_price"] - s["stop"]
    assert s["t1"] == pytest.approx(s["entry_price"] + risk)


def test_gateway_shadow_only_never_routes_live(monkeypatch):
    """A shadow_only setup must be recorded but never fill demo/live slots."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway()
    monkeypatch.setattr(gw, "_is_live_enabled", lambda sid: True)
    monkeypatch.setattr(gw, "_is_demo_enabled", lambda sid: True)
    setup = {
        "firing_system": 2, "direction": "LONG", "classification": "OPENING_DRIVE",
        "confidence": 0.6, "entry_price": 7535.0, "stop": 7526.75, "t1": 7543.25,
        "t2": None, "t3": None,
        "metadata": {"opening_entry": "DRIVE", "shadow_only": True},
    }
    result = gw.route_setup(setup, 2)
    # The essential property: a shadow_only setup NEVER fills demo/live —
    # whether it passed all gates (→ shadow=True via the guard) or an earlier
    # gate blocked it (time-of-day dependent in this test environment).
    assert result.get("live") is None and result.get("demo") is None
    assert gw.live_slot is None and gw.demo_slot is None
    if not result.get("blocked_by"):
        assert result.get("shadow") is True  # guard branch reached


# ── EXTREME_REJECT (Michael's opening rule, validated 31 sessions) ──

def test_extreme_reject_low_test_confirm_fires():
    """Test bar touches running low + rejection close; next bar confirms
    (closes higher) → LONG at confirm close, stop = extreme − 10T."""
    b1 = B(7530.0, 7536.0, 7529.0, 7530.5)
    b2 = B(7530.5, 7531.0, 7524.0, 7526.0)   # running low 7524
    b3 = B(7526.0, 7527.0, 7524.25, 7526.5)  # tests 7524 (low 7524.25<=7524.5), closes 7526.5>7524.5
    b4 = B(7526.5, 7530.0, 7526.0, 7529.0)   # confirms (7529 > 7526.5)
    t = evaluate_opening_entry([b1, b2, b3, b4])
    assert t and t["type"] == "EXTREME_REJECT" and t["direction"] == "LONG"
    s = build_opening_setup(t, [b1, b2, b3, b4], shadow_only=True)
    assert s["stop"] == 7524.0 - 2.5  # extreme 7524 − 10T
    assert s["metadata"]["shadow_only"] is True


def test_extreme_reject_no_confirm_no_fire():
    b1 = B(7530.0, 7536.0, 7529.0, 7530.5)
    b2 = B(7530.5, 7531.0, 7524.0, 7526.0)
    b3 = B(7526.0, 7527.0, 7524.25, 7526.5)  # test bar
    b4 = B(7526.5, 7526.75, 7523.0, 7525.0)  # does NOT confirm (close < test close)
    t = evaluate_opening_entry([b1, b2, b3, b4])
    assert not (t and t["type"] == "EXTREME_REJECT")


def test_extreme_reject_sliding_close_not_a_test():
    """Close only 0.25 above the extreme = sliding, not rejection."""
    b1 = B(7530.0, 7536.0, 7529.0, 7530.5)
    b2 = B(7530.5, 7531.0, 7524.0, 7526.0)
    b3 = B(7526.0, 7526.5, 7524.0, 7524.25)  # close 7524.25 <= 7524+0.5
    b4 = B(7524.25, 7528.0, 7524.0, 7527.5)
    t = evaluate_opening_entry([b1, b2, b3, b4])
    assert not (t and t["type"] == "EXTREME_REJECT")
