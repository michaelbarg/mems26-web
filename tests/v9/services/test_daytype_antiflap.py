"""Anti-flap hysteresis tests (Michael 2026-07-09 live incident): a live day-type CHANGE must
persist >= hold before it reaches the gates, so a bar-to-bar flapping machine cannot SKIP fires on
a transient wrong label (07-09: REACTIVE/ZLR were killed on a transient 'Nontrend' on a +50pt
drive-up day, while classify_replay stayed stable). Targets the pure helper; get_live_day_type's
flag-OFF path is byte-identical raw passthrough."""
from backend.v9.services.trade_context import _antiflap_day_type

HOLD = 300.0


def fresh():
    return {"stable": None, "pending": None, "since": 0.0}


def test_first_value_accepted_immediately():
    st = fresh()
    assert _antiflap_day_type("Normal", 0.0, HOLD, st) == "Normal"
    assert st["stable"] == "Normal"


def test_same_value_returns_stable():
    st = fresh(); _antiflap_day_type("Normal", 0.0, HOLD, st)
    assert _antiflap_day_type("Normal", 5.0, HOLD, st) == "Normal"


def test_transient_flap_is_suppressed():
    # THE INCIDENT: a 1-read flap to Nontrend within the hold must NOT reach the gates.
    st = fresh(); _antiflap_day_type("Normal", 0.0, HOLD, st)
    assert _antiflap_day_type("Nontrend", 10.0, HOLD, st) == "Normal"   # held, not promoted
    assert _antiflap_day_type("Normal", 20.0, HOLD, st) == "Normal"     # flap gone → pending cleared
    assert st["pending"] is None


def test_flap_sequence_never_leaks():
    # 07-09 shape: Nontrend<->Normal<->Nontrend all within < hold → output stays Normal throughout.
    st = fresh(); _antiflap_day_type("Normal", 0.0, HOLD, st)
    seq = [("Nontrend", 30), ("Normal", 60), ("Nontrend", 90), ("Normal", 120), ("Nontrend", 150)]
    outs = [_antiflap_day_type(v, t, HOLD, st) for v, t in seq]
    assert set(outs) == {"Normal"}, outs


def test_sustained_change_promotes_after_hold():
    st = fresh(); _antiflap_day_type("Normal", 0.0, HOLD, st)
    assert _antiflap_day_type("Variation", 100.0, HOLD, st) == "Normal"              # candidate starts
    assert _antiflap_day_type("Variation", 100.0 + HOLD - 1, HOLD, st) == "Normal"   # not held yet
    assert _antiflap_day_type("Variation", 100.0 + HOLD, HOLD, st) == "Variation"    # held → promoted
    assert st["stable"] == "Variation"


def test_a_different_candidate_restarts_the_clock():
    # ANTI-TAUTOLOGY: switching the candidate resets 'since' → the FIRST candidate never promotes.
    st = fresh(); _antiflap_day_type("Normal", 0.0, HOLD, st)
    _antiflap_day_type("Nontrend", 100.0, HOLD, st)                                  # candidate A @100
    _antiflap_day_type("Variation", 200.0, HOLD, st)                                 # candidate B @200 (resets)
    assert _antiflap_day_type("Variation", 200.0 + HOLD - 1, HOLD, st) == "Normal"   # B not held yet
    assert st["stable"] == "Normal"


def test_transient_none_keeps_stable():
    st = fresh(); _antiflap_day_type("Normal", 0.0, HOLD, st)
    assert _antiflap_day_type(None, 10.0, HOLD, st) == "Normal"


def test_zero_hold_propagates_immediately():
    # ANTI-TAUTOLOGY: with hold=0 a change is NOT suppressed → proves the hold is what gates it.
    st = fresh(); _antiflap_day_type("Normal", 0.0, 0.0, st)
    assert _antiflap_day_type("Nontrend", 1.0, 0.0, st) == "Nontrend"
