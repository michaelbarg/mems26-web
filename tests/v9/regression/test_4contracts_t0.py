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
    # 2026-08-18: neutralise EVERY fixed-size flag. These tests set the one
    # they are about and left the rest to the ambient .env — which now
    # carries FIXED_CONTRACTS_5=1, a HIGHER precedence, so the assertion
    # measured the live ruling instead of the precedence it is testing.
    for _f in ("FIXED_CONTRACTS_5", "FIXED_CONTRACTS_6"):
        monkeypatch.setenv(_f, "0")
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")   # must lose to _4
    monkeypatch.delenv("FIXED_CONTRACTS_2", raising=False)
    monkeypatch.delenv("SIZE_CAP_OVER_FIXED_V1", raising=False)
    assert effective_contracts(dict(SETUP)) == 4


def _pin_ambient(monkeypatch):
    """28.08 (cowork-night, §11): the ambient .env now carries
    FIXED_CONTRACTS_2=1 (today's ruling) + SIZE_CAP_OVER_FIXED_V1=1 (ruled —
    judgment cut min(fixed, cut)). Under a full-env suite run these leak in
    and falsify the tests' premises (4→3 via the cut; _3 loses to ambient _2).
    Pin them OFF here; the ruled interaction itself is pinned separately in
    test_fc4_with_ruled_size_cap_tomorrow_gate."""
    for _f in ("FIXED_CONTRACTS_5", "FIXED_CONTRACTS_6", "FIXED_CONTRACTS_2",
               "SIZE_CAP_OVER_FIXED_V1",
               # F5 (RUNNER_TRAIL_V2, ruled 20.08, postdates these tests):
               # drops the runner leg's target -> t4=None by design. These
               # tests pin the 07-15 T0-ladder shape, so F5 is pinned off.
               "RUNNER_TRAIL_V2"):
        monkeypatch.setenv(_f, "0")


def test_t0_ladder_shift_long(monkeypatch, tmp_path):
    _pin_ambient(monkeypatch)
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
    _pin_ambient(monkeypatch)
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setenv("T0_TARGET_PTS", "3.5")
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    s = {**SETUP, "direction": "SHORT", "t1": 7594.0, "t2": 7588.0, "t3": 7582.0, "stop": 7609.0}
    p = command_from_setup(s, trade_id="t", account="Sim1", mode="demo")
    assert p["target_price"] == 7596.5            # entry−3.5
    assert p["context"]["t4"] == 7582.0


def test_without_flags_3pair_unchanged(monkeypatch, tmp_path):
    _pin_ambient(monkeypatch)
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


def test_fc4_with_ruled_size_cap_tomorrow_gate(monkeypatch, tmp_path):
    """The 28.08 morning-gate scenario AS RULED: FIXED_CONTRACTS_4=1 with
    SIZE_CAP_OVER_FIXED_V1=1 (both will be ON tomorrow) and a setup carrying a
    judgment cut of 3 ⇒ effective size is **3**, not 4 — the cut overrides
    downward (Michael 07-09, 'still overrides downward, even under FIXED').
    The morning gate MUST therefore verify the effective COMMAND size, not
    just ruled_contracts(). A setup with sizing 4 ships the full 4."""
    for _f in ("FIXED_CONTRACTS_5", "FIXED_CONTRACTS_6", "FIXED_CONTRACTS_2"):
        monkeypatch.setenv(_f, "0")
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setenv("SIZE_CAP_OVER_FIXED_V1", "1")
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    cut3 = dict(SETUP)                            # metadata.sizing == 3
    p3 = command_from_setup(cut3, trade_id="t", account="Sim1", mode="demo")
    assert p3["contracts"] == 3, "the ruled judgment cut must win downward"
    full4 = {**SETUP, "metadata": {"sizing": 4}}
    p4 = command_from_setup(full4, trade_id="t", account="Sim1", mode="demo")
    assert p4["contracts"] == 4, "no cut info below 4 — fixed size must ship"


def test_t1setup_schema_accepts_the_ruled_size():
    """S-10 (07-15): le=3 in T1Setup swallowed every live 4c S2 fire silently.
    The cap has since moved with the ruling — 4 (07-15) → 6 (Michael 08-19,
    same failure class: on 18.08 le=4 killed every S2 fire with a silent
    'non-fatal' ValidationError while FIXED_CONTRACTS_5 was set). The schema
    must accept the ruled size and reject one above the cap."""
    import pytest as _pt
    from datetime import datetime, timezone
    from backend.v9.systems.five_min.output_schema import T1Setup
    base = dict(
        pattern_name="REACTIVE_SHORT", direction="SHORT",
        entry_price=7600.0, stop_price=7606.5,
        t1_price=7596.0, t2_price=7592.0, t3_price=7588.0,
        confidence=90, bar_index=10, fired_at=datetime.now(timezone.utc),
    )
    for n in (4, 5, 6):                       # every size up to the 08-19 cap
        assert T1Setup(**base, sizing_contracts=n).sizing_contracts == n
    with _pt.raises(Exception):
        T1Setup(**base, sizing_contracts=7)   # cap still enforced, one above
