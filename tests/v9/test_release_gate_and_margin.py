

# ── 2026-07-29 audit fixes: trend bypass + V-reversal release ──────────────

def test_trend_bypass_with_move_short_on_displaced_session():
    from backend.v9.systems.release_gate import trend_bypass
    # session opened 7451, now 7411 (40pt down) — SHORT is with-move → bypass
    assert trend_bypass(7451.0, 7411.0, "SHORT", pts=15.0) is True


def test_trend_bypass_counter_move_keeps_gate():
    from backend.v9.systems.release_gate import trend_bypass
    # same displaced-down session — a LONG is counter-move → gate stays
    assert trend_bypass(7451.0, 7411.0, "LONG", pts=15.0) is False


def test_trend_bypass_small_displacement_keeps_gate():
    from backend.v9.systems.release_gate import trend_bypass
    assert trend_bypass(7450.0, 7440.0, "SHORT", pts=15.0) is False


def test_trend_bypass_unknown_inputs_fail_closed():
    from backend.v9.systems.release_gate import trend_bypass
    assert trend_bypass(None, 7411.0, "SHORT") is False
    assert trend_bypass(7451.0, None, "SHORT") is False


def test_v_reversal_releases_on_conviction_without_contraction():
    """Today's bottom: low 7373 on vol 9690, reversal bars on HIGH volume
    (13876/8434/11646) with higher lows, closing far above the zone. The old
    gate demanded volume dry-up and held every long into a +62pt recovery."""
    from backend.v9.systems.release_gate import Bar, check_release
    bars = [
        Bar(7385, 7378, 7380, 8000),
        Bar(7380, 7373, 7375, 9690),    # extreme low, heavy volume
        Bar(7390, 7377.5, 7389, 13876),  # higher low, HIGH vol
        Bar(7395, 7385, 7394, 8434),     # higher low
        Bar(7404, 7391, 7403, 11646),    # higher low, closes 7403 > 7373+16
    ]
    v = check_release(bars, "LONG")
    assert v.released, v.reason
    assert "V-reversal" in v.reason
    assert v.structural_stop is not None and v.structural_stop < 7373


def test_v_reversal_needs_decisive_close_not_just_edge():
    """One close barely past the zone edge on active volume still waits."""
    from backend.v9.systems.release_gate import Bar, check_release
    bars = [
        Bar(7385, 7378, 7380, 8000),
        Bar(7380, 7373, 7375, 9690),
        Bar(7384, 7375, 7382, 13876),
        Bar(7385, 7377, 7382, 12000),
        Bar(7386, 7379, 7382, 11000),   # close 7382 > zone_hi 7381 but < 7389
    ]
    v = check_release(bars, "LONG")
    assert not v.released
