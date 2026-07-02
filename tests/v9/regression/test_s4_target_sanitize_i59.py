"""I-59 regression — S4 fire package must pass A7's monotonic-ladder validator.

Live incident (2026-07-02 ~19:46 IL): ZLR SHORT detected, A1-A6 PASS, then
A7 FAIL "SHORT: must have entry > t1 > t2" — RUNNER_T2 produced t2 equal to /
beyond t1 (277/278: t1==t2==7530.625) → every S4 fire dropped silently.

Tests drive the real sanitizer + the real pre_fire validator end-to-end.
"""
from backend.v9.systems.woodies.woodies_system import _sanitize_s4_targets
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire


def _validate(direction, entry, stop, t1, t2):
    return validate_fire(FireRequest(
        system_id="T2_WOODIES", direction=direction, entry_price=entry,
        stop_price=stop, t1_price=t1, t2_price=t2,
        time_stop_minutes=90, confidence=65,
    ))


def test_short_duplicate_t2_becomes_none_and_passes_validator():
    """The 277/278 case: SHORT with t1==t2 → sanitize → t2=None → A7 PASS."""
    t1, t2 = _sanitize_s4_targets("SHORT", 7532.0, 7530.625, 7530.625)
    assert t2 is None and t1 == 7530.625
    resp = _validate("SHORT", 7532.0, 7545.25, t1, t2)
    assert resp.valid, f"validator must accept t2=None: {resp.fail_reason}"


def test_short_t2_beyond_t1_becomes_none():
    t1, t2 = _sanitize_s4_targets("SHORT", 7560.0, 7550.0, 7555.0)  # t2 ABOVE t1
    assert t2 is None
    assert _validate("SHORT", 7560.0, 7570.0, t1, t2).valid


def test_long_bad_t2_becomes_none():
    t1, t2 = _sanitize_s4_targets("LONG", 7500.0, 7510.0, 7505.0)
    assert t2 is None
    assert _validate("LONG", 7500.0, 7492.0, t1, t2).valid


def test_valid_ladder_untouched():
    t1, t2 = _sanitize_s4_targets("SHORT", 7560.0, 7553.0, 7545.0)
    assert (t1, t2) == (7553.0, 7545.0)
    assert _validate("SHORT", 7560.0, 7570.0, t1, t2).valid


def test_unsanitized_duplicate_fails_validator_proving_the_incident():
    """Anti-tautological control: WITHOUT the sanitizer, the incident package
    is rejected by the real validator with the exact live message."""
    resp = _validate("SHORT", 7532.0, 7545.25, 7530.625, 7530.625)
    assert not resp.valid
    assert "entry > t1 > t2" in (resp.fail_reason or "")
