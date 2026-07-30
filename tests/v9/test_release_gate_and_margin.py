

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


def test_daytype_conf_sufficient_thresholds():
    from backend.v9.gateway.trading_gateway import _daytype_conf_sufficient
    assert _daytype_conf_sufficient(0.0, 0.4) is False    # today's poisoned label
    assert _daytype_conf_sufficient(0.33, 0.4) is False
    assert _daytype_conf_sufficient(0.4, 0.4) is True
    assert _daytype_conf_sufficient(0.9, 0.4) is True
    assert _daytype_conf_sufficient(None, 0.4) is True    # unknown => legacy behavior
    assert _daytype_conf_sufficient("bad", 0.4) is True   # unparsable => legacy


# ── P5 executions (Michael ruling 2026-07-30 "תבצע אתה") ──────────────────

def _fire_req(mult):
    from backend.v9.shared.pre_fire_validator import FireRequest
    return FireRequest(system_id="T1_NUMBER_BAR", direction="LONG",
                       entry_price=7444.0, stop_price=7410.25,
                       t1_price=7452.0, t2_price=7460.25,
                       time_stop_minutes=90, confidence=70,
                       expected_t2_r_mult=mult)


def test_rr_breakout_mm_rescues_capped_t2(monkeypatch):
    """21:40 07-29: risk 33.75, t2-reward 16.25 (old high), continuation mult 2.0."""
    monkeypatch.setenv("RR_BREAKOUT_MM_V1", "1")
    from backend.v9.shared.pre_fire_validator import validate_fire
    assert validate_fire(_fire_req(2.0)).valid is True


def test_rr_breakout_mm_off_keeps_reject(monkeypatch):
    monkeypatch.delenv("RR_BREAKOUT_MM_V1", raising=False)
    from backend.v9.shared.pre_fire_validator import validate_fire
    r = validate_fire(_fire_req(2.0))
    assert r.valid is False and "R:R" in r.fail_reason


def test_rr_breakout_mm_no_rescue_for_reversal_mult(monkeypatch):
    """Reversal-class mult (1.5) is NOT > RR_BREAKOUT_MIN_MULT — stays rejected."""
    monkeypatch.setenv("RR_BREAKOUT_MM_V1", "1")
    from backend.v9.shared.pre_fire_validator import validate_fire
    assert validate_fire(_fire_req(1.5)).valid is False
