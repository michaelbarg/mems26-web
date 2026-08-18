"""C4_RULING6_V1 (Michael ruling 2026-07-21 08:45 + "מאשר 1" 08:56):
the 4th contract's target per day-type when the setup has no T3 price —
rotation days → opposite edge ("הקצה השני") · Variation → None (stop-only,
trails with T3) · Trend → falls back to the shifted C3 target.

Anti-tautological: goes through the REAL command_from_setup path (not a
hand-built quality dict). Also regression-covers the two bugs found in the
first implementation (cc ab8e3807, fixed by cursor 09:45):
  1. NameError: the block referenced `context`, undefined in command_from_setup
     → every 4-contract no-T3 fire would crash at fire time.
  2. Normal_Variation matched startswith("Normal") and was given an
     opposite-edge target instead of the ruling's stop-only mapping.
"""
import importlib

import pytest


@pytest.fixture()
def _env(monkeypatch, tmp_path):
    # 2026-08-18: pin every fixed-size flag, not only the one this suite sets.
    # The ambient .env now carries FIXED_CONTRACTS_5=1 at a higher precedence,
    # so a fixture that sets _4 and leaves _5 alone tests the live ruling.
    for _f in ("FIXED_CONTRACTS_5", "FIXED_CONTRACTS_6"):
        monkeypatch.setenv(_f, "0")
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setenv("T0_TARGET_PTS", "4.0")
    monkeypatch.setenv("C4_RULING6_V1", "1")
    monkeypatch.setenv("SIERRA_CMD_DIR", str(tmp_path))


def _fire(direction: str, day_type: str, t3=None):
    from backend.v9.services.sierra_command import command_from_setup
    short = direction == "SHORT"
    setup = {
        "direction": direction,
        "entry_price": 7500.0,
        "stop": 7510.0 if short else 7490.0,
        "t1": 7494.0 if short else 7506.0,
        "t2": 7488.0 if short else 7512.0,
        "t3": t3,
        "day_type_at_entry": day_type,
        "metadata": {"vah": 7530.0, "val": 7470.0,
                     "ib_high": 7525.0, "ib_low": 7475.0},
        "firing_system": "TEST", "classification": "TEST", "confidence": 75,
    }
    return command_from_setup(setup, trade_id="t", account="SIM", mode="demo")


def test_normal_short_gets_opposite_edge_val(_env):
    cmd = _fire("SHORT", "Normal")
    assert cmd["contracts"] == 4
    assert cmd["context"]["t4"] == 7470.0  # VAL — the opposite edge for a SHORT


def test_normal_long_gets_opposite_edge_vah(_env):
    cmd = _fire("LONG", "Normal")
    assert cmd["context"]["t4"] == 7530.0  # VAH — the opposite edge for a LONG


def test_neutral_gets_opposite_edge(_env):
    cmd = _fire("SHORT", "Neutral_Extreme")
    assert cmd["context"]["t4"] == 7470.0


def test_variation_stays_stop_only(_env):
    """Michael's ruling: Variation C4 trails with T3 → t4 stays None
    (DLL hardening builds Group 4 stop-only). Bug #2 regression."""
    assert _fire("LONG", "Variation")["context"]["t4"] is None
    assert _fire("SHORT", "Normal_Variation")["context"]["t4"] is None


def test_missing_day_type_honest_none(_env):
    """No day_type → no invented target (Rule 1). Stop-only via DLL hardening."""
    assert _fire("SHORT", "")["context"]["t4"] is None


def test_no_name_error_on_no_t3_fire(_env):
    """Bug #1 regression: the first implementation raised NameError (`context`)
    on every no-T3 4-contract fire. The call itself completing IS the assertion."""
    cmd = _fire("SHORT", "Normal")
    assert cmd["op"] == "PLACE"


def test_flag_off_preserves_old_behavior(_env, monkeypatch):
    monkeypatch.setenv("C4_RULING6_V1", "0")
    assert _fire("SHORT", "Normal")["context"]["t4"] is None


def test_existing_t3_wins_over_ruling(_env):
    """A real T3 price (trend day) takes the C4 slot untouched — the ruling
    block only fills the gap when t4 would otherwise be None."""
    cmd = _fire("LONG", "Trend_Normal", t3=7524.0)
    assert cmd["context"]["t4"] == 7524.0
