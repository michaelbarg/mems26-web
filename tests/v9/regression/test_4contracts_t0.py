"""Michael 07-15: FIXED_CONTRACTS_4 (top precedence) + T0=3.5 ladder shift.
Anti-tautological: same setup yields 3-pair payload without the flags and the
shifted 4-pair payload with them; SHORT mirrors; tick-snap verified."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.services.sierra_command import effective_contracts, command_from_setup  # noqa: E402

SETUP = {"direction": "LONG", "entry_price": 7600.0, "stop": 7591.0,
         "t1": 7606.0, "t2": 7612.0, "t3": 7618.0,
         "classification": "REACTIVE_LONG", "metadata": {"sizing": 3}}


def test_fc4_top_precedence(monkeypatch):
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")   # must lose to _4
    monkeypatch.delenv("FIXED_CONTRACTS_2", raising=False)
    monkeypatch.delenv("SIZE_CAP_OVER_FIXED_V1", raising=False)
    assert effective_contracts(dict(SETUP)) == 4


def test_t0_ladder_shift_long(monkeypatch, tmp_path):
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setenv("T0_TARGET_PTS", "3.5")
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    s = dict(SETUP)
    p = command_from_setup(s, trade_id="t", account="Sim1", mode="demo")
    assert p["contracts"] == 4
    assert p["target_price"] == 7603.5            # C1 = T0 = entry+3.5
    assert p["context"]["t2"] == 7606.0           # C2 = T1
    assert p["context"]["t3"] == 7612.0           # C3 = T2
    assert p["context"]["t4"] == 7618.0           # C4 = T3 (runner)
    assert s["t0"] == 7603.5


def test_t0_short_mirror(monkeypatch, tmp_path):
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setenv("T0_TARGET_PTS", "3.5")
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    s = {**SETUP, "direction": "SHORT", "t1": 7594.0, "t2": 7588.0, "t3": 7582.0, "stop": 7609.0}
    p = command_from_setup(s, trade_id="t", account="Sim1", mode="demo")
    assert p["target_price"] == 7596.5            # entry−3.5
    assert p["context"]["t4"] == 7582.0


def test_without_flags_3pair_unchanged(monkeypatch, tmp_path):
    monkeypatch.delenv("FIXED_CONTRACTS_4", raising=False)
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    monkeypatch.delenv("T0_TARGET_PTS", raising=False)
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    s = dict(SETUP)
    p = command_from_setup(s, trade_id="t", account="Sim1", mode="demo")
    assert p["contracts"] == 3
    assert p["target_price"] == 7606.0            # C1 = T1 (קלאסי)
    assert p["context"]["t4"] is None
    assert "t0" not in s


def test_t1setup_schema_accepts_4_contracts():
    """S-10 (07-15): le=3 in T1Setup swallowed every live 4c S2 fire silently.
    The schema must accept sizing_contracts=4 (and still reject 5)."""
    import pytest as _pt
    from datetime import datetime, timezone
    from backend.v9.systems.five_min.output_schema import T1Setup
    base = dict(
        pattern_name="REACTIVE_SHORT", direction="SHORT",
        entry_price=7600.0, stop_price=7606.5,
        t1_price=7596.0, t2_price=7592.0, t3_price=7588.0,
        confidence=90, bar_index=10, fired_at=datetime.now(timezone.utc),
    )
    s = T1Setup(**base, sizing_contracts=4)   # the 07-15 killer — must validate
    assert s.sizing_contracts == 4
    with _pt.raises(Exception):
        T1Setup(**base, sizing_contracts=5)   # cap still enforced
